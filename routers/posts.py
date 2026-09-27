import os
import uuid
from pathlib import Path
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import (
    User,
    Post,
    PostLike,
    PostComment,
    PostSave,
    PostShare,
)
from auth import require_user


router = APIRouter(
    prefix="/api/posts",
    tags=["posts"]
)


# ============================================================
# MEDIA DIRECTORY
# ============================================================

UPLOAD_DIR = Path("static/uploads")

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
}

VIDEO_EXTENSIONS = {
    ".mp4",
    ".webm",
    ".mov",
    ".m4v",
}

MAX_IMAGE_SIZE = 15 * 1024 * 1024
MAX_VIDEO_SIZE = 100 * 1024 * 1024


def ensure_upload_dir():
    UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# SERIALIZER
# ============================================================

def serialize_post(
    post: Post,
    current_user_id: int | None = None,
):
    return post.to_dict(
        current_user_id=current_user_id
    )


# ============================================================
# CREATE POST
# ============================================================

@router.post("/create")
async def create_post(
    caption: str = Form(""),
    media: UploadFile | None = File(None),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    caption = (caption or "").strip()

    if not caption and media is None:
        raise HTTPException(
            status_code=400,
            detail="Write a caption or select an image/video."
        )

    media_url = ""
    media_type = "text"

    if media is not None:

        ensure_upload_dir()

        filename = media.filename or ""

        extension = Path(filename).suffix.lower()

        content_type = (
            media.content_type
            or ""
        ).lower()

        if extension in IMAGE_EXTENSIONS:
            media_type = "image"

            max_size = MAX_IMAGE_SIZE

        elif extension in VIDEO_EXTENSIONS:
            media_type = "video"

            max_size = MAX_VIDEO_SIZE

        elif content_type.startswith("image/"):
            media_type = "image"

            max_size = MAX_IMAGE_SIZE

        elif content_type.startswith("video/"):
            media_type = "video"

            max_size = MAX_VIDEO_SIZE

        else:
            raise HTTPException(
                status_code=400,
                detail="Only image and video files are supported."
            )

        data = await media.read()

        if len(data) > max_size:
            raise HTTPException(
                status_code=413,
                detail=(
                    "File is too large. "
                    f"Maximum allowed size is "
                    f"{max_size // (1024 * 1024)}MB."
                ),
            )

        safe_extension = extension

        if not safe_extension:
            if media_type == "image":
                safe_extension = ".jpg"
            else:
                safe_extension = ".mp4"

        generated_name = (
            f"{uuid.uuid4().hex}"
            f"{safe_extension}"
        )

        destination = (
            UPLOAD_DIR /
            generated_name
        )

        with open(destination, "wb") as f:
            f.write(data)

        media_url = (
            f"/static/uploads/{generated_name}"
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

    post = (
        db.query(Post)
        .options(joinedload(Post.user))
        .filter(Post.id == post.id)
        .first()
    )

    return {
        "ok": True,
        "message": "Post created successfully",
        "post": serialize_post(
            post,
            user.id
        ),
    }


# ============================================================
# GET SINGLE POST
# ============================================================

@router.get("/{post_id}")
def get_post(
    post_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    post = (
        db.query(Post)
        .options(
            joinedload(Post.user),
            joinedload(Post.likes),
            joinedload(Post.comments),
            joinedload(Post.saves),
            joinedload(Post.shares),
        )
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found"
        )

    return {
        "post": serialize_post(
            post,
            user.id
        )
    }


# ============================================================
# DELETE POST
# ============================================================

@router.delete("/{post_id}")
def delete_post(
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

    if post.user_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own posts."
        )

    db.delete(post)
    db.commit()

    return {
        "ok": True,
        "message": "Post deleted"
    }


# ============================================================
# LIKE / UNLIKE
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
                user_id=user.id
            )
        )
        liked = True

    db.commit()

    count = (
        db.query(PostLike)
        .filter(
            PostLike.post_id == post_id
        )
        .count()
    )

    return {
        "ok": True,
        "liked": liked,
        "likes": count,
    }


# ============================================================
# COMMENTS — LIST
# ============================================================

@router.get("/{post_id}/comments")
def get_comments(
    post_id: int,
    db: Session = Depends(get_db),
):
    comments = (
        db.query(PostComment)
        .options(
            joinedload(PostComment.user)
        )
        .filter(
            PostComment.post_id == post_id
        )
        .order_by(
            PostComment.created_at.asc()
        )
        .all()
    )

    return {
        "comments": [
            comment.to_dict()
            for comment in comments
        ]
    }


# ============================================================
# COMMENTS — CREATE
# ============================================================

@router.post("/{post_id}/comments")
def create_comment(
    post_id: int,
    text: str = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    text = (text or "").strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Comment cannot be empty."
        )

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

    comment = PostComment(
        post_id=post_id,
        user_id=user.id,
        text=text,
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    comment = (
        db.query(PostComment)
        .options(
            joinedload(PostComment.user)
        )
        .filter(
            PostComment.id == comment.id
        )
        .first()
    )

    count = (
        db.query(PostComment)
        .filter(
            PostComment.post_id == post_id
        )
        .count()
    )

    return {
        "ok": True,
        "comment": comment.to_dict(),
        "comments": count,
    }


# ============================================================
# SAVE / UNSAVE
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
                user_id=user.id
            )
        )
        saved = True

    db.commit()

    count = (
        db.query(PostSave)
        .filter(
            PostSave.post_id == post_id
        )
        .count()
    )

    return {
        "ok": True,
        "saved": saved,
        "saves": count,
    }


# ============================================================
# SHARE / RESHARE
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
        user_id=user.id
    )

    db.add(share)
    db.commit()

    count = (
        db.query(PostShare)
        .filter(
            PostShare.post_id == post_id
        )
        .count()
    )

    return {
        "ok": True,
        "message": "Post shared",
        "shares": count,
        "share_url": f"/?post={post_id}",
    }
