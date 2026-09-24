# ============================================================
# MSAFIRI GLOBAL MEDIA - PHASE 1 + 2
# FastAPI + PostgreSQL + JWT + LiveKit + Base64 Storage
# ============================================================

import os
import hashlib
import secrets
import base64
import mimetypes
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Optional, List

import psycopg
from psycopg.rows import dict_row

from fastapi import (
    FastAPI, HTTPException, UploadFile, File, Form,
    Header, Query, Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
import jwt


# ============================================================
# APP CONFIG
# ============================================================

APP_NAME = "MSAFIRI GLOBAL MEDIA"
APP_VERSION = "6.0.0-PHASE2"

BASE_DIR = Path(__file__).resolve().parent

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_IN_RENDER")
JWT_ALGORITHM = "HS256"
TOKEN_DAYS = 30

LIVEKIT_URL = (os.getenv("LIVEKIT_URL") or "").strip()
LIVEKIT_API_KEY = (os.getenv("LIVEKIT_API_KEY") or "").strip()
LIVEKIT_API_SECRET = (os.getenv("LIVEKIT_API_SECRET") or "").strip()

# Base64 storage limits (bytes)
MAX_AVATAR_BYTES = 2 * 1024 * 1024
MAX_POST_IMAGE_BYTES = 5 * 1024 * 1024
MAX_POST_VIDEO_BYTES = 50 * 1024 * 1024
MAX_CHAT_FILE_BYTES = 25 * 1024 * 1024
MAX_VOICE_BYTES = 5 * 1024 * 1024
MAX_WALLPAPER_BYTES = 1 * 1024 * 1024

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Msafiri Global Media - Phase 1 + 2 Backend",
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
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


def init_db():
    with get_conn() as conn:
        # ==================== USERS ====================
        conn.execute("""
            CREATE TABLE IF NOT EXISTS m_users (
                id BIGSERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                username TEXT UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                bio TEXT DEFAULT '',
                location TEXT DEFAULT '',
                avatar_data TEXT,
                avatar_mime TEXT,
                theme TEXT DEFAULT 'dark',
                deleted_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for col, typ in [
            ("username", "TEXT"),
            ("bio", "TEXT DEFAULT ''"),
            ("location", "TEXT DEFAULT ''"),
            ("avatar_data", "TEXT"),
            ("avatar_mime", "TEXT"),
            ("theme", "TEXT DEFAULT 'dark'"),
            ("deleted_at", "TIMESTAMPTZ"),
        ]:
            conn.execute(f"ALTER TABLE m_users ADD COLUMN IF NOT EXISTS {col} {typ}")

        # ==================== SESSIONS ====================
        conn.execute("""
            CREATE TABLE IF NOT EXISTS m_sessions (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMPTZ NOT NULL,
                revoked BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_m_sessions_token ON m_sessions(token_hash)")

        # ==================== FOLLOWS ====================
        conn.execute("""
            CREATE TABLE IF NOT EXISTS m_follows (
                id BIGSERIAL PRIMARY KEY,
                follower_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                following_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(follower_id, following_id)
            )
        """)

        # ==================== POSTS ====================
        conn.execute("""
            CREATE TABLE IF NOT EXISTS m_posts (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                caption TEXT NOT NULL DEFAULT '',
                media_data TEXT,
                media_mime TEXT,
                media_type TEXT,
                deleted_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_m_posts_created ON m_posts(created_at DESC)")

        # ==================== LIKES ====================
        conn.execute("""
            CREATE TABLE IF NOT EXISTS m_likes (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL REFERENCES m_posts(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id, user_id)
            )
        """)

        # ==================== COMMENTS ====================
        conn.execute("""
            CREATE TABLE IF NOT EXISTS m_comments (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL REFERENCES m_posts(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                text TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # ==================== SAVED POSTS ====================
        conn.execute("""
            CREATE TABLE IF NOT EXISTS m_saved (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL REFERENCES m_posts(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id, user_id)
            )
        """)

        # ==================== RESHARES ====================
        conn.execute("""
            CREATE TABLE IF NOT EXISTS m_reshares (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL REFERENCES m_posts(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id, user_id)
            )
        """)

        # ==================== MESSAGES ====================
        conn.execute("""
            CREATE TABLE IF NOT EXISTS m_messages (
                id BIGSERIAL PRIMARY KEY,
                sender_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                receiver_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                text TEXT DEFAULT '',
                media_data TEXT,
                media_mime TEXT,
                media_type TEXT,
                duration_seconds INTEGER DEFAULT 0,
                deleted_for_sender BOOLEAN NOT NULL DEFAULT FALSE,
                deleted_for_receiver BOOLEAN NOT NULL DEFAULT FALSE,
                seen BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_m_msg_sr ON m_messages(sender_id, receiver_id, created_at DESC)")

        # ==================== CHAT SETTINGS ====================
        conn.execute("""
            CREATE TABLE IF NOT EXISTS m_chat_settings (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                other_user_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                wallpaper_data TEXT,
                wallpaper_mime TEXT,
                pinned BOOLEAN NOT NULL DEFAULT FALSE,
                muted BOOLEAN NOT NULL DEFAULT FALSE,
                blocked BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, other_user_id)
            )
        """)

        # ==================== BLOCKS ====================
        conn.execute("""
            CREATE TABLE IF NOT EXISTS m_blocks (
                id BIGSERIAL PRIMARY KEY,
                blocker_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                blocked_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(blocker_id, blocked_id)
            )
        """)

        # ==================== STATUSES / STORIES ====================
        conn.execute("""
            CREATE TABLE IF NOT EXISTS m_statuses (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES m_users(id) ON DELETE CASCADE,
                text TEXT DEFAULT '',
                media_data TEXT,
                media_mime TEXT,
                media_type TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMPTZ
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_m_statuses_user ON m_statuses(user_id, created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_m_statuses_expires ON m_statuses(expires_at)")

        conn.commit()


@app.on_event("startup")
def startup():
    try:
        init_db()
        print("=" * 50)
        print(f"{APP_NAME} STARTED")
        print("DB:", "OK" if DATABASE_URL else "MISSING")
        print("LiveKit:", "OK" if (LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET) else "NOT SET")
        print("=" * 50)
    except Exception as exc:
        print("STARTUP ERROR:", type(exc).__name__, str(exc))
        raise


# ============================================================
# MODELS
# ============================================================

class RegisterIn(BaseModel):
    name: str
    username: Optional[str] = None
    email: EmailStr
    password: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class ProfileIn(BaseModel):
    name: Optional[str] = None
    username: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    theme: Optional[str] = None


class MessageIn(BaseModel):
    receiver_id: int
    text: str = ""


class CommentIn(BaseModel):
    text: str


class SettingsIn(BaseModel):
    pinned: Optional[bool] = None
    muted: Optional[bool] = None
    blocked: Optional[bool] = None


class CallIn(BaseModel):
    receiver_id: int
    call_type: str = "video"


# ============================================================
# AUTH HELPERS
# ============================================================

def hash_token(t: str) -> str:
    return hashlib.sha256(t.encode()).hexdigest()


def create_token(uid: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(uid), "iat": now, "exp": now + timedelta(days=TOKEN_DAYS)},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )


def decode_token(t: str):
    try:
        return jwt.decode(t, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")


def bearer(auth: Optional[str]) -> str:
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(401, "Bearer token required")
    t = auth.split(" ", 1)[1].strip()
    if not t:
        raise HTTPException(401, "Bearer token required")
    return t


def require_user(auth: Optional[str]):
    token = bearer(auth)
    payload = decode_token(token)
    try:
        uid = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(401, "Invalid token subject")
    with get_conn() as conn:
        u = conn.execute("""
            SELECT u.id, u.name, u.username, u.email, u.bio, u.location,
                   u.avatar_data, u.avatar_mime, u.theme,
                   u.created_at, u.updated_at
            FROM m_sessions s
            JOIN m_users u ON u.id = s.user_id
            WHERE s.token_hash = %s
              AND s.revoked = FALSE
              AND s.expires_at > CURRENT_TIMESTAMP
              AND u.id = %s
              AND u.deleted_at IS NULL
            LIMIT 1
        """, (hash_token(token), uid)).fetchone()
    if not u:
        raise HTTPException(401, "Session not found")
    return u


def make_avatar_url(user):
    if user.get("avatar_data") and user.get("avatar_mime"):
        return f"data:{user['avatar_mime']};base64,{user['avatar_data']}"
    return None


def public_user(u, viewer_id: Optional[int] = None):
    d = {
        "id": u["id"],
        "name": u["name"],
        "username": u.get("username"),
        "bio": u.get("bio") or "",
        "location": u.get("location") or "",
        "avatar": make_avatar_url(u),
        "theme": u.get("theme") or "dark",
        "created_at": u.get("created_at"),
    }
    if viewer_id is not None:
        with get_conn() as conn:
            d["followers_count"] = conn.execute(
                "SELECT COUNT(*) AS c FROM m_follows WHERE following_id = %s", (u["id"],)
            ).fetchone()["c"]
            d["following_count"] = conn.execute(
                "SELECT COUNT(*) AS c FROM m_follows WHERE follower_id = %s", (u["id"],)
            ).fetchone()["c"]
            d["posts_count"] = conn.execute(
                "SELECT COUNT(*) AS c FROM m_posts WHERE user_id = %s AND deleted_at IS NULL",
                (u["id"],)
            ).fetchone()["c"]
            d["is_following"] = conn.execute(
                "SELECT 1 FROM m_follows WHERE follower_id = %s AND following_id = %s",
                (viewer_id, u["id"])
            ).fetchone() is not None
    return d


# ============================================================
# ROOT / HEALTH
# ============================================================

@app.get("/", include_in_schema=False)
def root():
    idx = BASE_DIR / "index.html"
    if not idx.exists():
        return JSONResponse(404, {"status": "error", "message": "index.html not found"})
    return FileResponse(idx, media_type="text/html")


@app.get("/health")
def health():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}


@app.get("/api/health")
def health_api():
    return {"status": "ok", "app": APP_NAME, "version": APP_VERSION}
    # ============================================================
# AUTH ENDPOINTS
# ============================================================

@app.post("/api/register")
@app.post("/api/auth/register")
def register(data: RegisterIn):
    name = data.name.strip()
    email = str(data.email).strip().lower()
    username = (data.username or "").strip().lower() or None

    if len(name) < 2:
        raise HTTPException(400, "Name is too short")
    if len(data.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    if username and not username.replace("_", "").replace(".", "").isalnum():
        raise HTTPException(400, "Username can only contain letters, numbers, _ and .")

    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id, deleted_at FROM m_users WHERE email = %s LIMIT 1", (email,)
        ).fetchone()

        if existing and existing["deleted_at"] is None:
            raise HTTPException(409, "Email already registered")

        if username:
            u_ex = conn.execute(
                "SELECT id FROM m_users WHERE username = %s LIMIT 1", (username,)
            ).fetchone()
            if u_ex and (not existing or u_ex["id"] != existing["id"]):
                raise HTTPException(409, "Username already taken")

        pwd_hash = pwd_context.hash(data.password)

        if existing:
            uid = existing["id"]
            conn.execute("""
                UPDATE m_users
                SET name = %s, username = %s, password_hash = %s,
                    deleted_at = NULL, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (name, username, pwd_hash, uid))
        else:
            row = conn.execute("""
                INSERT INTO m_users (name, username, email, password_hash)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (name, username, email, pwd_hash)).fetchone()
            uid = row["id"]

        token = create_token(uid)
        expires = datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)

        conn.execute("""
            INSERT INTO m_sessions (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
        """, (uid, hash_token(token), expires))

        user = conn.execute("""
            SELECT id, name, username, email, bio, location,
                   avatar_data, avatar_mime, theme, created_at, updated_at
            FROM m_users WHERE id = %s
        """, (uid,)).fetchone()

        conn.commit()

    return {
        "message": "Account created",
        "token": token,
        "access_token": token,
        "user": public_user(user, uid),
    }


@app.post("/api/login")
@app.post("/api/auth/login")
def login(data: LoginIn):
    email = str(data.email).strip().lower()

    with get_conn() as conn:
        user = conn.execute("""
            SELECT id, name, username, email, password_hash, bio, location,
                   avatar_data, avatar_mime, theme, created_at, updated_at
            FROM m_users WHERE email = %s AND deleted_at IS NULL LIMIT 1
        """, (email,)).fetchone()

        if not user:
            raise HTTPException(401, "Invalid email or password")

        try:
            ok = pwd_context.verify(data.password, user["password_hash"])
        except Exception:
            ok = False
        if not ok:
            raise HTTPException(401, "Invalid email or password")

        token = create_token(user["id"])
        expires = datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)

        conn.execute("""
            INSERT INTO m_sessions (user_id, token_hash, expires_at)
            VALUES (%s, %s, %s)
        """, (user["id"], hash_token(token), expires))

        conn.commit()

    user.pop("password_hash", None)
    return {
        "message": "Login successful",
        "token": token,
        "access_token": token,
        "user": public_user(user, user["id"]),
    }


@app.post("/api/logout")
@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    token = bearer(authorization)
    with get_conn() as conn:
        conn.execute(
            "UPDATE m_sessions SET revoked = TRUE WHERE token_hash = %s",
            (hash_token(token),)
        )
        conn.commit()
    return {"message": "Logged out"}


@app.get("/api/me")
@app.get("/api/auth/me")
def me(authorization: Optional[str] = Header(default=None)):
    u = require_user(authorization)
    return {"user": public_user(u, u["id"])}


# ============================================================
# PROFILE
# ============================================================

@app.get("/api/users/{user_id}")
@app.get("/api/profile/{user_id}")
def profile(user_id: int, authorization: Optional[str] = Header(default=None)):
    viewer_id = None
    if authorization:
        try:
            viewer_id = require_user(authorization)["id"]
        except Exception:
            viewer_id = None

    with get_conn() as conn:
        u = conn.execute("""
            SELECT id, name, username, email, bio, location,
                   avatar_data, avatar_mime, theme, created_at, updated_at
            FROM m_users WHERE id = %s AND deleted_at IS NULL
        """, (user_id,)).fetchone()

    if not u:
        raise HTTPException(404, "User not found")
    return {"user": public_user(u, viewer_id if viewer_id is not None else user_id)}


@app.patch("/api/profile")
def update_profile(
    data: ProfileIn,
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)

    new_name = data.name.strip() if data.name is not None else user["name"]
    new_username = None
    if data.username is not None:
        u = data.username.strip().lower()
        if u and not u.replace("_", "").replace(".", "").isalnum():
            raise HTTPException(400, "Invalid username")
        new_username = u or None
    else:
        new_username = user.get("username")

    new_bio = data.bio.strip() if data.bio is not None else (user.get("bio") or "")
    new_loc = data.location.strip() if data.location is not None else (user.get("location") or "")
    new_theme = data.theme if data.theme in ("dark", "light") else user.get("theme", "dark")

    if len(new_name) < 2:
        raise HTTPException(400, "Name is too short")
    if len(new_bio) > 500:
        raise HTTPException(400, "Bio is too long")

    with get_conn() as conn:
        if new_username:
            ex = conn.execute(
                "SELECT id FROM m_users WHERE username = %s AND id != %s",
                (new_username, user["id"])
            ).fetchone()
            if ex:
                raise HTTPException(409, "Username already taken")

        row = conn.execute("""
            UPDATE m_users
            SET name = %s, username = %s, bio = %s, location = %s, theme = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            RETURNING id, name, username, email, bio, location,
                      avatar_data, avatar_mime, theme, created_at, updated_at
        """, (new_name, new_username, new_bio, new_loc, new_theme, user["id"])).fetchone()
        conn.commit()

    return {"message": "Profile updated", "user": public_user(row, user["id"])}


@app.post("/api/profile/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)

    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(400, "Avatar must be an image")

    content = await file.read()
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(400, f"Avatar too large (max {MAX_AVATAR_BYTES // 1024 // 1024} MB)")

    b64 = base64.b64encode(content).decode("ascii")

    with get_conn() as conn:
        conn.execute("""
            UPDATE m_users
            SET avatar_data = %s, avatar_mime = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (b64, content_type, user["id"]))
        conn.commit()

    return {"message": "Avatar updated", "avatar": f"data:{content_type};base64,{b64}"}


@app.delete("/api/profile/avatar")
def delete_avatar(authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        conn.execute(
            "UPDATE m_users SET avatar_data = NULL, avatar_mime = NULL WHERE id = %s",
            (user["id"],)
        )
        conn.commit()
    return {"message": "Avatar removed"}


# ============================================================
# FOLLOWS
# ============================================================

@app.post("/api/users/{user_id}/follow")
def follow(user_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    if user_id == user["id"]:
        raise HTTPException(400, "Cannot follow yourself")

    with get_conn() as conn:
        target = conn.execute(
            "SELECT id FROM m_users WHERE id = %s AND deleted_at IS NULL", (user_id,)
        ).fetchone()
        if not target:
            raise HTTPException(404, "User not found")

        conn.execute("""
            INSERT INTO m_follows (follower_id, following_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
        """, (user["id"], user_id))
        conn.commit()

    return {"following": True}


@app.delete("/api/users/{user_id}/follow")
def unfollow(user_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM m_follows WHERE follower_id = %s AND following_id = %s",
            (user["id"], user_id)
        )
        conn.commit()
    return {"following": False}


@app.get("/api/users/{user_id}/followers")
def followers(user_id: int):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT u.id, u.name, u.username, u.bio,
                   u.avatar_data, u.avatar_mime, u.created_at
            FROM m_follows f
            JOIN m_users u ON u.id = f.follower_id
            WHERE f.following_id = %s AND u.deleted_at IS NULL
            ORDER BY f.created_at DESC LIMIT 200
        """, (user_id,)).fetchall()

    return {"users": [public_user(r) for r in rows]}


@app.get("/api/users/{user_id}/following")
def following(user_id: int):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT u.id, u.name, u.username, u.bio,
                   u.avatar_data, u.avatar_mime, u.created_at
            FROM m_follows f
            JOIN m_users u ON u.id = f.following_id
            WHERE f.follower_id = %s AND u.deleted_at IS NULL
            ORDER BY f.created_at DESC LIMIT 200
        """, (user_id,)).fetchall()

    return {"users": [public_user(r) for r in rows]}


@app.get("/api/users/suggested")
def suggested(authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT u.id, u.name, u.username, u.bio,
                   u.avatar_data, u.avatar_mime, u.created_at
            FROM m_users u
            WHERE u.deleted_at IS NULL
              AND u.id != %s
              AND u.id NOT IN (
                SELECT following_id FROM m_follows WHERE follower_id = %s
              )
            ORDER BY u.created_at DESC LIMIT 30
        """, (user["id"], user["id"])).fetchall()

    return {"users": [public_user(r) for r in rows]}


# ============================================================
# SEARCH
# ============================================================

@app.get("/api/search")
def search(
    q: str = Query(..., min_length=1),
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)
    like = f"%{q.strip()}%"

    with get_conn() as conn:
        users = conn.execute("""
            SELECT id, name, username, bio, avatar_data, avatar_mime, created_at
            FROM m_users
            WHERE deleted_at IS NULL
              AND (name ILIKE %s OR username ILIKE %s OR email ILIKE %s)
            ORDER BY name LIMIT 30
        """, (like, like, like)).fetchall()

        posts = conn.execute("""
            SELECT p.id, p.caption, p.created_at,
                   u.id AS user_id, u.name AS user_name, u.username AS user_username,
                   u.avatar_data, u.avatar_mime
            FROM m_posts p
            JOIN m_users u ON u.id = p.user_id
            WHERE p.deleted_at IS NULL AND u.deleted_at IS NULL
              AND p.caption ILIKE %s
            ORDER BY p.created_at DESC LIMIT 30
        """, (like,)).fetchall()

    return {
        "users": [public_user(u) for u in users],
        "posts": [{
            "id": p["id"],
            "caption": p["caption"],
            "created_at": p["created_at"],
            "user": {
                "id": p["user_id"],
                "name": p["user_name"],
                "username": p["user_username"],
                "avatar": (f"data:{p['avatar_mime']};base64,{p['avatar_data']}"
                          if p["avatar_data"] and p["avatar_mime"] else None),
            },
        } for p in posts],
    }


# ============================================================
# POSTS
# ============================================================

@app.post("/api/posts")
async def create_post(
    caption: str = Form(""),
    file: Optional[UploadFile] = File(default=None),
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)
    caption = caption.strip()

    media_data = None
    media_mime = None
    media_type = None

    if file and file.filename:
        ct = (file.content_type or "").lower()
        content = await file.read()

        if ct.startswith("image/"):
            if len(content) > MAX_POST_IMAGE_BYTES:
                raise HTTPException(400, "Image too large (max 5 MB)")
            media_type = "image"
        elif ct.startswith("video/"):
            if len(content) > MAX_POST_VIDEO_BYTES:
                raise HTTPException(400, "Video too large (max 50 MB)")
            media_type = "video"
        else:
            raise HTTPException(400, "Only images and videos are allowed")

        media_data = base64.b64encode(content).decode("ascii")
        media_mime = ct

    if not caption and not media_data:
        raise HTTPException(400, "Post cannot be empty")

    with get_conn() as conn:
        post = conn.execute("""
            INSERT INTO m_posts (user_id, caption, media_data, media_mime, media_type)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id, user_id, caption, media_type, created_at
        """, (user["id"], caption, media_data, media_mime, media_type)).fetchone()
        conn.commit()

    return {"message": "Post created", "post_id": post["id"]}


def post_row_to_dict(p, viewer_id: Optional[int]):
    with get_conn() as conn:
        likes = conn.execute(
            "SELECT COUNT(*) AS c FROM m_likes WHERE post_id = %s", (p["id"],)
        ).fetchone()["c"]
        comments = conn.execute(
            "SELECT COUNT(*) AS c FROM m_comments WHERE post_id = %s", (p["id"],)
        ).fetchone()["c"]
        reshares = conn.execute(
            "SELECT COUNT(*) AS c FROM m_reshares WHERE post_id = %s", (p["id"],)
        ).fetchone()["c"]
        liked = False
        saved = False
        if viewer_id:
            liked = conn.execute(
                "SELECT 1 FROM m_likes WHERE post_id = %s AND user_id = %s",
                (p["id"], viewer_id)
            ).fetchone() is not None
            saved = conn.execute(
                "SELECT 1 FROM m_saved WHERE post_id = %s AND user_id = %s",
                (p["id"], viewer_id)
            ).fetchone() is not None

    media = None
    if p.get("media_data") and p.get("media_mime"):
        media = f"data:{p['media_mime']};base64,{p['media_data']}"

    avatar = None
    if p.get("avatar_data") and p.get("avatar_mime"):
        avatar = f"data:{p['avatar_mime']};base64,{p['avatar_data']}"

    return {
        "id": p["id"],
        "user_id": p["user_id"],
        "caption": p["caption"],
        "media": media,
        "media_type": p.get("media_type"),
        "created_at": p["created_at"],
        "user": {
            "id": p["user_id"],
            "name": p["user_name"],
            "username": p.get("user_username"),
            "avatar": avatar,
        },
        "likes_count": likes,
        "comments_count": comments,
        "reshares_count": reshares,
        "liked": liked,
        "saved": saved,
    }


def fetch_post(conn, post_id: int):
    return conn.execute("""
        SELECT p.id, p.user_id, p.caption, p.media_data, p.media_mime, p.media_type,
               p.created_at, p.deleted_at,
               u.name AS user_name, u.username AS user_username,
               u.avatar_data, u.avatar_mime
        FROM m_posts p
        JOIN m_users u ON u.id = p.user_id
        WHERE p.id = %s
    """, (post_id,)).fetchone()


@app.get("/api/posts")
def list_posts(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    feed: str = Query("all"),
    authorization: Optional[str] = Header(default=None),
):
    viewer_id = None
    if authorization:
        try:
            viewer_id = require_user(authorization)["id"]
        except Exception:
            viewer_id = None

    with get_conn() as conn:
        if feed == "following" and viewer_id:
            rows = conn.execute("""
                SELECT p.id, p.user_id, p.caption, p.media_data, p.media_mime,
                       p.media_type, p.created_at,
                       u.name AS user_name, u.username AS user_username,
                       u.avatar_data, u.avatar_mime
                FROM m_posts p
                JOIN m_users u ON u.id = p.user_id
                WHERE p.deleted_at IS NULL AND u.deleted_at IS NULL
                  AND (
                    p.user_id = %s
                    OR p.user_id IN (
                        SELECT following_id FROM m_follows WHERE follower_id = %s
                    )
                  )
                ORDER BY p.created_at DESC LIMIT %s OFFSET %s
            """, (viewer_id, viewer_id, limit, offset)).fetchall()
        else:
            rows = conn.execute("""
                SELECT p.id, p.user_id, p.caption, p.media_data, p.media_mime,
                       p.media_type, p.created_at,
                       u.name AS user_name, u.username AS user_username,
                       u.avatar_data, u.avatar_mime
                FROM m_posts p
                JOIN m_users u ON u.id = p.user_id
                WHERE p.deleted_at IS NULL AND u.deleted_at IS NULL
                ORDER BY p.created_at DESC LIMIT %s OFFSET %s
            """, (limit, offset)).fetchall()

    return {"posts": [post_row_to_dict(p, viewer_id) for p in rows]}


@app.get("/api/posts/{post_id}")
def get_post(post_id: int, authorization: Optional[str] = Header(default=None)):
    viewer_id = None
    if authorization:
        try:
            viewer_id = require_user(authorization)["id"]
        except Exception:
            viewer_id = None

    with get_conn() as conn:
        p = fetch_post(conn, post_id)

    if not p or p["deleted_at"]:
        raise HTTPException(404, "Post not found")

    return {"post": post_row_to_dict(p, viewer_id)}


@app.delete("/api/posts/{post_id}")
def delete_post(post_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        row = conn.execute("""
            UPDATE m_posts SET deleted_at = CURRENT_TIMESTAMP
            WHERE id = %s AND user_id = %s AND deleted_at IS NULL
            RETURNING id
        """, (post_id, user["id"])).fetchone()
        if not row:
            raise HTTPException(404, "Post not found")
        conn.commit()
    return {"message": "Post deleted"}


@app.get("/api/users/{user_id}/posts")
def user_posts(user_id: int, authorization: Optional[str] = Header(default=None)):
    viewer_id = None
    if authorization:
        try:
            viewer_id = require_user(authorization)["id"]
        except Exception:
            viewer_id = None

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT p.id, p.user_id, p.caption, p.media_data, p.media_mime,
                   p.media_type, p.created_at,
                   u.name AS user_name, u.username AS user_username,
                   u.avatar_data, u.avatar_mime
            FROM m_posts p
            JOIN m_users u ON u.id = p.user_id
            WHERE p.user_id = %s AND p.deleted_at IS NULL AND u.deleted_at IS NULL
            ORDER BY p.created_at DESC LIMIT 100
        """, (user_id,)).fetchall()

    return {"posts": [post_row_to_dict(p, viewer_id) for p in rows]}
    # ============================================================
# LIKES / SAVES / RESHARES
# ============================================================

def _post_exists(conn, post_id):
    row = conn.execute(
        "SELECT id FROM m_posts WHERE id = %s AND deleted_at IS NULL", (post_id,)
    ).fetchone()
    if not row:
        raise HTTPException(404, "Post not found")


@app.post("/api/posts/{post_id}/like")
def like(post_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        _post_exists(conn, post_id)
        conn.execute("""
            INSERT INTO m_likes (post_id, user_id) VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (post_id, user["id"]))
        conn.commit()
    return {"liked": True}


@app.delete("/api/posts/{post_id}/like")
def unlike(post_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM m_likes WHERE post_id = %s AND user_id = %s",
            (post_id, user["id"])
        )
        conn.commit()
    return {"liked": False}


@app.post("/api/posts/{post_id}/save")
def save_post(post_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        _post_exists(conn, post_id)
        conn.execute("""
            INSERT INTO m_saved (post_id, user_id) VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (post_id, user["id"]))
        conn.commit()
    return {"saved": True}


@app.delete("/api/posts/{post_id}/save")
def unsave_post(post_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM m_saved WHERE post_id = %s AND user_id = %s",
            (post_id, user["id"])
        )
        conn.commit()
    return {"saved": False}


@app.get("/api/saved")
def my_saved(authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT p.id, p.user_id, p.caption, p.media_data, p.media_mime,
                   p.media_type, p.created_at,
                   u.name AS user_name, u.username AS user_username,
                   u.avatar_data, u.avatar_mime
            FROM m_saved s
            JOIN m_posts p ON p.id = s.post_id
            JOIN m_users u ON u.id = p.user_id
            WHERE s.user_id = %s AND p.deleted_at IS NULL AND u.deleted_at IS NULL
            ORDER BY s.created_at DESC LIMIT 100
        """, (user["id"],)).fetchall()
    return {"posts": [post_row_to_dict(p, user["id"]) for p in rows]}


@app.post("/api/posts/{post_id}/reshare")
def reshare(post_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        _post_exists(conn, post_id)
        conn.execute("""
            INSERT INTO m_reshares (post_id, user_id) VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (post_id, user["id"]))
        conn.commit()
    return {"reshared": True}


@app.delete("/api/posts/{post_id}/reshare")
def unreshare(post_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM m_reshares WHERE post_id = %s AND user_id = %s",
            (post_id, user["id"])
        )
        conn.commit()
    return {"reshared": False}


# ============================================================
# COMMENTS
# ============================================================

@app.post("/api/posts/{post_id}/comments")
def add_comment(
    post_id: int,
    data: CommentIn,
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)
    text = data.text.strip()
    if not text:
        raise HTTPException(400, "Comment cannot be empty")
    if len(text) > 2000:
        raise HTTPException(400, "Comment too long")

    with get_conn() as conn:
        _post_exists(conn, post_id)
        row = conn.execute("""
            INSERT INTO m_comments (post_id, user_id, text)
            VALUES (%s, %s, %s)
            RETURNING id, post_id, user_id, text, created_at
        """, (post_id, user["id"], text)).fetchone()
        conn.commit()

    return {
        "comment": {
            "id": row["id"],
            "post_id": row["post_id"],
            "user_id": row["user_id"],
            "text": row["text"],
            "created_at": row["created_at"],
            "user": {
                "id": user["id"],
                "name": user["name"],
                "username": user.get("username"),
                "avatar": make_avatar_url(user),
            },
        }
    }


@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id: int):
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT c.id, c.post_id, c.user_id, c.text, c.created_at,
                   u.name AS user_name, u.username AS user_username,
                   u.avatar_data, u.avatar_mime
            FROM m_comments c
            JOIN m_users u ON u.id = c.user_id
            WHERE c.post_id = %s AND u.deleted_at IS NULL
            ORDER BY c.created_at ASC LIMIT 500
        """, (post_id,)).fetchall()

    return {
        "comments": [{
            "id": r["id"],
            "post_id": r["post_id"],
            "user_id": r["user_id"],
            "text": r["text"],
            "created_at": r["created_at"],
            "user": {
                "id": r["user_id"],
                "name": r["user_name"],
                "username": r["user_username"],
                "avatar": (f"data:{r['avatar_mime']};base64,{r['avatar_data']}"
                          if r["avatar_data"] and r["avatar_mime"] else None),
            },
        } for r in rows],
    }


@app.delete("/api/comments/{comment_id}")
def delete_comment(comment_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        row = conn.execute(
            "DELETE FROM m_comments WHERE id = %s AND user_id = %s RETURNING id",
            (comment_id, user["id"])
        ).fetchone()
        if not row:
            raise HTTPException(404, "Comment not found")
        conn.commit()
    return {"message": "Comment deleted"}


# ============================================================
# MESSAGES
# ============================================================

@app.get("/api/messages")
def chat_list(authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT DISTINCT ON (other_id)
                other_id, name, username, avatar_data, avatar_mime,
                last_text, last_at, last_seen
            FROM (
                SELECT
                    CASE WHEN m.sender_id = %s THEN m.receiver_id ELSE m.sender_id END AS other_id,
                    u.name, u.username, u.avatar_data, u.avatar_mime,
                    m.text AS last_text, m.created_at AS last_at, m.seen AS last_seen
                FROM m_messages m
                JOIN m_users u ON u.id = CASE WHEN m.sender_id = %s THEN m.receiver_id ELSE m.sender_id END
                WHERE (m.sender_id = %s OR m.receiver_id = %s)
                  AND u.deleted_at IS NULL
                ORDER BY m.created_at DESC
            ) x
            ORDER BY other_id, last_at DESC
        """, (user["id"], user["id"], user["id"], user["id"])).fetchall()

    chats = []
    for r in rows:
        avatar = (f"data:{r['avatar_mime']};base64,{r['avatar_data']}"
                 if r["avatar_data"] and r["avatar_mime"] else None)
        chats.append({
            "other_id": r["other_id"],
            "name": r["name"],
            "username": r["username"],
            "avatar": avatar,
            "last_text": r["last_text"],
            "last_at": r["last_at"],
        })

    return {"chats": chats}


@app.get("/api/messages/{other_id}")
def message_history(
    other_id: int,
    limit: int = Query(100, ge=1, le=200),
    before_id: Optional[int] = None,
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)

    with get_conn() as conn:
        if before_id:
            rows = conn.execute("""
                SELECT id, sender_id, receiver_id, text, media_data, media_mime,
                       media_type, duration_seconds, created_at, seen
                FROM m_messages
                WHERE (
                    (sender_id = %s AND receiver_id = %s AND deleted_for_sender = FALSE)
                    OR (sender_id = %s AND receiver_id = %s AND deleted_for_receiver = FALSE)
                )
                AND id < %s
                ORDER BY created_at DESC LIMIT %s
            """, (user["id"], other_id, other_id, user["id"], before_id, limit)).fetchall()
        else:
            rows = conn.execute("""
                SELECT id, sender_id, receiver_id, text, media_data, media_mime,
                       media_type, duration_seconds, created_at, seen
                FROM m_messages
                WHERE (
                    (sender_id = %s AND receiver_id = %s AND deleted_for_sender = FALSE)
                    OR (sender_id = %s AND receiver_id = %s AND deleted_for_receiver = FALSE)
                )
                ORDER BY created_at DESC LIMIT %s
            """, (user["id"], other_id, other_id, user["id"], limit)).fetchall()

        conn.execute("""
            UPDATE m_messages SET seen = TRUE
            WHERE sender_id = %s AND receiver_id = %s
        """, (other_id, user["id"]))
        conn.commit()

    rows.reverse()

    out = []
    for r in rows:
        media = (f"data:{r['media_mime']};base64,{r['media_data']}"
                if r["media_data"] and r["media_mime"] else None)
        out.append({
            "id": r["id"],
            "sender_id": r["sender_id"],
            "receiver_id": r["receiver_id"],
            "text": r["text"] or "",
            "media": media,
            "media_type": r["media_type"],
            "duration_seconds": r["duration_seconds"] or 0,
            "created_at": r["created_at"],
            "seen": r["seen"],
        })

    return {"messages": out}


@app.post("/api/messages")
def send_message(data: MessageIn, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)

    if data.receiver_id == user["id"]:
        raise HTTPException(400, "Cannot message yourself")

    text = data.text.strip()
    if not text:
        raise HTTPException(400, "Message cannot be empty")
    if len(text) > 5000:
        raise HTTPException(400, "Message too long")

    with get_conn() as conn:
        rec = conn.execute(
            "SELECT id FROM m_users WHERE id = %s AND deleted_at IS NULL",
            (data.receiver_id,)
        ).fetchone()
        if not rec:
            raise HTTPException(404, "Receiver not found")

        blocked = conn.execute("""
            SELECT 1 FROM m_blocks
            WHERE (blocker_id = %s AND blocked_id = %s)
               OR (blocker_id = %s AND blocked_id = %s)
        """, (user["id"], data.receiver_id, data.receiver_id, user["id"])).fetchone()
        if blocked:
            raise HTTPException(403, "Messaging blocked")

        row = conn.execute("""
            INSERT INTO m_messages (sender_id, receiver_id, text)
            VALUES (%s, %s, %s)
            RETURNING id, sender_id, receiver_id, text, created_at, seen
        """, (user["id"], data.receiver_id, text)).fetchone()
        conn.commit()

    return {
        "message": {
            "id": row["id"],
            "sender_id": row["sender_id"],
            "receiver_id": row["receiver_id"],
            "text": row["text"],
            "media": None,
            "media_type": None,
            "duration_seconds": 0,
            "created_at": row["created_at"],
            "seen": row["seen"],
        }
    }


@app.post("/api/messages/voice")
async def send_voice(
    receiver_id: int = Form(...),
    duration_seconds: int = Form(0),
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)

    if receiver_id == user["id"]:
        raise HTTPException(400, "Cannot send to yourself")

    ct = (file.content_type or "").lower()
    if not ct.startswith("audio/"):
        raise HTTPException(400, "Voice note must be audio")

    content = await file.read()
    if len(content) > MAX_VOICE_BYTES:
        raise HTTPException(400, "Voice note too large (max 5 MB)")

    b64 = base64.b64encode(content).decode("ascii")

    with get_conn() as conn:
        row = conn.execute("""
            INSERT INTO m_messages
                (sender_id, receiver_id, text, media_data, media_mime, media_type, duration_seconds)
            VALUES (%s, %s, '', %s, %s, 'voice', %s)
            RETURNING id, sender_id, receiver_id, created_at, seen
        """, (user["id"], receiver_id, b64, ct, duration_seconds)).fetchone()
        conn.commit()

    return {
        "message": {
            "id": row["id"],
            "sender_id": row["sender_id"],
            "receiver_id": row["receiver_id"],
            "text": "",
            "media": f"data:{ct};base64,{b64}",
            "media_type": "voice",
            "duration_seconds": duration_seconds,
            "created_at": row["created_at"],
            "seen": row["seen"],
        }
    }


@app.post("/api/messages/file")
async def send_file(
    receiver_id: int = Form(...),
    text: str = Form(""),
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)

    if receiver_id == user["id"]:
        raise HTTPException(400, "Cannot send to yourself")

    content = await file.read()
    if len(content) > MAX_CHAT_FILE_BYTES:
        raise HTTPException(400, "File too large (max 25 MB)")

    ct = (file.content_type or "").lower() or "application/octet-stream"
    b64 = base64.b64encode(content).decode("ascii")

    media_type = "image" if ct.startswith("image/") else ("video" if ct.startswith("video/") else "file")

    with get_conn() as conn:
        row = conn.execute("""
            INSERT INTO m_messages
                (sender_id, receiver_id, text, media_data, media_mime, media_type)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, created_at, seen
        """, (user["id"], receiver_id, text.strip(), b64, ct, media_type)).fetchone()
        conn.commit()

    return {
        "message": {
            "id": row["id"],
            "sender_id": user["id"],
            "receiver_id": receiver_id,
            "text": text.strip(),
            "media": f"data:{ct};base64,{b64}",
            "media_type": media_type,
            "duration_seconds": 0,
            "created_at": row["created_at"],
            "seen": row["seen"],
        }
    }


@app.delete("/api/chats/{other_id}")
def clear_chat(other_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        conn.execute("""
            UPDATE m_messages SET deleted_for_sender = TRUE
            WHERE sender_id = %s AND receiver_id = %s
        """, (user["id"], other_id))
        conn.execute("""
            UPDATE m_messages SET deleted_for_receiver = TRUE
            WHERE sender_id = %s AND receiver_id = %s
        """, (other_id, user["id"]))
        conn.commit()
    return {"message": "Chat cleared"}


# ============================================================
# CHAT SETTINGS / WALLPAPER
# ============================================================

@app.get("/api/chats/{other_id}/settings")
def get_settings(other_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        row = conn.execute("""
            SELECT wallpaper_data, wallpaper_mime, pinned, muted, blocked
            FROM m_chat_settings
            WHERE user_id = %s AND other_user_id = %s
        """, (user["id"], other_id)).fetchone()

    if not row:
        return {"settings": {"pinned": False, "muted": False, "blocked": False, "wallpaper": None}}

    wp = (f"data:{row['wallpaper_mime']};base64,{row['wallpaper_data']}"
         if row["wallpaper_data"] and row["wallpaper_mime"] else None)

    return {"settings": {
        "pinned": row["pinned"],
        "muted": row["muted"],
        "blocked": row["blocked"],
        "wallpaper": wp,
    }}


@app.post("/api/chats/{other_id}/settings")
def update_settings(
    other_id: int,
    data: SettingsIn,
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)
    with get_conn() as conn:
        old = conn.execute("""
            SELECT pinned, muted, blocked FROM m_chat_settings
            WHERE user_id = %s AND other_user_id = %s
        """, (user["id"], other_id)).fetchone()

        pinned = data.pinned if data.pinned is not None else (old["pinned"] if old else False)
        muted = data.muted if data.muted is not None else (old["muted"] if old else False)
        blocked = data.blocked if data.blocked is not None else (old["blocked"] if old else False)

        conn.execute("""
            INSERT INTO m_chat_settings (user_id, other_user_id, pinned, muted, blocked)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (user_id, other_user_id)
            DO UPDATE SET pinned = EXCLUDED.pinned,
                          muted = EXCLUDED.muted,
                          blocked = EXCLUDED.blocked,
                          updated_at = CURRENT_TIMESTAMP
        """, (user["id"], other_id, pinned, muted, blocked))
        conn.commit()

    return {"settings": {"pinned": pinned, "muted": muted, "blocked": blocked}}


@app.post("/api/chats/{other_id}/wallpaper")
async def set_wallpaper(
    other_id: int,
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)

    ct = (file.content_type or "").lower()
    if not ct.startswith("image/"):
        raise HTTPException(400, "Wallpaper must be an image")

    content = await file.read()
    if len(content) > MAX_WALLPAPER_BYTES:
        raise HTTPException(400, "Wallpaper too large (max 1 MB)")

    b64 = base64.b64encode(content).decode("ascii")

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO m_chat_settings (user_id, other_user_id, wallpaper_data, wallpaper_mime)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (user_id, other_user_id)
            DO UPDATE SET wallpaper_data = EXCLUDED.wallpaper_data,
                          wallpaper_mime = EXCLUDED.wallpaper_mime,
                          updated_at = CURRENT_TIMESTAMP
        """, (user["id"], other_id, b64, ct))
        conn.commit()

    return {"message": "Wallpaper updated", "wallpaper": f"data:{ct};base64,{b64}"}


@app.delete("/api/chats/{other_id}/wallpaper")
def delete_wallpaper(other_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        conn.execute("""
            UPDATE m_chat_settings
            SET wallpaper_data = NULL, wallpaper_mime = NULL
            WHERE user_id = %s AND other_user_id = %s
        """, (user["id"], other_id))
        conn.commit()
    return {"message": "Wallpaper removed"}


# ============================================================
# BLOCK / UNBLOCK
# ============================================================

@app.post("/api/users/{user_id}/block")
def block_user(user_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    if user_id == user["id"]:
        raise HTTPException(400, "Cannot block yourself")

    with get_conn() as conn:
        conn.execute("""
            INSERT INTO m_blocks (blocker_id, blocked_id)
            VALUES (%s, %s) ON CONFLICT DO NOTHING
        """, (user["id"], user_id))
        conn.commit()
    return {"blocked": True}


@app.delete("/api/users/{user_id}/block")
def unblock_user(user_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM m_blocks WHERE blocker_id = %s AND blocked_id = %s",
            (user["id"], user_id)
        )
        conn.commit()
    return {"blocked": False}


# ============================================================
# LIVEKIT CALL TOKEN
# ============================================================

@app.post("/api/calls/token")
def call_token(data: CallIn, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)

    if not (LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET):
        raise HTTPException(503, "LiveKit not configured")

    if data.receiver_id == user["id"]:
        raise HTTPException(400, "Cannot call yourself")

    call_type = "audio" if data.call_type.lower().strip() == "audio" else "video"

    try:
        from livekit import api
    except ImportError:
        raise HTTPException(500, "LiveKit package missing")

    room_name = "msafiri-" + secrets.token_hex(10)

    token = (
        api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
        .with_identity(str(user["id"]))
        .with_name(user["name"])
        .with_grants(api.VideoGrants(room_join=True, room=room_name))
        .to_jwt()
    )

    return {
        "token": token,
        "livekit_url": LIVEKIT_URL,
        "room_name": room_name,
        "call_type": call_type,
        "caller_id": user["id"],
        "receiver_id": data.receiver_id,
    }

# ============================================================
# VIDEO PLATFORM (PHASE 3)
# ============================================================

@app.get("/api/videos")
def list_videos(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    authorization: Optional[str] = Header(default=None),
):
    viewer_id = None
    if authorization:
        try:
            viewer_id = require_user(authorization)["id"]
        except Exception:
            viewer_id = None

    with get_conn() as conn:
        rows = conn.execute("""
            SELECT p.id, p.user_id, p.caption, p.media_data, p.media_mime,
                   p.media_type, p.created_at,
                   u.name AS user_name, u.username AS user_username,
                   u.avatar_data, u.avatar_mime,
                   (
                       SELECT COUNT(*) FROM m_likes l WHERE l.post_id = p.id
                   ) AS likes_count,
                   (
                       SELECT COUNT(*) FROM m_comments c WHERE c.post_id = p.id
                   ) AS comments_count,
                   (
                       SELECT COUNT(*) FROM m_reshares r WHERE r.post_id = p.id
                   ) AS reshares_count
            FROM m_posts p
            JOIN m_users u ON u.id = p.user_id
            WHERE p.deleted_at IS NULL
              AND u.deleted_at IS NULL
              AND p.media_type = 'video'
            ORDER BY p.created_at DESC
            LIMIT %s OFFSET %s
        """, (limit, offset)).fetchall()

        out = []
        for p in rows:
            media = None
            if p["media_data"] and p["media_mime"]:
                media = f"data:{p['media_mime']};base64,{p['media_data']}"
            avatar = None
            if p["avatar_data"] and p["avatar_mime"]:
                avatar = f"data:{p['avatar_mime']};base64,{p['avatar_data']}"

            liked = False
            if viewer_id:
                liked = conn.execute(
                    "SELECT 1 FROM m_likes WHERE post_id = %s AND user_id = %s",
                    (p["id"], viewer_id)
                ).fetchone() is not None

            out.append({
                "id": p["id"],
                "user_id": p["user_id"],
                "caption": p["caption"],
                "media": media,
                "media_type": p["media_type"],
                "created_at": p["created_at"],
                "user": {
                    "id": p["user_id"],
                    "name": p["user_name"],
                    "username": p["user_username"],
                    "avatar": avatar,
                },
                "likes_count": p["likes_count"],
                "comments_count": p["comments_count"],
                "reshares_count": p["reshares_count"],
                "liked": liked,
            })

    return {"videos": out}
# ============================================================
# ACCOUNT DELETION
# ============================================================

@app.delete("/api/account")
def delete_account(authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        conn.execute("""
            UPDATE m_users SET deleted_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (user["id"],))
        conn.execute("UPDATE m_sessions SET revoked = TRUE WHERE user_id = %s", (user["id"],))
        conn.commit()
    return {"message": "Account deleted"}


# ============================================================
# STATUSES / STORIES (PHASE 2)
# ============================================================

@app.post("/api/statuses")
async def create_status(
    text: str = Form(""),
    file: Optional[UploadFile] = File(default=None),
    authorization: Optional[str] = Header(default=None),
):
    user = require_user(authorization)
    text = (text or "").strip()
    media_data = None
    media_mime = None
    media_type = None

    if file and file.filename:
        ct = (file.content_type or "").lower()
        content = await file.read()

        if ct.startswith("image/"):
            if len(content) > 10 * 1024 * 1024:
                raise HTTPException(400, "Image too large (max 10 MB)")
            media_type = "image"
        elif ct.startswith("video/"):
            if len(content) > 50 * 1024 * 1024:
                raise HTTPException(400, "Video too large (max 50 MB)")
            media_type = "video"
        elif ct.startswith("audio/"):
            if len(content) > 15 * 1024 * 1024:
                raise HTTPException(400, "Audio too large (max 15 MB)")
            media_type = "audio"
        else:
            raise HTTPException(400, "Unsupported file type")

        media_data = base64.b64encode(content).decode("ascii")
        media_mime = ct

    if not text and not media_data:
        raise HTTPException(400, "Status cannot be empty")

    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    with get_conn() as conn:
        row = conn.execute("""
            INSERT INTO m_statuses (user_id, text, media_data, media_mime, media_type, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id, user_id, text, media_type, created_at, expires_at
        """, (user["id"], text, media_data, media_mime, media_type, expires_at)).fetchone()
        conn.commit()

    return {"message": "Status created", "status": dict(row)}


@app.get("/api/statuses")
def list_statuses(authorization: Optional[str] = Header(default=None)):
    me = require_user(authorization)
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT s.id, s.user_id, s.text, s.media_data, s.media_mime, s.media_type,
                   s.created_at, s.expires_at,
                   u.name AS user_name, u.username AS user_username,
                   u.avatar_data, u.avatar_mime
            FROM m_statuses s
            JOIN m_users u ON u.id = s.user_id
            WHERE s.expires_at > CURRENT_TIMESTAMP
              AND u.deleted_at IS NULL
              AND (
                s.user_id = %s
                OR s.user_id IN (
                    SELECT following_id FROM m_follows WHERE follower_id = %s
                )
              )
            ORDER BY s.created_at DESC
            LIMIT 200
        """, (me["id"], me["id"])).fetchall()

        users_map = {}
        for r in rows:
            uid = r["user_id"]
            if uid not in users_map:
                avatar = None
                if r["avatar_data"] and r["avatar_mime"]:
                    avatar = f"data:{r['avatar_mime']};base64,{r['avatar_data']}"
                users_map[uid] = {
                    "user": {
                        "id": uid,
                        "name": r["user_name"],
                        "username": r["user_username"],
                        "avatar": avatar,
                    },
                    "statuses": [],
                }
            media = None
            if r["media_data"] and r["media_mime"]:
                media = f"data:{r['media_mime']};base64,{r['media_data']}"
            users_map[uid]["statuses"].append({
                "id": r["id"],
                "text": r["text"] or "",
                "media": media,
                "media_type": r["media_type"],
                "created_at": r["created_at"],
                "expires_at": r["expires_at"],
            })

    groups = list(users_map.values())
    groups.sort(key=lambda g: 0 if g["user"]["id"] == me["id"] else 1)
    return {"groups": groups}


@app.delete("/api/statuses/{status_id}")
def delete_status(status_id: int, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    with get_conn() as conn:
        row = conn.execute("""
            DELETE FROM m_statuses
            WHERE id = %s AND user_id = %s
            RETURNING id
        """, (status_id, user["id"])).fetchone()
        if not row:
            raise HTTPException(404, "Status not found or not yours")
        conn.commit()
    return {"message": "Status deleted"}
    # ============================================================
# ERROR HANDLER
# ============================================================

@app.exception_handler(Exception)
async def global_error(request: Request, exc: Exception):
    print("UNHANDLED:", type(exc).__name__, str(exc))
    return JSONResponse(500, {
        "status": "error",
        "detail": "Internal Server Error",
        "error": str(exc),
        "type": type(exc).__name__,
    })


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
