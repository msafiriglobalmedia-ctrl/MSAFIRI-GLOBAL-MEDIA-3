# ============================================================
# MSAFIRI GLOBAL MEDIA — Posts Router
# Version: Media V0.0.1
# Purpose: Create, Read, Update, Delete Posts + Likes + Comments
# ============================================================

import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import desc

from database import db
from models import User, Post, Like, Comment
from routers.auth import token_required


# ------------------------------------------------------------
# 1. DEFINE BLUEPRINT
# ------------------------------------------------------------
posts_bp = Blueprint("posts", __name__)


# ------------------------------------------------------------
# 2. FILE UPLOAD HELPER
# ------------------------------------------------------------
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_VIDEO_EXT = {"mp4", "mov", "avi", "webm"}
ALLOWED_FILE_EXT = {"pdf", "doc", "docx", "txt", "zip"}


def allowed_file(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set


def save_uploaded_file(file, subfolder="posts"):
    """Save an uploaded file and return its public URL path."""
    if not file or file.filename == "":
        return None

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
    unique_name = f"{uuid.uuid4().hex}.{ext}"

    upload_dir = os.path.join(
        current_app.config["UPLOAD_FOLDER"],
        subfolder
    )
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)

    # Return public URL
    return f"/static/uploads/{subfolder}/{unique_name}"


# ------------------------------------------------------------
# 3. CREATE POST
# ------------------------------------------------------------
@posts_bp.route("", methods=["POST"])
@posts_bp.route("/", methods=["POST"])
@token_required
def create_post(current_user):
    """
    Create a new post.
    Accepts: multipart/form-data OR application/json
    Fields:
        - content (optional, text)
        - media (optional, file — image/video)
        - file (optional, file — document)
        - is_public (optional, bool)
    """
    content = ""
    media_url = None
    media_type = None
    is_public = True

    # Handle JSON body
    if request.is_json:
        data = request.get_json(silent=True) or {}
        content = (data.get("content") or data.get("caption") or "").strip()
        media_url = data.get("media_url")
        media_type = data.get("media_type")
        is_public = data.get("is_public", True)

    # Handle form-data (file uploads)
    else:
        content = (request.form.get("content") or request.form.get("caption") or "").strip()
        is_public = request.form.get("is_public", "true").lower() != "false"

        # Media (image/video)
        if "media" in request.files:
            file = request.files["media"]
            if file and file.filename:
                ext = file.filename.rsplit(".", 1)[1].lower() if "." in file.filename else ""
                if ext in ALLOWED_IMAGE_EXT:
                    media_url = save_uploaded_file(file, "posts")
                    media_type = "image"
                elif ext in ALLOWED_VIDEO_EXT:
                    media_url = save_uploaded_file(file, "posts")
                    media_type = "video"
                else:
                    return jsonify({"error": "Unsupported media type"}), 400

        # Document file
        if not media_url and "file" in request.files:
            file = request.files["file"]
            if file and file.filename:
                if allowed_file(file.filename, ALLOWED_FILE_EXT):
                    media_url = save_uploaded_file(file, "posts")
                    media_type = "file"
                else:
                    return jsonify({"error": "Unsupported file type"}), 400

    if not content and not media_url:
        return jsonify({"error": "Post must have content or media"}), 400

    # Create post
    post = Post(
        user_id=current_user.id,
        content=content,
        media_url=media_url,
        media_type=media_type,
        is_public=is_public
    )

    db.session.add(post)
    db.session.commit()

    return jsonify({
        "message": "Post created successfully",
        "post": post.to_dict()
    }), 201


# ------------------------------------------------------------
# 4. GET SINGLE POST
# ------------------------------------------------------------
@posts_bp.route("/<int:post_id>", methods=["GET"])
@token_required
def get_post(current_user, post_id):
    """Get a single post by ID."""
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    if not post.is_public and post.user_id != current_user.id:
        return jsonify({"error": "Post is private"}), 403

    return jsonify({"post": post.to_dict()}), 200


# ------------------------------------------------------------
# 5. DELETE POST
# ------------------------------------------------------------
@posts_bp.route("/<int:post_id>", methods=["DELETE"])
@token_required
def delete_post(current_user, post_id):
    """Delete a post (only owner or admin)."""
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    if post.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Not authorized to delete this post"}), 403

    db.session.delete(post)
    db.session.commit()

    return jsonify({"message": "Post deleted successfully"}), 200


# ------------------------------------------------------------
# 6. UPDATE POST
# ------------------------------------------------------------
@posts_bp.route("/<int:post_id>", methods=["PUT"])
@token_required
def update_post(current_user, post_id):
    """Update post content (only owner)."""
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    if post.user_id != current_user.id:
        return jsonify({"error": "Not authorized"}), 403

    data = request.get_json(silent=True) or {}
    content = data.get("content")
    if content is not None:
        post.content = content.strip()
    if "is_public" in data:
        post.is_public = bool(data["is_public"])

    db.session.commit()

    return jsonify({
        "message": "Post updated",
        "post": post.to_dict()
    }), 200


# ------------------------------------------------------------
# 7. LIKE / UNLIKE POST
# ------------------------------------------------------------
@posts_bp.route("/<int:post_id>/like", methods=["POST"])
@token_required
def toggle_like(current_user, post_id):
    """Like or unlike a post (toggle)."""
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    existing = Like.query.filter_by(user_id=current_user.id, post_id=post_id).first()

    if existing:
        db.session.delete(existing)
        post.likes_count = max(0, post.likes_count - 1)
        liked = False
    else:
        like = Like(user_id=current_user.id, post_id=post_id)
        db.session.add(like)
        post.likes_count += 1
        liked = True

    db.session.commit()

    return jsonify({
        "liked": liked,
        "likes_count": post.likes_count
    }), 200


# ------------------------------------------------------------
# 8. GET LIKES OF A POST
# ------------------------------------------------------------
@posts_bp.route("/<int:post_id>/likes", methods=["GET"])
@token_required
def get_likes(current_user, post_id):
    """Get all users who liked this post."""
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    likes = Like.query.filter_by(post_id=post_id).all()
    users = [like.user.to_dict() for like in likes if like.user]

    return jsonify({
        "count": len(users),
        "users": users
    }), 200


# ------------------------------------------------------------
# 9. COMMENT ON POST
# ------------------------------------------------------------
@posts_bp.route("/<int:post_id>/comment", methods=["POST"])
@token_required
def add_comment(current_user, post_id):
    """Add a comment to a post."""
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    data = request.get_json(silent=True) or {}
    content = (data.get("content") or "").strip()

    if not content:
        return jsonify({"error": "Comment content is required"}), 400

    comment = Comment(
        user_id=current_user.id,
        post_id=post_id,
        content=content
    )
    db.session.add(comment)
    post.comments_count += 1
    db.session.commit()

    return jsonify({
        "message": "Comment added",
        "comment": comment.to_dict()
    }), 201


# ------------------------------------------------------------
# 10. GET COMMENTS
# ------------------------------------------------------------
@posts_bp.route("/<int:post_id>/comments", methods=["GET"])
@token_required
def get_comments(current_user, post_id):
    """Get all comments of a post."""
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    comments = Comment.query.filter_by(post_id=post_id) \
        .order_by(desc(Comment.created_at)) \
        .all()

    return jsonify({
        "count": len(comments),
        "comments": [c.to_dict() for c in comments]
    }), 200


# ------------------------------------------------------------
# 11. DELETE COMMENT
# ------------------------------------------------------------
@posts_bp.route("/comments/<int:comment_id>", methods=["DELETE"])
@token_required
def delete_comment(current_user, comment_id):
    """Delete a comment (owner or admin)."""
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({"error": "Comment not found"}), 404

    if comment.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Not authorized"}), 403

    # Decrement comments_count
    post = comment.post
    if post:
        post.comments_count = max(0, post.comments_count - 1)

    db.session.delete(comment)
    db.session.commit()

    return jsonify({"message": "Comment deleted"}), 200


# ------------------------------------------------------------
# 12. SHARE POST (Increment share count)
# ------------------------------------------------------------
@posts_bp.route("/<int:post_id>/share", methods=["POST"])
@token_required
def share_post(current_user, post_id):
    """Increment share count of a post."""
    post = Post.query.get(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404

    post.shares_count += 1
    db.session.commit()

    return jsonify({
        "message": "Post shared",
        "shares_count": post.shares_count
    }), 200


# ------------------------------------------------------------
# 13. MY POSTS
# ------------------------------------------------------------
@posts_bp.route("/my-posts", methods=["GET"])
@token_required
def my_posts(current_user):
    """Get current user's own posts."""
    page = int(request.args.get("page", 1))
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = (page - 1) * limit

    query = Post.query.filter_by(user_id=current_user.id) \
        .order_by(desc(Post.created_at))

    total = query.count()
    posts = query.offset(offset).limit(limit).all()

    return jsonify({
        "page": page,
        "total": total,
        "has_more": offset + len(posts) < total,
        "posts": [p.to_dict() for p in posts]
    }), 200


# ------------------------------------------------------------
# 14. EXPORTS
# ------------------------------------------------------------
__all__ = ["posts_bp"]
