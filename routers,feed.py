"""
routers/feed.py
MSAFIRI GLOBAL MEDIA — Feed Router
Inatoa /api/feed?type=for-you na /api/feed?type=following
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Post, User, Follow
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["feed"])


@router.get("/feed")
def get_feed(
    type: str = Query("for-you", description="for-you | following"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Rudisha feed ya posts.
    
    - type=for-you : posts zote (zilizopangwa kwa muda)
    - type=following : posts za watu unaowafollow
    """
    query = db.query(Post)

    if type == "following" and current_user:
        following_ids = [
            f.following_id
            for f in db.query(Follow).filter(Follow.follower_id == current_user.id).all()
        ]
        if following_ids:
            query = query.filter(Post.user_id.in_(following_ids))
        else:
            return {"posts": [], "type": type, "total": 0}

    posts = (
        query.order_by(Post.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )

    return {
        "posts": [p.to_dict() if hasattr(p, "to_dict") else p.__dict__ for p in posts],
        "type": type,
        "total": len(posts),
        "limit": limit,
        "offset": offset,
    }
