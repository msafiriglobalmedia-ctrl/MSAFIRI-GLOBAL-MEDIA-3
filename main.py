# ============================================================
# MSAFIRI GLOBAL MEDIA V5.0
# FULL CLEAN BACKEND
# FastAPI + PostgreSQL + JWT + LiveKit
# ============================================================

import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt

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

import psycopg
from psycopg.rows import dict_row
from psycopg.errors import UniqueViolation

from passlib.context import CryptContext

try:
    from livekit import api as livekit_api
except Exception:
    livekit_api = None


# ============================================================
# CONFIG
# ============================================================

APP_NAME = "MSAFIRI GLOBAL MEDIA"
APP_VERSION = "5.0"

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
)

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

logger = logging.getLogger("msafiri")


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
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


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_conn():
    if not DATABASE_URL:
        raise HTTPException(
            status_code=500,
            detail="DATABASE_URL is not configured.",
        )

    return psycopg.connect(
        DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=15,
    )


# ============================================================
# DATABASE INIT
# ============================================================

def init_database():

    if not DATABASE_URL:
        logger.warning(
            "DATABASE_URL is missing."
        )
        return

    with get_conn() as conn:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                name VARCHAR(150) NOT NULL,
                username VARCHAR(80) UNIQUE,
                email VARCHAR(255) UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                bio TEXT DEFAULT '',
                location VARCHAR(255) DEFAULT '',
                avatar TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                deleted_at TIMESTAMPTZ
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL
                    REFERENCES users(id)
                    ON DELETE CASCADE,
                token_id VARCHAR(255) UNIQUE NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                expires_at TIMESTAMPTZ NOT NULL
            )
        """)

        conn.execute("""
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
        """)

        conn.execute("""
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
        """)

        conn.execute("""
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
        """)

        conn.execute("""
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
        """)

        conn.execute("""
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
        """)

        conn.execute("""
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
        """)

        conn.execute("""
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
        """)

        conn.execute("""
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
        """)

        conn.execute("""
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
        """)

        conn.execute("""
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
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_posts_created
            ON posts(created_at DESC)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_users
            ON messages(sender_id, receiver_id, created_at DESC)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_comments_post
            ON comments(post_id, created_at ASC)
        """)

        conn.commit()

    logger.info(
        "Database initialized successfully."
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
# HELPERS
# ============================================================

def now_utc():
    return datetime.now(timezone.utc)


def serialize_datetime(value):

    if isinstance(value, datetime):
        return value.isoformat()

    return value


def public_url(path: Path):

    relative = "/" + str(
        path.relative_to(BASE_DIR)
    ).replace("\\", "/")

    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL + relative

    return relative


def hash_password(password: str):

    return pwd_context.hash(password)


def verify_password(
    password: str,
    password_hash: str,
):

    try:
        return pwd_context.verify(
            password,
            password_hash,
        )
    except Exception:
        return False


# ============================================================
# JWT
# ============================================================

def create_jwt(user_id: int):

    token_id = uuid.uuid4().hex

    issued_at = now_utc()

    expires_at = (
        issued_at
        + timedelta(days=JWT_EXPIRE_DAYS)
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

    return token, token_id, expires_at


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
            detail="Session expired. Please login again.",
        )

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=401,
            detail="Invalid authentication token.",
        )


def extract_bearer(
    authorization: Optional[str],
):

    if not authorization:

        raise HTTPException(
            status_code=401,
            detail="Authorization token required.",
        )

    if not authorization.lower().startswith(
        "bearer "
    ):

        raise HTTPException(
            status_code=401,
            detail="Authorization must use Bearer token.",
        )

    token = authorization[7:].strip()

    if not token:

        raise HTTPException(
            status_code=401,
            detail="Empty authentication token.",
        )

    return token


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
            detail="Invalid authentication payload.",
        )

    try:
        user_id = int(user_id)
    except Exception:

        raise HTTPException(
            status_code=401,
            detail="Invalid user ID.",
        )

    # --------------------------------------------------------
    # IMPORTANT:
    # Also verify that this JWT session exists in PostgreSQL.
    # --------------------------------------------------------

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
                detail="Session expired. Please login again.",
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
            detail="User account not found.",
        )

    return user


# ============================================================
# USER SERIALIZER
# ============================================================

def clean_user(user):

    if not user:
        return None

    return {
        "id": user.get("id"),
        "name": user.get("name"),
        "username": user.get("username"),
        "email": user.get("email"),
        "bio": user.get("bio") or "",
        "location": user.get("location") or "",
        "avatar": user.get("avatar"),
        "created_at": serialize_datetime(
            user.get("created_at")
        ),
    }


# ============================================================
# UPLOAD
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

    destination = (
        directory
        / f"{uuid.uuid4().hex}{extension}"
    )

    total = 0

    try:

        with destination.open("wb") as output:

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

                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "File too large. "
                            f"Maximum "
                            f"{max_size // "
                            "(1024 * 1024)"
                            } MB."
                        ),
                    )

                output.write(chunk)

    finally:

        await upload.close()

    return public_url(destination)


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


class ChatMessageRequest(BaseModel):

    receiver_id: int

    text: str = Field(
        default="",
        max_length=5000,
    )


class CallRequest(BaseModel):

    receiver_id: int

    call_type: str = "audio"


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    index_file = BASE_DIR / "index.html"

    if index_file.exists():

        return FileResponse(
            index_file,
            media_type="text/html",
        )

    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "status": "online",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    db_ok = False

    if DATABASE_URL:

        try:

            with get_conn() as conn:

                conn.execute(
                    "SELECT 1"
                ).fetchone()

            db_ok = True

        except Exception as exc:

            logger.error(
                "Database health error: %s",
                exc,
            )

    lk_ok = bool(
        LIVEKIT_URL
        and LIVEKIT_API_KEY
        and LIVEKIT_API_SECRET
        and livekit_api
    )

    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "database": (
            "postgresql"
            if db_ok
            else "not_connected"
        ),
        "livekit": lk_ok,
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
    data: RegisterRequest,
):

    name = data.name.strip()

    username = (
        data.username.strip().lower()
        if data.username
        else None
    )

    email = (
        str(data.email)
        .strip()
        .lower()
    )

    if not name:

        raise HTTPException(
            status_code=400,
            detail="Name is required.",
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

    password_hash = hash_password(
        data.password
    )

    try:

        with get_conn() as conn:

            user = conn.execute(
                """
                INSERT INTO users
                    (
                        name,
                        username,
                        email,
                        password_hash
                    )
                VALUES
                    (%s,%s,%s,%s)
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
                ),
            ).fetchone()

            conn.commit()

        token, token_id, expires_at = (
            create_jwt(user["id"])
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

        return {
            "success": True,
            "message": "Registration successful.",
            "token": token,
            "access_token": token,
            "user": clean_user(user),
        }

    except UniqueViolation:

        raise HTTPException(
            status_code=409,
            detail=(
                "Email or username already exists."
            ),
        )


@app.post("/api/register")
def register_alias(
    data: RegisterRequest,
):

    return register(data)


# ============================================================
# LOGIN
# ============================================================

@app.post("/api/auth/login")
def login(
    data: LoginRequest,
):

    email = (
        str(data.email)
        .strip()
        .lower()
    )

    with get_conn() as conn:

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE LOWER(email)=LOWER(%s)
              AND deleted_at IS NULL
            """,
            (email,),
        ).fetchone()

    if not user:

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    if not verify_password(
        data.password,
        user["password_hash"],
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    token, token_id, expires_at = (
        create_jwt(user["id"])
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

    return {
        "success": True,
        "message": "Login successful.",
        "token": token,
        "access_token": token,
        "user": clean_user(user),
    }


@app.post("/api/login")
def login_alias(
    data: LoginRequest,
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
    user=Depends(require_user),
):

    return {
        "success": True,
        "user": clean_user(user),
    }


@app.get("/api/auth/me")
def auth_me(
    user=Depends(require_user),
):

    return {
        "success": True,
        "user": clean_user(user),
    }


# ============================================================
# USERS / PEOPLE
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
                ORDER BY name ASC
                LIMIT 100
                """,
                (
                    user["id"],
                    f"%{q}%",
                    f"%{q}%",
                    f"%{q}%",
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

        name = data.name.strip()

        if not name:

            raise HTTPException(
                status_code=400,
                detail="Name cannot be empty.",
            )

        fields.append("name=%s")
        values.append(name)

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

        fields.append("username=%s")
        values.append(username or None)

    if data.bio is not None:

        fields.append("bio=%s")
        values.append(
            data.bio.strip()
        )

    if data.location is not None:

        fields.append("location=%s")
        values.append(
            data.location.strip()
        )

    if not fields:

        return {
            "success": True,
            "user": clean_user(user),
        }

    fields.append(
        "updated_at=NOW()"
    )

    values.append(user["id"])

    try:

        with get_conn() as conn:

            row = conn.execute(
                f"""
                UPDATE users
                SET {", ".join(fields)}
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

        return {
            "success": True,
            "user": clean_user(row),
        }

    except UniqueViolation:

        raise HTTPException(
            status_code=409,
            detail="Username is already taken.",
        )


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

        row = conn.execute(
            """
            UPDATE users
            SET
                avatar=%s,
                updated_at=NOW()
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
            (
                avatar_url,
                user["id"],
            ),
        ).fetchone()

        conn.commit()

    return {
        "success": True,
        "avatar": avatar_url,
        "user": clean_user(row),
    }


# ============================================================
# POSTS
# ============================================================

POST_SELECT = """
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
            "username": row["author_username"],
            "email": row["author_email"],
            "bio": row["author_bio"] or "",
            "location": row["author_location"] or "",
            "avatar": row["author_avatar"],
        },
    }


# ============================================================
# GET POSTS
# ============================================================

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
            POST_SELECT
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


# ============================================================
# CREATE POST
# ============================================================

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
        ).lower().strip()

        allowed = (
            content_type.startswith("image/")
            or content_type.startswith("video/")
            or content_type.startswith("audio/")
        )

        if not allowed:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Only image, video or audio "
                    "media is supported."
                ),
            )

        if content_type.startswith(
            "video/"
        ):

            max_size = (
                200 * 1024 * 1024
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
                "Write something or select "
                "media first."
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
        "message": "Post published successfully.",
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


# ============================================================
# LIKE
# ============================================================

@app.post("/api/posts/{post_id}/like")
def like_post(
    post_id: int,
    user=Depends(require_user),
):

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

        conn.commit()

        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM likes
            WHERE post_id=%s
            """,
            (post_id,),
        ).fetchone()["count"]

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

        conn.commit()

        count = conn.execute(
            """
            SELECT COUNT(*)
            FROM likes
            WHERE post_id=%s
            """,
            (post_id,),
        ).fetchone()["count"]

    return {
        "success": True,
        "liked": False,
        "likes_count": int(count),
    }


# ============================================================
# COMMENTS
# ============================================================

@app.post("/api/posts/{post_id}/comment")
def comment_post(
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
            "id": row["id"],
            "user_id": row["user_id"],
            "post_id": row["post_id"],
            "text": row["text"],
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
                "id": r["id"],
                "user_id": r["user_id"],
                "post_id": r["post_id"],
                "text": r["text"],
                "created_at": serialize_datetime(
                    r["created_at"]
                ),
                "author": {
                    "id": r["user_id"],
                    "name": r["name"],
                    "username": r["username"],
                    "avatar": r["avatar"],
                },
            }
            for r in rows
        ],
    }


# ============================================================
# DELETE POST
# ============================================================

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
                detail="You can only delete your own post.",
            )

        conn.execute(
            """
            UPDATE posts
            SET deleted_at=NOW(),
                updated_at=NOW()
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
# SAVE
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
                (user_id,post_id)
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


# ============================================================
# MEDIA
# ============================================================

@app.get("/posts/{filename}")
def get_post_media(
    filename: str,
):

    path = POST_DIR / filename

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail="Post media not found.",
        )

    return FileResponse(path)


@app.get("/avatars/{filename}")
def get_avatar(
    filename: str,
):

    path = AVATAR_DIR / filename

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail="Avatar not found.",
        )

    return FileResponse(path)


@app.get("/uploads/{filename}")
def get_upload(
    filename: str,
):

    path = UPLOAD_DIR / filename

    if not path.exists():

        raise HTTPException(
            status_code=404,
            detail="File not found.",
        )

    return FileResponse(path)


# ============================================================
# CHAT
# ============================================================

@app.post("/api/messages")
def send_message(
    data: ChatMessageRequest,
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
            detail="You cannot message yourself.",
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

    return {
        "success": True,
        "messages": [
            {
                **r,
                "created_at": serialize_datetime(
                    r["created_at"]
                ),
                "read_at": serialize_datetime(
                    r["read_at"]
                ),
            }
            for r in rows
        ],
    }


# ============================================================
# LIVEKIT
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


@app.post("/api/livekit/token")
def livekit_token(
    room: str = Query(...),
    call_type: str = Query(
        default="audio"
    ),
    user=Depends(require_user),
):

    if not (
        LIVEKIT_URL
        and LIVEKIT_API_KEY
        and LIVEKIT_API_SECRET
        and livekit_api
    ):

        raise HTTPException(
            status_code=503,
            detail="LiveKit is not configured.",
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
            "LiveKit error: %s",
            exc,
        )

        raise HTTPException(
            status_code=500,
            detail="Could not create LiveKit token.",
        )


# ============================================================
# CALLS
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
            detail="Call type must be audio or video.",
        )

    room_name = (
        "msafiri-"
        + uuid.uuid4().hex
    )

    with get_conn() as conn:

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


# ============================================================
# GLOBAL ERROR HANDLER
# ============================================================

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):

    logger.exception(
        "Unhandled error: %s %s",
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
# STATIC DIRECTORIES
# ============================================================

try:

    app.mount(
        "/static-posts",
        StaticFiles(
            directory=str(POST_DIR)
        ),
        name="static-posts",
    )

    app.mount(
        "/static-avatars",
        StaticFiles(
            directory=str(AVATAR_DIR)
        ),
        name="static-avatars",
    )

except Exception as exc:

    logger.warning(
        "Static mount warning: %s",
        exc,
    )


# ============================================================
# LOCAL RUN
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
