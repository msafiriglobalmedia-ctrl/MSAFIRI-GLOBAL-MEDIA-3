# ============================================================
# MSAFIRI GLOBAL MEDIA — Messages Router
# Version: Media V0.0.1
# Purpose: Conversations, Messages, Chat media (WhatsApp-style)
# ============================================================

import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import or_, and_, desc

from database import db
from models import User, Conversation, Message
from routers.auth import token_required


# ------------------------------------------------------------
# 1. DEFINE BLUEPRINT
# ------------------------------------------------------------
messages_bp = Blueprint("messages", __name__)


# ------------------------------------------------------------
# 2. CONSTANTS
# ------------------------------------------------------------
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_VIDEO_EXT = {"mp4", "mov", "avi", "webm"}
ALLOWED_AUDIO_EXT = {"webm", "mp3", "wav", "ogg", "m4a"}
ALLOWED_DOC_EXT = {"pdf", "doc", "docx", "txt", "zip"}


def save_chat_file(file, subfolder="messages"):
    """Save a chat file and return (url, media_type)."""
    if not file or file.filename == "":
        return None, None

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""

    if ext in ALLOWED_IMAGE_EXT:
        media_type = "image"
    elif ext in ALLOWED_VIDEO_EXT:
        media_type = "video"
    elif ext in ALLOWED_AUDIO_EXT:
        media_type = "voice"
    elif ext in ALLOWED_DOC_EXT:
        media_type = "document"
    else:
        return None, None

    unique_name = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)

    url = f"/static/uploads/{subfolder}/{unique_name}"
    return url, media_type


# ------------------------------------------------------------
# 3. GET ALL CONVERSATIONS
# ------------------------------------------------------------
@messages_bp.route("/conversations", methods=["GET"])
@token_required
def get_conversations(current_user):
    """Get all conversations of the current user."""
    convos = Conversation.query.filter(
        or_(
            Conversation.user1_id == current_user.id,
            Conversation.user2_id == current_user.id
        )
    ).order_by(desc(Conversation.updated_at)).all()

    return jsonify({
        "count": len(convos),
        "conversations": [c.to_dict(current_user.id) for c in convos]
    }), 200


# ------------------------------------------------------------
# 4. CREATE / GET CONVERSATION
# ------------------------------------------------------------
@messages_bp.route("/conversations", methods=["POST"])
@token_required
def create_conversation(current_user):
    """
    Start a conversation with another user.
    Body: { participant_id: <user_id> }
    If already exists, return existing.
    """
    data = request.get_json(silent=True) or {}
    participant_id = data.get("participant_id") or data.get("user_id")

    if not participant_id:
        return jsonify({"error": "participant_id is required"}), 400

    if participant_id == current_user.id:
        return jsonify({"error": "Cannot create conversation with yourself"}), 400

    other = User.query.get(participant_id)
    if not other:
        return jsonify({"error": "User not found"}), 404

    # Check if conversation exists (either direction)
    user1_id, user2_id = sorted([current_user.id, participant_id])
    convo = Conversation.query.filter_by(
        user1_id=user1_id,
        user2_id=user2_id
    ).first()

    if convo:
        return jsonify({
            "message": "Conversation already exists",
            "conversation_id": convo.id,
            "conversation": convo.to_dict(current_user.id)
        }), 200

    # Create new conversation
    convo = Conversation(
        user1_id=user1_id,
        user2_id=user2_id
    )
    db.session.add(convo)
    db.session.commit()

    return jsonify({
        "message": "Conversation created",
        "conversation_id": convo.id,
        "conversation": convo.to_dict(current_user.id)
    }), 201


# ------------------------------------------------------------
# 5. GET MESSAGES IN CONVERSATION
# ------------------------------------------------------------
@messages_bp.route("/<int:conversation_id>", methods=["GET"])
@token_required
def get_messages(current_user, conversation_id):
    """Get all messages in a conversation."""
    convo = Conversation.query.get(conversation_id)
    if not convo:
        return jsonify({"error": "Conversation not found"}), 404

    # Verify user is part of this conversation
    if current_user.id not in (convo.user1_id, convo.user2_id):
        return jsonify({"error": "Not authorized"}), 403

    page = int(request.args.get("page", 1))
    limit = min(int(request.args.get("limit", 50)), 100)
    offset = (page - 1) * limit

    query = Message.query.filter_by(conversation_id=conversation_id) \
        .order_by(Message.created_at.asc())

    total = query.count()
    messages = query.offset(offset).limit(limit).all()

    # Mark messages as read (those sent to current user)
    unread = Message.query.filter_by(
        conversation_id=conversation_id,
        receiver_id=current_user.id,
        is_read=False
    ).all()
    for msg in unread:
        msg.is_read = True
    if unread:
        db.session.commit()

    return jsonify({
        "conversation_id": conversation_id,
        "page": page,
        "total": total,
        "has_more": offset + len(messages) < total,
        "messages": [m.to_dict(current_user.id) for m in messages]
    }), 200


# ------------------------------------------------------------
# 6. SEND TEXT MESSAGE
# ------------------------------------------------------------
@messages_bp.route("/<int:conversation_id>", methods=["POST"])
@token_required
def send_message(current_user, conversation_id):
    """
    Send a text message.
    Body: { content: "Hello!" }
    """
    convo = Conversation.query.get(conversation_id)
    if not convo:
        return jsonify({"error": "Conversation not found"}), 404

    if current_user.id not in (convo.user1_id, convo.user2_id):
        return jsonify({"error": "Not authorized"}), 403

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()

    if not content:
        return jsonify({"error": "Message content is required"}), 400

    # Determine receiver
    receiver_id = convo.user2_id if convo.user1_id == current_user.id else convo.user1_id

    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=content,
        is_delivered=True
    )
    db.session.add(message)

    # Update conversation
    convo.last_message = content[:255]
    convo.last_message_at = datetime.utcnow()
    convo.updated_at = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "message": "Message sent",
        "data": message.to_dict(current_user.id)
    }), 201


# ------------------------------------------------------------
# 7. SEND MEDIA MESSAGE
# ------------------------------------------------------------
@messages_bp.route("/<int:conversation_id>/media", methods=["POST"])
@token_required
def send_media_message(current_user, conversation_id):
    """
    Send a media message (image/video/voice/document).
    Accepts: multipart/form-data
    Fields: media (file), type (optional)
    """
    convo = Conversation.query.get(conversation_id)
    if not convo:
        return jsonify({"error": "Conversation not found"}), 404

    if current_user.id not in (convo.user1_id, convo.user2_id):
        return jsonify({"error": "Not authorized"}), 403

    if "media" not in request.files:
        return jsonify({"error": "No media file provided"}), 400

    file = request.files["media"]
    url, media_type = save_chat_file(file)

    if not url:
        return jsonify({"error": "Unsupported file type"}), 400

    receiver_id = convo.user2_id if convo.user1_id == current_user.id else convo.user1_id

    # Default content per media type
    default_content = {
        "image": "📷 Photo",
        "video": "🎥 Video",
        "voice": "🎤 Voice message",
        "document": "📎 Document"
    }.get(media_type, "Media")

    message = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        receiver_id=receiver_id,
        content=request.form.get("content", default_content),
        media_url=url,
        media_type=media_type,
        is_delivered=True
    )
    db.session.add(message)

    convo.last_message = default_content
    convo.last_message_at = datetime.utcnow()
    convo.updated_at = datetime.utcnow()
    db.session.commit()

    return jsonify({
        "message": "Media sent",
        "data": message.to_dict(current_user.id)
    }), 201


# ------------------------------------------------------------
# 8. MARK MESSAGES AS READ
# ------------------------------------------------------------
@messages_bp.route("/<int:conversation_id>/read", methods=["POST"])
@token_required
def mark_read(current_user, conversation_id):
    """Mark all messages in conversation as read."""
    convo = Conversation.query.get(conversation_id)
    if not convo:
        return jsonify({"error": "Conversation not found"}), 404

    if current_user.id not in (convo.user1_id, convo.user2_id):
        return jsonify({"error": "Not authorized"}), 403

    unread = Message.query.filter_by(
        conversation_id=conversation_id,
        receiver_id=current_user.id,
        is_read=False
    ).all()

    for msg in unread:
        msg.is_read = True
    db.session.commit()

    return jsonify({
        "message": f"Marked {len(unread)} messages as read"
    }), 200


# ------------------------------------------------------------
# 9. DELETE MESSAGE
# ------------------------------------------------------------
@messages_bp.route("/message/<int:message_id>", methods=["DELETE"])
@token_required
def delete_message(current_user, message_id):
    """Delete a message (sender only)."""
    message = Message.query.get(message_id)
    if not message:
        return jsonify({"error": "Message not found"}), 404

    if message.sender_id != current_user.id:
        return jsonify({"error": "Not authorized"}), 403

    db.session.delete(message)
    db.session.commit()

    return jsonify({"message": "Message deleted"}), 200


# ------------------------------------------------------------
# 10. DELETE CONVERSATION
# ------------------------------------------------------------
@messages_bp.route("/<int:conversation_id>", methods=["DELETE"])
@token_required
def delete_conversation(current_user, conversation_id):
    """Delete a whole conversation (both users)."""
    convo = Conversation.query.get(conversation_id)
    if not convo:
        return jsonify({"error": "Conversation not found"}), 404

    if current_user.id not in (convo.user1_id, convo.user2_id):
        return jsonify({"error": "Not authorized"}), 403

    db.session.delete(convo)
    db.session.commit()

    return jsonify({"message": "Conversation deleted"}), 200


# ------------------------------------------------------------
# 11. UNREAD COUNT (Total)
# ------------------------------------------------------------
@messages_bp.route("/unread-count", methods=["GET"])
@token_required
def unread_count(current_user):
    """Get total unread messages for current user."""
    count = Message.query.filter_by(
        receiver_id=current_user.id,
        is_read=False
    ).count()

    return jsonify({"unread_count": count}), 200


# ------------------------------------------------------------
# 12. EXPORTS
# ------------------------------------------------------------
__all__ = ["messages_bp"]
