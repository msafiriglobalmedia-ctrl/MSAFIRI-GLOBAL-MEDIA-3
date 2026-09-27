# ============================================================
# MSAFIRI GLOBAL MEDIA — Profile Router
# Version: Media V0.0.1
# Purpose: Profile, Upload Pic, Edit, Search Users, Follow
# ============================================================

import os
import uuid
from werkzeug.utils import secure_filename

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import or_, desc

from database import db
from models import User, Post, Follow
from routers.auth import token_required


# ------------------------------------------------------------
# 1. DEFINE BLUEPRINT
# ------------------------------------------------------------
profile_bp = Blueprint("profile", __name__)


# ------------------------------------------------------------
# 2. CONSTANTS
# ------------------------------------------------------------
ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "gif", "webp"}


# ------------------------------------------------------------
# 3. FILE UPLOAD HELPER
# ------------------------------------------------------------
def save_profile_image(file):
    """Save a profile/cover image and return its public URL."""
    if not file or file.filename == "":
        return None

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""

    if ext not in ALLOWED_IMAGE_EXT:
        return None

    unique_name = f"{uuid.uuid4().hex}.{ext}"
    upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], "profiles")
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)

    return f"/static/uploads/profiles/{unique_name}"


# ------------------------------------------------------------
# 4. GET MY PROFILE
# ------------------------------------------------------------
@profile_bp.route("/me", methods=["GET"])
@token_required
def get_my_profile(current_user):
    """Get the current user's own profile."""
    return jsonify({
        "user": current_user.to_dict(include_email=True)
    }), 200


# ------------------------------------------------------------
# 5. GET USER PROFILE BY ID
# ------------------------------------------------------------
@profile_bp.route("/<int:user_id>", methods=["GET"])
@token_required
def get_user_profile(current_user, user_id):
    """Get a specific user's profile."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Check if current user follows this user
    is_following = Follow.query.filter_by(
        follower_id=current_user.id,
        following_id=user_id
    ).first() is not None

    data = user.to_dict()
    data["is_following"] = is_following

    return jsonify({"user": data}), 200


# ------------------------------------------------------------
# 6. UPDATE PROFILE
# ------------------------------------------------------------
@profile_bp.route("/update", methods=["PUT", "POST"])
@token_required
def update_profile(current_user):
    """
    Update current user's profile.
    Accepts JSON or form-data.
    Fields: name, bio, location, phone
    """
    if request.is_json:
        data = request.get_json(silent=True) or {}
    else:
        data = request.form.to_dict()

    # Update fields if provided
    if "name" in data and data["name"]:
        current_user.name = data["name"].strip()[:100]
    if "bio" in data:
        current_user.bio = (data["bio"] or "").strip()[:500]
    if "location" in data:
        current_user.location = (data["location"] or "").strip()[:100]
    if "phone" in data:
        current_user.phone = (data["phone"] or "").strip()[:20]

    db.session.commit()

    return jsonify({
        "message": "Profile updated successfully",
        "user": current_user.to_dict(include_email=True)
    }), 200


# ------------------------------------------------------------
# 7. UPLOAD PROFILE PICTURE
# ------------------------------------------------------------
@profile_bp.route("/upload_pic", methods=["POST"])
@profile_bp.route("/upload-pic", methods=["POST"])
@token_required
def upload_profile_pic(current_user):
    """
    Upload profile picture.
    Accepts: multipart/form-data
    Field: profile_pic (file)
    """
    if "profile_pic" not in request.files:
        return jsonify({"error": "No file provided. Use 'profile_pic' field."}), 400

    file = request.files["profile_pic"]
    url = save_profile_image(file)

    if not url:
        return jsonify({"error": "Invalid image. Allowed: png, jpg, jpeg, gif, webp"}), 400

    # Delete old profile pic (optional)
    if current_user.profile_pic and current_user.profile_pic.startswith("/static/uploads/"):
        old_path = os.path.join(
            current_app.root_path,
            current_user.profile_pic.lstrip("/")
        )
        try:
            if os.path.exists(old_path):
                os.remove(old_path)
        except Exception:
            pass

    current_user.profile_pic = url
    db.session.commit()

    return jsonify({
        "message": "Profile picture updated",
        "profile_pic": url,
        "user": current_user.to_dict(include_email=True)
    }), 200


# ------------------------------------------------------------
# 8. UPLOAD COVER PICTURE
# ------------------------------------------------------------
@profile_bp.route("/upload_cover", methods=["POST"])
@profile_bp.route("/upload-cover", methods=["POST"])
@token_required
def upload_cover_pic(current_user):
    """Upload cover picture."""
    if "cover_pic" not in request.files:
        return jsonify({"error": "No file provided. Use 'cover_pic' field."}), 400

    file = request.files["cover_pic"]
    url = save_profile_image(file)

    if not url:
        return jsonify({"error": "Invalid image"}), 400

    current_user.cover_pic = url
    db.session.commit()

    return jsonify({
        "message": "Cover picture updated",
        "cover_pic": url
    }), 200


# ------------------------------------------------------------
# 9. SEARCH USERS
# ------------------------------------------------------------
@profile_bp.route("/search", methods=["GET"])
@token_required
def search_users(current_user):
    """
    Search users by username, name, or email.
    Query params:
        ?q=searchterm
        ?limit=20
    """
    query = (request.args.get("q") or "").strip()
    limit = min(int(request.args.get("limit", 20)), 50)

    if not query or len(query) < 2:
        return jsonify({
            "users": [],
            "count": 0,
            "message": "Query must be at least 2 characters"
        }), 200

    search_pattern = f"%{query}%"

    users = User.query.filter(
        User.is_active == True,
        or_(
            User.username.ilike(search_pattern),
            User.name.ilike(search_pattern),
            User.email.ilike(search_pattern)
        )
    ).limit(limit).all()

    return jsonify({
        "query": query,
        "count": len(users),
        "users": [u.to_dict() for u in users]
    }), 200


# ------------------------------------------------------------
# 10. FOLLOW / UNFOLLOW
# ------------------------------------------------------------
@profile_bp.route("/<int:user_id>/follow", methods=["POST"])
@token_required
def toggle_follow(current_user, user_id):
    """Follow or unfollow a user (toggle)."""
    if user_id == current_user.id:
        return jsonify({"error": "You cannot follow yourself"}), 400

    target = User.query.get(user_id)
    if not target:
        return jsonify({"error": "User not found"}), 404

    existing = Follow.query.filter_by(
        follower_id=current_user.id,
        following_id=user_id
    ).first()

    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({
            "following": False,
            "message": f"Unfollowed {target.username}"
        }), 200
    else:
        follow = Follow(follower_id=current_user.id, following_id=user_id)
        db.session.add(follow)
        db.session.commit()
        return jsonify({
            "following": True,
            "message": f"Now following {target.username}"
        }), 201


# ------------------------------------------------------------
# 11. FOLLOWERS / FOLLOWING LISTS
# ------------------------------------------------------------
@profile_bp.route("/<int:user_id>/followers", methods=["GET"])
@token_required
def get_followers(current_user, user_id):
    """Get list of users who follow this user."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    follows = Follow.query.filter_by(following_id=user_id).all()
    followers = [f.follower.to_dict() for f in follows if f.follower]

    return jsonify({
        "count": len(followers),
        "followers": followers
    }), 200


@profile_bp.route("/<int:user_id>/following", methods=["GET"])
@token_required
def get_following(current_user, user_id):
    """Get list of users this user is following."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    follows = Follow.query.filter_by(follower_id=user_id).all()
    following = [f.following.to_dict() for f in follows if f.following]

    return jsonify({
        "count": len(following),
        "following": following
    }), 200


# ------------------------------------------------------------
# 12. GET USER POSTS
# ------------------------------------------------------------
@profile_bp.route("/<int:user_id>/posts", methods=["GET"])
@token_required
def get_user_posts(current_user, user_id):
    """Get posts by a specific user."""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    page = int(request.args.get("page", 1))
    limit = min(int(request.args.get("limit", 20)), 50)
    offset = (page - 1) * limit

    query = Post.query.filter_by(user_id=user_id, is_public=True) \
        .order_by(desc(Post.created_at))

    total = query.count()
    posts = query.offset(offset).limit(limit).all()

    return jsonify({
        "user": user.to_dict(),
        "page": page,
        "total": total,
        "has_more": offset + len(posts) < total,
        "posts": [p.to_dict() for p in posts]
    }), 200


# ------------------------------------------------------------
# 13. DELETE ACCOUNT (Soft delete)
# ------------------------------------------------------------
@profile_bp.route("/delete-account", methods=["DELETE"])
@token_required
def delete_account(current_user):
    """
    Deactivate (soft delete) current user's account.
    """
    current_user.is_active = False
    db.session.commit()

    return jsonify({
        "message": "Account deactivated. Contact support to reactivate."
    }), 200


# ------------------------------------------------------------
# 14. EXPORTS
# ------------------------------------------------------------
__all__ = ["profile_bp"]
