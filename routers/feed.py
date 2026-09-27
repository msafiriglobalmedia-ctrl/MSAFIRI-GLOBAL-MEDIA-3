from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Post, User
from auth import get_current_user


router = APIRouter(
    prefix="/api/feed",
    tags=["feed"]
)


@router.get("")
def get_feed(
    type: str = Query(
        "for-you",
        pattern="^(for-you|following)$"
    ),
    limit: int = Query(
        30,
        ge=1,
        le=100
    ),
    offset: int = Query(
        0,
        ge=0
    ),
    db: Session = Depends(get_db),
    user: User | None = Depends(get_current_user),
):
    query = (
        db.query(Post)
        .options(
            joinedload(Post.user),
            joinedload(Post.likes),
            joinedload(Post.comments),
            joinedload(Post.saves),
            joinedload(Post.shares),
        )
        .order_by(
            Post.created_at.desc()
        )
    )

    # --------------------------------------------------------
    # FOLLOWING
    # --------------------------------------------------------

    if type == "following" and user:

        following_ids = [
            row.following_id
            for row in user.following
        ] if hasattr(user, "following") else []

        if following_ids:
            query = query.filter(
                Post.user_id.in_(
                    following_ids
                )
            )
        else:
            query = query.filter(
                Post.user_id == user.id
            )

    posts = (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )

    current_user_id = (
        user.id
        if user
        else None
    )

    return {
        "type": type,
        "posts": [
            post.to_dict(
                current_user_id
            )
            for post in posts
        ],
        "count": len(posts),
        "offset": offset,
        "limit": limit,
    }
