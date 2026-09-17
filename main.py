# ============================================================
# MSAFIRI GLOBAL MEDIA V4.4
# CLEAN FULL BACKEND
# FastAPI + PostgreSQL + JWT + LiveKit
# ============================================================

import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
import psycopg
from psycopg.rows import dict_row
from psycopg.errors import UniqueViolation

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    UploadFile,
    File,
    Form,
    Header,
    Query,
    Request,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pydantic import BaseModel, EmailStr, Field

from passlib.context import CryptContext

try:
    from livekit import api as livekit_api
except Exception:
    livekit_api = None


# ============================================================
# CONFIG
# ============================================================

APP_NAME = "MSAFIRI GLOBAL MEDIA V4.4"

BASE_DIR = Path(__file__).resolve().parent

UPLOAD_DIR = BASE_DIR / "uploads"
AVATAR_DIR = BASE_DIR / "avatars"
POST_DIR = BASE_DIR / "posts"
VOICE_DIR = BASE_DIR / "voice"
CHAT_FILE_DIR = BASE_DIR / "chat_files"
WALLPAPER_DIR = BASE_DIR / "wallpapers"

for directory in [
    UPLOAD_DIR,
    AVATAR_DIR,
    POST_DIR,
    VOICE_DIR,
    CHAT_FILE_DIR,
    WALLPAPER_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)


# ============================================================
# ENVIRONMENT
# ============================================================

DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("POSTGRES_URL")
    or os.getenv("POSTGRESQL_URL")
    or ""
).strip()

JWT_SECRET = os.getenv("JWT_SECRET", "").strip()

if not JWT_SECRET:
    JWT_SECRET = "CHANGE_THIS_JWT_SECRET_IN_RENDER"

JWT_ALGORITHM = "HS256"

try:
    JWT_EXPIRE_DAYS = int(
        os.getenv("JWT_EXPIRE_DAYS", "30")
    )
except Exception:
    JWT_EXPIRE_DAYS = 30

PUBLIC_BASE_URL = (
    os.getenv("PUBLIC_BASE_URL", "")
    .strip()
    .rstrip("/")
)

LIVEKIT_URL = (
    os.getenv("LIVEKIT_URL", "")
    .strip()
    .rstrip("/")
)

LIVEKIT_API_KEY = (
    os.getenv("LIVEKIT_API_KEY", "")
    .strip()
)

LIVEKIT_API_SECRET = (
    os.getenv("LIVEKIT_API_SECRET", "")
    .strip()
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(
    "msafiri-global-media"
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title=APP_NAME,
    version="4.4",
    description="MSAFIRI GLOBAL MEDIA social platform",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# PASSWORD
# ============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
)


def hash_password(password: str):

    password_bytes = password.encode(
        "utf-8"
    )

    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=400,
            detail=(
                "Password is too long. "
                "Please use a shorter password."
            ),
        )

    try:
        return pwd_context.hash(password)
    except Exception as exc:
        logger.exception(
            "Password hashing error: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail="Unable to secure password.",
        )


def verify_password(
    password: str,
    password_hash: str,
):

    try:

        password_bytes = password.encode(
            "utf-8"
        )

        if len(password_bytes) > 72:
            return False

        return pwd_context.verify(
            password,
            password_hash,
        )

    except Exception as exc:

        logger.error(
            "Password verification error: %s",
            exc,
        )

        return False


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_conn():

    if not DATABASE_URL:

        raise HTTPException(
            status_code=500,
            detail=(
                "DATABASE_URL is not configured."
            ),
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=15,
    )


# ============================================================
# GENERAL HELPERS
# ============================================================

def now_utc():

    return datetime.now(timezone.utc)


def serialize_datetime(value):

    if isinstance(value, datetime):
        return value.isoformat()

    return value


def public_url(path: Path):

    relative = (
        "/"
        + str(
            path.relative_to(BASE_DIR)
        ).replace("\\", "/")
    )

    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL + relative

    return relative


# ============================================================
# DATABASE INITIALIZATION + MIGRATION
# ============================================================

def init_database():

    if not DATABASE_URL:

        logger.warning(
            "DATABASE_URL is not configured."
        )

        return

    with get_conn() as conn:

        # ----------------------------------------------------
        # USERS
        # ----------------------------------------------------

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
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                deleted_at TIMESTAMPTZ
            )
            """
        )

        # ----------------------------------------------------
        # IMPORTANT:
        # Existing PostgreSQL database may have been created
        # by an older version of the application.
        #
        # CREATE TABLE IF NOT EXISTS DOES NOT ALTER an
        # existing table.
        #
        # Therefore we explicitly migrate old users table.
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
            ADD COLUMN IF NOT EXISTS location VARCHAR(255)
            DEFAULT ''
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
            ADD COLUMN IF NOT EXISTS created_at
            TIMESTAMPTZ DEFAULT NOW()
            """
        )

        conn.execute(
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS updated_at
            TIMESTAMPTZ DEFAULT NOW()
            """
        )

        conn.execute(
            """
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS deleted_at
            TIMESTAMPTZ
            """
        )

        # ----------------------------------------------------
        # Ensure NULL/default values are safe for old records.
        # ----------------------------------------------------

        conn.execute(
            """
            UPDATE users
            SET bio=''
            WHERE bio IS NULL
            """
        )

        conn.execute(
            """
            UPDATE users
            SET location=''
            WHERE location IS NULL
            """
        )

        conn.execute(
            """
            UPDATE users
            SET created_at=NOW()
            WHERE created_at IS NULL
            """
        )

        conn.execute(
            """
            UPDATE users
            SET updated_at=NOW()
            WHERE updated_at IS NULL
            """
        )

        # ----------------------------------------------------
        # Username unique index.
        #
        # NULL usernames are allowed.
        # Existing duplicate NULL values do not matter.
        # ----------------------------------------------------

        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_users_username_unique
            ON users(username)
            WHERE username IS NOT NULL
            """
        )

        # ----------------------------------------------------
        # SESSIONS
        # ----------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                token_id VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL
            )
            """
        )

        # ----------------------------------------------------
        # POSTS
        # ----------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                caption TEXT DEFAULT '',
                media_url TEXT,
                media_type VARCHAR(100),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                deleted_at TIMESTAMPTZ
            )
            """
        )

        # ----------------------------------------------------
        # LIKES
        # ----------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS likes (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                post_id BIGINT NOT NULL
                    REFERENCES posts(id)
                    ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, post_id)
            )
            """
        )

        # ----------------------------------------------------
        # COMMENTS
        # ----------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS comments (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                post_id BIGINT NOT NULL
                    REFERENCES posts(id)
                    ON DELETE CASCADE,
                text TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        # ----------------------------------------------------
        # SAVED POSTS
        # ----------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_posts (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                post_id BIGINT NOT NULL
                    REFERENCES posts(id)
                    ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, post_id)
            )
            """
        )

        # ----------------------------------------------------
        # RESHARES
        # ----------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reshares (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                post_id BIGINT NOT NULL
                    REFERENCES posts(id)
                    ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, post_id)
            )
            """
        )

        # ----------------------------------------------------
        # MESSAGES
        # ----------------------------------------------------

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
                media_type VARCHAR(100),
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                read_at TIMESTAMPTZ
            )
            """
        )

        # ----------------------------------------------------
        # BLOCKS
        # ----------------------------------------------------

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
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                UNIQUE(blocker_id, blocked_id)
            )
            """
        )

        # ----------------------------------------------------
        # REPORTS
        # ----------------------------------------------------

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id BIGSERIAL PRIMARY KEY,
                reporter_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                reported_user_id BIGINT
                    REFERENCES users(id)
                    ON DELETE SET NULL,
                post_id BIGINT
                    REFERENCES posts(id)
                    ON DELETE SET NULL,
                reason TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )

        # ----------------------------------------------------
        # CHAT SETTINGS
        # ----------------------------------------------------

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
                muted BOOLEAN NOT NULL DEFAULT FALSE,
                notifications BOOLEAN NOT NULL DEFAULT TRUE,
                pinned BOOLEAN NOT NULL DEFAULT FALSE,
                wallpaper TEXT,
                UNIQUE(user_id, other_user_id)
            )
            """
        )

        # ----------------------------------------------------
        # CALLS
        # ----------------------------------------------------

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
                room_name VARCHAR(255) NOT NULL,
                call_type VARCHAR(30) NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'ringing',
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                ended_at TIMESTAMPTZ
            )
            """
        )

        # ----------------------------------------------------
        # INDEXES
        # ----------------------------------------------------

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
            idx_messages_conversation
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
            idx_users_email
            ON users(email)
            """
        )

        conn.commit()

    logger.info(
        "Database initialized and migrated successfully."
    )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():

    try:

        init_database()

    except Exception as exc:

        logger.exception(
            "Database initialization error: %s",
            exc,
        )


# ============================================================
# JWT
# ============================================================

def create_jwt(user_id: int):

    token_id = str(uuid.uuid4())

    issued_at = now_utc()

    expires_at = (
        issued_at
        + timedelta(
            days=JWT_EXPIRE_DAYS
        )
    )

    payload = {
        "sub": str(user_id),
        "jti": token_id,
        "iat": issued_at,
        "exp": expires_at,
    }

    token = jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    return (
        token,
        token_id,
        expires_at,
    )


def decode_jwt(token: str):

    try:

        return jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=401,
            detail="SESSION_EXPIRED",
        )

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=401,
            detail="INVALID_TOKEN",
        )


def extract_bearer(
    authorization: Optional[str],
):

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail="LOGIN_REQUIRED",
        )

    if not authorization.lower().startswith(
        "bearer "
    ):

        raise HTTPException(
            status_code=401,
            detail="INVALID_AUTHORIZATION",
        )

    token = authorization[7:].strip()

    if not token:

        raise HTTPException(
            status_code=401,
            detail="LOGIN_REQUIRED",
        )

    return token


# ============================================================
# AUTHENTICATED USER
# ============================================================

def require_user(
    authorization: Optional[str] = Header(
        default=None
    ),
):

    token = extract_bearer(
        authorization
    )

    payload = decode_jwt(token)

    user_id = payload.get("sub")
    token_id = payload.get("jti")

    if not user_id:

        raise HTTPException(
            status_code=401,
            detail="INVALID_TOKEN",
        )

    try:

        user_id = int(user_id)

    except Exception:

        raise HTTPException(
            status_code=401,
            detail="INVALID_USER_ID",
        )

    with get_conn() as conn:

        session = conn.execute(
            """
            SELECT id
            FROM sessions
            WHERE token_id=%s
              AND user_id=%s
              AND expires_at > NOW()
            """,
            (
                token_id,
                user_id,
            ),
        ).fetchone()

        if not session:

            raise HTTPException(
                status_code=401,
                detail="SESSION_EXPIRED",
            )

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
                created_at
            FROM users
            WHERE id=%s
              AND deleted_at IS NULL
            """,
            (user_id,),
        ).fetchone()

    if not user:

        raise HTTPException(
            status_code=401,
            detail="USER_NOT_FOUND",
        )

    return user


# ============================================================
# USER SERIALIZATION
# ============================================================

def clean_user(user):

    if not user:
        return None

    return {
        "id": user["id"],
        "name": user["name"],
        "username": user.get("username"),
        "email": user["email"],
        "bio": user.get("bio") or "",
        "location": user.get("location") or "",
        "avatar": user.get("avatar"),
        "created_at": serialize_datetime(
            user.get("created_at")
        ),
    }


# ============================================================
# FILE UPLOAD
# ============================================================

async def save_upload(
    upload: UploadFile,
    directory: Path,
    max_size: int,
):

    filename = upload.filename or "file"

    extension = Path(
        filename
    ).suffix.lower()

    if len(extension) > 15:
        extension = ""

    unique_name = (
        uuid.uuid4().hex
        + extension
    )

    destination = (
        directory / unique_name
    )

    total = 0

    try:

        with destination.open(
            "wb"
        ) as output:

            while True:

                chunk = await upload.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                total += len(chunk)

                if total > max_size:

                    destination.unlink(
                        missing_ok=True
                    )

                    max_mb = (
                        max_size
                        // (
                            1024 * 1024
                        )
                    )

                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File too large. "
                            "Maximum allowed: "
                            + str(max_mb)
                            + " MB."
                        ),
                    )

                output.write(chunk)

    finally:

        await upload.close()

    return public_url(
        destination
    )


# ============================================================
# MODELS
# ============================================================

class RegisterRequest(BaseModel):

    name: str = Field(
        min_length=1,
        max_length=150,
    )

    username: Optional[str] = Field(
        default=None,
        max_length=80,
    )

    email: EmailStr

    password: str = Field(
        min_length=6,
        max_length=200,
    )


class LoginRequest(BaseModel):

    email: EmailStr
    password: str


class ProfileUpdateRequest(BaseModel):

    name: Optional[str] = Field(
        default=None,
        max_length=150,
    )

    username: Optional[str] = Field(
        default=None,
        max_length=80,
    )

    bio: Optional[str] = Field(
        default=None,
        max_length=1000,
    )

    location: Optional[str] = Field(
        default=None,
        max_length=255,
    )


class CommentRequest(BaseModel):

    text: str = Field(
        min_length=1,
        max_length=2000,
    )


class MessageRequest(BaseModel):

    receiver_id: int

    text: str = Field(
        default="",
        max_length=5000,
    )


class ReportRequest(BaseModel):

    reason: str = Field(
        min_length=1,
        max_length=1000,
    )

    reported_user_id: Optional[int] = None

    post_id: Optional[int] = None


class CallRequest(BaseModel):

    receiver_id: int

    call_type: str = "audio"


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    index_file = (
        BASE_DIR / "index.html"
    )

    if index_file.exists():

        return FileResponse(
            index_file,
            media_type="text/html",
        )

    return {
        "app": APP_NAME,
        "status": "online",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    database = False

    if DATABASE_URL:

        try:

            with get_conn() as conn:

                conn.execute(
                    "SELECT 1"
                ).fetchone()

            database = True

        except Exception as exc:

            logger.error(
                "Database health error: %s",
                exc,
            )

    livekit = bool(
        LIVEKIT_URL
        and LIVEKIT_API_KEY
        and LIVEKIT_API_SECRET
        and livekit_api
    )

    return {
        "status": "ok",
        "app": APP_NAME,
        "database": (
            "postgresql"
            if database
            else "not_connected"
        ),
        "livekit": livekit,
        "timestamp": now_utc().isoformat(),
    }


@app.get("/api/health")
def api_health():

    return health()


# ============================================================
# REGISTER
# ============================================================

@app.post("/api/auth/register")
def register(
    data: RegisterRequest
):

    name = data.name.strip()

    if not name:

        raise HTTPException(
            status_code=400,
            detail="Name is required.",
        )

    username = None

    if data.username:

        username = (
            data.username
            .strip()
            .lower()
        )

        username = username[:80]

        if username:

            cleaned = (
                username
                .replace("_", "")
                .replace(".", "")
            )

            if not cleaned.isalnum():

                raise HTTPException(
                    status_code=400,
                    detail="Invalid username.",
                )

    email = (
        str(data.email)
        .strip()
        .lower()
    )

    # --------------------------------------------------------
    # Check existing email / username before password hashing.
    # --------------------------------------------------------

    try:

        with get_conn() as conn:

            existing = conn.execute(
                """
                SELECT
                    id,
                    email,
                    username
                FROM users
                WHERE
                    LOWER(email)=LOWER(%s)
                    OR (
                        %s IS NOT NULL
                        AND LOWER(username)=LOWER(%s)
                    )
                LIMIT 1
                """,
                (
                    email,
                    username,
                    username,
                ),
            ).fetchone()

        if existing:

            if (
                existing["email"]
                and existing["email"].lower()
                == email.lower()
            ):

                raise HTTPException(
                    status_code=409,
                    detail=(
                        "Email already exists."
                    ),
                )

            raise HTTPException(
                status_code=409,
                detail=(
                    "Username already exists."
                ),
            )

    except HTTPException:
        raise

    except Exception as exc:

        logger.exception(
            "Register pre-check error: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to check account information."
            ),
        )

    # --------------------------------------------------------
    # Hash password
    # --------------------------------------------------------

    password_hash = hash_password(
        data.password
    )

    # --------------------------------------------------------
    # Create user
    # --------------------------------------------------------

    try:

        with get_conn() as conn:

            user = conn.execute(
                """
                INSERT INTO users
                    (
                        name,
                        username,
                        email,
                        password_hash,
                        bio,
                        location
                    )
                VALUES
                    (%s,%s,%s,%s,%s,%s)
                RETURNING
                    id,
                    name,
                    username,
                    email,
                    bio,
                    location,
                    avatar,
                    created_at
                """,
                (
                    name,
                    username,
                    email,
                    password_hash,
                    "",
                    "",
                ),
            ).fetchone()

            conn.commit()

    except UniqueViolation:

        raise HTTPException(
            status_code=409,
            detail=(
                "Email or username already exists."
            ),
        )

    except Exception as exc:

        logger.exception(
            "Register database error: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to create account."
            ),
        )

    # --------------------------------------------------------
    # Create session
    # --------------------------------------------------------

    try:

        (
            token,
            token_id,
            expires_at,
        ) = create_jwt(
            user["id"]
        )

        with get_conn() as conn:

            conn.execute(
                """
                INSERT INTO sessions
                    (
                        user_id,
                        token_id,
                        expires_at
                    )
                VALUES
                    (%s,%s,%s)
                """,
                (
                    user["id"],
                    token_id,
                    expires_at,
                ),
            )

            conn.commit()

    except Exception as exc:

        logger.exception(
            "Session creation error: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Account created but session "
                "could not be created."
            ),
        )

    return {
        "success": True,
        "message": "Registration successful.",
        "token": token,
        "access_token": token,
        "expires_at": expires_at.isoformat(),
        "user": clean_user(user),
    }


@app.post("/api/register")
def register_alias(
    data: RegisterRequest
):

    return register(data)


# ============================================================
# LOGIN
# ============================================================

@app.post("/api/auth/login")
def login(
    data: LoginRequest
):

    email = (
        str(data.email)
        .strip()
        .lower()
    )

    try:

        with get_conn() as conn:

            user = conn.execute(
                """
                SELECT *
                FROM users
                WHERE LOWER(email)=LOWER(%s)
                  AND deleted_at IS NULL
                LIMIT 1
                """,
                (email,),
            ).fetchone()

    except Exception as exc:

        logger.exception(
            "Login database error: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Unable to access account database."
            ),
        )

    if not user:

        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid email or password."
            ),
        )

    password_hash = (
        user.get("password_hash")
    )

    if not password_hash:

        raise HTTPException(
            status_code=401,
            detail=(
                "This account has no valid password."
            ),
        )

    if not verify_password(
        data.password,
        password_hash,
    ):

        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid email or password."
            ),
        )

    try:

        (
            token,
            token_id,
            expires_at,
        ) = create_jwt(
            user["id"]
        )

        with get_conn() as conn:

            conn.execute(
                """
                INSERT INTO sessions
                    (
                        user_id,
                        token_id,
                        expires_at
                    )
                VALUES
                    (%s,%s,%s)
                """,
                (
                    user["id"],
                    token_id,
                    expires_at,
                ),
            )

            conn.commit()

    except Exception as exc:

        logger.exception(
            "Login session error: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Login succeeded but session "
                "could not be created."
            ),
        )

    return {
        "success": True,
        "message": "Login successful.",
        "token": token,
        "access_token": token,
        "expires_at": expires_at.isoformat(),
        "user": clean_user(user),
    }


@app.post("/api/login")
def login_alias(
    data: LoginRequest
):

    return login(data)


# ============================================================
# LOGOUT
# ============================================================

@app.post("/api/auth/logout")
def logout(
    authorization: Optional[str] = Header(
        default=None
    ),
):

    token = extract_bearer(
        authorization
    )

    payload = decode_jwt(token)

    token_id = payload.get("jti")

    if token_id:

        with get_conn() as conn:

            conn.execute(
                """
                DELETE FROM sessions
                WHERE token_id=%s
                """,
                (token_id,),
            )

            conn.commit()

    return {
        "success": True,
        "message": "Logged out.",
    }


# ============================================================
# CURRENT USER
# ============================================================

@app.get("/api/me")
def me(
    user=Depends(require_user)
):

    return {
        "success": True,
        "user": clean_user(user),
    }


@app.get("/api/auth/me")
def auth_me(
    user=Depends(require_user)
):

    return {
        "success": True,
        "user": clean_user(user),
    }


# ============================================================
# USERS
# ============================================================

@app.get("/api/users")
def get_users(
    user=Depends(require_user),
    q: str = Query(default=""),
):

    q = q.strip()

    with get_conn() as conn:

        if q:

            rows = conn.execute(
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
                  AND id <> %s
                  AND (
                    name ILIKE %s
                    OR username ILIKE %s
                    OR email ILIKE %s
                  )
                ORDER BY name
                LIMIT 100
                """,
                (
                    user["id"],
                    "%" + q + "%",
                    "%" + q + "%",
                    "%" + q + "%",
                ),
            ).fetchall()

        else:

            rows = conn.execute(
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
                  AND id <> %s
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (user["id"],),
            ).fetchall()

    return {
        "success": True,
        "users": [
            clean_user(row)
            for row in rows
        ],
    }


@app.get("/api/users/search")
def search_users(
    q: str,
    user=Depends(require_user),
):

    return get_users(
        user=user,
        q=q,
    )


@app.get("/api/users/{user_id}")
def get_user(
    user_id: int,
    user=Depends(require_user),
):

    with get_conn() as conn:

        row = conn.execute(
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
            WHERE id=%s
              AND deleted_at IS NULL
            """,
            (user_id,),
        ).fetchone()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    return {
        "success": True,
        "user": clean_user(row),
    }


# ============================================================
# PROFILE
# ============================================================

@app.put("/api/profile")
def update_profile(
    data: ProfileUpdateRequest,
    user=Depends(require_user),
):

    fields = []
    values = []

    if data.name is not None:

        new_name = data.name.strip()

        if not new_name:

            raise HTTPException(
                status_code=400,
                detail="Name cannot be empty.",
            )

        fields.append(
            "name=%s"
        )

        values.append(
            new_name
        )

    if data.username is not None:

        username = (
            data.username
            .strip()
            .lower()
        )

        if username:

            cleaned = (
                username
                .replace("_", "")
                .replace(".", "")
            )

            if not cleaned.isalnum():

                raise HTTPException(
                    status_code=400,
                    detail="Invalid username.",
                )

        fields.append(
            "username=%s"
        )

        values.append(
            username or None
        )

    if data.bio is not None:

        fields.append(
            "bio=%s"
        )

        values.append(
            data.bio.strip()
        )

    if data.location is not None:

        fields.append(
            "location=%s"
        )

        values.append(
            data.location.strip()
        )

    if not fields:

        return {
            "success": True,
            "message": "Nothing to update.",
        }

    fields.append(
        "updated_at=NOW()"
    )

    values.append(
        user["id"]
    )

    try:

        with get_conn() as conn:

            row = conn.execute(
                """
                UPDATE users
                SET """
                + ", ".join(fields)
                + """
                WHERE id=%s
                RETURNING
                    id,
                    name,
                    username,
                    email,
                    bio,
                    location,
                    avatar,
                    created_at
                """,
                tuple(values),
            ).fetchone()

            conn.commit()

    except UniqueViolation:

        raise HTTPException(
            status_code=409,
            detail="Username already exists.",
        )

    return {
        "success": True,
        "user": clean_user(row),
    }


@app.post("/api/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user=Depends(require_user),
):

    content_type = (
        file.content_type or ""
    ).lower()

    if not content_type.startswith(
        "image/"
    ):

        raise HTTPException(
            status_code=400,
            detail="Avatar must be an image.",
        )

    avatar_url = await save_upload(
        file,
        AVATAR_DIR,
        10 * 1024 * 1024,
    )

    with get_conn() as conn:

        conn.execute(
            """
            UPDATE users
            SET
                avatar=%s,
                updated_at=NOW()
            WHERE id=%s
            """,
            (
                avatar_url,
                user["id"],
            ),
        )

        conn.commit()

    return {
        "success": True,
        "avatar": avatar_url,
    }


# ============================================================
# POSTS
# ============================================================

def post_query():

    return """
        SELECT
            p.id,
            p.user_id,
            p.caption,
            p.media_url,
            p.media_type,
            p.created_at,

            u.id AS author_id,
            u.name AS author_name,
            u.username AS author_username,
            u.email AS author_email,
            u.bio AS author_bio,
            u.location AS author_location,
            u.avatar AS author_avatar,

            (
                SELECT COUNT(*)
                FROM likes l
                WHERE l.post_id=p.id
            ) AS likes_count,

            (
                SELECT COUNT(*)
                FROM comments c
                WHERE c.post_id=p.id
            ) AS comments_count,

            (
                SELECT COUNT(*)
                FROM reshares r
                WHERE r.post_id=p.id
            ) AS reshares_count

        FROM posts p

        JOIN users u
          ON u.id=p.user_id

        WHERE p.deleted_at IS NULL
          AND u.deleted_at IS NULL
    """


def serialize_post(
    row,
    current_user_id: Optional[int] = None,
):

    liked = False
    saved = False
    reshared = False

    if current_user_id:

        with get_conn() as conn:

            liked = bool(
                conn.execute(
                    """
                    SELECT 1
                    FROM likes
                    WHERE user_id=%s
                      AND post_id=%s
                    """,
                    (
                        current_user_id,
                        row["id"],
                    ),
                ).fetchone()
            )

            saved = bool(
                conn.execute(
                    """
                    SELECT 1
                    FROM saved_posts
                    WHERE user_id=%s
                      AND post_id=%s
                    """,
                    (
                        current_user_id,
                        row["id"],
                    ),
                ).fetchone()
            )

            reshared = bool(
                conn.execute(
                    """
                    SELECT 1
                    FROM reshares
                    WHERE user_id=%s
                      AND post_id=%s
                    """,
                    (
                        current_user_id,
                        row["id"],
                    ),
                ).fetchone()
            )

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "caption": row["caption"] or "",
        "media_url": row["media_url"],
        "media_type": row["media_type"],
        "created_at": serialize_datetime(
            row["created_at"]
        ),
        "likes_count": int(
            row["likes_count"] or 0
        ),
        "comments_count": int(
            row["comments_count"] or 0
        ),
        "reshares_count": int(
            row["reshares_count"] or 0
        ),
        "liked": liked,
        "saved": saved,
        "reshared": reshared,
        "author": {
            "id": row["author_id"],
            "name": row["author_name"],
            "username": row[
                "author_username"
            ],
            "email": row["author_email"],
            "bio": row[
                "author_bio"
            ] or "",
            "location": row[
                "author_location"
            ] or "",
            "avatar": row[
                "author_avatar"
            ],
        },
    }


@app.get("/api/posts")
def get_posts(
    user=Depends(require_user),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
):

    with get_conn() as conn:

        rows = conn.execute(
            post_query()
            + """
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
        "success": True,
        "posts": [
            serialize_post(
                row,
                user["id"],
            )
            for row in rows
        ],
    }


@app.post("/api/posts")
async def create_post(
    caption: str = Form(default=""),
    file: Optional[UploadFile] = File(
        default=None
    ),
    media: Optional[UploadFile] = File(
        default=None
    ),
    authorization: Optional[str] = Header(
        default=None
    ),
):

    user = require_user(
        authorization
    )

    caption = (
        caption or ""
    ).strip()

    upload = file or media

    media_url = None
    media_type = None

    if upload:

        content_type = (
            upload.content_type or ""
        ).lower()

        allowed = (
            content_type.startswith(
                "image/"
            )
            or content_type.startswith(
                "video/"
            )
            or content_type.startswith(
                "audio/"
            )
        )

        if not allowed:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Unsupported media type."
                ),
            )

        if content_type.startswith(
            "video/"
        ):

            max_size = (
                200 * 1024 * 1024
            )

        elif content_type.startswith(
            "audio/"
        ):

            max_size = (
                50 * 1024 * 1024
            )

        else:

            max_size = (
                50 * 1024 * 1024
            )

        media_url = await save_upload(
            upload,
            POST_DIR,
            max_size,
        )

        media_type = content_type

    if not caption and not media_url:

        raise HTTPException(
            status_code=400,
            detail=(
                "Write something or "
                "select a photo/video."
            ),
        )

    with get_conn() as conn:

        row = conn.execute(
            """
            INSERT INTO posts
                (
                    user_id,
                    caption,
                    media_url,
                    media_type
                )
            VALUES
                (%s,%s,%s,%s)
            RETURNING
                id,
                user_id,
                caption,
                media_url,
                media_type,
                created_at
            """,
            (
                user["id"],
                caption,
                media_url,
                media_type,
            ),
        ).fetchone()

        conn.commit()

    return {
        "success": True,
        "message": "Post published.",
        "post": {
            "id": row["id"],
            "user_id": row["user_id"],
            "caption": row["caption"] or "",
            "media_url": row["media_url"],
            "media_type": row["media_type"],
            "created_at": serialize_datetime(
                row["created_at"]
            ),
        },
    }


@app.delete("/api/posts/{post_id}")
def delete_post(
    post_id: int,
    user=Depends(require_user),
):

    with get_conn() as conn:

        post = conn.execute(
            """
            SELECT id,user_id
            FROM posts
            WHERE id=%s
              AND deleted_at IS NULL
            """,
            (post_id,),
        ).fetchone()

        if not post:

            raise HTTPException(
                status_code=404,
                detail="Post not found.",
            )

        if post["user_id"] != user["id"]:

            raise HTTPException(
                status_code=403,
                detail=(
                    "You can only delete "
                    "your own post."
                ),
            )

        conn.execute(
            """
            UPDATE posts
            SET deleted_at=NOW()
            WHERE id=%s
            """,
            (post_id,),
        )

        conn.commit()

    return {
        "success": True,
        "message": "Post deleted.",
    }


# ============================================================
# LIKE
# ============================================================

@app.post("/api/posts/{post_id}/like")
def like_post(
    post_id: int,
    user=Depends(require_user),
):

    with get_conn() as conn:

        conn.execute(
            """
            INSERT INTO likes
                (
                    user_id,
                    post_id
                )
            VALUES
                (%s,%s)
            ON CONFLICT
                (user_id,post_id)
            DO NOTHING
            """,
            (
                user["id"],
                post_id,
            ),
        )

        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM likes
            WHERE post_id=%s
            """,
            (post_id,),
        ).fetchone()["count"]

        conn.commit()

    return {
        "success": True,
        "liked": True,
        "likes_count": int(count),
    }


@app.delete("/api/posts/{post_id}/like")
def unlike_post(
    post_id: int,
    user=Depends(require_user),
):

    with get_conn() as conn:

        conn.execute(
            """
            DELETE FROM likes
            WHERE user_id=%s
              AND post_id=%s
            """,
            (
                user["id"],
                post_id,
            ),
        )

        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM likes
            WHERE post_id=%s
            """,
            (post_id,),
        ).fetchone()["count"]

        conn.commit()

    return {
        "success": True,
        "liked": False,
        "likes_count": int(count),
    }


# ============================================================
# COMMENTS
# ============================================================

@app.post("/api/posts/{post_id}/comment")
def add_comment(
    post_id: int,
    data: CommentRequest,
    user=Depends(require_user),
):

    text = data.text.strip()

    if not text:

        raise HTTPException(
            status_code=400,
            detail="Comment cannot be empty.",
        )

    with get_conn() as conn:

        post = conn.execute(
            """
            SELECT id
            FROM posts
            WHERE id=%s
              AND deleted_at IS NULL
            """,
            (post_id,),
        ).fetchone()

        if not post:

            raise HTTPException(
                status_code=404,
                detail="Post not found.",
            )

        row = conn.execute(
            """
            INSERT INTO comments
                (
                    user_id,
                    post_id,
                    text
                )
            VALUES
                (%s,%s,%s)
            RETURNING
                id,
                user_id,
                post_id,
                text,
                created_at
            """,
            (
                user["id"],
                post_id,
                text,
            ),
        ).fetchone()

        conn.commit()

    return {
        "success": True,
        "comment": {
            **row,
            "created_at": serialize_datetime(
                row["created_at"]
            ),
            "author": clean_user(user),
        },
    }


@app.get("/api/posts/{post_id}/comments")
def get_comments(
    post_id: int,
    user=Depends(require_user),
):

    with get_conn() as conn:

        rows = conn.execute(
            """
            SELECT
                c.id,
                c.user_id,
                c.post_id,
                c.text,
                c.created_at,
                u.name,
                u.username,
                u.avatar
            FROM comments c
            JOIN users u
              ON u.id=c.user_id
            WHERE c.post_id=%s
              AND u.deleted_at IS NULL
            ORDER BY c.created_at ASC
            LIMIT 500
            """,
            (post_id,),
        ).fetchall()

    return {
        "success": True,
        "comments": [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "post_id": row["post_id"],
                "text": row["text"],
                "created_at": serialize_datetime(
                    row["created_at"]
                ),
                "author": {
                    "id": row["user_id"],
                    "name": row["name"],
                    "username": row[
                        "username"
                    ],
                    "avatar": row[
                        "avatar"
                    ],
                },
            }
            for row in rows
        ],
    }


# ============================================================
# SAVE / RESHARE
# ============================================================

@app.post("/api/posts/{post_id}/save")
def save_post(
    post_id: int,
    user=Depends(require_user),
):

    with get_conn() as conn:

        conn.execute(
            """
            INSERT INTO saved_posts
                (
                    user_id,
                    post_id
                )
            VALUES
                (%s,%s)
            ON CONFLICT
                (user_id,post_id)
            DO NOTHING
            """,
            (
                user["id"],
                post_id,
            ),
        )

        conn.commit()

    return {
        "success": True,
        "saved": True,
    }


@app.delete("/api/posts/{post_id}/save")
def unsave_post(
    post_id: int,
    user=Depends(require_user),
):

    with get_conn() as conn:

        conn.execute(
            """
            DELETE FROM saved_posts
            WHERE user_id=%s
              AND post_id=%s
            """,
            (
                user["id"],
                post_id,
            ),
        )

        conn.commit()

    return {
        "success": True,
        "saved": False,
    }


@app.post("/api/posts/{post_id}/reshare")
def reshare_post(
    post_id: int,
    user=Depends(require_user),
):

    with get_conn() as conn:

        conn.execute(
            """
            INSERT INTO reshares
                (
                    user_id,
                    post_id
                )
            VALUES
                (%s,%s)
            ON CONFLICT
                (user_id,post_id)
            DO NOTHING
            """,
            (
                user["id"],
                post_id,
            ),
        )

        conn.commit()

    return {
        "success": True,
        "reshared": True,
    }


@app.delete("/api/posts/{post_id}/reshare")
def unreshare_post(
    post_id: int,
    user=Depends(require_user),
):

    with get_conn() as conn:

        conn.execute(
            """
            DELETE FROM reshares
            WHERE user_id=%s
              AND post_id=%s
            """,
            (
                user["id"],
                post_id,
            ),
        )

        conn.commit()

    return {
        "success": True,
        "reshared": False,
    }


# ============================================================
# CHAT
# ============================================================

@app.post("/api/messages")
def send_message(
    data: MessageRequest,
    user=Depends(require_user),
):

    text = data.text.strip()

    if not text:

        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    if data.receiver_id == user["id"]:

        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot message yourself."
            ),
        )

    with get_conn() as conn:

        receiver = conn.execute(
            """
            SELECT id
            FROM users
            WHERE id=%s
              AND deleted_at IS NULL
            """,
            (data.receiver_id,),
        ).fetchone()

        if not receiver:

            raise HTTPException(
                status_code=404,
                detail="Receiver not found.",
            )

        blocked = conn.execute(
            """
            SELECT 1
            FROM blocks
            WHERE
                (
                    blocker_id=%s
                    AND blocked_id=%s
                )
                OR
                (
                    blocker_id=%s
                    AND blocked_id=%s
                )
            LIMIT 1
            """,
            (
                user["id"],
                data.receiver_id,
                data.receiver_id,
                user["id"],
            ),
        ).fetchone()

        if blocked:

            raise HTTPException(
                status_code=403,
                detail="Messaging is blocked.",
            )

        row = conn.execute(
            """
            INSERT INTO messages
                (
                    sender_id,
                    receiver_id,
                    text
                )
            VALUES
                (%s,%s,%s)
            RETURNING
                id,
                sender_id,
                receiver_id,
                text,
                media_url,
                media_type,
                created_at,
                read_at
            """,
            (
                user["id"],
                data.receiver_id,
                text,
            ),
        ).fetchone()

        conn.commit()

    return {
        "success": True,
        "message": {
            **row,
            "created_at": serialize_datetime(
                row["created_at"]
            ),
            "read_at": serialize_datetime(
                row["read_at"]
            ),
        },
    }


@app.get("/api/messages/{other_user_id}")
def get_messages(
    other_user_id: int,
    user=Depends(require_user),
):

    with get_conn() as conn:

        rows = conn.execute(
            """
            SELECT
                id,
                sender_id,
                receiver_id,
                text,
                media_url,
                media_type,
                created_at,
                read_at
            FROM messages
            WHERE
                (
                    sender_id=%s
                    AND receiver_id=%s
                )
                OR
                (
                    sender_id=%s
                    AND receiver_id=%s
                )
            ORDER BY created_at ASC
            LIMIT 500
            """,
            (
                user["id"],
                other_user_id,
                other_user_id,
                user["id"],
            ),
        ).fetchall()

        conn.execute(
            """
            UPDATE messages
            SET read_at=NOW()
            WHERE sender_id=%s
              AND receiver_id=%s
              AND read_at IS NULL
            """,
            (
                other_user_id,
                user["id"],
            ),
        )

        conn.commit()

    return {
        "success": True,
        "messages": [
            {
                **row,
                "created_at": serialize_datetime(
                    row["created_at"]
                ),
                "read_at": serialize_datetime(
                    row["read_at"]
                ),
            }
            for row in rows
        ],
    }


# ============================================================
# VOICE NOTE
# ============================================================

@app.post("/api/messages/voice")
async def send_voice_note(
    receiver_id: int = Form(...),
    file: UploadFile = File(...),
    user=Depends(require_user),
):

    content_type = (
        file.content_type or ""
    ).lower()

    if not content_type.startswith(
        "audio/"
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Voice note must be audio."
            ),
        )

    media_url = await save_upload(
        file,
        VOICE_DIR,
        50 * 1024 * 1024,
    )

    with get_conn() as conn:

        row = conn.execute(
            """
            INSERT INTO messages
                (
                    sender_id,
                    receiver_id,
                    text,
                    media_url,
                    media_type
                )
            VALUES
                (%s,%s,%s,%s,%s)
            RETURNING
                id,
                sender_id,
                receiver_id,
                text,
                media_url,
                media_type,
                created_at
            """,
            (
                user["id"],
                receiver_id,
                "",
                media_url,
                content_type,
            ),
        ).fetchone()

        conn.commit()

    return {
        "success": True,
        "message": {
            **row,
            "created_at": serialize_datetime(
                row["created_at"]
            ),
        },
    }


# ============================================================
# CHAT FILE
# ============================================================

@app.post("/api/messages/file")
async def send_chat_file(
    receiver_id: int = Form(...),
    file: UploadFile = File(...),
    user=Depends(require_user),
):

    content_type = (
        file.content_type
        or "application/octet-stream"
    ).lower()

    media_url = await save_upload(
        file,
        CHAT_FILE_DIR,
        100 * 1024 * 1024,
    )

    with get_conn() as conn:

        row = conn.execute(
            """
            INSERT INTO messages
                (
                    sender_id,
                    receiver_id,
                    text,
                    media_url,
                    media_type
                )
            VALUES
                (%s,%s,%s,%s,%s)
            RETURNING
                id,
                sender_id,
                receiver_id,
                text,
                media_url,
                media_type,
                created_at
            """,
            (
                user["id"],
                receiver_id,
                "",
                media_url,
                content_type,
            ),
        ).fetchone()

        conn.commit()

    return {
        "success": True,
        "message": {
            **row,
            "created_at": serialize_datetime(
                row["created_at"]
            ),
        },
    }


# ============================================================
# BLOCK
# ============================================================

@app.post("/api/users/{other_user_id}/block")
def block_user(
    other_user_id: int,
    user=Depends(require_user),
):

    if other_user_id == user["id"]:

        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot block yourself."
            ),
        )

    with get_conn() as conn:

        receiver = conn.execute(
            """
            SELECT id
            FROM users
            WHERE id=%s
              AND deleted_at IS NULL
            """,
            (other_user_id,),
        ).fetchone()

        if not receiver:

            raise HTTPException(
                status_code=404,
                detail="User not found.",
            )

        conn.execute(
            """
            INSERT INTO blocks
                (
                    blocker_id,
                    blocked_id
                )
            VALUES
                (%s,%s)
            ON CONFLICT
                (blocker_id,blocked_id)
            DO NOTHING
            """,
            (
                user["id"],
                other_user_id,
            ),
        )

        conn.commit()

    return {
        "success": True,
        "blocked": True,
    }


@app.delete("/api/users/{other_user_id}/block")
def unblock_user(
    other_user_id: int,
    user=Depends(require_user),
):

    with get_conn() as conn:

        conn.execute(
            """
            DELETE FROM blocks
            WHERE blocker_id=%s
              AND blocked_id=%s
            """,
            (
                user["id"],
                other_user_id,
            ),
        )

        conn.commit()

    return {
        "success": True,
        "blocked": False,
    }


# ============================================================
# REPORT
# ============================================================

@app.post("/api/reports")
def report(
    data: ReportRequest,
    user=Depends(require_user),
):

    reason = data.reason.strip()

    if not reason:

        raise HTTPException(
            status_code=400,
            detail="Report reason is required.",
        )

    with get_conn() as conn:

        conn.execute(
            """
            INSERT INTO reports
                (
                    reporter_id,
                    reported_user_id,
                    post_id,
                    reason
                )
            VALUES
                (%s,%s,%s,%s)
            """,
            (
                user["id"],
                data.reported_user_id,
                data.post_id,
                reason,
            ),
        )

        conn.commit()

    return {
        "success": True,
        "message": "Report submitted.",
    }


# ============================================================
# LIVEKIT STATUS
# ============================================================

@app.get("/api/livekit/status")
def livekit_status():

    configured = bool(
        LIVEKIT_URL
        and LIVEKIT_API_KEY
        and LIVEKIT_API_SECRET
        and livekit_api
    )

    return {
        "success": True,
        "livekit": configured,
        "url": (
            LIVEKIT_URL
            if configured
            else None
        ),
    }


# ============================================================
# LIVEKIT TOKEN
# ============================================================

@app.get("/api/livekit/token")
def livekit_token_get(
    room: str = Query(
        ...,
        min_length=1,
        max_length=255,
    ),
    call_type: str = Query(
        default="audio"
    ),
    user=Depends(require_user),
):

    if not LIVEKIT_URL:

        raise HTTPException(
            status_code=503,
            detail=(
                "LIVEKIT_URL is not configured."
            ),
        )

    if not LIVEKIT_API_KEY:

        raise HTTPException(
            status_code=503,
            detail=(
                "LIVEKIT_API_KEY is not configured."
            ),
        )

    if not LIVEKIT_API_SECRET:

        raise HTTPException(
            status_code=503,
            detail=(
                "LIVEKIT_API_SECRET is not configured."
            ),
        )

    if livekit_api is None:

        raise HTTPException(
            status_code=503,
            detail=(
                "LiveKit package is not installed."
            ),
        )

    if call_type not in [
        "audio",
        "video",
    ]:

        raise HTTPException(
            status_code=400,
            detail=(
                "Call type must be audio or video."
            ),
        )

    try:

        token = (
            livekit_api.AccessToken(
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
                livekit_api.VideoGrants(
                    room_join=True,
                    room=room,
                    can_publish=True,
                    can_subscribe=True,
                )
            )
        )

        return {
            "success": True,
            "token": token.to_jwt(),
            "room": room,
            "url": LIVEKIT_URL,
            "call_type": call_type,
        }

    except Exception as exc:

        logger.exception(
            "LiveKit token error: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Failed to create LiveKit token."
            ),
        )


@app.post("/api/livekit/token")
def livekit_token_post(
    room: str = Query(
        ...,
        min_length=1,
        max_length=255,
    ),
    call_type: str = Query(
        default="audio"
    ),
    user=Depends(require_user),
):

    return livekit_token_get(
        room=room,
        call_type=call_type,
        user=user,
    )


# ============================================================
# CALL RECORDS
# ============================================================

@app.post("/api/calls")
def create_call(
    data: CallRequest,
    user=Depends(require_user),
):

    if data.call_type not in [
        "audio",
        "video",
    ]:

        raise HTTPException(
            status_code=400,
            detail=(
                "Call type must be audio or video."
            ),
        )

    if data.receiver_id == user["id"]:

        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot call yourself."
            ),
        )

    room_name = (
        "msafiri-"
        + uuid.uuid4().hex
    )

    with get_conn() as conn:

        receiver = conn.execute(
            """
            SELECT id
            FROM users
            WHERE id=%s
              AND deleted_at IS NULL
            """,
            (data.receiver_id,),
        ).fetchone()

        if not receiver:

            raise HTTPException(
                status_code=404,
                detail="Receiver not found.",
            )

        row = conn.execute(
            """
            INSERT INTO calls
                (
                    caller_id,
                    receiver_id,
                    room_name,
                    call_type
                )
            VALUES
                (%s,%s,%s,%s)
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
                user["id"],
                data.receiver_id,
                room_name,
                data.call_type,
            ),
        ).fetchone()

        conn.commit()

    return {
        "success": True,
        "call": {
            **row,
            "created_at": serialize_datetime(
                row["created_at"]
            ),
        },
    }


@app.patch("/api/calls/{call_id}")
def update_call(
    call_id: int,
    status: str = Query(...),
    user=Depends(require_user),
):

    allowed = [
        "ringing",
        "accepted",
        "rejected",
        "ended",
        "missed",
    ]

    if status not in allowed:

        raise HTTPException(
            status_code=400,
            detail="Invalid call status.",
        )

    with get_conn() as conn:

        row = conn.execute(
            """
            UPDATE calls
            SET
                status=%s,
                ended_at=
                    CASE
                        WHEN %s='ended'
                        THEN NOW()
                        ELSE ended_at
                    END
            WHERE id=%s
              AND (
                caller_id=%s
                OR receiver_id=%s
              )
            RETURNING
                id,
                caller_id,
                receiver_id,
                room_name,
                call_type,
                status,
                created_at,
                ended_at
            """,
            (
                status,
                status,
                call_id,
                user["id"],
                user["id"],
            ),
        ).fetchone()

        conn.commit()

    if not row:

        raise HTTPException(
            status_code=404,
            detail="Call not found.",
        )

    return {
        "success": True,
        "call": {
            **row,
            "created_at": serialize_datetime(
                row["created_at"]
            ),
            "ended_at": serialize_datetime(
                row["ended_at"]
            ),
        },
    }


# ============================================================
# STATIC MEDIA
# ============================================================

@app.get("/uploads/{filename}")
def uploaded_file(
    filename: str
):

    path = (
        UPLOAD_DIR / filename
    )

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail="File not found.",
        )

    return FileResponse(path)


@app.get("/posts/{filename}")
def post_file(
    filename: str
):

    path = (
        POST_DIR / filename
    )

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail="Post media not found.",
        )

    return FileResponse(path)


@app.get("/avatars/{filename}")
def avatar_file(
    filename: str
):

    path = (
        AVATAR_DIR / filename
    )

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail="Avatar not found.",
        )

    return FileResponse(path)


@app.get("/voice/{filename}")
def voice_file(
    filename: str
):

    path = (
        VOICE_DIR / filename
    )

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail="Voice file not found.",
        )

    return FileResponse(path)


@app.get("/chat_files/{filename}")
def chat_file(
    filename: str
):

    path = (
        CHAT_FILE_DIR / filename
    )

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail="Chat file not found.",
        )

    return FileResponse(path)


@app.get("/wallpapers/{filename}")
def wallpaper_file(
    filename: str
):

    path = (
        WALLPAPER_DIR / filename
    )

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail="Wallpaper not found.",
        )

    return FileResponse(path)


# ============================================================
# GLOBAL ERROR HANDLER
# ============================================================

@app.exception_handler(Exception)
async def global_error_handler(
    request: Request,
    exc: Exception,
):

    logger.exception(
        "Unhandled error %s %s",
        request.method,
        request.url.path,
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "detail": "Internal server error.",
        },
    )


# ============================================================
# STATIC MOUNTS
# ============================================================

try:

    app.mount(
        "/static-uploads",
        StaticFiles(
            directory=str(
                UPLOAD_DIR
            )
        ),
        name="static-uploads",
    )

    app.mount(
        "/static-posts",
        StaticFiles(
            directory=str(
                POST_DIR
            )
        ),
        name="static-posts",
    )

    app.mount(
        "/static-avatars",
        StaticFiles(
            directory=str(
                AVATAR_DIR
            )
        ),
        name="static-avatars",
    )

except Exception as exc:

    logger.warning(
        "Static mount warning: %s",
        exc,
    )


# ============================================================
# LOCAL START
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
    )
