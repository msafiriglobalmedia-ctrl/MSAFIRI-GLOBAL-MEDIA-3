import os
import uuid
import shutil
from typing import Optional
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
)

from sqlalchemy.orm import Session

from database import get_db
from models import (
    User,
    Post,
    Comment,
    PostLike,
    PostSave,
    PostShare,
)
from auth import require_user


router = APIRouter(
    prefix="/api/posts",
    tags=["posts"]
)

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def serialize_comment(comment):
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "user_id": comment.user_id,
        "username": (
            comment.user.username
            if comment.user else "User"
        ),
        "full_name": (
            comment.user.full_name
            if comment.user else "User"
        ),
        "text": comment.text,
        "created_at": (
            comment.created_at.isoformat()
            if comment.created_at else None
        ),
    }


# ============================================================
# CREATE POST
# ============================================================

@router.post("")
async def create_post(
    caption: str = Form(""),
    media: Optional[UploadFile] = File(None),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):

    caption = caption.strip()

    media_url = ""
    media_type = "text"

    if media and media.filename:

        extension = os.path.splitext(
            media.filename
        )[1].lower()

        image_extensions = {
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".webp",
        }

        video_extensions = {
            ".mp4",
            ".webm",
            ".mov",
            ".m4v",
        }

        if extension in image_extensions:
            media_type = "image"

        elif extension in video_extensions:
            media_type = "video"

        else:
            raise HTTPException(
                status_code=400,
                detail="Only image and video files are supported"
            )

        filename = (
            uuid.uuid4().hex +
            extension
        )

        filepath = os.path.join(
            UPLOAD_DIR,
            filename
        )

        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(
                media.file,
                buffer
            )

        media_url = (
            "/static/uploads/" +
            filename
        )

    if not caption and not media_url:
        raise HTTPException(
            status_code=400,
            detail="Write a caption or select an image/video"
        )

    post = Post(
        user_id=user.id,
        caption=caption,
        media_url=media_url,
        media_type=media_type,
        created_at=datetime.utcnow(),
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    return {
        "ok": True,
        "message": "Post published successfully",
        "post": post.to_dict(),
    }


# ============================================================
# GET POSTS
# ============================================================

@router.get("")
def get_posts(
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):

    posts = (
        db.query(Post)
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "posts": [
            p.to_dict()
            for p in posts
        ]
    }


# ============================================================
# LIKE
# ============================================================

@router.post("/{post_id}/like")
def toggle_like(
    post_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):

    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    existing = (
        db.query(PostLike)
        .filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user.id,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        liked = False
    else:
        db.add(
            PostLike(
                post_id=post_id,
                user_id=user.id,
            )
        )
        liked = True

    db.commit()

    count = (
        db.query(PostLike)
        .filter(PostLike.post_id == post_id)
        .count()
    )

    return {
        "ok": True,
        "liked": liked,
        "likes": count,
    }


# ============================================================
# SAVE
# ============================================================

@router.post("/{post_id}/save")
def toggle_save(
    post_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):

    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    existing = (
        db.query(PostSave)
        .filter(
            PostSave.post_id == post_id,
            PostSave.user_id == user.id,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        saved = False
    else:
        db.add(
            PostSave(
                post_id=post_id,
                user_id=user.id,
            )
        )
        saved = True

    db.commit()

    return {
        "ok": True,
        "saved": saved,
    }


# ============================================================
# SHARE
# ============================================================

@router.post("/{post_id}/share")
def share_post(
    post_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):

    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    share = PostShare(
        post_id=post_id,
        user_id=user.id,
    )

    db.add(share)
    db.commit()

    count = (
        db.query(PostShare)
        .filter(PostShare.post_id == post_id)
        .count()
    )

    return {
        "ok": True,
        "shares": count,
    }


# ============================================================
# COMMENTS
# ============================================================

@router.get("/{post_id}/comments")
def get_comments(
    post_id: int,
    db: Session = Depends(get_db),
):

    comments = (
        db.query(Comment)
        .filter(Comment.post_id == post_id)
        .order_by(Comment.created_at.asc())
        .all()
    )

    return {
        "comments": [
            serialize_comment(c)
            for c in comments
        ]
    }


@router.post("/{post_id}/comments")
def add_comment(
    post_id: int,
    text: str = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):

    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    text = text.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Comment cannot be empty"
        )

    comment = Comment(
        post_id=post_id,
        user_id=user.id,
        text=text,
        created_at=datetime.utcnow(),
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "ok": True,
        "comment": serialize_comment(comment),
    }
