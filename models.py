from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from database import Base


# ============================================================
# USER
# ============================================================

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(
        String(50),
        unique=True,
        index=True,
        nullable=False
    )

    email = Column(
        String(120),
        unique=True,
        index=True,
        nullable=False
    )

    hashed_password = Column(
        String(255),
        nullable=False
    )

    full_name = Column(
        String(100),
        default=""
    )

    bio = Column(
        Text,
        default=""
    )

    location = Column(
        String(100),
        default=""
    )

    avatar_url = Column(
        String(500),
        default=""
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    posts = relationship(
        "Post",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    statuses = relationship(
        "Status",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    post_likes = relationship(
        "PostLike",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    comments = relationship(
        "PostComment",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    saved_posts = relationship(
        "PostSave",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    shares = relationship(
        "PostShare",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name or "",
            "bio": self.bio or "",
            "location": self.location or "",
            "avatar_url": self.avatar_url or "",
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }


# ============================================================
# POST
# ============================================================

class Post(Base):
    __tablename__ = "posts"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    caption = Column(
        Text,
        default=""
    )

    media_url = Column(
        String(500),
        default=""
    )

    media_type = Column(
        String(20),
        default="text"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )

    user = relationship(
        "User",
        back_populates="posts"
    )

    likes = relationship(
        "PostLike",
        back_populates="post",
        cascade="all, delete-orphan"
    )

    comments = relationship(
        "PostComment",
        back_populates="post",
        cascade="all, delete-orphan"
    )

    saves = relationship(
        "PostSave",
        back_populates="post",
        cascade="all, delete-orphan"
    )

    shares = relationship(
        "PostShare",
        back_populates="post",
        cascade="all, delete-orphan"
    )

    def to_dict(self, current_user_id=None):
        like_count = len(self.likes)
        comment_count = len(self.comments)
        save_count = len(self.saves)
        share_count = len(self.shares)

        liked = False
        saved = False

        if current_user_id is not None:
            liked = any(
                x.user_id == current_user_id
                for x in self.likes
            )

            saved = any(
                x.user_id == current_user_id
                for x in self.saves
            )

        return {
            "id": self.id,
            "user_id": self.user_id,

            "username": (
                self.user.username
                if self.user
                else ""
            ),

            "full_name": (
                self.user.full_name
                if self.user
                else ""
            ),

            "avatar_url": (
                self.user.avatar_url
                if self.user
                else ""
            ),

            "caption": self.caption or "",
            "media_url": self.media_url or "",
            "media_type": self.media_type or "text",

            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),

            "likes": like_count,
            "comments": comment_count,
            "saves": save_count,
            "shares": share_count,

            "liked": liked,
            "saved": saved,
        }


# ============================================================
# FOLLOW
# ============================================================

class Follow(Base):
    __tablename__ = "follows"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    follower_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    following_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "follower_id",
            "following_id",
            name="uq_follow_pair"
        ),
    )


# ============================================================
# STATUS / STORY
# ============================================================

class Status(Base):
    __tablename__ = "statuses"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    media_url = Column(
        String(500),
        default=""
    )

    caption = Column(
        Text,
        default=""
    )

    media_type = Column(
        String(20),
        default="image"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    user = relationship(
        "User",
        back_populates="statuses"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "media_url": self.media_url or "",
            "caption": self.caption or "",
            "media_type": self.media_type or "image",
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }


# ============================================================
# POST LIKE
# ============================================================

class PostLike(Base):
    __tablename__ = "post_likes"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    post = relationship(
        "Post",
        back_populates="likes"
    )

    user = relationship(
        "User",
        back_populates="post_likes"
    )

    __table_args__ = (
        UniqueConstraint(
            "post_id",
            "user_id",
            name="uq_post_like"
        ),
    )


# ============================================================
# POST COMMENT
# ============================================================

class PostComment(Base):
    __tablename__ = "post_comments"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    text = Column(
        Text,
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    post = relationship(
        "Post",
        back_populates="comments"
    )

    user = relationship(
        "User",
        back_populates="comments"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "post_id": self.post_id,
            "user_id": self.user_id,
            "username": (
                self.user.username
                if self.user
                else ""
            ),
            "full_name": (
                self.user.full_name
                if self.user
                else ""
            ),
            "avatar_url": (
                self.user.avatar_url
                if self.user
                else ""
            ),
            "text": self.text,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),
        }


# ============================================================
# POST SAVE
# ============================================================

class PostSave(Base):
    __tablename__ = "post_saves"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    post = relationship(
        "Post",
        back_populates="saves"
    )

    user = relationship(
        "User",
        back_populates="saved_posts"
    )

    __table_args__ = (
        UniqueConstraint(
            "post_id",
            "user_id",
            name="uq_post_save"
        ),
    )


# ============================================================
# POST SHARE / RESHARE
# ============================================================

class PostShare(Base):
    __tablename__ = "post_shares"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    post_id = Column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )

    post = relationship(
        "Post",
        back_populates="shares"
    )

    user = relationship(
        "User",
        back_populates="shares"
    )
