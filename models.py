# ============================================================
# MSAFIRI GLOBAL MEDIA — Database Models
# Version: Media V0.0.1
# Purpose: User, Post, Story, Status, Video, Conversation,
#          Message, Like, Comment, Follow, Notification,
#          Product, Community
# ============================================================

from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from database import db


# ============================================================
# 1. USER MODEL
# ============================================================
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100))
    bio = db.Column(db.Text)
    location = db.Column(db.String(100))
    profile_pic = db.Column(db.String(255))
    cover_pic = db.Column(db.String(255))
    phone = db.Column(db.String(20))
    is_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    posts = db.relationship("Post", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    stories = db.relationship("Story", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    statuses = db.relationship("Status", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    videos = db.relationship("Video", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    likes = db.relationship("Like", backref="user", lazy="dynamic", cascade="all, delete-orphan")
    products = db.relationship("Product", backref="seller", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self, include_email=False):
        data = {
            "id": self.id,
            "username": self.username,
            "name": self.name or self.username,
            "bio": self.bio,
            "location": self.location,
            "profile_pic": self.profile_pic,
            "cover_pic": self.cover_pic,
            "is_verified": self.is_verified,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "posts_count": self.posts.count(),
            "followers_count": Follow.query.filter_by(following_id=self.id).count(),
            "following_count": Follow.query.filter_by(follower_id=self.id).count()
        }
        if include_email:
            data["email"] = self.email
            data["phone"] = self.phone
        return data


# ============================================================
# 2. POST MODEL
# ============================================================
class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = db.Column(db.Text)
    media_url = db.Column(db.String(255))
    media_type = db.Column(db.String(20))  # image, video, file
    is_public = db.Column(db.Boolean, default=True)
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    shares_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    likes = db.relationship("Like", backref="post", lazy="dynamic", cascade="all, delete-orphan")
    comments = db.relationship("Comment", backref="post", lazy="dynamic", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user.to_dict() if self.user else None,
            "content": self.content,
            "media_url": self.media_url,
            "media_type": self.media_type,
            "likes_count": self.likes_count,
            "comments_count": self.comments_count,
            "shares_count": self.shares_count,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# 3. STORY MODEL (24-hour expiry)
# ============================================================
class Story(db.Model):
    __tablename__ = "stories"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    media_url = db.Column(db.String(255), nullable=False)
    media_type = db.Column(db.String(20), default="image")  # image, video
    caption = db.Column(db.String(255))
    views_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24), index=True)

    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user.to_dict() if self.user else None,
            "media_url": self.media_url,
            "media_type": self.media_type,
            "caption": self.caption,
            "views_count": self.views_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


# ============================================================
# 4. STATUS MODEL (WhatsApp-style status)
# ============================================================
class Status(db.Model):
    __tablename__ = "statuses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = db.Column(db.Text)
    media_url = db.Column(db.String(255))
    background_color = db.Column(db.String(20), default="#4f46e5")
    text_color = db.Column(db.String(20), default="#ffffff")
    views_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    expires_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(hours=24))

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user.to_dict() if self.user else None,
            "content": self.content,
            "media_url": self.media_url,
            "background_color": self.background_color,
            "text_color": self.text_color,
            "views_count": self.views_count,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# 5. VIDEO MODEL (TikTok-style feed)
# ============================================================
class Video(db.Model):
    __tablename__ = "videos"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_url = db.Column(db.String(255), nullable=False)
    thumbnail_url = db.Column(db.String(255))
    caption = db.Column(db.Text)
    music = db.Column(db.String(255))
    likes_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    shares_count = db.Column(db.Integer, default=0)
    views_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user.to_dict() if self.user else None,
            "video_url": self.video_url,
            "thumbnail_url": self.thumbnail_url,
            "caption": self.caption,
            "music": self.music,
            "likes_count": self.likes_count,
            "comments_count": self.comments_count,
            "shares_count": self.shares_count,
            "views_count": self.views_count,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# 6. CONVERSATION MODEL (Chat)
# ============================================================
class Conversation(db.Model):
    __tablename__ = "conversations"

    id = db.Column(db.Integer, primary_key=True)
    user1_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user2_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    last_message = db.Column(db.String(255))
    last_message_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    messages = db.relationship("Message", backref="conversation", lazy="dynamic", cascade="all, delete-orphan")
    user1 = db.relationship("User", foreign_keys=[user1_id])
    user2 = db.relationship("User", foreign_keys=[user2_id])

    def other_user(self, current_user_id):
        """Get the other user in this conversation."""
        return self.user2 if self.user1_id == current_user_id else self.user1

    def to_dict(self, current_user_id):
        other = self.other_user(current_user_id)
        unread = self.messages.filter_by(
            receiver_id=current_user_id,
            is_read=False
        ).count()
        return {
            "id": self.id,
            "user": other.to_dict() if other else None,
            "last_message": self.last_message,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "unread_count": unread
        }


# ============================================================
# 7. MESSAGE MODEL
# ============================================================
class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = db.Column(db.Text)
    media_url = db.Column(db.String(255))
    media_type = db.Column(db.String(20))  # image, video, voice, document
    is_read = db.Column(db.Boolean, default=False)
    is_delivered = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    sender = db.relationship("User", foreign_keys=[sender_id])
    receiver = db.relationship("User", foreign_keys=[receiver_id])

    def to_dict(self, current_user_id=None):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "sender_id": self.sender_id,
            "receiver_id": self.receiver_id,
            "content": self.content,
            "media_url": self.media_url,
            "media_type": self.media_type,
            "is_read": self.is_read,
            "is_mine": self.sender_id == current_user_id if current_user_id else False,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# 8. LIKE MODEL
# ============================================================
class Like(db.Model):
    __tablename__ = "likes"
    __table_args__ = (
        db.UniqueConstraint("user_id", "post_id", name="unique_user_post_like"),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# 9. COMMENT MODEL
# ============================================================
class Comment(db.Model):
    __tablename__ = "comments"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user.to_dict() if self.user else None,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# 10. FOLLOW MODEL
# ============================================================
class Follow(db.Model):
    __tablename__ = "follows"
    __table_args__ = (
        db.UniqueConstraint("follower_id", "following_id", name="unique_follow"),
    )

    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    following_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# 11. NOTIFICATION MODEL
# ============================================================
class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    type = db.Column(db.String(30))  # like, comment, follow, message, mention
    message = db.Column(db.String(255))
    reference_id = db.Column(db.Integer)  # post_id, comment_id, etc.
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# 12. PRODUCT MODEL (Marketplace)
# ============================================================
class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(10), default="TZS")
    image_url = db.Column(db.String(255))
    category = db.Column(db.String(50))  # products, services, digital
    location = db.Column(db.String(100))
    contact = db.Column(db.String(50))
    shipping_cost = db.Column(db.Float, default=0)
    is_available = db.Column(db.Boolean, default=True)
    views_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id,
            "seller": self.seller.to_dict() if self.seller else None,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "currency": self.currency,
            "image_url": self.image_url,
            "category": self.category,
            "location": self.location,
            "contact": self.contact,
            "shipping_cost": self.shipping_cost,
            "is_available": self.is_available,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# 13. COMMUNITY MODEL
# ============================================================
class Community(db.Model):
    __tablename__ = "communities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(50))
    image_url = db.Column(db.String(255))
    creator_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"))
    members_count = db.Column(db.Integer, default=0)
    is_public = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "image_url": self.image_url,
            "members_count": self.members_count,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


# ============================================================
# 14. COMMUNITY MEMBER (Join table)
# ============================================================
class CommunityMember(db.Model):
    __tablename__ = "community_members"
    __table_args__ = (
        db.UniqueConstraint("community_id", "user_id", name="unique_community_member"),
    )

    id = db.Column(db.Integer, primary_key=True)
    community_id = db.Column(db.Integer, db.ForeignKey("communities.id", ondelete="CASCADE"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = db.Column(db.String(20), default="member")  # member, admin
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# 15. EXPORTS
# ============================================================
__all__ = [
    "User",
    "Post",
    "Story",
    "Status",
    "Video",
    "Conversation",
    "Message",
    "Like",
    "Comment",
    "Follow",
    "Notification",
    "Product",
    "Community",
    "CommunityMember"
]
