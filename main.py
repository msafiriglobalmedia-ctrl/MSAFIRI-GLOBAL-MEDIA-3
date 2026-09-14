# ============================================================
# MSAFIRI GLOBAL MEDIA V4.1
# FastAPI + PostgreSQL + JWT + LiveKit
# ============================================================

import os
import hashlib
import secrets
import mimetypes
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

import psycopg
from psycopg.rows import dict_row

from fastapi import (
    FastAPI,
    HTTPException,
    UploadFile,
    File,
    Form,
    Header,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr

from passlib.context import CryptContext
import jwt


# ============================================================
# CONFIG
# ============================================================

APP_NAME = "MSAFIRI GLOBAL MEDIA V4.1"

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
AVATAR_DIR = UPLOAD_DIR / "avatars"
POST_DIR = UPLOAD_DIR / "posts"
VOICE_DIR = UPLOAD_DIR / "voice"
CHAT_FILE_DIR = UPLOAD_DIR / "chat_files"
WALLPAPER_DIR = UPLOAD_DIR / "wallpapers"

for folder in [
    UPLOAD_DIR,
    AVATAR_DIR,
    POST_DIR,
    VOICE_DIR,
    CHAT_FILE_DIR,
    WALLPAPER_DIR,
]:
    folder.mkdir(parents=True, exist_ok=True)


DATABASE_URL = os.getenv("DATABASE_URL")

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_THIS_SECRET_IN_RENDER")
JWT_ALGORITHM = "HS256"
TOKEN_DAYS = 30

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "")

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title=APP_NAME,
    version="4.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE
# ============================================================

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
    )


# ============================================================
# DATABASE INITIALIZATION + MIGRATION
# ============================================================

def init_db():
    with get_conn() as conn:

        # ----------------------------------------------------
        # USERS
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                bio TEXT DEFAULT '',
                avatar TEXT,
                deleted_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # IMPORTANT:
        # Existing PostgreSQL tables are NOT changed by
        # CREATE TABLE IF NOT EXISTS.
        # These migrations repair older V3/V4 databases.

        conn.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS bio TEXT DEFAULT ''
        """)

        conn.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS avatar TEXT
        """)

        conn.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ
        """)

        conn.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS created_at
            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        """)

        conn.execute("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS updated_at
            TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        """)

        # ----------------------------------------------------
        # SESSIONS
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMPTZ NOT NULL,
                revoked BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_token
            ON sessions(token_hash)
        """)

        # ----------------------------------------------------
        # POSTS
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                caption TEXT NOT NULL DEFAULT '',
                media_url TEXT,
                media_type TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_posts_created
            ON posts(created_at DESC)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_posts_user
            ON posts(user_id)
        """)

        # ----------------------------------------------------
        # LIKES
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id, user_id)
            )
        """)

        # ----------------------------------------------------
        # COMMENTS
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                text TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ----------------------------------------------------
        # SAVED POSTS
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_posts (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id, user_id)
            )
        """)

        # ----------------------------------------------------
        # RESHARES
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS reshares (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id, user_id)
            )
        """)

        # ----------------------------------------------------
        # MESSAGES
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id BIGSERIAL PRIMARY KEY,
                sender_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                receiver_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                text TEXT DEFAULT '',
                media_url TEXT,
                media_type TEXT,
                duration_seconds INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_for_sender BOOLEAN NOT NULL DEFAULT FALSE,
                deleted_for_receiver BOOLEAN NOT NULL DEFAULT FALSE,
                seen BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_sender_receiver
            ON messages(sender_id, receiver_id, created_at DESC)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_receiver_sender
            ON messages(receiver_id, sender_id, created_at DESC)
        """)

        # ----------------------------------------------------
        # CHAT SETTINGS
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_settings (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                other_user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                wallpaper_url TEXT,
                pinned BOOLEAN NOT NULL DEFAULT FALSE,
                muted BOOLEAN NOT NULL DEFAULT FALSE,
                blocked BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, other_user_id)
            )
        """)

        # ----------------------------------------------------
        # BLOCKS
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS blocks (
                id BIGSERIAL PRIMARY KEY,
                blocker_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                blocked_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(blocker_id, blocked_id)
            )
        """)

        # ----------------------------------------------------
        # REPORTS
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id BIGSERIAL PRIMARY KEY,
                reporter_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                reported_user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                post_id BIGINT REFERENCES posts(id) ON DELETE CASCADE,
                reason TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ----------------------------------------------------
        # CALLS
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                id BIGSERIAL PRIMARY KEY,
                caller_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                receiver_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                room_name TEXT NOT NULL,
                call_type TEXT NOT NULL DEFAULT 'video',
                status TEXT NOT NULL DEFAULT 'started',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMPTZ
            )
        """)

        # ----------------------------------------------------
        # STATUSES
        # ----------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS statuses (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                text TEXT DEFAULT '',
                media_url TEXT,
                media_type TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMPTZ
            )
        """)

        # ----------------------------------------------------
        # FINAL NORMALIZATION
        # ----------------------------------------------------

        conn.execute("""
            UPDATE users
            SET bio = ''
            WHERE bio IS NULL
        """)

        conn.execute("""
            UPDATE users
            SET updated_at = CURRENT_TIMESTAMP
            WHERE updated_at IS NULL
        """)

        conn.commit()


@app.on_event("startup")
def startup():
    init_db()


# ============================================================
# MODELS
# ============================================================

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None


class MessageRequest(BaseModel):
    receiver_id: int
    text: str = ""


class CommentRequest(BaseModel):
    text: str


class ReportRequest(BaseModel):
    reason: str = ""


class ChatSettingsRequest(BaseModel):
    pinned: Optional[bool] = None
    muted: Optional[bool] = None
    blocked: Optional[bool] = None


class CallTokenRequest(BaseModel):
    receiver_id: int
    call_type: str = "video"


# ============================================================
# HELPERS
# ============================================================

def hash_token(token: str) -> str:
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()


def create_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=TOKEN_DAYS),
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def decode_token(token: str):
    try:
        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="Session expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )


def get_bearer_token(
    authorization: Optional[str],
) -> str:

    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization required",
        )

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=401,
            detail="Bearer token required",
        )

    return authorization.split(" ", 1)[1].strip()


def require_user(
    authorization: Optional[str],
):

    token = get_bearer_token(authorization)

    payload = decode_token(token)

    user_id = int(payload["sub"])

    token_hash = hash_token(token)

    with get_conn() as conn:

        user = conn.execute("""
            SELECT
                u.id,
                u.name,
                u.email,
                u.bio,
                u.avatar,
                u.created_at,
                u.updated_at
            FROM sessions s
            JOIN users u
                ON u.id = s.user_id
            WHERE s.token_hash = %s
              AND s.revoked = FALSE
              AND s.expires_at > CURRENT_TIMESTAMP
              AND u.id = %s
              AND u.deleted_at IS NULL
            LIMIT 1
        """, (token_hash, user_id)).fetchone()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Session not found",
        )

    return user


def safe_filename(filename: str) -> str:
    original = Path(filename or "file").name

    ext = Path(original).suffix.lower()

    allowed = {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".mp4",
        ".mov",
        ".webm",
        ".m4a",
        ".mp3",
        ".wav",
        ".ogg",
        ".pdf",
        ".doc",
        ".docx",
        ".txt",
        ".zip",
    }

    if ext not in allowed:
        ext = ""

    return secrets.token_hex(16) + ext


def public_file_url(path: Path) -> str:
    relative = path.relative_to(BASE_DIR)

    return "/files/" + str(relative).replace("\\", "/")


# ============================================================
# ROOT / HEALTH
# ============================================================

@app.get("/")
def root():
    return {
        "app": APP_NAME,
        "version": "4.1.0",
        "status": "online",
        "database": "configured" if DATABASE_URL else "missing",
        "livekit": bool(
            LIVEKIT_URL
            and LIVEKIT_API_KEY
            and LIVEKIT_API_SECRET
        ),
    }


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": "4.1.0",
    }


@app.get("/api/health/db")
def database_health():

    if not DATABASE_URL:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL is missing",
        )

    try:
        with get_conn() as conn:
            row = conn.execute("""
                SELECT CURRENT_TIMESTAMP AS server_time
            """).fetchone()

        return {
            "status": "ok",
            "database": "postgresql",
            "server_time": row["server_time"],
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}",
        )


# ============================================================
# FILE SERVING
# ============================================================

@app.get("/files/{file_path:path}")
def serve_file(file_path: str):

    requested = (BASE_DIR / file_path).resolve()

    upload_root = UPLOAD_DIR.resolve()

    if not str(requested).startswith(
        str(upload_root)
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden",
        )

    if not requested.exists() or not requested.is_file():
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    return FileResponse(
        requested,
        media_type=mimetypes.guess_type(
            str(requested)
        )[0] or "application/octet-stream",
    )


# ============================================================
# AUTH — REGISTER
# ============================================================

@app.post("/api/register")
def register(data: RegisterRequest):

    name = data.name.strip()
    email = str(data.email).strip().lower()
    password = data.password

    if len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Name is too short",
        )

    if len(password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 6 characters",
        )

    password_hash = pwd_context.hash(password)

    with get_conn() as conn:

        existing = conn.execute("""
            SELECT id, deleted_at
            FROM users
            WHERE email = %s
            LIMIT 1
        """, (email,)).fetchone()

        if existing:

            if existing["deleted_at"] is not None:
                conn.execute("""
                    UPDATE users
                    SET
                        name = %s,
                        password_hash = %s,
                        deleted_at = NULL,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (
                    name,
                    password_hash,
                    existing["id"],
                ))

                user_id = existing["id"]

            else:
                raise HTTPException(
                    status_code=409,
                    detail="An account with this email already exists",
                )

        else:

            row = conn.execute("""
                INSERT INTO users (
                    name,
                    email,
                    password_hash,
                    bio
                )
                VALUES (%s, %s, %s, '')
                RETURNING
                    id,
                    name,
                    email,
                    bio,
                    avatar,
                    created_at,
                    updated_at
            """, (
                name,
                email,
                password_hash,
            )).fetchone()

            user_id = row["id"]

        token = create_token(user_id)

        token_hash = hash_token(token)

        expires = datetime.now(
            timezone.utc
        ) + timedelta(days=TOKEN_DAYS)

        conn.execute("""
            INSERT INTO sessions (
                user_id,
                token_hash,
                expires_at
            )
            VALUES (%s, %s, %s)
        """, (
            user_id,
            token_hash,
            expires,
        ))

        conn.commit()

        user = conn.execute("""
            SELECT
                id,
                name,
                email,
                bio,
                avatar,
                created_at,
                updated_at
            FROM users
            WHERE id = %s
        """, (user_id,)).fetchone()

    return {
        "message": "Account created successfully",
        "token": token,
        "access_token": token,
        "user": user,
    }


# ============================================================
# AUTH — LOGIN
# ============================================================

@app.post("/api/login")
def login(data: LoginRequest):

    email = str(data.email).strip().lower()

    with get_conn() as conn:

        user = conn.execute("""
            SELECT
                id,
                name,
                email,
                password_hash,
                bio,
                avatar,
                created_at,
                updated_at
            FROM users
            WHERE email = %s
              AND deleted_at IS NULL
            LIMIT 1
        """, (email,)).fetchone()

        if not user:
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

        if not pwd_context.verify(
            data.password,
            user["password_hash"],
        ):
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password",
            )

        token = create_token(user["id"])

        token_hash = hash_token(token)

        expires = datetime.now(
            timezone.utc
        ) + timedelta(days=TOKEN_DAYS)

        conn.execute("""
            INSERT INTO sessions (
                user_id,
                token_hash,
                expires_at
            )
            VALUES (%s, %s, %s)
        """, (
            user["id"],
            token_hash,
            expires,
        ))

        conn.commit()

    user.pop("password_hash", None)

    return {
        "message": "Login successful",
        "token": token,
        "access_token": token,
        "user": user,
    }


# ============================================================
# LOGOUT
# ============================================================

@app.post("/api/logout")
def logout(
    authorization: Optional[str] = Header(default=None),
):

    token = get_bearer_token(authorization)

    token_hash = hash_token(token)

    with get_conn() as conn:

        conn.execute("""
            UPDATE sessions
            SET revoked = TRUE
            WHERE token_hash = %s
        """, (token_hash,))

        conn.commit()

    return {
        "message": "Logged out successfully",
    }


# ============================================================
# CURRENT USER
# ============================================================

@app.get("/api/me")
def me(
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    return {
        "user": user,
    }


# ============================================================
# PROFILE
# ============================================================

@app.patch("/api/profile")
def update_profile(
    data: ProfileUpdate,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    name = (
        data.name.strip()
        if data.name is not None
        else user["name"]
    )

    bio = (
        data.bio.strip()
        if data.bio is not None
        else user["bio"]
    )

    if len(name) < 2:
        raise HTTPException(
            status_code=400,
            detail="Name is too short",
        )

    with get_conn() as conn:

        updated = conn.execute("""
            UPDATE users
            SET
                name = %s,
                bio = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING
                id,
                name,
                email,
                bio,
                avatar,
                created_at,
                updated_at
        """, (
            name,
            bio,
            user["id"],
        )).fetchone()

        conn.commit()

    return {
        "message": "Profile updated",
        "user": updated,
    }


# ============================================================
# PROFILE AVATAR
# ============================================================

@app.post("/api/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected",
        )

    content_type = (
        file.content_type or ""
    ).lower()

    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Avatar must be an image",
        )

    filename = safe_filename(file.filename)

    destination = AVATAR_DIR / filename

    content = await file.read()

    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Avatar is too large",
        )

    destination.write_bytes(content)

    url = public_file_url(destination)

    with get_conn() as conn:

        updated = conn.execute("""
            UPDATE users
            SET
                avatar = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING
                id,
                name,
                email,
                bio,
                avatar,
                created_at,
                updated_at
        """, (
            url,
            user["id"],
        )).fetchone()

        conn.commit()

    return {
        "message": "Avatar updated",
        "user": updated,
        "avatar": url,
    }


# ============================================================
# USER PROFILE
# ============================================================

@app.get("/api/users/{user_id}")
def get_user_profile(user_id: int):

    with get_conn() as conn:

        user = conn.execute("""
            SELECT
                id,
                name,
                email,
                bio,
                avatar,
                created_at
            FROM users
            WHERE id = %s
              AND deleted_at IS NULL
        """, (user_id,)).fetchone()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return {
        "user": user,
    }


# ============================================================
# SEARCH USERS
# ============================================================

@app.get("/api/search")
def search_users(
    q: str = Query(..., min_length=1),
    authorization: Optional[str] = Header(default=None),
):

    require_user(authorization)

    search = q.strip()

    with get_conn() as conn:

        users = conn.execute("""
            SELECT
                id,
                name,
                email,
                bio,
                avatar,
                created_at
            FROM users
            WHERE deleted_at IS NULL
              AND (
                    name ILIKE %s
                    OR email ILIKE %s
              )
            ORDER BY name ASC
            LIMIT 50
        """, (
            f"%{search}%",
            f"%{search}%",
        )).fetchall()

    return {
        "users": users,
    }


# ============================================================
# POSTS — CREATE
# ============================================================

@app.post("/api/posts")
async def create_post(
    caption: str = Form(""),
    file: Optional[UploadFile] = File(default=None),
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    caption = caption.strip()

    media_url = None
    media_type = None

    if file and file.filename:

        content_type = (
            file.content_type or ""
        ).lower()

        if not (
            content_type.startswith("image/")
            or content_type.startswith("video/")
            or content_type.startswith("audio/")
        ):
            raise HTTPException(
                status_code=400,
                detail="Unsupported media type",
            )

        content = await file.read()

        if len(content) > 100 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File is too large",
            )

        filename = safe_filename(file.filename)

        if content_type.startswith("image/"):
            folder = POST_DIR

        elif content_type.startswith("video/"):
            folder = POST_DIR

        else:
            folder = POST_DIR

        destination = folder / filename

        destination.write_bytes(content)

        media_url = public_file_url(destination)
        media_type = content_type

    if not caption and not media_url:
        raise HTTPException(
            status_code=400,
            detail="Post cannot be empty",
        )

    with get_conn() as conn:

        post = conn.execute("""
            INSERT INTO posts (
                user_id,
                caption,
                media_url,
                media_type
            )
            VALUES (%s, %s, %s, %s)
            RETURNING
                id,
                user_id,
                caption,
                media_url,
                media_type,
                created_at
        """, (
            user["id"],
            caption,
            media_url,
            media_type,
        )).fetchone()

        conn.commit()

    return {
        "message": "Post created",
        "post": post,
    }


# ============================================================
# POSTS — FEED
# ============================================================

@app.get("/api/posts")
def get_posts(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
):

    with get_conn() as conn:

        posts = conn.execute("""
            SELECT
                p.id,
                p.user_id,
                p.caption,
                p.media_url,
                p.media_type,
                p.created_at,
                u.name AS user_name,
                u.avatar AS user_avatar,

                (
                    SELECT COUNT(*)
                    FROM likes l
                    WHERE l.post_id = p.id
                ) AS likes_count,

                (
                    SELECT COUNT(*)
                    FROM comments c
                    WHERE c.post_id = p.id
                ) AS comments_count,

                (
                    SELECT COUNT(*)
                    FROM reshares r
                    WHERE r.post_id = p.id
                ) AS reshares_count

            FROM posts p

            JOIN users u
                ON u.id = p.user_id

            WHERE u.deleted_at IS NULL

            ORDER BY p.created_at DESC

            LIMIT %s
            OFFSET %s
        """, (
            limit,
            offset,
        )).fetchall()

    return {
        "posts": posts,
        "limit": limit,
        "offset": offset,
    }


# ============================================================
# DELETE POST
# ============================================================

@app.delete("/api/posts/{post_id}")
def delete_post(
    post_id: int,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        post = conn.execute("""
            SELECT id
            FROM posts
            WHERE id = %s
              AND user_id = %s
        """, (
            post_id,
            user["id"],
        )).fetchone()

        if not post:
            raise HTTPException(
                status_code=404,
                detail="Post not found",
            )

        conn.execute("""
            DELETE FROM posts
            WHERE id = %s
              AND user_id = %s
        """, (
            post_id,
            user["id"],
        ))

        conn.commit()

    return {
        "message": "Post deleted",
    }


# ============================================================
# LIKE / UNLIKE
# ============================================================

@app.post("/api/posts/{post_id}/like")
def like_post(
    post_id: int,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        post = conn.execute("""
            SELECT id
            FROM posts
            WHERE id = %s
        """, (post_id,)).fetchone()

        if not post:
            raise HTTPException(
                status_code=404,
                detail="Post not found",
            )

        conn.execute("""
            INSERT INTO likes (
                post_id,
                user_id
            )
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (
            post_id,
            user["id"],
        ))

        conn.commit()

    return {
        "liked": True,
    }


@app.delete("/api/posts/{post_id}/like")
def unlike_post(
    post_id: int,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        conn.execute("""
            DELETE FROM likes
            WHERE post_id = %s
              AND user_id = %s
        """, (
            post_id,
            user["id"],
        ))

        conn.commit()

    return {
        "liked": False,
    }


# ============================================================
# COMMENTS
# ============================================================

@app.post("/api/posts/{post_id}/comments")
def add_comment(
    post_id: int,
    data: CommentRequest,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    text = data.text.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Comment cannot be empty",
        )

    with get_conn() as conn:

        post = conn.execute("""
            SELECT id
            FROM posts
            WHERE id = %s
        """, (post_id,)).fetchone()

        if not post:
            raise HTTPException(
                status_code=404,
                detail="Post not found",
            )

        comment = conn.execute("""
            INSERT INTO comments (
                post_id,
                user_id,
                text
            )
            VALUES (%s, %s, %s)
            RETURNING
                id,
                post_id,
                user_id,
                text,
                created_at
        """, (
            post_id,
            user["id"],
            text,
        )).fetchone()

        conn.commit()

    return {
        "comment": comment,
    }


@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id: int):

    with get_conn() as conn:

        comments = conn.execute("""
            SELECT
                c.id,
                c.post_id,
                c.user_id,
                c.text,
                c.created_at,
                u.name AS user_name,
                u.avatar AS user_avatar
            FROM comments c
            JOIN users u
                ON u.id = c.user_id
            WHERE c.post_id = %s
              AND u.deleted_at IS NULL
            ORDER BY c.created_at ASC
            LIMIT 200
        """, (post_id,)).fetchall()

    return {
        "comments": comments,
    }


# ============================================================
# SAVE / UNSAVE
# ============================================================

@app.post("/api/posts/{post_id}/save")
def save_post(
    post_id: int,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        conn.execute("""
            INSERT INTO saved_posts (
                post_id,
                user_id
            )
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (
            post_id,
            user["id"],
        ))

        conn.commit()

    return {
        "saved": True,
    }


@app.delete("/api/posts/{post_id}/save")
def unsave_post(
    post_id: int,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        conn.execute("""
            DELETE FROM saved_posts
            WHERE post_id = %s
              AND user_id = %s
        """, (
            post_id,
            user["id"],
        ))

        conn.commit()

    return {
        "saved": False,
    }


# ============================================================
# RESHARE
# ============================================================

@app.post("/api/posts/{post_id}/reshare")
def reshare_post(
    post_id: int,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        post = conn.execute("""
            SELECT id
            FROM posts
            WHERE id = %s
        """, (post_id,)).fetchone()

        if not post:
            raise HTTPException(
                status_code=404,
                detail="Post not found",
            )

        conn.execute("""
            INSERT INTO reshares (
                post_id,
                user_id
            )
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (
            post_id,
            user["id"],
        ))

        conn.commit()

    return {
        "reshared": True,
    }


# ============================================================
# CHAT — SEND TEXT
# ============================================================

@app.post("/api/messages")
def send_message(
    data: MessageRequest,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    text = data.text.strip()

    if not text:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty",
        )

    if data.receiver_id == user["id"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot message yourself",
        )

    with get_conn() as conn:

        receiver = conn.execute("""
            SELECT id
            FROM users
            WHERE id = %s
              AND deleted_at IS NULL
        """, (data.receiver_id,)).fetchone()

        if not receiver:
            raise HTTPException(
                status_code=404,
                detail="Receiver not found",
            )

        blocked = conn.execute("""
            SELECT id
            FROM blocks
            WHERE (
                blocker_id = %s
                AND blocked_id = %s
            )
            OR (
                blocker_id = %s
                AND blocked_id = %s
            )
            LIMIT 1
        """, (
            user["id"],
            data.receiver_id,
            data.receiver_id,
            user["id"],
        )).fetchone()

        if blocked:
            raise HTTPException(
                status_code=403,
                detail="Messaging is blocked",
            )

        message = conn.execute("""
            INSERT INTO messages (
                sender_id,
                receiver_id,
                text
            )
            VALUES (%s, %s, %s)
            RETURNING
                id,
                sender_id,
                receiver_id,
                text,
                media_url,
                media_type,
                duration_seconds,
                created_at,
                seen
        """, (
            user["id"],
            data.receiver_id,
            text,
        )).fetchone()

        conn.commit()

    return {
        "message": message,
    }


# ============================================================
# CHAT — HISTORY
# ============================================================

@app.get("/api/messages/{other_user_id}")
def get_messages(
    other_user_id: int,
    limit: int = Query(100, ge=1, le=200),
    before_id: Optional[int] = None,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        if before_id is None:

            messages = conn.execute("""
                SELECT
                    id,
                    sender_id,
                    receiver_id,
                    text,
                    media_url,
                    media_type,
                    duration_seconds,
                    created_at,
                    seen
                FROM messages
                WHERE (
                    (
                        sender_id = %s
                        AND receiver_id = %s
                        AND deleted_for_sender = FALSE
                    )
                    OR
                    (
                        sender_id = %s
                        AND receiver_id = %s
                        AND deleted_for_receiver = FALSE
                    )
                )
                ORDER BY created_at DESC
                LIMIT %s
            """, (
                user["id"],
                other_user_id,
                other_user_id,
                user["id"],
                limit,
            )).fetchall()

        else:

            messages = conn.execute("""
                SELECT
                    id,
                    sender_id,
                    receiver_id,
                    text,
                    media_url,
                    media_type,
                    duration_seconds,
                    created_at,
                    seen
                FROM messages
                WHERE (
                    (
                        sender_id = %s
                        AND receiver_id = %s
                        AND deleted_for_sender = FALSE
                    )
                    OR
                    (
                        sender_id = %s
                        AND receiver_id = %s
                        AND deleted_for_receiver = FALSE
                    )
                )
                AND id < %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (
                user["id"],
                other_user_id,
                other_user_id,
                user["id"],
                before_id,
                limit,
            )).fetchall()

        # Mark received messages as seen
        conn.execute("""
            UPDATE messages
            SET seen = TRUE
            WHERE sender_id = %s
              AND receiver_id = %s
              AND seen = FALSE
        """, (
            other_user_id,
            user["id"],
        ))

        conn.commit()

    messages.reverse()

    return {
        "messages": messages,
    }


# ============================================================
# CHAT LIST
# ============================================================

@app.get("/api/messages")
def message_list(
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        contacts = conn.execute("""
            SELECT DISTINCT ON (x.other_id)
                x.other_id,
                u.name,
                u.email,
                u.avatar,
                x.last_message,
                x.last_message_at
            FROM (
                SELECT
                    CASE
                        WHEN sender_id = %s
                        THEN receiver_id
                        ELSE sender_id
                    END AS other_id,
                    text AS last_message,
                    created_at AS last_message_at
                FROM messages
                WHERE
                    sender_id = %s
                    OR receiver_id = %s
                ORDER BY created_at DESC
            ) x
            JOIN users u
                ON u.id = x.other_id
            WHERE u.deleted_at IS NULL
            ORDER BY
                x.other_id,
                x.last_message_at DESC
        """, (
            user["id"],
            user["id"],
            user["id"],
        )).fetchall()

    return {
        "chats": contacts,
    }


# ============================================================
# VOICE NOTE
# ============================================================

@app.post("/api/messages/voice")
async def send_voice_note(
    receiver_id: int = Form(...),
    duration_seconds: int = Form(0),
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    if receiver_id == user["id"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot send voice note to yourself",
        )

    content_type = (
        file.content_type or ""
    ).lower()

    if not (
        content_type.startswith("audio/")
    ):
        raise HTTPException(
            status_code=400,
            detail="Voice note must be an audio file",
        )

    content = await file.read()

    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Voice note is too large",
        )

    filename = safe_filename(file.filename)

    destination = VOICE_DIR / filename

    destination.write_bytes(content)

    media_url = public_file_url(destination)

    with get_conn() as conn:

        receiver = conn.execute("""
            SELECT id
            FROM users
            WHERE id = %s
              AND deleted_at IS NULL
        """, (receiver_id,)).fetchone()

        if not receiver:
            raise HTTPException(
                status_code=404,
                detail="Receiver not found",
            )

        message = conn.execute("""
            INSERT INTO messages (
                sender_id,
                receiver_id,
                text,
                media_url,
                media_type,
                duration_seconds
            )
            VALUES (%s, %s, '', %s, %s, %s)
            RETURNING
                id,
                sender_id,
                receiver_id,
                text,
                media_url,
                media_type,
                duration_seconds,
                created_at,
                seen
        """, (
            user["id"],
            receiver_id,
            media_url,
            content_type,
            duration_seconds,
        )).fetchone()

        conn.commit()

    return {
        "message": message,
    }


# ============================================================
# CHAT FILE
# ============================================================

@app.post("/api/messages/file")
async def send_chat_file(
    receiver_id: int = Form(...),
    text: str = Form(""),
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    if receiver_id == user["id"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot send file to yourself",
        )

    content = await file.read()

    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File is too large",
        )

    filename = safe_filename(file.filename)

    destination = CHAT_FILE_DIR / filename

    destination.write_bytes(content)

    media_url = public_file_url(destination)

    media_type = (
        file.content_type
        or mimetypes.guess_type(
            file.filename or ""
        )[0]
        or "application/octet-stream"
    )

    with get_conn() as conn:

        message = conn.execute("""
            INSERT INTO messages (
                sender_id,
                receiver_id,
                text,
                media_url,
                media_type
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING
                id,
                sender_id,
                receiver_id,
                text,
                media_url,
                media_type,
                duration_seconds,
                created_at,
                seen
        """, (
            user["id"],
            receiver_id,
            text.strip(),
            media_url,
            media_type,
        )).fetchone()

        conn.commit()

    return {
        "message": message,
    }


# ============================================================
# CLEAR CHAT
# ============================================================

@app.delete("/api/chats/{other_user_id}")
def clear_chat(
    other_user_id: int,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        conn.execute("""
            UPDATE messages
            SET deleted_for_sender = TRUE
            WHERE sender_id = %s
              AND receiver_id = %s
        """, (
            user["id"],
            other_user_id,
        ))

        conn.execute("""
            UPDATE messages
            SET deleted_for_receiver = TRUE
            WHERE sender_id = %s
              AND receiver_id = %s
        """, (
            other_user_id,
            user["id"],
        ))

        conn.commit()

    return {
        "message": "Chat cleared",
    }


# ============================================================
# CHAT SETTINGS
# ============================================================

@app.post("/api/chats/{other_user_id}/settings")
def update_chat_settings(
    other_user_id: int,
    data: ChatSettingsRequest,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        existing = conn.execute("""
            SELECT *
            FROM chat_settings
            WHERE user_id = %s
              AND other_user_id = %s
        """, (
            user["id"],
            other_user_id,
        )).fetchone()

        if existing:

            pinned = (
                data.pinned
                if data.pinned is not None
                else existing["pinned"]
            )

            muted = (
                data.muted
                if data.muted is not None
                else existing["muted"]
            )

            blocked = (
                data.blocked
                if data.blocked is not None
                else existing["blocked"]
            )

            conn.execute("""
                UPDATE chat_settings
                SET
                    pinned = %s,
                    muted = %s,
                    blocked = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
                  AND other_user_id = %s
            """, (
                pinned,
                muted,
                blocked,
                user["id"],
                other_user_id,
            ))

        else:

            conn.execute("""
                INSERT INTO chat_settings (
                    user_id,
                    other_user_id,
                    pinned,
                    muted,
                    blocked
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                user["id"],
                other_user_id,
                data.pinned or False,
                data.muted or False,
                data.blocked or False,
            ))

        conn.commit()

        settings = conn.execute("""
            SELECT
                user_id,
                other_user_id,
                wallpaper_url,
                pinned,
                muted,
                blocked,
                updated_at
            FROM chat_settings
            WHERE user_id = %s
              AND other_user_id = %s
        """, (
            user["id"],
            other_user_id,
        )).fetchone()

    return {
        "settings": settings,
    }


# ============================================================
# CHAT WALLPAPER
# ============================================================

@app.post("/api/chats/{other_user_id}/wallpaper")
async def upload_wallpaper(
    other_user_id: int,
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    content_type = (
        file.content_type or ""
    ).lower()

    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Wallpaper must be an image",
        )

    content = await file.read()

    if len(content) > 15 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="Wallpaper is too large",
        )

    filename = safe_filename(file.filename)

    destination = WALLPAPER_DIR / filename

    destination.write_bytes(content)

    url = public_file_url(destination)

    with get_conn() as conn:

        conn.execute("""
            INSERT INTO chat_settings (
                user_id,
                other_user_id,
                wallpaper_url
            )
            VALUES (%s, %s, %s)
            ON CONFLICT (
                user_id,
                other_user_id
            )
            DO UPDATE SET
                wallpaper_url = EXCLUDED.wallpaper_url,
                updated_at = CURRENT_TIMESTAMP
        """, (
            user["id"],
            other_user_id,
            url,
        ))

        conn.commit()

    return {
        "message": "Wallpaper updated",
        "wallpaper_url": url,
    }


# ============================================================
# BLOCK USER
# ============================================================

@app.post("/api/users/{user_id}/block")
def block_user(
    user_id: int,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    if user_id == user["id"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot block yourself",
        )

    with get_conn() as conn:

        conn.execute("""
            INSERT INTO blocks (
                blocker_id,
                blocked_id
            )
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (
            user["id"],
            user_id,
        ))

        conn.commit()

    return {
        "blocked": True,
    }


# ============================================================
# UNBLOCK USER
# ============================================================

@app.delete("/api/users/{user_id}/block")
def unblock_user(
    user_id: int,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        conn.execute("""
            DELETE FROM blocks
            WHERE blocker_id = %s
              AND blocked_id = %s
        """, (
            user["id"],
            user_id,
        ))

        conn.commit()

    return {
        "blocked": False,
    }


# ============================================================
# REPORT USER
# ============================================================

@app.post("/api/users/{user_id}/report")
def report_user(
    user_id: int,
    data: ReportRequest,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        conn.execute("""
            INSERT INTO reports (
                reporter_id,
                reported_user_id,
                reason
            )
            VALUES (%s, %s, %s)
        """, (
            user["id"],
            user_id,
            data.reason.strip(),
        ))

        conn.commit()

    return {
        "message": "Report submitted",
    }


# ============================================================
# REPORT POST
# ============================================================

@app.post("/api/posts/{post_id}/report")
def report_post(
    post_id: int,
    data: ReportRequest,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        conn.execute("""
            INSERT INTO reports (
                reporter_id,
                post_id,
                reason
            )
            VALUES (%s, %s, %s)
        """, (
            user["id"],
            post_id,
            data.reason.strip(),
        ))

        conn.commit()

    return {
        "message": "Report submitted",
    }


# ============================================================
# LIVEKIT CALL TOKEN
# ============================================================

@app.post("/api/calls/token")
def create_call_token(
    data: CallTokenRequest,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    if not (
        LIVEKIT_URL
        and LIVEKIT_API_KEY
        and LIVEKIT_API_SECRET
    ):
        raise HTTPException(
            status_code=503,
            detail="LiveKit is not configured",
        )

    if data.receiver_id == user["id"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot call yourself",
        )

    call_type = data.call_type.lower().strip()

    if call_type not in {
        "audio",
        "video",
    }:
        call_type = "video"

    try:

        from livekit import api

        room_name = (
            "msafiri-"
            + secrets.token_hex(12)
        )

        token = (
            api.AccessToken(
                LIVEKIT_API_KEY,
                LIVEKIT_API_SECRET,
            )
            .with_identity(
                str(user["id"])
            )
            .with_name(
                user["name"]
            )
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                )
            )
        )

        jwt_token = token.to_jwt()

        with get_conn() as conn:

            call = conn.execute("""
                INSERT INTO calls (
                    caller_id,
                    receiver_id,
                    room_name,
                    call_type
                )
                VALUES (%s, %s, %s, %s)
                RETURNING
                    id,
                    room_name,
                    call_type,
                    status,
                    created_at
            """, (
                user["id"],
                data.receiver_id,
                room_name,
                call_type,
            )).fetchone()

            conn.commit()

        return {
            "token": jwt_token,
            "livekit_url": LIVEKIT_URL,
            "room_name": room_name,
            "call": call,
        }

    except ImportError:

        raise HTTPException(
            status_code=500,
            detail="LiveKit package is not installed",
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"LiveKit error: {str(e)}",
        )


# ============================================================
# END CALL
# ============================================================

@app.post("/api/calls/{call_id}/end")
def end_call(
    call_id: int,
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        call = conn.execute("""
            UPDATE calls
            SET
                status = 'ended',
                ended_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND (
                    caller_id = %s
                    OR receiver_id = %s
              )
            RETURNING *
        """, (
            call_id,
            user["id"],
            user["id"],
        )).fetchone()

        conn.commit()

    if not call:
        raise HTTPException(
            status_code=404,
            detail="Call not found",
        )

    return {
        "call": call,
    }


# ============================================================
# DELETE ACCOUNT
# ============================================================

@app.delete("/api/account")
def delete_account(
    authorization: Optional[str] = Header(default=None),
):

    user = require_user(authorization)

    with get_conn() as conn:

        conn.execute("""
            UPDATE users
            SET
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (user["id"],))

        conn.execute("""
            UPDATE sessions
            SET revoked = TRUE
            WHERE user_id = %s
        """, (user["id"],))

        conn.commit()

    return {
        "message": "Account deleted",
    }


# ============================================================
# ADMIN / DEBUG — DATABASE STRUCTURE
# ============================================================

@app.get("/api/debug/database")
def database_debug(
    authorization: Optional[str] = Header(default=None),
):

    # Requires login.
    # This endpoint does NOT expose passwords or secrets.
    require_user(authorization)

    with get_conn() as conn:

        tables = conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """).fetchall()

    return {
        "tables": [
            row["table_name"]
            for row in tables
        ]
    }


# ============================================================
# GLOBAL ERROR HANDLER
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):

    # Keep API alive and return useful JSON instead
    # of an unexplained browser error.

    print(
        "UNHANDLED ERROR:",
        type(exc).__name__,
        str(exc),
    )

    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal Server Error",
            "error": str(exc),
            "type": type(exc).__name__,
        },
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    import uvicorn

    port = int(
        os.getenv(
            "PORT",
            "8000",
        )
    )

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )n
