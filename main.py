# ============================================================
# MSAFIRI GLOBAL MEDIA
# main.py
# VERSION 6.0.0-PHASE2
#
# FastAPI backend
# Authentication
# Posts
# Image/Video posts
# Likes
# Comments
# Saves
# Shares
# Feed
# Stories
# Discovery
# AI Council
# Studio
# Market
# World Map
# Channels
# Communities
# User Manual
# Settings
# SPA frontend
# ============================================================

import os
import uuid
from datetime import datetime
from typing import Optional

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    Query,
    Request,
    UploadFile,
    File,
    Form,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    Boolean,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Session

from database import get_db, Base, engine
from models import User, Post, Follow, Status

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    require_user,
)


# ============================================================
# APP CONFIGURATION
# ============================================================

APP_VERSION = "6.0.0-PHASE2"
APP_NAME = "MSAFIRI GLOBAL MEDIA"
APP_TAGLINE = "Connect beyond — Media V0.0.1"
FOUNDER = "MSAFIRI WILLIAM MUNGA"
COMPANY = "ZetroLink Technology Limited"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
MEDIA_DIR = os.path.join(STATIC_DIR, "uploads")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=(
        f"{APP_TAGLINE}\n\n"
        f"Founded by {FOUNDER}\n"
        f"{COMPANY}"
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# EXTRA DATABASE TABLES
#
# Your original models.py does not contain:
# likes
# comments
# saves
# shares
#
# These tables are created here so we do not need to destroy
# your existing database.
# ============================================================


class PostLike(Base):
    __tablename__ = "post_likes"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "post_id",
            "user_id",
            name="uq_post_like_user",
        ),
    )


class PostSave(Base):
    __tablename__ = "post_saves"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "post_id",
            "user_id",
            name="uq_post_save_user",
        ),
    )


class PostComment(Base):
    __tablename__ = "post_comments"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PostShare(Base):
    __tablename__ = "post_shares"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup():
    try:
        Base.metadata.create_all(bind=engine)

        print("=" * 60)
        print(f"{APP_NAME} {APP_VERSION}")
        print("Database initialized")
        print(f"Founder: {FOUNDER}")
        print(f"Company: {COMPANY}")
        print("=" * 60)

    except Exception as e:
        print("DATABASE STARTUP ERROR:", repr(e))


# ============================================================
# HEALTH
# ============================================================

@app.get("/health", tags=["health"])
def health():
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "time": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/health", tags=["health"])
def api_health():
    return {
        "status": "ok",
        "service": "msafiri-api",
        "version": APP_VERSION,
        "uptime": "running",
    }


# ============================================================
# AUTHENTICATION
# ============================================================

class RegisterIn(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str = ""


class LoginIn(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register", tags=["auth"])
def register(
    data: RegisterIn,
    db: Session = Depends(get_db),
):
    username = data.username.strip()
    email = str(data.email).strip().lower()

    if len(username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must contain at least 3 characters",
        )

    if len(data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 6 characters",
        )

    existing_email = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    existing_username = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Username taken",
        )

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name.strip(),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        {"sub": str(user.id)}
    )

    return {
        "user": user.to_dict(),
        "access_token": token,
        "token_type": "bearer",
    }


@app.post("/api/auth/login", tags=["auth"])
def login(
    data: LoginIn,
    db: Session = Depends(get_db),
):
    login_value = data.username.strip()

    user = (
        db.query(User)
        .filter(
            (User.username == login_value)
            | (User.email == login_value.lower())
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    if not verify_password(
        data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    token = create_access_token(
        {"sub": str(user.id)}
    )

    return {
        "user": user.to_dict(),
        "access_token": token,
        "token_type": "bearer",
    }


@app.post("/api/auth/logout", tags=["auth"])
def logout():
    return {
        "ok": True,
        "message": "Logged out",
    }


@app.get("/api/auth/me", tags=["auth"])
def me(
    user: User = Depends(require_user),
):
    return user.to_dict()


@app.get("/api/auth/ping", tags=["auth"])
def auth_ping():
    return {
        "status": "ok",
        "service": "msafiri-auth",
        "time": datetime.utcnow().isoformat() + "Z",
    }


# ============================================================
# HELPERS
# ============================================================

def get_user_by_id(
    db: Session,
    user_id: int,
):
    return (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )


def get_post_or_404(
    db: Session,
    post_id: int,
):
    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    return post


def count_likes(
    db: Session,
    post_id: int,
):
    return (
        db.query(PostLike)
        .filter(PostLike.post_id == post_id)
        .count()
    )


def count_comments(
    db: Session,
    post_id: int,
):
    return (
        db.query(PostComment)
        .filter(PostComment.post_id == post_id)
        .count()
    )


def count_saves(
    db: Session,
    post_id: int,
):
    return (
        db.query(PostSave)
        .filter(PostSave.post_id == post_id)
        .count()
    )


def count_shares(
    db: Session,
    post_id: int,
):
    return (
        db.query(PostShare)
        .filter(PostShare.post_id == post_id)
        .count()
    )


def user_liked(
    db: Session,
    post_id: int,
    user_id: Optional[int],
):
    if not user_id:
        return False

    return (
        db.query(PostLike)
        .filter(
            PostLike.post_id == post_id,
            PostLike.user_id == user_id,
        )
        .first()
        is not None
    )


def user_saved(
    db: Session,
    post_id: int,
    user_id: Optional[int],
):
    if not user_id:
        return False

    return (
        db.query(PostSave)
        .filter(
            PostSave.post_id == post_id,
            PostSave.user_id == user_id,
        )
        .first()
        is not None
    )


def serialize_post(
    db: Session,
    post: Post,
    current_user_id: Optional[int] = None,
):
    user = get_user_by_id(db, post.user_id)

    return {
        "id": post.id,
        "user_id": post.user_id,

        "username": (
            user.username
            if user
            else f"user_{post.user_id}"
        ),

        "full_name": (
            user.full_name
            if user
            else ""
        ),

        "avatar_url": (
            user.avatar_url
            if user
            else ""
        ),

        "caption": post.caption or "",
        "media_url": post.media_url or "",
        "media_type": post.media_type or "text",

        "created_at": (
            post.created_at.isoformat()
            if post.created_at
            else None
        ),

        "likes": count_likes(db, post.id),
        "comments": count_comments(db, post.id),
        "saves": count_saves(db, post.id),
        "shares": count_shares(db, post.id),

        "liked": user_liked(
            db,
            post.id,
            current_user_id,
        ),

        "saved": user_saved(
            db,
            post.id,
            current_user_id,
        ),
    }


# ============================================================
# MEDIA UPLOAD
# ============================================================

ALLOWED_IMAGE = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}

ALLOWED_VIDEO = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
    "video/x-matroska",
}


def save_uploaded_file(
    file: UploadFile,
):
    if not file:
        return None, None

    content_type = file.content_type or ""

    if content_type not in (
        ALLOWED_IMAGE | ALLOWED_VIDEO
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Unsupported media type. "
                "Use JPG, PNG, WEBP, GIF, MP4, WEBM or MOV."
            ),
        )

    extension = os.path.splitext(
        file.filename or ""
    )[1].lower()

    if not extension:
        extension = ".bin"

    filename = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    filepath = os.path.join(
        MEDIA_DIR,
        filename,
    )

    with open(filepath, "wb") as output:
        while True:
            chunk = file.file.read(1024 * 1024)

            if not chunk:
                break

            output.write(chunk)

    media_type = (
        "video"
        if content_type.startswith("video/")
        else "image"
    )

    return (
        f"/static/uploads/{filename}",
        media_type,
    )


# ============================================================
# CREATE POST
#
# IMPORTANT:
# This is the endpoint fixing:
# "405 Method Not Allowed"
#
# Supports:
# 1. JSON
# 2. multipart/form-data
# 3. image
# 4. video
# 5. caption
# ============================================================

@app.post("/api/posts", tags=["posts"])
async def create_post(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    content_type = (
        request.headers.get("content-type", "")
        .lower()
    )

    caption = ""
    media_url = ""
    media_type = "text"

    # --------------------------------------------------------
    # JSON REQUEST
    # --------------------------------------------------------

    if "application/json" in content_type:
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid JSON",
            )

        caption = str(
            data.get("caption", "")
        ).strip()

        media_url = str(
            data.get("media_url", "")
        ).strip()

        media_type = str(
            data.get("media_type", "text")
        ).strip() or "text"

    # --------------------------------------------------------
    # MULTIPART REQUEST
    # --------------------------------------------------------

    elif (
        "multipart/form-data" in content_type
        or "application/x-www-form-urlencoded"
        in content_type
    ):
        form = await request.form()

        caption = str(
            form.get("caption", "")
        ).strip()

        uploaded = form.get("file")

        if uploaded and hasattr(
            uploaded,
            "filename",
        ):
            media_url, media_type = save_uploaded_file(
                uploaded
            )

        # Some frontend versions may call the field "media"
        if not media_url:
            uploaded = form.get("media")

            if uploaded and hasattr(
                uploaded,
                "filename",
            ):
                media_url, media_type = save_uploaded_file(
                    uploaded
                )

        # Allow frontend to send an existing URL
        if not media_url:
            media_url = str(
                form.get("media_url", "")
            ).strip()

            if media_url:
                media_type = str(
                    form.get("media_type", "image")
                )

    else:
        # ----------------------------------------------------
        # FALLBACK
        # ----------------------------------------------------
        try:
            data = await request.json()

            caption = str(
                data.get("caption", "")
            ).strip()

            media_url = str(
                data.get("media_url", "")
            ).strip()

            media_type = str(
                data.get("media_type", "text")
            ).strip()

        except Exception:
            raise HTTPException(
                status_code=415,
                detail="Unsupported request format",
            )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if not caption and not media_url:
        raise HTTPException(
            status_code=400,
            detail="Post must contain caption, image or video",
        )

    if media_type not in {
        "text",
        "image",
        "video",
    }:
        media_type = "image" if media_url else "text"

    # --------------------------------------------------------
    # CREATE DATABASE POST
    # --------------------------------------------------------

    post = Post(
        user_id=user.id,
        caption=caption,
        media_url=media_url,
        media_type=media_type,
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    return {
        "ok": True,
        "message": "Post published successfully",
        "post": serialize_post(
            db,
            post,
            user.id,
        ),
    }


# ============================================================
# GET ALL POSTS
# ============================================================

@app.get("/api/posts", tags=["posts"])
def get_posts(
    db: Session = Depends(get_db),
    user: Optional[User] = Depends(
        lambda: None
    ),
    limit: int = Query(50, ge=1, le=100),
):
    posts = (
        db.query(Post)
        .order_by(Post.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "posts": [
            serialize_post(db, p)
            for p in posts
        ]
    }


# ============================================================
# GET SINGLE POST
# ============================================================

@app.get("/api/posts/{post_id}", tags=["posts"])
def get_post(
    post_id: int,
    db: Session = Depends(get_db),
):
    post = get_post_or_404(
        db,
        post_id,
    )

    return {
        "post": serialize_post(
            db,
            post,
        )
    }


# ============================================================
# LIKE / UNLIKE
# ============================================================

@app.post(
    "/api/posts/{post_id}/like",
    tags=["posts"],
)
def toggle_like(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    post = get_post_or_404(
        db,
        post_id,
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
        db.commit()

        liked = False
    else:
        like = PostLike(
            post_id=post_id,
            user_id=user.id,
        )

        db.add(like)
        db.commit()

        liked = True

    return {
        "ok": True,
        "liked": liked,
        "likes": count_likes(
            db,
            post.id,
        ),
    }


# ============================================================
# SAVE / UNSAVE
# ============================================================

@app.post(
    "/api/posts/{post_id}/save",
    tags=["posts"],
)
def toggle_save(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    post = get_post_or_404(
        db,
        post_id,
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
        db.commit()

        saved = False
    else:
        saved_item = PostSave(
            post_id=post_id,
            user_id=user.id,
        )

        db.add(saved_item)
        db.commit()

        saved = True

    return {
        "ok": True,
        "saved": saved,
        "saves": count_saves(
            db,
            post.id,
        ),
    }


# ============================================================
# SHARE
# ============================================================

@app.post(
    "/api/posts/{post_id}/share",
    tags=["posts"],
)
def share_post(
    post_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    post = get_post_or_404(
        db,
        post_id,
    )

    share = PostShare(
        post_id=post_id,
        user_id=user.id,
    )

    db.add(share)
    db.commit()

    return {
        "ok": True,
        "message": "Post shared successfully",
        "shares": count_shares(
            db,
            post.id,
        ),
    }


# ============================================================
# COMMENTS
# ============================================================

class CommentIn(BaseModel):
    text: str


@app.post(
    "/api/posts/{post_id}/comments",
    tags=["posts"],
)
def create_comment(
    post_id: int,
    data: CommentIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    post = get_post_or_404(
        db,
        post_id,
    )

    text_value = data.text.strip()

    if not text_value:
        raise HTTPException(
            status_code=400,
            detail="Comment cannot be empty",
        )

    comment = PostComment(
        post_id=post_id,
        user_id=user.id,
        text=text_value,
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "ok": True,
        "comment": {
            "id": comment.id,
            "post_id": comment.post_id,
            "user_id": comment.user_id,
            "username": user.username,
            "full_name": user.full_name,
            "text": comment.text,
            "created_at": (
                comment.created_at.isoformat()
                if comment.created_at
                else None
            ),
        },
        "comments": count_comments(
            db,
            post.id,
        ),
    }


@app.get(
    "/api/posts/{post_id}/comments",
    tags=["posts"],
)
def get_comments(
    post_id: int,
    db: Session = Depends(get_db),
):
    post = get_post_or_404(
        db,
        post_id,
    )

    comments = (
        db.query(PostComment)
        .filter(
            PostComment.post_id == post.id
        )
        .order_by(
            PostComment.created_at.asc()
        )
        .all()
    )

    result = []

    for comment in comments:
        user = get_user_by_id(
            db,
            comment.user_id,
        )

        result.append(
            {
                "id": comment.id,
                "post_id": comment.post_id,
                "user_id": comment.user_id,
                "username": (
                    user.username
                    if user
                    else "User"
                ),
                "full_name": (
                    user.full_name
                    if user
                    else ""
                ),
                "avatar_url": (
                    user.avatar_url
                    if user
                    else ""
                ),
                "text": comment.text,
                "created_at": (
                    comment.created_at.isoformat()
                    if comment.created_at
                    else None
                ),
            }
        )

    return {
        "comments": result
    }


# ============================================================
# FEED
# ============================================================

@app.get("/api/feed", tags=["feed"])
def feed(
    type: str = Query("for-you"),
    db: Session = Depends(get_db),
):
    posts = (
        db.query(Post)
        .order_by(Post.created_at.desc())
        .limit(100)
        .all()
    )

    return {
        "type": type,
        "posts": [
            serialize_post(db, p)
            for p in posts
        ],
    }


# ============================================================
# STORIES
# ============================================================

@app.get("/api/stories", tags=["stories"])
def stories(
    db: Session = Depends(get_db),
):
    statuses = (
        db.query(Status)
        .order_by(Status.created_at.desc())
        .limit(50)
        .all()
    )

    result = []

    for status in statuses:
        user = get_user_by_id(
            db,
            status.user_id,
        )

        result.append(
            {
                "id": status.id,
                "user_id": status.user_id,
                "username": (
                    user.username
                    if user
                    else "User"
                ),
                "full_name": (
                    user.full_name
                    if user
                    else ""
                ),
                "avatar_url": (
                    user.avatar_url
                    if user
                    else ""
                ),
                "media_url": status.media_url,
                "caption": status.caption,
                "media_type": status.media_type,
                "created_at": (
                    status.created_at.isoformat()
                    if status.created_at
                    else None
                ),
            }
        )

    return {
        "stories": result
    }


# ============================================================
# CREATE STORY
# ============================================================

@app.post("/api/stories", tags=["stories"])
async def create_story(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    content_type = (
        request.headers.get(
            "content-type",
            "",
        ).lower()
    )

    caption = ""
    media_url = ""
    media_type = "image"

    if "application/json" in content_type:
        data = await request.json()

        caption = str(
            data.get("caption", "")
        ).strip()

        media_url = str(
            data.get("media_url", "")
        ).strip()

        media_type = str(
            data.get("media_type", "image")
        )

    else:
        form = await request.form()

        caption = str(
            form.get("caption", "")
        ).strip()

        uploaded = (
            form.get("file")
            or form.get("media")
        )

        if uploaded and hasattr(
            uploaded,
            "filename",
        ):
            media_url, media_type = save_uploaded_file(
                uploaded
            )

        if not media_url:
            media_url = str(
                form.get("media_url", "")
            ).strip()

    if not media_url and not caption:
        raise HTTPException(
            status_code=400,
            detail="Story requires media or caption",
        )

    story = Status(
        user_id=user.id,
        media_url=media_url,
        caption=caption,
        media_type=media_type,
    )

    db.add(story)
    db.commit()
    db.refresh(story)

    return {
        "ok": True,
        "message": "Story published",
        "story": story.to_dict(),
    }


# ============================================================
# PROFILE
# ============================================================

@app.get("/api/profile/me", tags=["profile"])
def profile_me(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    posts_count = (
        db.query(Post)
        .filter(Post.user_id == user.id)
        .count()
    )

    followers = (
        db.query(Follow)
        .filter(Follow.following_id == user.id)
        .count()
    )

    following = (
        db.query(Follow)
        .filter(Follow.follower_id == user.id)
        .count()
    )

    data = user.to_dict()

    data.update(
        {
            "posts_count": posts_count,
            "followers": followers,
            "following": following,
        }
    )

    return data


@app.get(
    "/api/profile/{username}",
    tags=["profile"],
)
def profile(
    username: str,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(User.username == username)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    posts = (
        db.query(Post)
        .filter(Post.user_id == user.id)
        .order_by(Post.created_at.desc())
        .all()
    )

    return {
        "user": user.to_dict(),
        "posts": [
            serialize_post(db, p)
            for p in posts
        ],
    }


# ============================================================
# DISCOVERY
# ============================================================

@app.get(
    "/api/discovery",
    tags=["discovery"],
)
def get_discovery():
    return {
        "cards": [
            {
                "id": "ai-council",
                "icon": "📖",
                "title": "AI Council",
                "desc": "Education, Health, Agriculture, Research",
            },
            {
                "id": "creative-studio",
                "icon": "🖼️",
                "title": "Creative Studio",
                "desc": "Image, Video, Documents",
            },
            {
                "id": "market",
                "icon": "🛍️",
                "title": "Market",
                "desc": "Products, Services, Digital",
            },
            {
                "id": "world-map",
                "icon": "🌍",
                "title": "World Map",
                "desc": "Explore the world",
            },
            {
                "id": "channels",
                "icon": "📺",
                "title": "Channels",
                "desc": "BBC, CNN, Aljazeera and more",
            },
            {
                "id": "communities",
                "icon": "👥",
                "title": "Communities",
                "desc": "Join groups and communities",
            },
            {
                "id": "videos",
                "icon": "▶️",
                "title": "Videos",
                "desc": "Short videos feed",
            },
            {
                "id": "settings",
                "icon": "⚙️",
                "title": "Settings",
                "desc": "App preferences",
            },
        ]
    }


# ============================================================
# AI COUNCIL
# ============================================================

@app.get(
    "/api/ai-council",
    tags=["discovery"],
)
def ai_council_list():
    return {
        "ais": [
            {
                "id": "education",
                "icon": "📖",
                "title": "Education AI",
                "desc": "Study notes, syllabus, past papers",
            },
            {
                "id": "health",
                "icon": "❤️",
                "title": "Health AI",
                "desc": "General health information",
            },
            {
                "id": "agriculture",
                "icon": "🌿",
                "title": "Agriculture AI",
                "desc": "Crops, soil, farming",
            },
            {
                "id": "research",
                "icon": "🔍",
                "title": "Research AI",
                "desc": "Methodology, citations",
            },
            {
                "id": "canvas",
                "icon": "📐",
                "title": "AI Canvas",
                "desc": "Workspace with documents",
            },
        ]
    }


@app.get(
    "/api/ai-council/countries",
    tags=["discovery"],
)
def ai_council_countries():
    return {
        "countries": [
            "Tanzania",
            "Kenya",
            "Uganda",
            "Rwanda",
            "Burundi",
            "South Africa",
            "Nigeria",
            "Ghana",
            "UK",
            "USA",
            "Canada",
            "Australia",
            "India",
            "China",
            "Japan",
            "Germany",
            "France",
            "Brazil",
        ]
    }


@app.get(
    "/api/ai-council/levels",
    tags=["discovery"],
)
def ai_council_levels():
    return {
        "levels": [
            "Nursery / Early Childhood",
            "Primary",
            "Secondary",
            "High School",
            "Certificate",
            "Diploma",
            "Degree",
            "Master",
            "PhD",
        ]
    }


@app.get(
    "/api/ai-council/content-types",
    tags=["discovery"],
)
def ai_council_content_types():
    return {
        "content_types": [
            "Notes",
            "Books",
            "Past Papers",
            "Marking Schemes",
        ]
    }


@app.get(
    "/api/ai-council/chat",
    tags=["discovery"],
)
def ai_council_chat(
    ai: str = Query("education"),
    country: str = Query("Tanzania"),
    level: str = Query("Degree"),
    content: str = Query("Notes"),
    q: str = Query(""),
):
    return {
        "ai": ai,
        "context": {
            "country": country,
            "level": level,
            "content": content,
        },
        "question": q,
        "reply": (
            f"Hello! I'm your {content} assistant for "
            f"{level} curriculum in {country}. "
            f"Ask me anything about a subject or topic."
        ),
        "phase": "placeholder",
    }


# ============================================================
# CREATIVE STUDIO
# ============================================================

@app.get(
    "/api/studio",
    tags=["discovery"],
)
def studio_tools():
    return {
        "tools": [
            {
                "id": "image",
                "icon": "🖼️",
                "title": "Image Creator",
                "desc": "Posters, social graphics, covers, thumbnails",
            },
            {
                "id": "video",
                "icon": "🎬",
                "title": "Video Creator",
                "desc": "Short videos, editing, social content",
            },
            {
                "id": "document",
                "icon": "📄",
                "title": "Document Creator",
                "desc": "Documents, digital resources, educational material",
            },
            {
                "id": "assistant",
                "icon": "✨",
                "title": "Design Assistant",
                "desc": "AI-assisted creative ideas",
            },
        ]
    }


# ============================================================
# MARKET
# ============================================================

@app.get(
    "/api/market/categories",
    tags=["discovery"],
)
def market_categories():
    return {
        "categories": [
            {
                "id": "products",
                "title": "Products",
                "desc": "Goods for sale",
            },
            {
                "id": "services",
                "title": "Services",
                "desc": "Professional services",
            },
            {
                "id": "digital",
                "title": "Digital",
                "desc": "Digital products",
            },
            {
                "id": "business",
                "title": "Business",
                "desc": "Business opportunities",
            },
        ]
    }


@app.get(
    "/api/market/items",
    tags=["discovery"],
)
def market_items(
    category: str = Query("products"),
):
    return {
        "category": category,
        "items": [],
        "phase": "placeholder",
    }


# ============================================================
# WORLD MAP
# ============================================================

@app.get(
    "/api/world-map/countries",
    tags=["discovery"],
)
def world_map_countries():
    return {
        "countries": [
            {
                "name": "Tanzania",
                "users": 0,
                "posts": 0,
            },
            {
                "name": "Kenya",
                "users": 0,
                "posts": 0,
            },
            {
                "name": "Uganda",
                "users": 0,
                "posts": 0,
            },
        ],
        "phase": "placeholder",
    }


# ============================================================
# CHANNELS
# ============================================================

@app.get(
    "/api/channels",
    tags=["discovery"],
)
def channels_list():
    return {
        "channels": [
            {
                "id": "bbc",
                "name": "BBC News",
                "color": "red",
                "desc": "Global news from UK",
            },
            {
                "id": "cnn",
                "name": "CNN",
                "color": "red",
                "desc": "Cable News Network",
            },
            {
                "id": "aljazeera",
                "name": "Al Jazeera",
                "color": "orange",
                "desc": "Qatar-based news",
            },
            {
                "id": "itv",
                "name": "ITV News",
                "color": "blue",
                "desc": "UK broadcaster",
            },
            {
                "id": "msafiri",
                "name": "Msafiri Global Media",
                "color": "blue",
                "desc": "Our own channel",
            },
        ]
    }


# ============================================================
# COMMUNITIES
# ============================================================

@app.get(
    "/api/communities/categories",
    tags=["discovery"],
)
def communities_categories():
    return {
        "categories": [
            {
                "id": "education",
                "title": "Education",
                "desc": "Study groups",
            },
            {
                "id": "technology",
                "title": "Technology",
                "desc": "Tech discussions",
            },
            {
                "id": "business",
                "title": "Business",
                "desc": "Entrepreneurship",
            },
            {
                "id": "health",
                "title": "Health",
                "desc": "Health tips",
            },
            {
                "id": "agriculture",
                "title": "Agriculture",
                "desc": "Farmers",
            },
            {
                "id": "entertainment",
                "title": "Entertainment",
                "desc": "Music, movies",
            },
            {
                "id": "sports",
                "title": "Sports",
                "desc": "Football, athletics",
            },
            {
                "id": "religion",
                "title": "Religion",
                "desc": "Faith-based",
            },
            {
                "id": "language",
                "title": "Language",
                "desc": "English, Swahili learning",
            },
        ]
    }


# ============================================================
# USER MANUAL
# ============================================================

@app.get(
    "/api/user-manual",
    tags=["settings"],
)
def user_manual():
    return {
        "app": APP_NAME,
        "tagline": APP_TAGLINE,
        "version": APP_VERSION,
        "founder": FOUNDER,
        "year_started": "2026",
        "company": COMPANY,

        "about": (
            f"{APP_NAME} is a social, communication, "
            f"and AI app. Founded by {FOUNDER} under "
            f"{COMPANY}. Version: {APP_VERSION}"
        ),

        "sections": {
            "home": "Feed, Stories, Posts",
            "discovery": (
                "AI Council, Studio, Market, World Map, "
                "Channels, Communities"
            ),
            "chats": "Messaging (WhatsApp-style)",
            "profile": "Your profile",
        },

        "how_to_use": {
            "create_account": (
                "Register, fill details, Create Account"
            ),
            "post_content": (
                "Create (+), caption, Photo/Video/File, Post"
            ),
            "share_story": (
                "\"+ My Story\", media, Post Story"
            ),
            "chat": (
                "Profile, Message icon, type or record"
            ),
            "explore_ai": (
                "Discovery, AI Council, choose AI"
            ),
        },

        "support": f"Contact {COMPANY}",
    }


# ============================================================
# SETTINGS
# ============================================================

@app.get(
    "/api/settings",
    tags=["settings"],
)
def settings():
    return {
        "theme": "light",
        "language": "en",
        "version": APP_VERSION,
        "logout_url": "/api/auth/logout",
    }


# ============================================================
# SIMPLE SEARCH
# ============================================================

@app.get(
    "/api/search",
    tags=["search"],
)
def search(
    q: str = Query(""),
    db: Session = Depends(get_db),
):
    query = q.strip()

    if not query:
        return {
            "users": [],
            "posts": [],
        }

    users = (
        db.query(User)
        .filter(
            (User.username.ilike(f"%{query}%"))
            | (User.full_name.ilike(f"%{query}%"))
        )
        .limit(20)
        .all()
    )

    posts = (
        db.query(Post)
        .filter(
            Post.caption.ilike(
                f"%{query}%"
            )
        )
        .order_by(
            Post.created_at.desc()
        )
        .limit(20)
        .all()
    )

    return {
        "users": [
            user.to_dict()
            for user in users
        ],
        "posts": [
            serialize_post(db, p)
            for p in posts
        ],
    }


# ============================================================
# STATIC FILES
# ============================================================

if os.path.isdir(STATIC_DIR):
    app.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR),
        name="static",
    )

    print("Static directory mounted:", STATIC_DIR)


# ============================================================
# ROOT
# ============================================================

@app.get(
    "/",
    include_in_schema=False,
)
async def root():
    index_path = os.path.join(
        STATIC_DIR,
        "index.html",
    )

    if os.path.isfile(index_path):
        return FileResponse(index_path)

    return JSONResponse(
        {
            "app": APP_NAME,
            "version": APP_VERSION,
            "message": "Frontend not found",
            "docs": "/docs",
        }
    )


# ============================================================
# SPA FALLBACK
# ============================================================

@app.get(
    "/{full_path:path}",
    include_in_schema=False,
)
async def spa_fallback(
    full_path: str,
):
    if full_path.startswith("api/"):
        raise HTTPException(
            status_code=404,
            detail=(
                f"API route '{full_path}' not found"
            ),
        )

    index_path = os.path.join(
        STATIC_DIR,
        "index.html",
    )

    if os.path.isfile(index_path):
        return FileResponse(index_path)

    raise HTTPException(
        status_code=404,
        detail="Not found",
    )


# ============================================================
# 404 HANDLER
# ============================================================

@app.exception_handler(404)
async def not_found_handler(
    request: Request,
    exc,
):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={
                "detail": (
                    exc.detail
                    if hasattr(exc, "detail")
                    else "Not found"
                )
            },
        )

    index_path = os.path.join(
        STATIC_DIR,
        "index.html",
    )

    if os.path.isfile(index_path):
        return FileResponse(index_path)

    return JSONResponse(
        status_code=404,
        content={
            "detail": "Not found"
        },
    )


# ============================================================
# DATABASE RESET
#
# DO NOT expose this publicly in production.
# Kept only for development/debugging.
# ============================================================

@app.get(
    "/admin/reset-db-temp-secret",
    tags=["admin"],
)
def reset_db():
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(
            text(
                "DROP TABLE IF EXISTS post_comments CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS post_likes CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS post_saves CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS post_shares CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS statuses CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS follows CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS posts CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS users CASCADE"
            )
        )

    Base.metadata.create_all(
        bind=engine
    )

    return {
        "ok": True,
        "message": (
            "Database reset completed. "
            "All users, posts, likes, comments, saves "
            "and shares were deleted."
        ),
    }


# ============================================================
# RUN LOCALLY / RENDER
# ============================================================

if __name__ == "__main__":
    import uvicorn

    port = int(
        os.environ.get(
            "PORT",
            "10000",
        )
    )

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
