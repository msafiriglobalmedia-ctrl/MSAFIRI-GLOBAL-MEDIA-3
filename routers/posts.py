from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Post, User
from auth import get_current_user, require_user

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.get("")
def list_posts(db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(Post.created_at.desc()).limit(50).all()
    return {"posts": [p.to_dict() for p in posts]}


@router.post("")
def create_post(
    caption: str = Form(""),
    media_url: str = Form(""),
    media_type: str = Form("text"),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    post = Post(
        user_id=user.id,
        caption=caption,
        media_url=media_url,
        media_type=media_type,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post.to_dict()


@router.get("/{post_id}")
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post.to_dict()


@router.delete("/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    db.delete(post)
    db.commit()
    return {"ok": True}
