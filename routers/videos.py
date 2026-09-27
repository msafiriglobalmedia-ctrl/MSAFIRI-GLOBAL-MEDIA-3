# ============================================================
# MSAFIRI GLOBAL MEDIA — Videos Router
# Version: Media V0.0.1
# Purpose: TikTok-style video feed (upload, view, like, comment)
# ============================================================

import os
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import desc

from database import db
from models import User, Video, Follow
from routers.auth import token_required


# ------------------------------------------------------------
# 1. DEFINE BLUEPRINT
# ------------------------------------------------------------
videos_bp = Blueprint("videos", __name__)


# ------------------------------------------------------------
# 2. CONSTANTS
# ------------------------------------------------------------
ALLOWED_VIDEO_EXT = {"mp4", "mov", "avi", "webm", "mkv"}
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


# ------------------------------------------------------------
# 3. FILE UPLOAD HELPERS
# ------------------------------------------------------------
def save_video_file(file, subfolder="videos"):
    """Save a video file and return its public URL."""
    if not file or file.filename == "":
        return None

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""

    if ext not in ALLOWED_VIDEO_EXT:
        return None

    unique_name = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)

    return f"/static/uploads/{subfolder}/{unique_name}"


def save_thumbnail_file(file):
    """Save a thumbnail image and return its public URL."""
    if not file or file.filename == "":
        return None

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""

    if ext not in ALLOWED_IMAGE_EXT:
        return None

    unique_name = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "videos", "thumbnails")
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)

    return f"/static/uploads/videos/thumbnails/{unique_name}"


# ------------------------------------------------------------
# 4. GET VIDEO FEED
# ------------------------------------------------------------
@videos_bp.route("", methods=["GET"])
@videos_bp.route("/", methods=["GET"])
@token_required
def get_videos(current_user):
    """
    Get the video feed (TikTok-style).
    Query params:
        ?tab=foryou (default) | following
        ?page=1
        ?limit=10
    """
    tab = request.args.get("tab", "foryou").lower()
    page = int(request.args.get("page", 1))
    limit = min(int(request.args.get("limit", 10)), 30)
    offset = (page - 1) * limit

    query = Video.query

    if tab == "following":
        following_ids = [
            f.following_id
            for f in Follow.query.filter_by(follower_id=current_user.id).all()
        ]
        following_ids.append(current_user.id)
        query = query.filter(Video.user_id.in_(following_ids))

    query = query.order_by(desc(Video.created_at))

    total = query.count()
    videos = query.offset(offset).limit(limit).all()

    return jsonify({
        "tab": tab,
        "page": page,
        "limit": limit,
        "total": total,
        "has_more": offset + len(videos) < total,
        "videos": [v.to_dict() for v in videos]
    }), 200


# ------------------------------------------------------------
# 5. GET SINGLE VIDEO
# ------------------------------------------------------------
@videos_bp.route("/<int:video_id>", methods=["GET"])
@token_required
def get_video(current_user, video_id):
    """Get a single video by ID."""
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    return jsonify({"video": video.to_dict()}), 200


# ------------------------------------------------------------
# 6. UPLOAD VIDEO
# ------------------------------------------------------------
@videos_bp.route("/upload", methods=["POST"])
@videos_bp.route("", methods=["POST"])
@videos_bp.route("/", methods=["POST"])
@token_required
def upload_video(current_user):
    """
    Upload a new video.
    Accepts: multipart/form-data
    Fields:
        - video (file, required)
        - thumbnail (file, optional)
        - caption (optional)
        - music (optional)
    """
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    video_file = request.files["video"]
    video_url = save_video_file(video_file)

    if not video_url:
        return jsonify({
            "error": f"Unsupported video type. Allowed: {', '.join(ALLOWED_VIDEO_EXT)}"
        }), 400

    thumbnail_url = None
    if "thumbnail" in request.files:
        thumbnail_url = save_thumbnail_file(request.files["thumbnail"])

    caption = (request.form.get("caption") or "").strip()
    music = (request.form.get("music") or "").strip()

    video = Video(
        user_id=current_user.id,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
        caption=caption or None,
        music=music or None
    )

    db.session.add(video)
    db.session.commit()

    return jsonify({
        "message": "Video uploaded successfully",
        "video": video.to_dict()
    }), 201


# ------------------------------------------------------------
# 7. DELETE VIDEO
# ------------------------------------------------------------
@videos_bp.route("/<int:video_id>", methods=["DELETE"])
@token_required
def delete_video(current_user, video_id):
    """Delete a video (owner or admin only)."""
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    if video.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"error": "Not authorized"}), 403

    # Delete files (optional)
    for url_attr in ["video_url", "thumbnail_url"]:
        url = getattr(video, url_attr)
        if url and url.startswith("/static/uploads/"):
            try:
                old_path = os.path.join(current_app.root_path, url.lstrip("/"))
                if os.path.exists(old_path):
                    os.remove(old_path)
            except Exception:
                pass

    db.session.delete(video)
    db.session.commit()

    return jsonify({"message": "Video deleted"}), 200


# ------------------------------------------------------------
# 8. LIKE VIDEO (Toggle)
# ------------------------------------------------------------
@videos_bp.route("/<int:video_id>/like", methods=["POST"])
@token_required
def like_video(current_user, video_id):
    """
    Like a video.
    Note: We use a simple counter for now.
    Future: Create VideoLike model for tracking.
    """
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    # Simple toggle logic (needs VideoLike model for full tracking)
    # For now, just increment/decrement counter
    data = request.get_json(silent=True) or {}
    action = data.get("action", "like")

    if action == "unlike":
        video.likes_count = max(0, video.likes_count - 1)
        liked = False
    else:
        video.likes_count += 1
        liked = True

    db.session.commit()

    return jsonify({
        "liked": liked,
        "likes_count": video.likes_count
    }), 200


# ------------------------------------------------------------
# 9. SHARE VIDEO
# ------------------------------------------------------------
@videos_bp.route("/<int:video_id>/share", methods=["POST"])
@token_required
def share_video(current_user, video_id):
    """Increment share count."""
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    video.shares_count += 1
    db.session.commit()

    return jsonify({
        "message": "Video shared",
        "shares_count": video.shares_count
    }), 200


# ------------------------------------------------------------
# 10. VIEW VIDEO (Increment views)
# ------------------------------------------------------------
@videos_bp.route("/<int:video_id>/view", methods=["POST"])
@token_required
def view_video(current_user, video_id):
    """Increment view count for a video."""
    video = Video.query.get(video_id)
    if not video:
        return jsonify({"error": "Video not found"}), 404

    # Don't increment if owner
    if video.user_id != current_user.id:
        video.views_count += 1
        db.session.commit()

    return jsonify({
        "views_count": video.views_count
    }), 200


# ------------------------------------------------------------
# 11. MY VIDEOS
# ------------------------------------------------------------
@videos_bp.route("/my-videos", methods=["GET"])
@token_required
def my_videos(current_user):
    """Get current user's own videos."""
    page = int(request.args.get("page", 1))
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = (page - 1) * limit

    query = Video.query.filter_by(user_id=current_user.id) \
        .order_by(desc(Video.created_at))

    total = query.count()
    videos = query.offset(offset).limit(limit).all()

    return jsonify({
        "page": page,
        "total": total,
        "has_more": offset + len(videos) < total,
        "videos": [v.to_dict() for v in videos]
    }), 200


# ------------------------------------------------------------
# 12. USER VIDEOS
# ------------------------------------------------------------
@videos_bp.route("/user/<int:user_id>", methods=["GET"])
@token_required
def user_videos(current_user, user_id):
    """Get videos by a specific user."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    page = int(request.args.get("page", 1))
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = (page - 1) * limit

    query = Video.query.filter_by(user_id=user_id) \
        .order_by(desc(Video.created_at))

    total = query.count()
    videos = query.offset(offset).limit(limit).all()

    return jsonify({
        "user": user.to_dict(),
        "page": page,
        "total": total,
        "has_more": offset + len(videos) < total,
        "videos": [v.to_dict() for v in videos]
    }), 200


# ------------------------------------------------------------
# 13. TRENDING VIDEOS
# ------------------------------------------------------------
@videos_bp.route("/trending", methods=["GET"])
@token_required
def trending_videos(current_user):
    """Get trending videos (most viewed)."""
    limit = min(int(request.args.get("limit", 20)), 50)

    videos = Video.query \
        .order_by(desc(Video.views_count), desc(Video.likes_count)) \
        .limit(limit) \
        .all()

    return jsonify({
        "videos": [v.to_dict() for v in videos]
    }), 200


# ------------------------------------------------------------
# 14. EXPORTS
# ------------------------------------------------------------
__all__ = ["videos_bp"]
