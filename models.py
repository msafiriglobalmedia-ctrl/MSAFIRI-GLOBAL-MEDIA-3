from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), default="")
    bio = Column(Text, default="")
    location = Column(String(100), default="")
    avatar_url = Column(String(500), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    statuses = relationship("Status", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "bio": self.bio,
            "location": self.location,
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    caption = Column(Text, default="")
    media_url = Column(String(500), default="")
    media_type = Column(String(20), default="text")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="posts")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "caption": self.caption,
            "media_url": self.media_url,
            "media_type": self.media_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Follow(Base):
    __tablename__ = "follows"

    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    following_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Status(Base):
    __tablename__ = "statuses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    media_url = Column(String(500), default="")
    caption = Column(Text, default="")
    media_type = Column(String(20), default="image")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="statuses")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "media_url": self.media_url,
            "caption": self.caption,
            "media_type": self.media_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
