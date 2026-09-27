# ============================================================
# MSAFIRI GLOBAL MEDIA
# routers/message.py
#
# WhatsApp-style Messaging Router
# ============================================================

from __future__ import annotations

import os
import uuid
import mimetypes
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
    Query,
)

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    UniqueConstraint,
    or_,
    and_,
)
from sqlalchemy.orm import (
    Session,
)

from database import Base, get_db
from models import User
from auth import require_user


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/api/messages",
    tags=["messages"],
)


# ============================================================
# CONFIGURATION
# ============================================================

MESSAGE_UPLOAD_DIR = Path("static/message_uploads")

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

DOCUMENT_EXTENSIONS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".txt",
    ".csv",
    ".zip",
}

AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".ogg",
    ".m4a",
    ".aac",
    ".webm",
}


MAX_IMAGE_SIZE = 15 * 1024 * 1024
MAX_VIDEO_SIZE = 100 * 1024 * 1024
MAX_AUDIO_SIZE = 25 * 1024 * 1024
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024


# ============================================================
# DATABASE MODELS
# ============================================================

class Message(Base):
    __tablename__ = "messages"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    sender_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    receiver_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    text = Column(
        Text,
        default="",
    )

    message_type = Column(
        String(30),
        default="text",
    )

    media_url = Column(
        String(500),
        default="",
    )

    file_name = Column(
        String(255),
        default="",
    )

    file_size = Column(
        Integer,
        default=0,
    )

    mime_type = Column(
        String(150),
        default="",
    )

    duration = Column(
        Integer,
        default=0,
    )

    is_read = Column(
        Boolean,
        default=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )


class ChatSetting(Base):
    __tablename__ = "chat_settings"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    other_user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    wallpaper_url = Column(
        String(500),
        default="",
    )

    wallpaper_type = Column(
        String(30),
        default="default",
    )

    wallpaper_name = Column(
        String(255),
        default="",
    )

    muted = Column(
        Boolean,
        default=False,
    )

    archived = Column(
        Boolean,
        default=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "other_user_id",
            name="uq_chat_setting_pair",
        ),
    )


class ChatBlock(Base):
    __tablename__ = "chat_blocks"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    blocker_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    blocked_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "blocker_id",
            "blocked_id",
            name="uq_chat_block",
        ),
    )


class ChatPin(Base):
    __tablename__ = "chat_pins"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    other_user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "other_user_id",
            name="uq_chat_pin",
        ),
    )


class ChatFavorite(Base):
    __tablename__ = "chat_favorites"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    other_user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "other_user_id",
            name="uq_chat_favorite",
        ),
    )


class TypingState(Base):
    __tablename__ = "typing_states"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    other_user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    state = Column(
        String(30),
        default="idle",
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "other_user_id",
            name="uq_typing_pair",
        ),
    )


class CallSession(Base):
    __tablename__ = "call_sessions"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    caller_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    receiver_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    call_type = Column(
        String(20),
        default="voice",
    )

    status = Column(
        String(30),
        default="calling",
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
    )

    ended_at = Column(
        DateTime,
        nullable=True,
    )


# ============================================================
# CREATE MESSAGE TABLES
# ============================================================

def ensure_message_tables():
    """
    Creates messaging tables if they don't already exist.
    """
    try:
        bind = Base.metadata.bind

        if bind is not None:
            Base.metadata.create_all(
                bind=bind,
                tables=[
                    Message.__table__,
                    ChatSetting.__table__,
                    ChatBlock.__table__,
                    ChatPin.__table__,
                    ChatFavorite.__table__,
                    TypingState.__table__,
                    CallSession.__table__,
                ],
            )
    except Exception:
        # Do not crash application import.
        # Main database initialization can create tables later.
        pass


try:
    ensure_message_tables()
except Exception:
    pass


# ============================================================
# HELPERS
# ============================================================

def ensure_upload_dir():
    MESSAGE_UPLOAD_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


def get_user_or_404(
    db: Session,
    user_id: int,
):
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    return user


def user_initial(user: User):
    name = (
        user.full_name
        or user.username
        or "U"
    ).strip()

    return name[:1].upper()


def serialize_user(user: User):
    return {
        "id": user.id,
        "username": user.username or "",
        "full_name": user.full_name or "",
        "avatar_url": user.avatar_url or "",
    }


def serialize_message(
    message: Message,
    current_user_id: int,
):
    return {
        "id": message.id,
        "sender_id": message.sender_id,
        "receiver_id": message.receiver_id,

        "text": message.text or "",

        "message_type": (
            message.message_type
            or "text"
        ),

        "media_url": (
            message.media_url
            or ""
        ),

        "file_name": (
            message.file_name
            or ""
        ),

        "file_size": (
            message.file_size
            or 0
        ),

        "mime_type": (
            message.mime_type
            or ""
        ),

        "duration": (
            message.duration
            or 0
        ),

        "is_read": bool(
            message.is_read
        ),

        "mine": (
            message.sender_id
            == current_user_id
        ),

        "created_at": (
            message.created_at.isoformat()
            if message.created_at
            else None
        ),
    }


def is_blocked(
    db: Session,
    user_a: int,
    user_b: int,
):
    return (
        db.query(ChatBlock)
        .filter(
            or_(
                and_(
                    ChatBlock.blocker_id
                    == user_a,
                    ChatBlock.blocked_id
                    == user_b,
                ),
                and_(
                    ChatBlock.blocker_id
                    == user_b,
                    ChatBlock.blocked_id
                    == user_a,
                ),
            )
        )
        .first()
        is not None
    )


def get_chat_setting(
    db: Session,
    user_id: int,
    other_user_id: int,
):
    return (
        db.query(ChatSetting)
        .filter(
            ChatSetting.user_id == user_id,
            ChatSetting.other_user_id
            == other_user_id,
        )
        .first()
    )


def get_or_create_chat_setting(
    db: Session,
    user_id: int,
    other_user_id: int,
):
    setting = get_chat_setting(
        db,
        user_id,
        other_user_id,
    )

    if setting:
        return setting

    setting = ChatSetting(
        user_id=user_id,
        other_user_id=other_user_id,
        wallpaper_url="",
        wallpaper_type="default",
        wallpaper_name="",
    )

    db.add(setting)
    db.commit()
    db.refresh(setting)

    return setting


def last_seen_status(
    user: User,
):
    """
    User model currently has no last_seen column.
    We therefore use created_at only as a safe fallback.
    Real presence can later be upgraded with Redis/WebSocket.
    """

    return {
        "online": False,
        "last_seen": (
            user.created_at.isoformat()
            if user.created_at
            else None
        ),
    }


# ============================================================
# CHAT LIST
# ============================================================

@router.get("")
def chat_list(
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Returns WhatsApp-style chat list.

    Includes:
    - person
    - profile image
    - last message
    - timestamp
    - unread count
    - pinned
    - favourite
    - blocked
    - online/last seen
    """

    other_ids = set()

    sent_ids = (
        db.query(Message.receiver_id)
        .filter(
            Message.sender_id == user.id
        )
        .all()
    )

    received_ids = (
        db.query(Message.sender_id)
        .filter(
            Message.receiver_id == user.id
        )
        .all()
    )

    for row in sent_ids:
        other_ids.add(row[0])

    for row in received_ids:
        other_ids.add(row[0])

    result = []

    for other_id in other_ids:

        other = (
            db.query(User)
            .filter(User.id == other_id)
            .first()
        )

        if not other:
            continue

        last_message = (
            db.query(Message)
            .filter(
                or_(
                    and_(
                        Message.sender_id
                        == user.id,
                        Message.receiver_id
                        == other_id,
                    ),
                    and_(
                        Message.sender_id
                        == other_id,
                        Message.receiver_id
                        == user.id,
                    ),
                )
            )
            .order_by(
                Message.created_at.desc()
            )
            .first()
        )

        unread = (
            db.query(Message)
            .filter(
                Message.sender_id == other_id,
                Message.receiver_id == user.id,
                Message.is_read.is_(False),
            )
            .count()
        )

        pinned = (
            db.query(ChatPin)
            .filter(
                ChatPin.user_id == user.id,
                ChatPin.other_user_id
                == other_id,
            )
            .first()
            is not None
        )

        favorite = (
            db.query(ChatFavorite)
            .filter(
                ChatFavorite.user_id == user.id,
                ChatFavorite.other_user_id
                == other_id,
            )
            .first()
            is not None
        )

        blocked = is_blocked(
            db,
            user.id,
            other_id,
        )

        presence = last_seen_status(
            other
        )

        result.append({
            "user": serialize_user(
                other
            ),

            "initial": user_initial(
                other
            ),

            "last_message": (
                serialize_message(
                    last_message,
                    user.id,
                )
                if last_message
                else None
            ),

            "unread": unread,

            "pinned": pinned,

            "favorite": favorite,

            "blocked": blocked,

            **presence,
        })

    result.sort(
        key=lambda x: (
            not x["pinned"],
            not x["favorite"],
            (
                x["last_message"]["created_at"]
                if x["last_message"]
                else ""
            ),
        ),
        reverse=False,
    )

    return {
        "ok": True,
        "chats": result,
        "count": len(result),
    }


# ============================================================
# SEARCH USERS
# ============================================================

@router.get("/users/search")
def search_users(
    q: str = Query(
        "",
        min_length=0,
        max_length=100,
    ),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    q = (q or "").strip()

    if not q:
        return {
            "ok": True,
            "users": [],
        }

    users = (
        db.query(User)
        .filter(
            User.id != user.id,
            or_(
                User.username.ilike(
                    f"%{q}%"
                ),
                User.full_name.ilike(
                    f"%{q}%"
                ),
                User.email.ilike(
                    f"%{q}%"
                ),
            ),
        )
        .limit(30)
        .all()
    )

    return {
        "ok": True,
        "users": [
            {
                **serialize_user(x),
                "initial": user_initial(x),
                **last_seen_status(x),
            }
            for x in users
        ],
    }


# ============================================================
# OPEN CHAT
# ============================================================

@router.get("/{other_user_id}")
def get_conversation(
    other_user_id: int,
    limit: int = Query(
        100,
        ge=1,
        le=500,
    ),
    before_id: Optional[int] = Query(
        None
    ),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    other = get_user_or_404(
        db,
        other_user_id,
    )

    blocked = is_blocked(
        db,
        user.id,
        other_user_id,
    )

    query = (
        db.query(Message)
        .filter(
            or_(
                and_(
                    Message.sender_id
                    == user.id,
                    Message.receiver_id
                    == other_user_id,
                ),
                and_(
                    Message.sender_id
                    == other_user_id,
                    Message.receiver_id
                    == user.id,
                ),
            )
        )
    )

    if before_id is not None:
        query = query.filter(
            Message.id < before_id
        )

    messages = (
        query
        .order_by(
            Message.created_at.desc()
        )
        .limit(limit)
        .all()
    )

    messages.reverse()

    # Mark incoming messages as read.
    (
        db.query(Message)
        .filter(
            Message.sender_id
            == other_user_id,
            Message.receiver_id
            == user.id,
            Message.is_read.is_(False),
        )
        .update(
            {
                Message.is_read: True
            },
            synchronize_session=False,
        )
    )

    db.commit()

    setting = get_or_create_chat_setting(
        db,
        user.id,
        other_user_id,
    )

    pinned = (
        db.query(ChatPin)
        .filter(
            ChatPin.user_id == user.id,
            ChatPin.other_user_id
            == other_user_id,
        )
        .first()
        is not None
    )

    favorite = (
        db.query(ChatFavorite)
        .filter(
            ChatFavorite.user_id == user.id,
            ChatFavorite.other_user_id
            == other_user_id,
        )
        .first()
        is not None
    )

    return {
        "ok": True,

        "user": serialize_user(
            other
        ),

        "initial": user_initial(
            other
        ),

        "presence": last_seen_status(
            other
        ),

        "blocked": blocked,

        "pinned": pinned,

        "favorite": favorite,

        "wallpaper": {
            "url": (
                setting.wallpaper_url
                or ""
            ),
            "type": (
                setting.wallpaper_type
                or "default"
            ),
            "name": (
                setting.wallpaper_name
                or ""
            ),
        },

        "messages": [
            serialize_message(
                message,
                user.id,
            )
            for message in messages
        ],
    }


# ============================================================
# SEND TEXT MESSAGE
# ============================================================

@router.post("/{other_user_id}/send")
def send_message(
    other_user_id: int,
    text: str = Form(""),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    other = get_user_or_404(
        db,
        other_user_id,
    )

    text = (text or "").strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    if is_blocked(
        db,
        user.id,
        other_user_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="This chat is blocked.",
        )

    message = Message(
        sender_id=user.id,
        receiver_id=other.id,
        text=text,
        message_type="text",
        is_read=False,
        created_at=datetime.utcnow(),
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return {
        "ok": True,
        "message": serialize_message(
            message,
            user.id,
        ),
    }


# ============================================================
# SEND MEDIA / DOCUMENT / VOICE
# ============================================================

@router.post("/{other_user_id}/upload")
async def upload_message_media(
    other_user_id: int,
    file: UploadFile = File(...),
    message_type: str = Form("auto"),
    caption: str = Form(""),
    duration: int = Form(0),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    other = get_user_or_404(
        db,
        other_user_id,
    )

    if is_blocked(
        db,
        user.id,
        other_user_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="This chat is blocked.",
        )

    ensure_upload_dir()

    original_name = (
        file.filename
        or "file"
    )

    extension = Path(
        original_name
    ).suffix.lower()

    content_type = (
        file.content_type
        or mimetypes.guess_type(
            original_name
        )[0]
        or ""
    ).lower()

    # --------------------------------------------
    # Detect type
    # --------------------------------------------

    if message_type == "auto":

        if (
            extension in IMAGE_EXTENSIONS
            or content_type.startswith(
                "image/"
            )
        ):
            message_type = "image"

        elif (
            extension in VIDEO_EXTENSIONS
            or content_type.startswith(
                "video/"
            )
        ):
            message_type = "video"

        elif (
            extension in AUDIO_EXTENSIONS
            or content_type.startswith(
                "audio/"
            )
        ):
            message_type = "voice"

        else:
            message_type = "document"

    allowed_types = {
        "image",
        "video",
        "voice",
        "document",
    }

    if message_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Invalid message type.",
        )

    # --------------------------------------------
    # Maximum size
    # --------------------------------------------

    if message_type == "image":
        max_size = MAX_IMAGE_SIZE

    elif message_type == "video":
        max_size = MAX_VIDEO_SIZE

    elif message_type == "voice":
        max_size = MAX_AUDIO_SIZE

    else:
        max_size = MAX_DOCUMENT_SIZE

    data = await file.read()

    if not data:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty.",
        )

    if len(data) > max_size:
        raise HTTPException(
            status_code=413,
            detail=(
                "File too large. Maximum allowed "
                f"size is "
                f"{max_size // (1024 * 1024)}MB."
            ),
        )

    # --------------------------------------------
    # Safe extension
    # --------------------------------------------

    safe_extension = extension

    if not safe_extension:
        if message_type == "image":
            safe_extension = ".jpg"

        elif message_type == "video":
            safe_extension = ".mp4"

        elif message_type == "voice":
            safe_extension = ".webm"

        else:
            safe_extension = ".bin"

    filename = (
        f"{uuid.uuid4().hex}"
        f"{safe_extension}"
    )

    destination = (
        MESSAGE_UPLOAD_DIR
        / filename
    )

    with open(
        destination,
        "wb",
    ) as output:
        output.write(data)

    media_url = (
        f"/static/message_uploads/"
        f"{filename}"
    )

    message = Message(
        sender_id=user.id,
        receiver_id=other.id,
        text=(
            caption.strip()
            if caption
            else ""
        ),
        message_type=message_type,
        media_url=media_url,
        file_name=original_name,
        file_size=len(data),
        mime_type=content_type,
        duration=max(
            0,
            duration,
        ),
        is_read=False,
        created_at=datetime.utcnow(),
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return {
        "ok": True,
        "message": serialize_message(
            message,
            user.id,
        ),
    }


# ============================================================
# DELETE MESSAGE
# ============================================================

@router.delete(
    "/message/{message_id}"
)
def delete_message(
    message_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    message = (
        db.query(Message)
        .filter(
            Message.id == message_id
        )
        .first()
    )

    if not message:
        raise HTTPException(
            status_code=404,
            detail="Message not found.",
        )

    if message.sender_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="You can only delete your own messages.",
        )

    db.delete(message)
    db.commit()

    return {
        "ok": True,
        "message": "Message deleted.",
    }


# ============================================================
# MARK CHAT AS READ
# ============================================================

@router.post(
    "/{other_user_id}/read"
)
def mark_chat_read(
    other_user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    get_user_or_404(
        db,
        other_user_id,
    )

    updated = (
        db.query(Message)
        .filter(
            Message.sender_id
            == other_user_id,
            Message.receiver_id
            == user.id,
            Message.is_read.is_(False),
        )
        .update(
            {
                Message.is_read: True
            },
            synchronize_session=False,
        )
    )

    db.commit()

    return {
        "ok": True,
        "marked_read": updated,
    }


# ============================================================
# TYPING INDICATOR
# ============================================================

@router.post(
    "/{other_user_id}/typing"
)
def update_typing(
    other_user_id: int,
    state: str = Form("typing"),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    get_user_or_404(
        db,
        other_user_id,
    )

    allowed = {
        "typing",
        "recording",
        "idle",
    }

    if state not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                "State must be typing, "
                "recording or idle."
            ),
        )

    existing = (
        db.query(TypingState)
        .filter(
            TypingState.user_id
            == user.id,
            TypingState.other_user_id
            == other_user_id,
        )
        .first()
    )

    now = datetime.utcnow()

    if existing:
        existing.state = state
        existing.updated_at = now

    else:
        existing = TypingState(
            user_id=user.id,
            other_user_id=other_user_id,
            state=state,
            updated_at=now,
        )

        db.add(existing)

    db.commit()

    return {
        "ok": True,
        "state": state,
        "updated_at": now.isoformat(),
    }


# ============================================================
# GET TYPING STATE
# ============================================================

@router.get(
    "/{other_user_id}/typing"
)
def get_typing(
    other_user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    state = (
        db.query(TypingState)
        .filter(
            TypingState.user_id
            == other_user_id,
            TypingState.other_user_id
            == user.id,
        )
        .first()
    )

    if not state:
        return {
            "ok": True,
            "typing": False,
            "recording": False,
            "state": "idle",
        }

    # State expires after 8 seconds.
    expired = (
        datetime.utcnow()
        - state.updated_at
        > timedelta(seconds=8)
    )

    if expired:
        return {
            "ok": True,
            "typing": False,
            "recording": False,
            "state": "idle",
        }

    return {
        "ok": True,
        "typing": (
            state.state == "typing"
        ),
        "recording": (
            state.state == "recording"
        ),
        "state": state.state,
        "updated_at": (
            state.updated_at.isoformat()
        ),
    }


# ============================================================
# WALLPAPER
# ============================================================

@router.post(
    "/{other_user_id}/wallpaper"
)
async def set_wallpaper(
    other_user_id: int,
    wallpaper: UploadFile = File(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    get_user_or_404(
        db,
        other_user_id,
    )

    ensure_upload_dir()

    filename_original = (
        wallpaper.filename
        or "wallpaper.jpg"
    )

    extension = Path(
        filename_original
    ).suffix.lower()

    if extension not in IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Wallpaper must be an image.",
        )

    data = await wallpaper.read()

    if len(data) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="Wallpaper is too large.",
        )

    filename = (
        f"wallpaper_"
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    destination = (
        MESSAGE_UPLOAD_DIR
        / filename
    )

    with open(
        destination,
        "wb",
    ) as output:
        output.write(data)

    url = (
        f"/static/message_uploads/"
        f"{filename}"
    )

    setting = get_or_create_chat_setting(
        db,
        user.id,
        other_user_id,
    )

    setting.wallpaper_url = url
    setting.wallpaper_type = "image"
    setting.wallpaper_name = (
        filename_original
    )
    setting.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(setting)

    return {
        "ok": True,
        "wallpaper": {
            "url": setting.wallpaper_url,
            "type": setting.wallpaper_type,
            "name": setting.wallpaper_name,
        },
    }


# ============================================================
# RESET WALLPAPER
# ============================================================

@router.delete(
    "/{other_user_id}/wallpaper"
)
def reset_wallpaper(
    other_user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    get_user_or_404(
        db,
        other_user_id,
    )

    setting = get_or_create_chat_setting(
        db,
        user.id,
        other_user_id,
    )

    setting.wallpaper_url = ""
    setting.wallpaper_type = "default"
    setting.wallpaper_name = ""
    setting.updated_at = datetime.utcnow()

    db.commit()

    return {
        "ok": True,
        "wallpaper": {
            "url": "",
            "type": "default",
            "name": "",
        },
    }


# ============================================================
# BLOCK / UNBLOCK
# ============================================================

@router.post(
    "/{other_user_id}/block"
)
def block_chat(
    other_user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    other = get_user_or_404(
        db,
        other_user_id,
    )

    if other.id == user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot block yourself.",
        )

    existing = (
        db.query(ChatBlock)
        .filter(
            ChatBlock.blocker_id
            == user.id,
            ChatBlock.blocked_id
            == other.id,
        )
        .first()
    )

    if not existing:
        db.add(
            ChatBlock(
                blocker_id=user.id,
                blocked_id=other.id,
            )
        )

        db.commit()

    return {
        "ok": True,
        "blocked": True,
        "user_id": other.id,
    }


@router.delete(
    "/{other_user_id}/block"
)
def unblock_chat(
    other_user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    get_user_or_404(
        db,
        other_user_id,
    )

    existing = (
        db.query(ChatBlock)
        .filter(
            ChatBlock.blocker_id
            == user.id,
            ChatBlock.blocked_id
            == other_user_id,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()

    return {
        "ok": True,
        "blocked": False,
        "user_id": other_user_id,
    }


# ============================================================
# PIN / UNPIN
# ============================================================

@router.post(
    "/{other_user_id}/pin"
)
def pin_chat(
    other_user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    get_user_or_404(
        db,
        other_user_id,
    )

    existing = (
        db.query(ChatPin)
        .filter(
            ChatPin.user_id == user.id,
            ChatPin.other_user_id
            == other_user_id,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        pinned = False

    else:
        db.add(
            ChatPin(
                user_id=user.id,
                other_user_id=other_user_id,
            )
        )
        pinned = True

    db.commit()

    return {
        "ok": True,
        "pinned": pinned,
    }


# ============================================================
# FAVOURITE / UNFAVOURITE
# ============================================================

@router.post(
    "/{other_user_id}/favorite"
)
def favorite_chat(
    other_user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    get_user_or_404(
        db,
        other_user_id,
    )

    existing = (
        db.query(ChatFavorite)
        .filter(
            ChatFavorite.user_id
            == user.id,
            ChatFavorite.other_user_id
            == other_user_id,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        favorite = False

    else:
        db.add(
            ChatFavorite(
                user_id=user.id,
                other_user_id=other_user_id,
            )
        )
        favorite = True

    db.commit()

    return {
        "ok": True,
        "favorite": favorite,
    }


# ============================================================
# MUTE / UNMUTE
# ============================================================

@router.post(
    "/{other_user_id}/mute"
)
def mute_chat(
    other_user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    get_user_or_404(
        db,
        other_user_id,
    )

    setting = get_or_create_chat_setting(
        db,
        user.id,
        other_user_id,
    )

    setting.muted = not bool(
        setting.muted
    )

    setting.updated_at = datetime.utcnow()

    db.commit()

    return {
        "ok": True,
        "muted": bool(
            setting.muted
        ),
    }


# ============================================================
# ARCHIVE / UNARCHIVE
# ============================================================

@router.post(
    "/{other_user_id}/archive"
)
def archive_chat(
    other_user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    get_user_or_404(
        db,
        other_user_id,
    )

    setting = get_or_create_chat_setting(
        db,
        user.id,
        other_user_id,
    )

    setting.archived = not bool(
        setting.archived
    )

    setting.updated_at = datetime.utcnow()

    db.commit()

    return {
        "ok": True,
        "archived": bool(
            setting.archived
        ),
    }


# ============================================================
# TRANSLATION
# ============================================================

@router.post(
    "/{other_user_id}/translate"
)
def translate_message(
    other_user_id: int,
    text: str = Form(""),
    target_language: str = Form("en"),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    """
    Translation API placeholder.

    Translation engine will be connected in a future version.
    """

    get_user_or_404(
        db,
        other_user_id,
    )

    text = (text or "").strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Text cannot be empty.",
        )

    return {
        "ok": True,
        "available": False,
        "source_text": text,
        "target_language": target_language,
        "translated_text": text,
        "message": (
            "Translation will be enabled "
            "in a future version."
        ),
    }


# ============================================================
# VOICE CALL
# ============================================================

@router.post(
    "/{other_user_id}/call/voice"
)
def start_voice_call(
    other_user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    other = get_user_or_404(
        db,
        other_user_id,
    )

    if is_blocked(
        db,
        user.id,
        other_user_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Cannot call a blocked user.",
        )

    call = CallSession(
        caller_id=user.id,
        receiver_id=other.id,
        call_type="voice",
        status="calling",
        created_at=datetime.utcnow(),
    )

    db.add(call)
    db.commit()
    db.refresh(call)

    return {
        "ok": True,
        "call": {
            "id": call.id,
            "type": "voice",
            "status": call.status,
            "caller_id": call.caller_id,
            "receiver_id": call.receiver_id,
            "created_at": (
                call.created_at.isoformat()
            ),
        },
    }


# ============================================================
# VIDEO CALL
# ============================================================

@router.post(
    "/{other_user_id}/call/video"
)
def start_video_call(
    other_user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    other = get_user_or_404(
        db,
        other_user_id,
    )

    if is_blocked(
        db,
        user.id,
        other_user_id,
    ):
        raise HTTPException(
            status_code=403,
            detail="Cannot call a blocked user.",
        )

    call = CallSession(
        caller_id=user.id,
        receiver_id=other.id,
        call_type="video",
        status="calling",
        created_at=datetime.utcnow(),
    )

    db.add(call)
    db.commit()
    db.refresh(call)

    return {
        "ok": True,
        "call": {
            "id": call.id,
            "type": "video",
            "status": call.status,
            "caller_id": call.caller_id,
            "receiver_id": call.receiver_id,
            "created_at": (
                call.created_at.isoformat()
            ),
        },
    }


# ============================================================
# UPDATE CALL STATUS
# ============================================================

@router.patch(
    "/call/{call_id}"
)
def update_call(
    call_id: int,
    status: str = Form(...),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    allowed = {
        "calling",
        "ringing",
        "accepted",
        "connected",
        "rejected",
        "busy",
        "ended",
        "missed",
        "cancelled",
    }

    if status not in allowed:
        raise HTTPException(
            status_code=400,
            detail="Invalid call status.",
        )

    call = (
        db.query(CallSession)
        .filter(
            CallSession.id == call_id
        )
        .first()
    )

    if not call:
        raise HTTPException(
            status_code=404,
            detail="Call not found.",
        )

    if (
        call.caller_id != user.id
        and call.receiver_id != user.id
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not part of this call.",
        )

    call.status = status

    if status in {
        "ended",
        "rejected",
        "cancelled",
        "missed",
    }:
        call.ended_at = datetime.utcnow()

    db.commit()

    return {
        "ok": True,
        "call": {
            "id": call.id,
            "type": call.call_type,
            "status": call.status,
            "caller_id": call.caller_id,
            "receiver_id": call.receiver_id,
            "created_at": (
                call.created_at.isoformat()
            ),
            "ended_at": (
                call.ended_at.isoformat()
                if call.ended_at
                else None
            ),
        },
    }


# ============================================================
# CALL HISTORY
# ============================================================

@router.get(
    "/calls/history"
)
def call_history(
    limit: int = Query(
        50,
        ge=1,
        le=200,
    ),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    calls = (
        db.query(CallSession)
        .filter(
            or_(
                CallSession.caller_id
                == user.id,
                CallSession.receiver_id
                == user.id,
            )
        )
        .order_by(
            CallSession.created_at.desc()
        )
        .limit(limit)
        .all()
    )

    output = []

    for call in calls:

        other_id = (
            call.receiver_id
            if call.caller_id == user.id
            else call.caller_id
        )

        other = (
            db.query(User)
            .filter(User.id == other_id)
            .first()
        )

        output.append({
            "id": call.id,
            "type": call.call_type,
            "status": call.status,
            "direction": (
                "outgoing"
                if call.caller_id == user.id
                else "incoming"
            ),
            "user": (
                serialize_user(other)
                if other
                else None
            ),
            "created_at": (
                call.created_at.isoformat()
                if call.created_at
                else None
            ),
            "ended_at": (
                call.ended_at.isoformat()
                if call.ended_at
                else None
            ),
        })

    return {
        "ok": True,
        "calls": output,
    }


# ============================================================
# CHAT SETTINGS
# ============================================================

@router.get(
    "/{other_user_id}/settings"
)
def chat_settings(
    other_user_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    other = get_user_or_404(
        db,
        other_user_id,
    )

    setting = get_or_create_chat_setting(
        db,
        user.id,
        other_user_id,
    )

    pinned = (
        db.query(ChatPin)
        .filter(
            ChatPin.user_id == user.id,
            ChatPin.other_user_id
            == other_user_id,
        )
        .first()
        is not None
    )

    favorite = (
        db.query(ChatFavorite)
        .filter(
            ChatFavorite.user_id
            == user.id,
            ChatFavorite.other_user_id
            == other_user_id,
        )
        .first()
        is not None
    )

    blocked = is_blocked(
        db,
        user.id,
        other_user_id,
    )

    return {
        "ok": True,

        "user": serialize_user(
            other
        ),

        "blocked": blocked,

        "pinned": pinned,

        "favorite": favorite,

        "muted": bool(
            setting.muted
        ),

        "archived": bool(
            setting.archived
        ),

        "wallpaper": {
            "url": (
                setting.wallpaper_url
                or ""
            ),
            "type": (
                setting.wallpaper_type
                or "default"
            ),
            "name": (
                setting.wallpaper_name
                or ""
            ),
        },
    }


# ============================================================
# HEALTH
# ============================================================

@router.get(
    "/system/health"
)
def messages_health():
    return {
        "ok": True,
        "service": "MSAFIRI GLOBAL MEDIA Messaging",
        "version": "1.0.0",
        "features": [
            "chat_list",
            "text_messages",
            "image_messages",
            "video_messages",
            "document_messages",
            "voice_notes",
            "typing_indicator",
            "recording_indicator",
            "wallpaper",
            "block",
            "pin",
            "favorites",
            "mute",
            "archive",
            "translation_placeholder",
            "voice_calls",
            "video_calls",
            "call_history",
        ],
    }
