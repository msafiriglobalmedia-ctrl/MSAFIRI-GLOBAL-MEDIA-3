# ============================================================
# MSAFIRI GLOBAL MEDIA — Feed Router
# Version: Media V0.0.1
# Purpose: Home feed (posts from all users + following)
# ============================================================

from flask import Blueprint, request, jsonify
from sqlalchemy import desc

from database import db
from models import User, Post, Follow, Like
from routers.auth import token_required


# ------------------------------------------------------------
# 1. DEFINE BLUEPRINT
# ------------------------------------------------------------
feed_bp = Blueprint("feed", __name__)


# ------------------------------------------------------------
# 2. MAIN FEED ENDPOINT
# ------------------------------------------------------------
@feed_bp.route("", methods=["GET"])
@feed_bp.route("/", methods=["GET"])
@token_required
def get_feed(current_user):
    """
    Get the home feed.
    Query params:
        ?tab=foryou (default) | following
        ?page=1
        ?limit=20
    """
    tab = request.args.get("tab", "foryou").lower()
    page = int(request.args.get("page", 1))
    limit = min(int(request.args.get("limit", 20)), 50)  # Max 50
    offset = (page - 1) * limit

    # Base query — only public posts
    query = Post.query.filter_by(is_public=True)

    # For "Following" tab — only posts from followed users
    if tab == "following":
        following_ids = [
            f.following_id
            for f in Follow.query.filter_by(follower_id=current_user.id).all()
        ]
        # Include current user's own posts
        following_ids.append(current_user.id)
        query = query.filter(Post.user_id.in_(following_ids))

    # Order by newest first
    query = query.order_by(desc(Post.created_at))

    # Paginate
    total = query.count()
    posts = query.offset(offset).limit(limit).all()

    # Build response
    return jsonify({
        "tab": tab,
        "page": page,
        "limit": limit,
        "total": total,
        "has_more": offset + len(posts) < total,
        "posts": [post.to_dict() for post in posts]
    }), 200


# ------------------------------------------------------------
# 3. FEED STATS (Optional)
# ------------------------------------------------------------
@feed_bp.route("/stats", methods=["GET"])
@token_required
def feed_stats(current_user):
    """
    Get feed statistics for the current user.
    """
    following_count = Follow.query.filter_by(follower_id=current_user.id).count()
    total_posts = Post.query.filter_by(is_public=True).count()

    return jsonify({
        "total_posts": total_posts,
        "following_count": following_count,
        "user_posts_count": Post.query.filter_by(user_id=current_user.id).count()
    }), 200


# ------------------------------------------------------------
# 4. TRENDING POSTS (For Discovery)
# ------------------------------------------------------------
@feed_bp.route("/trending", methods=["GET"])
@token_required
def trending_posts(current_user):
    """
    Get trending posts (most liked in recent time).
    Query params:
        ?limit=20
    """
    limit = min(int(request.args.get("limit", 20)), 50)

    # For now, order by likes_count (simplified)
    # In future, we can add time-based weighting
    posts = Post.query.filter_by(is_public=True) \
        .order_by(desc(Post.likes_count), desc(Post.created_at)) \
        .limit(limit) \
        .all()

    return jsonify({
        "posts": [post.to_dict() for post in posts]
    }), 200


# ------------------------------------------------------------
# 5. USER FEED (Posts by a specific user)
# ------------------------------------------------------------
@feed_bp.route("/user/<int:user_id>", methods=["GET"])
@token_required
def user_feed(current_user, user_id):
    """
    Get posts from a specific user.
    Query params:
        ?page=1
        ?limit=20
    """
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
        "posts": [post.to_dict() for post in posts]
    }), 200


# ------------------------------------------------------------
# 6. EXPORTS
# ------------------------------------------------------------
__all__ = ["feed_bp"]
