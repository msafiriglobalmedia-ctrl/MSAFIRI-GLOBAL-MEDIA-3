# ============================================================
# MSAFIRI GLOBAL MEDIA V5.0
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

import bcrypt
import jwt


# ============================================================
# APP CONFIG
# ============================================================

APP_NAME = "MSAFIRI GLOBAL MEDIA V5.0"
APP_VERSION = "5.0.0"

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
AVATAR_DIR = UPLOAD_DIR / "avatars"
POST_DIR = UPLOAD_DIR / "posts"
VOICE_DIR = UPLOAD_DIR / "voice"
CHAT_FILE_DIR = UPLOAD_DIR / "chat_files"
WALLPAPER_DIR = UPLOAD_DIR / "wallpapers"

for directory in (
    UPLOAD_DIR,
    AVATAR_DIR,
    POST_DIR,
    VOICE_DIR,
    CHAT_FILE_DIR,
    WALLPAPER_DIR,
):
    directory.mkdir(parents=True, exist_ok=True)


DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1,
    )


JWT_SECRET = (os.getenv("JWT_SECRET") or "").strip()

if not JWT_SECRET:
    JWT_SECRET = "CHANGE_THIS_SECRET_IN_RENDER"


JWT_ALGORITHM = "HS256"
TOKEN_DAYS = 30


LIVEKIT_URL = (os.getenv("LIVEKIT_URL") or "").strip()
LIVEKIT_API_KEY = (os.getenv("LIVEKIT_API_KEY") or "").strip()
LIVEKIT_API_SECRET = (os.getenv("LIVEKIT_API_SECRET") or "").strip()


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not configured"
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=10,
    )


# ============================================================
# DATABASE INITIALIZATION + MIGRATIONS
# ============================================================

def init_db():
    """
    Creates missing tables and safely upgrades old
    MSAFIRI GLOBAL MEDIA V3/V4 databases.

    Existing data is NOT deleted.
    """

    with get_conn() as conn:

        # ====================================================
        # USERS
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                username VARCHAR(80),
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                bio TEXT DEFAULT '',
                location VARCHAR(255) DEFAULT '',
                avatar TEXT,
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMPTZ
            )
            """
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # CREATE TABLE IF NOT EXISTS DOES NOT ADD COLUMNS
        # TO AN EXISTING TABLE.
        #
        # These statements repair the old users table.
        # ----------------------------------------------------

        conn.execute(
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS username VARCHAR(80)
            """
        )

        conn.execute(
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS bio TEXT DEFAULT ''
            """
        )

        conn.execute(
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS location
            VARCHAR(255) DEFAULT ''
            """
        )

        conn.execute(
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS avatar TEXT
            """
        )

        conn.execute(
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS deleted_at
            TIMESTAMPTZ
            """
        )

        conn.execute(
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS created_at
            TIMESTAMPTZ NOT NULL
            DEFAULT CURRENT_TIMESTAMP
            """
        )

        conn.execute(
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS updated_at
            TIMESTAMPTZ NOT NULL
            DEFAULT CURRENT_TIMESTAMP
            """
        )

        conn.execute(
            """
            UPDATE users
            SET bio = ''
            WHERE bio IS NULL
            """
        )

        conn.execute(
            """
            UPDATE users
            SET location = ''
            WHERE location IS NULL
            """
        )

        conn.execute(
            """
            UPDATE users
            SET updated_at = CURRENT_TIMESTAMP
            WHERE updated_at IS NULL
            """
        )

        # Username uniqueness.
        # NULL values are allowed for old accounts.
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_users_username_lower
            ON users (LOWER(username))
            WHERE username IS NOT NULL
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_users_name
            ON users(name)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_users_email
            ON users(email)
            """
        )


        # ====================================================
        # SESSIONS
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMPTZ NOT NULL,
                revoked BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )

        conn.execute(
            """
            ALTER TABLE sessions
            ADD COLUMN IF NOT EXISTS token_hash TEXT
            """
        )

        conn.execute(
            """
            ALTER TABLE sessions
            ADD COLUMN IF NOT EXISTS created_at
            TIMESTAMPTZ NOT NULL
            DEFAULT CURRENT_TIMESTAMP
            """
        )

        conn.execute(
            """
            ALTER TABLE sessions
            ADD COLUMN IF NOT EXISTS expires_at
            TIMESTAMPTZ
            """
        )

        conn.execute(
            """
            ALTER TABLE sessions
            ADD COLUMN IF NOT EXISTS revoked
            BOOLEAN NOT NULL DEFAULT FALSE
            """
        )

        conn.execute(
            """
            UPDATE sessions
            SET expires_at =
                CURRENT_TIMESTAMP + INTERVAL '30 days'
            WHERE expires_at IS NULL
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_sessions_token
            ON sessions(token_hash)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_sessions_user
            ON sessions(user_id)
            """
        )


        # ====================================================
        # POSTS
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                caption TEXT NOT NULL DEFAULT '',
                media_url TEXT,
                media_type TEXT,
                deleted_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            ALTER TABLE posts
            ADD COLUMN IF NOT EXISTS caption
            TEXT NOT NULL DEFAULT ''
            """
        )

        conn.execute(
            """
            ALTER TABLE posts
            ADD COLUMN IF NOT EXISTS media_url TEXT
            """
        )

        conn.execute(
            """
            ALTER TABLE posts
            ADD COLUMN IF NOT EXISTS media_type TEXT
            """
        )

        conn.execute(
            """
            ALTER TABLE posts
            ADD COLUMN IF NOT EXISTS deleted_at
            TIMESTAMPTZ
            """
        )

        conn.execute(
            """
            ALTER TABLE posts
            ADD COLUMN IF NOT EXISTS created_at
            TIMESTAMPTZ NOT NULL
            DEFAULT CURRENT_TIMESTAMP
            """
        )

        conn.execute(
            """
            ALTER TABLE posts
            ADD COLUMN IF NOT EXISTS updated_at
            TIMESTAMPTZ NOT NULL
            DEFAULT CURRENT_TIMESTAMP
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_posts_created
            ON posts(created_at DESC)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_posts_user
            ON posts(user_id)
            """
        )


        # ====================================================
        # LIKES
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS likes (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL
                    REFERENCES posts(id)
                    ON DELETE CASCADE,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id, user_id)
            )
            """
        )


        # ====================================================
        # COMMENTS
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL
                    REFERENCES posts(id)
                    ON DELETE CASCADE,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                text TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


        # ====================================================
        # SAVED POSTS
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_posts (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL
                    REFERENCES posts(id)
                    ON DELETE CASCADE,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id, user_id)
            )
            """
        )


        # ====================================================
        # RESHARES
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reshares (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL
                    REFERENCES posts(id)
                    ON DELETE CASCADE,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id, user_id)
            )
            """
        )


        # ====================================================
        # MESSAGES
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id BIGSERIAL PRIMARY KEY,
                sender_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                receiver_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                text TEXT DEFAULT '',
                media_url TEXT,
                media_type TEXT,
                voice_url TEXT,
                duration_seconds INTEGER,
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                deleted_for_sender BOOLEAN NOT NULL
                    DEFAULT FALSE,
                deleted_for_receiver BOOLEAN NOT NULL
                    DEFAULT FALSE,
                seen BOOLEAN NOT NULL DEFAULT FALSE
            )
            """
        )

        message_migrations = [
            """
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS text TEXT DEFAULT ''
            """,

            """
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS media_url TEXT
            """,

            """
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS media_type TEXT
            """,

            """
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS voice_url TEXT
            """,

            """
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS duration_seconds INTEGER
            """,

            """
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS
            deleted_for_sender
            BOOLEAN NOT NULL DEFAULT FALSE
            """,

            """
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS
            deleted_for_receiver
            BOOLEAN NOT NULL DEFAULT FALSE
            """,

            """
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS
            seen
            BOOLEAN NOT NULL DEFAULT FALSE
            """,

            """
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS created_at
            TIMESTAMPTZ NOT NULL
            DEFAULT CURRENT_TIMESTAMP
            """,
        ]

        for sql in message_migrations:
            conn.execute(sql)

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_messages_sr
            ON messages(
                sender_id,
                receiver_id,
                created_at DESC
            )
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_messages_rs
            ON messages(
                receiver_id,
                sender_id,
                created_at DESC
            )
            """
        )


        # ====================================================
        # CHAT SETTINGS
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_settings (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                other_user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                wallpaper_url TEXT,
                pinned BOOLEAN NOT NULL DEFAULT FALSE,
                muted BOOLEAN NOT NULL DEFAULT FALSE,
                blocked BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, other_user_id)
            )
            """
        )

        chat_migrations = [
            """
            ALTER TABLE chat_settings
            ADD COLUMN IF NOT EXISTS wallpaper_url TEXT
            """,

            """
            ALTER TABLE chat_settings
            ADD COLUMN IF NOT EXISTS pinned
            BOOLEAN NOT NULL DEFAULT FALSE
            """,

            """
            ALTER TABLE chat_settings
            ADD COLUMN IF NOT EXISTS muted
            BOOLEAN NOT NULL DEFAULT FALSE
            """,

            """
            ALTER TABLE chat_settings
            ADD COLUMN IF NOT EXISTS blocked
            BOOLEAN NOT NULL DEFAULT FALSE
            """,

            """
            ALTER TABLE chat_settings
            ADD COLUMN IF NOT EXISTS created_at
            TIMESTAMPTZ NOT NULL
            DEFAULT CURRENT_TIMESTAMP
            """,

            """
            ALTER TABLE chat_settings
            ADD COLUMN IF NOT EXISTS updated_at
            TIMESTAMPTZ NOT NULL
            DEFAULT CURRENT_TIMESTAMP
            """,
        ]

        for sql in chat_migrations:
            conn.execute(sql)


        # ====================================================
        # BLOCKS
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS blocks (
                id BIGSERIAL PRIMARY KEY,
                blocker_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                blocked_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(blocker_id, blocked_id)
            )
            """
        )


        # ====================================================
        # REPORTS
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id BIGSERIAL PRIMARY KEY,
                reporter_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                reported_user_id BIGINT
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                post_id BIGINT
                    REFERENCES posts(id)
                    ON DELETE CASCADE,
                message_id BIGINT,
                reason TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        conn.execute(
            """
            ALTER TABLE reports
            ADD COLUMN IF NOT EXISTS message_id BIGINT
            """
        )


        # ====================================================
        # CALLS
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS calls (
                id BIGSERIAL PRIMARY KEY,
                caller_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                receiver_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                room_name TEXT NOT NULL,
                call_type TEXT NOT NULL DEFAULT 'video',
                status TEXT NOT NULL DEFAULT 'started',
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMPTZ
            )
            """
        )

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_calls_room
            ON calls(room_name)
            """
        )


        # ====================================================
        # STATUSES
        # ====================================================

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS statuses (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                text TEXT DEFAULT '',
                media_url TEXT,
                media_type TEXT,
                created_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMPTZ
            )
            """
        )


        # ====================================================
        # FINISH DATABASE MIGRATION
        # ====================================================

        conn.commit()


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():
    init_db()


# ============================================================
# REQUEST MODELS
# ============================================================

class RegisterRequest(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None


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
# PASSWORD / TOKEN HELPERS
# ============================================================

def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")

    if len(password_bytes) > 72:
        raise HTTPException(
            400,
            "Password is too long",
        )

    return bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(),
    ).decode("utf-8")


def verify_password(
    password: str,
    password_hash: str,
) -> bool:

    try:
        password_bytes = password.encode("utf-8")

        if len(password_bytes) > 72:
            return False

        return bcrypt.checkpw(
            password_bytes,
            password_hash.encode("utf-8"),
        )

    except (ValueError, TypeError):
        return False


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
            401,
            "Session expired",
        )

    except jwt.InvalidTokenError:
        raise HTTPException(
            401,
            "Invalid token",
        )


def bearer(
    authorization: Optional[str],
) -> str:

    if not authorization:
        raise HTTPException(
            401,
            "Bearer token required",
        )

    if not authorization.lower().startswith(
        "bearer "
    ):
        raise HTTPException(
            401,
            "Bearer token required",
        )

    token = authorization.split(
        " ",
        1,
    )[1].strip()

    if not token:
        raise HTTPException(
            401,
            "Bearer token required",
        )

    return token


def require_user(
    authorization: Optional[str],
):

    token = bearer(authorization)
    payload = decode_token(token)

    try:
        user_id = int(payload["sub"])
    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        raise HTTPException(
            401,
            "Invalid token",
        )

    with get_conn() as conn:

        user = conn.execute(
            """
            SELECT
                u.id,
                u.name,
                u.username,
                u.email,
                u.bio,
                u.location,
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
            """,
            (
                hash_token(token),
                user_id,
            ),
        ).fetchone()

    if not user:
        raise HTTPException(
            401,
            "Session not found",
        )

    return user


def normalize_username(
    value: str,
) -> str:

    username = value.strip().lower()

    if not username:
        raise HTTPException(
            400,
            "Username is required",
        )

    if len(username) < 3:
        raise HTTPException(
            400,
            "Username must contain at least 3 characters",
        )

    if len(username) > 80:
        raise HTTPException(
            400,
            "Username is too long",
        )

    allowed = set(
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
        "._-"
    )

    if any(
        character not in allowed
        for character in username
    ):
        raise HTTPException(
            400,
            "Username may contain letters, numbers, dot, underscore and hyphen only",
        )

    return username


# ============================================================
# FILE HELPERS
# ============================================================

def safe_filename(
    name: Optional[str],
) -> str:

    extension = Path(
        name or "file"
    ).suffix.lower()

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

    if extension not in allowed:
        extension = ""

    return (
        secrets.token_hex(16)
        + extension
    )


def public_url(path: Path) -> str:

    relative = path.relative_to(
        BASE_DIR
    )

    return (
        "/files/"
        + str(relative).replace(
            "\\",
            "/",
        )
    )


async def save_upload(
    file: UploadFile,
    directory: Path,
    max_bytes: int,
) -> str:

    content = await file.read()

    if len(content) > max_bytes:
        raise HTTPException(
            400,
            "File is too large",
        )

    destination = (
        directory
        / safe_filename(file.filename)
    )

    destination.write_bytes(content)

    return public_url(destination)


# ============================================================
# ROOT / HEALTH
# ============================================================

@app.get("/")
def root():

    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "status": "online",
        "database": (
            "configured"
            if DATABASE_URL
            else "missing"
        ),
        "livekit": bool(
            LIVEKIT_URL
            and LIVEKIT_API_KEY
            and LIVEKIT_API_SECRET
        ),
    }


@app.get("/health")
@app.get("/api/health")
def health():

    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
    }


@app.get("/api/health/db")
def db_health():

    with get_conn() as conn:

        result = conn.execute(
            """
            SELECT CURRENT_TIMESTAMP
            AS server_time
            """
        ).fetchone()

    return {
        "status": "ok",
        "database": "postgresql",
        "server_time": result[
            "server_time"
        ],
    }


# ============================================================
# FILE SERVING
# ============================================================

@app.get("/files/{file_path:path}")
def serve_file(
    file_path: str,
):

    requested = (
        BASE_DIR / file_path
    ).resolve()

    upload_root = (
        UPLOAD_DIR.resolve()
    )

    if not (
        requested == upload_root
        or str(requested).startswith(
            str(upload_root) + os.sep
        )
    ):
        raise HTTPException(
            403,
            "Forbidden",
        )

    if not requested.is_file():
        raise HTTPException(
            404,
            "File not found",
        )

    media_type = (
        mimetypes.guess_type(
            str(requested)
        )[0]
        or "application/octet-stream"
    )

    return FileResponse(
        requested,
        media_type=media_type,
    )


# ============================================================
# REGISTER
# ============================================================

@app.post("/api/register")
def register(
    data: RegisterRequest,
):

    name = data.name.strip()

    username = normalize_username(
        data.username
    )

    email = str(
        data.email
    ).strip().lower()

    if len(name) < 2:
        raise HTTPException(
            400,
            "Name is too short",
        )

    if len(name) > 150:
        raise HTTPException(
            400,
            "Name is too long",
        )

    if len(data.password) < 6:
        raise HTTPException(
            400,
            "Password must contain at least 6 characters",
        )

    password_hash = hash_password(
        data.password
    )

    with get_conn() as conn:

        # ----------------------------------------------------
        # CHECK USERNAME FIRST
        # ----------------------------------------------------

        existing_username = conn.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(username) = LOWER(%s)
              AND deleted_at IS NULL
            LIMIT 1
            """,
            (username,),
        ).fetchone()

        if existing_username:
            raise HTTPException(
                409,
                "This username is already taken",
            )


        # ----------------------------------------------------
        # CHECK EMAIL
        # ----------------------------------------------------

        existing_email = conn.execute(
            """
            SELECT id, deleted_at
            FROM users
            WHERE LOWER(email) = LOWER(%s)
            LIMIT 1
            """,
            (email,),
        ).fetchone()


        # ----------------------------------------------------
        # RESTORE DELETED ACCOUNT
        # ----------------------------------------------------

        if existing_email:

            if existing_email["deleted_at"] is None:
                raise HTTPException(
                    409,
                    "An account with this email already exists",
                )

            user_id = existing_email["id"]

            conn.execute(
                """
                UPDATE users
                SET
                    name = %s,
                    username = %s,
                    password_hash = %s,
                    bio = '',
                    location = '',
                    avatar = NULL,
                    deleted_at = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (
                    name,
                    username,
                    password_hash,
                    user_id,
                ),
            )

        else:

            # ------------------------------------------------
            # CREATE NEW USER
            # ------------------------------------------------

            row = conn.execute(
                """
                INSERT INTO users (
                    name,
                    username,
                    email,
                    password_hash,
                    bio,
                    location
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    '',
                    ''
                )
                RETURNING id
                """,
                (
                    name,
                    username,
                    email,
                    password_hash,
                ),
            ).fetchone()

            user_id = row["id"]


        # ----------------------------------------------------
        # CREATE SESSION
        # ----------------------------------------------------

        token = create_token(
            user_id
        )

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(days=TOKEN_DAYS)
        )

        conn.execute(
            """
            INSERT INTO sessions (
                user_id,
                token_hash,
                expires_at,
                revoked
            )
            VALUES (
                %s,
                %s,
                %s,
                FALSE
            )
            """,
            (
                user_id,
                hash_token(token),
                expires_at,
            ),
        )


        # ----------------------------------------------------
        # RETURN USER
        # ----------------------------------------------------

        user = conn.execute(
            """
            SELECT
                id,
                name,
                username,
                email,
                bio,
                location,
                avatar,
                created_at,
                updated_at
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        ).fetchone()

        conn.commit()


    return {
        "message": "Account created successfully",
        "token": token,
        "access_token": token,
        "user": user,
    }


# ============================================================
# LOGIN
# ============================================================

@app.post("/api/login")
@app.post("/api/auth/login")
def login(
    data: LoginRequest,
):

    email = str(
        data.email
    ).strip().lower()

    with get_conn() as conn:

        user = conn.execute(
            """
            SELECT
                id,
                name,
                username,
                email,
                password_hash,
                bio,
                location,
                avatar,
                created_at,
                updated_at
            FROM users
            WHERE LOWER(email) = LOWER(%s)
              AND deleted_at IS NULL
            LIMIT 1
            """,
            (email,),
        ).fetchone()

        if not user:
            raise HTTPException(
                401,
                "Invalid email or password",
            )

        if not verify_password(
            data.password,
            user["password_hash"],
        ):
            raise HTTPException(
                401,
                "Invalid email or password",
            )


        token = create_token(
            user["id"]
        )

        expires_at = (
            datetime.now(timezone.utc)
            + timedelta(days=TOKEN_DAYS)
        )

        conn.execute(
            """
            INSERT INTO sessions (
                user_id,
                token_hash,
                expires_at,
                revoked
            )
            VALUES (
                %s,
                %s,
                %s,
                FALSE
            )
            """,
            (
                user["id"],
                hash_token(token),
                expires_at,
            ),
        )

        conn.commit()


    user.pop(
        "password_hash",
        None,
    )

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
    authorization: Optional[str] = Header(
        default=None
    ),
):

    token = bearer(
        authorization
    )

    with get_conn() as conn:

        conn.execute(
            """
            UPDATE sessions
            SET revoked = TRUE
            WHERE token_hash = %s
            """,
            (
                hash_token(token),
            ),
        )

        conn.commit()

    return {
        "message": "Logged out successfully",
    }


# ============================================================
# CURRENT USER
# ============================================================

@app.get("/api/me")
def me(
    authorization: Optional[str] = Header(
        default=None
    ),
):

    return {
        "user": require_user(
            authorization
        )
    }


# ============================================================
# PROFILE UPDATE
# ============================================================

@app.patch("/api/profile")
def update_profile(
    data: ProfileUpdate,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    name = (
        data.name.strip()
        if data.name is not None
        else current_user["name"]
    )

    bio = (
        data.bio.strip()
        if data.bio is not None
        else (
            current_user["bio"]
            or ""
        )
    )

    location = (
        data.location.strip()
        if data.location is not None
        else (
            current_user["location"]
            or ""
        )
    )

    username = (
        normalize_username(
            data.username
        )
        if data.username is not None
        else current_user["username"]
    )

    if len(name) < 2:
        raise HTTPException(
            400,
            "Name is too short",
        )

    if len(name) > 150:
        raise HTTPException(
            400,
            "Name is too long",
        )

    with get_conn() as conn:

        if (
            username
            != current_user["username"]
        ):

            taken = conn.execute(
                """
                SELECT id
                FROM users
                WHERE LOWER(username)
                    = LOWER(%s)
                  AND id <> %s
                  AND deleted_at IS NULL
                LIMIT 1
                """,
                (
                    username,
                    current_user["id"],
                ),
            ).fetchone()

            if taken:
                raise HTTPException(
                    409,
                    "This username is already taken",
                )


        row = conn.execute(
            """
            UPDATE users
            SET
                name = %s,
                username = %s,
                bio = %s,
                location = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING
                id,
                name,
                username,
                email,
                bio,
                location,
                avatar,
                created_at,
                updated_at
            """,
            (
                name,
                username,
                bio,
                location,
                current_user["id"],
            ),
        ).fetchone()

        conn.commit()


    return {
        "message": "Profile updated",
        "user": row,
    }


# ============================================================
# AVATAR
# ============================================================

@app.post("/api/profile/avatar")
async def avatar(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    content_type = (
        file.content_type
        or ""
    ).lower()

    if not content_type.startswith(
        "image/"
    ):
        raise HTTPException(
            400,
            "Avatar must be an image",
        )

    url = await save_upload(
        file,
        AVATAR_DIR,
        10 * 1024 * 1024,
    )

    with get_conn() as conn:

        row = conn.execute(
            """
            UPDATE users
            SET
                avatar = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING
                id,
                name,
                username,
                email,
                bio,
                location,
                avatar,
                created_at,
                updated_at
            """,
            (
                url,
                current_user["id"],
            ),
        ).fetchone()

        conn.commit()


    return {
        "message": "Avatar updated",
        "user": row,
        "avatar": url,
    }


# ============================================================
# USER PROFILE
# ============================================================

@app.get("/api/users/{user_id}")
@app.get("/api/profile/{user_id}")
def profile(
    user_id: int,
):

    with get_conn() as conn:

        user = conn.execute(
            """
            SELECT
                id,
                name,
                username,
                email,
                bio,
                location,
                avatar,
                created_at,
                updated_at
            FROM users
            WHERE id = %s
              AND deleted_at IS NULL
            """,
            (user_id,),
        ).fetchone()


    if not user:
        raise HTTPException(
            404,
            "User not found",
        )

    return {
        "user": user,
    }


# ============================================================
# USER SEARCH
# ============================================================

@app.get("/api/search")
def search(
    q: str = Query(
        ...,
        min_length=1,
    ),
    authorization: Optional[str] = Header(
        default=None
    ),
):

    require_user(
        authorization
    )

    search_text = q.strip()

    with get_conn() as conn:

        users = conn.execute(
            """
            SELECT
                id,
                name,
                username,
                email,
                bio,
                location,
                avatar,
                created_at
            FROM users
            WHERE deleted_at IS NULL
              AND (
                  name ILIKE %s
                  OR username ILIKE %s
                  OR email ILIKE %s
              )
            ORDER BY name
            LIMIT 50
            """,
            (
                f"%{search_text}%",
                f"%{search_text}%",
                f"%{search_text}%",
            ),
        ).fetchall()


    return {
        "users": users,
    }


@app.get("/api/users/search")
def users_search(
    q: str = Query(
        ...,
        min_length=1,
    ),
    authorization: Optional[str] = Header(
        default=None
    ),
):

    return search(
        q,
        authorization,
    )


# ============================================================
# CREATE POST
# ============================================================

@app.post("/api/posts")
async def create_post(
    caption: str = Form(""),
    file: Optional[UploadFile] = File(
        default=None
    ),
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    caption = caption.strip()

    media_url = None
    media_type = None


    if file and file.filename:

        content_type = (
            file.content_type
            or ""
        ).lower()

        if not (
            content_type.startswith(
                "image/"
            )
            or content_type.startswith(
                "video/"
            )
            or content_type.startswith(
                "audio/"
            )
        ):
            raise HTTPException(
                400,
                "Unsupported media type",
            )

        media_url = await save_upload(
            file,
            POST_DIR,
            100 * 1024 * 1024,
        )

        media_type = content_type


    if not caption and not media_url:
        raise HTTPException(
            400,
            "Post cannot be empty",
        )


    with get_conn() as conn:

        post = conn.execute(
            """
            INSERT INTO posts (
                user_id,
                caption,
                media_url,
                media_type
            )
            VALUES (
                %s,
                %s,
                %s,
                %s
            )
            RETURNING
                id,
                user_id,
                caption,
                media_url,
                media_type,
                created_at
            """,
            (
                current_user["id"],
                caption,
                media_url,
                media_type,
            ),
        ).fetchone()

        conn.commit()


    return {
        "message": "Post created",
        "post": post,
    }


# ============================================================
# POSTS FEED
# ============================================================

@app.get("/api/posts")
def posts(
    limit: int = Query(
        30,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        0,
        ge=0,
    ),
):

    with get_conn() as conn:

        rows = conn.execute(
            """
            SELECT
                p.id,
                p.user_id,
                p.caption,
                p.media_url,
                p.media_type,
                p.created_at,
                u.name AS user_name,
                u.username AS username,
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

            WHERE p.deleted_at IS NULL
              AND u.deleted_at IS NULL

            ORDER BY p.created_at DESC

            LIMIT %s
            OFFSET %s
            """,
            (
                limit,
                offset,
            ),
        ).fetchall()


    return {
        "posts": rows,
        "limit": limit,
        "offset": offset,
    }


# ============================================================
# DELETE POST
# ============================================================

@app.delete("/api/posts/{post_id}")
def delete_post(
    post_id: int,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        result = conn.execute(
            """
            UPDATE posts
            SET
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
              AND user_id = %s
              AND deleted_at IS NULL
            RETURNING id
            """,
            (
                post_id,
                current_user["id"],
            ),
        ).fetchone()

        if not result:
            raise HTTPException(
                404,
                "Post not found",
            )

        conn.commit()


    return {
        "message": "Post deleted",
    }


# ============================================================
# POST EXISTENCE
# ============================================================

def post_exists(
    conn,
    post_id: int,
):

    post = conn.execute(
        """
        SELECT id
        FROM posts
        WHERE id = %s
          AND deleted_at IS NULL
        """,
        (post_id,),
    ).fetchone()

    if not post:
        raise HTTPException(
            404,
            "Post not found",
        )


# ============================================================
# LIKE
# ============================================================

@app.post("/api/posts/{post_id}/like")
def like(
    post_id: int,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        post_exists(
            conn,
            post_id,
        )

        conn.execute(
            """
            INSERT INTO likes(
                post_id,
                user_id
            )
            VALUES(
                %s,
                %s
            )
            ON CONFLICT DO NOTHING
            """,
            (
                post_id,
                current_user["id"],
            ),
        )

        conn.commit()


    return {
        "liked": True,
    }


# ============================================================
# UNLIKE
# ============================================================

@app.delete("/api/posts/{post_id}/like")
def unlike(
    post_id: int,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        conn.execute(
            """
            DELETE FROM likes
            WHERE post_id = %s
              AND user_id = %s
            """,
            (
                post_id,
                current_user["id"],
            ),
        )

        conn.commit()


    return {
        "liked": False,
    }


# ============================================================
# COMMENT
# ============================================================

@app.post("/api/posts/{post_id}/comments")
def comment(
    post_id: int,
    data: CommentRequest,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    text = data.text.strip()

    if not text:
        raise HTTPException(
            400,
            "Comment cannot be empty",
        )

    with get_conn() as conn:

        post_exists(
            conn,
            post_id,
        )

        result = conn.execute(
            """
            INSERT INTO comments(
                post_id,
                user_id,
                text
            )
            VALUES(
                %s,
                %s,
                %s
            )
            RETURNING
                id,
                post_id,
                user_id,
                text,
                created_at
            """,
            (
                post_id,
                current_user["id"],
                text,
            ),
        ).fetchone()

        conn.commit()


    return {
        "comment": result,
    }


# ============================================================
# COMMENTS
# ============================================================

@app.get("/api/posts/{post_id}/comments")
def comments(
    post_id: int,
):

    with get_conn() as conn:

        rows = conn.execute(
            """
            SELECT
                c.id,
                c.post_id,
                c.user_id,
                c.text,
                c.created_at,
                u.name AS user_name,
                u.username AS username,
                u.avatar AS user_avatar
            FROM comments c
            JOIN users u
                ON u.id = c.user_id
            WHERE c.post_id = %s
              AND u.deleted_at IS NULL
            ORDER BY c.created_at ASC
            LIMIT 200
            """,
            (post_id,),
        ).fetchall()


    return {
        "comments": rows,
    }


# ============================================================
# SAVE POST
# ============================================================

@app.post("/api/posts/{post_id}/save")
def save_post(
    post_id: int,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        post_exists(
            conn,
            post_id,
        )

        conn.execute(
            """
            INSERT INTO saved_posts(
                post_id,
                user_id
            )
            VALUES(
                %s,
                %s
            )
            ON CONFLICT DO NOTHING
            """,
            (
                post_id,
                current_user["id"],
            ),
        )

        conn.commit()


    return {
        "saved": True,
    }


# ============================================================
# UNSAVE POST
# ============================================================

@app.delete("/api/posts/{post_id}/save")
def unsave_post(
    post_id: int,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        conn.execute(
            """
            DELETE FROM saved_posts
            WHERE post_id = %s
              AND user_id = %s
            """,
            (
                post_id,
                current_user["id"],
            ),
        )

        conn.commit()


    return {
        "saved": False,
    }


# ============================================================
# RESHARE
# ============================================================

@app.post("/api/posts/{post_id}/reshare")
def reshare(
    post_id: int,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        post_exists(
            conn,
            post_id,
        )

        conn.execute(
            """
            INSERT INTO reshares(
                post_id,
                user_id
            )
            VALUES(
                %s,
                %s
            )
            ON CONFLICT DO NOTHING
            """,
            (
                post_id,
                current_user["id"],
            ),
        )

        conn.commit()


    return {
        "reshared": True,
    }


# ============================================================
# SEND TEXT MESSAGE
# ============================================================

@app.post("/api/messages")
def send_message(
    data: MessageRequest,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    if (
        data.receiver_id
        == current_user["id"]
    ):
        raise HTTPException(
            400,
            "Cannot message yourself",
        )

    text = data.text.strip()

    if not text:
        raise HTTPException(
            400,
            "Message cannot be empty",
        )

    with get_conn() as conn:

        receiver = conn.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s
              AND deleted_at IS NULL
            """,
            (
                data.receiver_id,
            ),
        ).fetchone()

        if not receiver:
            raise HTTPException(
                404,
                "Receiver not found",
            )


        blocked = conn.execute(
            """
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
            """,
            (
                current_user["id"],
                data.receiver_id,
                data.receiver_id,
                current_user["id"],
            ),
        ).fetchone()

        if blocked:
            raise HTTPException(
                403,
                "Messaging is blocked",
            )


        message = conn.execute(
            """
            INSERT INTO messages(
                sender_id,
                receiver_id,
                text
            )
            VALUES(
                %s,
                %s,
                %s
            )
            RETURNING
                id,
                sender_id,
                receiver_id,
                text,
                media_url,
                media_type,
                voice_url,
                duration_seconds,
                created_at,
                seen
            """,
            (
                current_user["id"],
                data.receiver_id,
                text,
            ),
        ).fetchone()

        conn.commit()


    return {
        "message": message,
    }


# ============================================================
# CHAT HISTORY
# ============================================================

@app.get("/api/messages/{other_user_id}")
def history(
    other_user_id: int,
    limit: int = Query(
        100,
        ge=1,
        le=200,
    ),
    before_id: Optional[int] = None,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        if before_id is None:

            rows = conn.execute(
                """
                SELECT
                    id,
                    sender_id,
                    receiver_id,
                    text,
                    media_url,
                    media_type,
                    voice_url,
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
                """,
                (
                    current_user["id"],
                    other_user_id,
                    other_user_id,
                    current_user["id"],
                    limit,
                ),
            ).fetchall()

        else:

            rows = conn.execute(
                """
                SELECT
                    id,
                    sender_id,
                    receiver_id,
                    text,
                    media_url,
                    media_type,
                    voice_url,
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
                """,
                (
                    current_user["id"],
                    other_user_id,
                    other_user_id,
                    current_user["id"],
                    before_id,
                    limit,
                ),
            ).fetchall()


        conn.execute(
            """
            UPDATE messages
            SET seen = TRUE
            WHERE sender_id = %s
              AND receiver_id = %s
            """,
            (
                other_user_id,
                current_user["id"],
            ),
        )

        conn.commit()


    rows.reverse()

    return {
        "messages": rows,
    }


# ============================================================
# CHAT LIST
# ============================================================

@app.get("/api/messages")
def chat_list(
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        rows = conn.execute(
            """
            SELECT DISTINCT ON (x.other_id)
                x.other_id,
                u.name,
                u.username,
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

                WHERE sender_id = %s
                   OR receiver_id = %s

                ORDER BY created_at DESC
            ) x

            JOIN users u
                ON u.id = x.other_id

            WHERE u.deleted_at IS NULL

            ORDER BY
                x.other_id,
                x.last_message_at DESC
            """,
            (
                current_user["id"],
                current_user["id"],
                current_user["id"],
            ),
        ).fetchall()


    return {
        "chats": rows,
    }


# ============================================================
# VOICE NOTE
# ============================================================

@app.post("/api/messages/voice")
async def voice(
    receiver_id: int = Form(...),
    duration_seconds: int = Form(0),
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    if (
        receiver_id
        == current_user["id"]
    ):
        raise HTTPException(
            400,
            "Cannot send voice note to yourself",
        )

    content_type = (
        file.content_type
        or ""
    ).lower()

    if not content_type.startswith(
        "audio/"
    ):
        raise HTTPException(
            400,
            "Voice note must be an audio file",
        )

    if duration_seconds < 0:
        duration_seconds = 0

    url = await save_upload(
        file,
        VOICE_DIR,
        25 * 1024 * 1024,
    )

    with get_conn() as conn:

        receiver = conn.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s
              AND deleted_at IS NULL
            """,
            (receiver_id,),
        ).fetchone()

        if not receiver:
            raise HTTPException(
                404,
                "Receiver not found",
            )


        message = conn.execute(
            """
            INSERT INTO messages(
                sender_id,
                receiver_id,
                text,
                media_url,
                voice_url,
                media_type,
                duration_seconds
            )
            VALUES(
                %s,
                %s,
                '',
                %s,
                %s,
                %s,
                %s
            )
            RETURNING
                id,
                sender_id,
                receiver_id,
                text,
                media_url,
                media_type,
                voice_url,
                duration_seconds,
                created_at,
                seen
            """,
            (
                current_user["id"],
                receiver_id,
                url,
                url,
                content_type,
                duration_seconds,
            ),
        ).fetchone()

        conn.commit()


    return {
        "message": message,
    }


# ============================================================
# CHAT FILE
# ============================================================

@app.post("/api/messages/file")
async def chat_file(
    receiver_id: int = Form(...),
    text: str = Form(""),
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    if (
        receiver_id
        == current_user["id"]
    ):
        raise HTTPException(
            400,
            "Cannot send file to yourself",
        )

    url = await save_upload(
        file,
        CHAT_FILE_DIR,
        100 * 1024 * 1024,
    )

    content_type = (
        file.content_type
        or mimetypes.guess_type(
            file.filename or ""
        )[0]
        or "application/octet-stream"
    )

    with get_conn() as conn:

        receiver = conn.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s
              AND deleted_at IS NULL
            """,
            (
                receiver_id,
            ),
        ).fetchone()

        if not receiver:
            raise HTTPException(
                404,
                "Receiver not found",
            )


        message = conn.execute(
            """
            INSERT INTO messages(
                sender_id,
                receiver_id,
                text,
                media_url,
                media_type
            )
            VALUES(
                %s,
                %s,
                %s,
                %s,
                %s
            )
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
            """,
            (
                current_user["id"],
                receiver_id,
                text.strip(),
                url,
                content_type,
            ),
        ).fetchone()

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
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        conn.execute(
            """
            UPDATE messages
            SET deleted_for_sender = TRUE
            WHERE sender_id = %s
              AND receiver_id = %s
            """,
            (
                current_user["id"],
                other_user_id,
            ),
        )

        conn.execute(
            """
            UPDATE messages
            SET deleted_for_receiver = TRUE
            WHERE sender_id = %s
              AND receiver_id = %s
            """,
            (
                other_user_id,
                current_user["id"],
            ),
        )

        conn.commit()


    return {
        "message": "Chat cleared",
    }


# ============================================================
# CHAT SETTINGS
# ============================================================

@app.post("/api/chats/{other_user_id}/settings")
def settings(
    other_user_id: int,
    data: ChatSettingsRequest,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        old = conn.execute(
            """
            SELECT *
            FROM chat_settings
            WHERE user_id = %s
              AND other_user_id = %s
            LIMIT 1
            """,
            (
                current_user["id"],
                other_user_id,
            ),
        ).fetchone()


        pinned = (
            data.pinned
            if data.pinned is not None
            else (
                old["pinned"]
                if old
                else False
            )
        )

        muted = (
            data.muted
            if data.muted is not None
            else (
                old["muted"]
                if old
                else False
            )
        )

        blocked = (
            data.blocked
            if data.blocked is not None
            else (
                old["blocked"]
                if old
                else False
            )
        )


        conn.execute(
            """
            INSERT INTO chat_settings(
                user_id,
                other_user_id,
                pinned,
                muted,
                blocked
            )
            VALUES(
                %s,
                %s,
                %s,
                %s,
                %s
            )
            ON CONFLICT(
                user_id,
                other_user_id
            )
            DO UPDATE SET
                pinned = EXCLUDED.pinned,
                muted = EXCLUDED.muted,
                blocked = EXCLUDED.blocked,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                current_user["id"],
                other_user_id,
                bool(pinned),
                bool(muted),
                bool(blocked),
            ),
        )


        result = conn.execute(
            """
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
            """,
            (
                current_user["id"],
                other_user_id,
            ),
        ).fetchone()

        conn.commit()


    return {
        "settings": result,
    }


# ============================================================
# CHAT WALLPAPER
# ============================================================

@app.post("/api/chats/{other_user_id}/wallpaper")
async def wallpaper(
    other_user_id: int,
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    content_type = (
        file.content_type
        or ""
    ).lower()

    if not content_type.startswith(
        "image/"
    ):
        raise HTTPException(
            400,
            "Wallpaper must be an image",
        )

    url = await save_upload(
        file,
        WALLPAPER_DIR,
        15 * 1024 * 1024,
    )

    with get_conn() as conn:

        conn.execute(
            """
            INSERT INTO chat_settings(
                user_id,
                other_user_id,
                wallpaper_url
            )
            VALUES(
                %s,
                %s,
                %s
            )
            ON CONFLICT(
                user_id,
                other_user_id
            )
            DO UPDATE SET
                wallpaper_url =
                    EXCLUDED.wallpaper_url,
                updated_at =
                    CURRENT_TIMESTAMP
            """,
            (
                current_user["id"],
                other_user_id,
                url,
            ),
        )

        conn.commit()


    return {
        "message": "Wallpaper updated",
        "wallpaper_url": url,
    }


# ============================================================
# BLOCK USER
# ============================================================

@app.post("/api/users/{user_id}/block")
def block(
    user_id: int,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    if (
        user_id
        == current_user["id"]
    ):
        raise HTTPException(
            400,
            "Cannot block yourself",
        )

    with get_conn() as conn:

        target = conn.execute(
            """
            SELECT id
            FROM users
            WHERE id = %s
              AND deleted_at IS NULL
            """,
            (user_id,),
        ).fetchone()

        if not target:
            raise HTTPException(
                404,
                "User not found",
            )


        conn.execute(
            """
            INSERT INTO blocks(
                blocker_id,
                blocked_id
            )
            VALUES(
                %s,
                %s
            )
            ON CONFLICT DO NOTHING
            """,
            (
                current_user["id"],
                user_id,
            ),
        )

        conn.commit()


    return {
        "blocked": True,
    }


# ============================================================
# UNBLOCK USER
# ============================================================

@app.delete("/api/users/{user_id}/block")
def unblock(
    user_id: int,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        conn.execute(
            """
            DELETE FROM blocks
            WHERE blocker_id = %s
              AND blocked_id = %s
            """,
            (
                current_user["id"],
                user_id,
            ),
        )

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
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        conn.execute(
            """
            INSERT INTO reports(
                reporter_id,
                reported_user_id,
                reason
            )
            VALUES(
                %s,
                %s,
                %s
            )
            """,
            (
                current_user["id"],
                user_id,
                data.reason.strip(),
            ),
        )

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
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        post_exists(
            conn,
            post_id,
        )

        conn.execute(
            """
            INSERT INTO reports(
                reporter_id,
                post_id,
                reason
            )
            VALUES(
                %s,
                %s,
                %s
            )
            """,
            (
                current_user["id"],
                post_id,
                data.reason.strip(),
            ),
        )

        conn.commit()


    return {
        "message": "Report submitted",
    }


# ============================================================
# LIVEKIT CALL TOKEN
# ============================================================

@app.post("/api/calls/token")
def call_token(
    data: CallTokenRequest,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    if not (
        LIVEKIT_URL
        and LIVEKIT_API_KEY
        and LIVEKIT_API_SECRET
    ):
        raise HTTPException(
            503,
            "LiveKit is not configured",
        )


    if (
        data.receiver_id
        == current_user["id"]
    ):
        raise HTTPException(
            400,
            "Cannot call yourself",
        )


    call_type = (
        data.call_type
        .lower()
        .strip()
    )

    if call_type not in {
        "audio",
        "video",
    }:
        call_type = "video"


    with get_conn() as conn:

        receiver = conn.execute(
            """
            SELECT
                id,
                name
            FROM users
            WHERE id = %s
              AND deleted_at IS NULL
            """,
            (
                data.receiver_id,
            ),
        ).fetchone()

        if not receiver:
            raise HTTPException(
                404,
                "Receiver not found",
            )


        blocked = conn.execute(
            """
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
            """,
            (
                current_user["id"],
                data.receiver_id,
                data.receiver_id,
                current_user["id"],
            ),
        ).fetchone()

        if blocked:
            raise HTTPException(
                403,
                "Calling is blocked",
            )


        try:
            from livekit import api
        except ImportError:
            raise HTTPException(
                500,
                "LiveKit package is not installed",
            )


        room_name = (
            "msafiri-"
            + secrets.token_hex(12)
        )


        access_token = (
            api.AccessToken(
                LIVEKIT_API_KEY,
                LIVEKIT_API_SECRET,
            )
            .with_identity(
                str(current_user["id"])
            )
            .with_name(
                current_user["name"]
            )
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                )
            )
            .to_jwt()
        )


        call = conn.execute(
            """
            INSERT INTO calls(
                caller_id,
                receiver_id,
                room_name,
                call_type,
                status
            )
            VALUES(
                %s,
                %s,
                %s,
                %s,
                'started'
            )
            RETURNING
                id,
                caller_id,
                receiver_id,
                room_name,
                call_type,
                status,
                created_at
            """,
            (
                current_user["id"],
                data.receiver_id,
                room_name,
                call_type,
            ),
        ).fetchone()

        conn.commit()


    return {
        "token": access_token,
        "livekit_url": LIVEKIT_URL,
        "room_name": room_name,
        "call": call,
    }


# ============================================================
# END CALL
# ============================================================

@app.post("/api/calls/{call_id}/end")
def end_call(
    call_id: int,
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        result = conn.execute(
            """
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
            """,
            (
                call_id,
                current_user["id"],
                current_user["id"],
            ),
        ).fetchone()

        if not result:
            raise HTTPException(
                404,
                "Call not found",
            )

        conn.commit()


    return {
        "call": result,
    }


# ============================================================
# DELETE ACCOUNT
# ============================================================

@app.delete("/api/account")
def delete_account(
    authorization: Optional[str] = Header(
        default=None
    ),
):

    current_user = require_user(
        authorization
    )

    with get_conn() as conn:

        conn.execute(
            """
            UPDATE users
            SET
                deleted_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (
                current_user["id"],
            ),
        )


        conn.execute(
            """
            UPDATE sessions
            SET revoked = TRUE
            WHERE user_id = %s
            """,
            (
                current_user["id"],
            ),
        )

        conn.commit()


    return {
        "message": "Account deleted",
    }


# ============================================================
# DATABASE DEBUG
# ============================================================

@app.get("/api/debug/database")
def database_debug(
    authorization: Optional[str] = Header(
        default=None
    ),
):

    require_user(
        authorization
    )

    with get_conn() as conn:

        tables = conn.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
            """
        ).fetchall()


    return {
        "tables": [
            row["table_name"]
            for row in tables
        ]
    }


# ============================================================
# SERVER
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(
            os.getenv(
                "PORT",
                "8000",
            )
        ),
        reload=False,
    )
