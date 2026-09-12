import os
import uuid
import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException,
    Request,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel


# =========================================================
# MSAFIRI GLOBAL MEDIA V3
# Backend API
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "msafiri.db"
UPLOAD_DIR = BASE_DIR / "uploads"

UPLOAD_DIR.mkdir(exist_ok=True)

MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB

app = FastAPI(
    title="MSAFIRI GLOBAL MEDIA V3 API",
    version="3.0.0",
    description="Backend API for MSAFIRI GLOBAL MEDIA",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# STATIC UPLOADS
# =========================================================

app.mount(
    "/uploads",
    StaticFiles(directory=str(UPLOAD_DIR)),
    name="uploads",
)


# =========================================================
# DATABASE
# =========================================================

def db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def now():
    return datetime.utcnow().isoformat()


def init_db():

    conn = db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        bio TEXT DEFAULT '',
        avatar TEXT DEFAULT '',
        followers_count INTEGER DEFAULT 0,
        following_count INTEGER DEFAULT 0,
        likes_count INTEGER DEFAULT 0,
        posts_count INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        caption TEXT DEFAULT '',
        media_url TEXT DEFAULT '',
        media_type TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS likes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        UNIQUE(user_id, post_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS saved_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        UNIQUE(user_id, post_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reshares (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        post_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(user_id, post_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER NOT NULL,
        receiver_id INTEGER NOT NULL,
        text TEXT DEFAULT '',
        media_url TEXT DEFAULT '',
        voice_url TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        read INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS statuses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        text TEXT DEFAULT '',
        media_url TEXT DEFAULT '',
        media_type TEXT DEFAULT '',
        audio_url TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS followers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        follower_id INTEGER NOT NULL,
        following_id INTEGER NOT NULL,
        UNIQUE(follower_id, following_id)
    )
    """)

    conn.commit()
    conn.close()


init_db()


# =========================================================
# SECURITY HELPERS
# =========================================================

def hash_password(password: str):
    salt = secrets.token_bytes(16)

    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        120000,
    )

    return salt.hex() + ":" + key.hex()


def verify_password(password: str, stored: str):

    try:

        salt_hex, key_hex = stored.split(":")

        salt = bytes.fromhex(salt_hex)

        new_key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode(),
            salt,
            120000,
        )

        return secrets.compare_digest(
            new_key.hex(),
            key_hex,
        )

    except Exception:
        return False


def create_session(user_id: int):

    token = secrets.token_urlsafe(48)

    conn = db()

    conn.execute(
        """
        INSERT INTO sessions(token,user_id,created_at)
        VALUES(?,?,?)
        """,
        (token, user_id, now()),
    )

    conn.commit()
    conn.close()

    return token


def get_token(request: Request):

    auth = request.headers.get("Authorization", "")

    if auth.startswith("Bearer "):
        return auth[7:]

    return request.cookies.get("session")


def current_user(request: Request):

    token = get_token(request)

    if not token:
        return None

    conn = db()

    row = conn.execute(
        """
        SELECT users.*
        FROM users
        JOIN sessions
        ON users.id=sessions.user_id
        WHERE sessions.token=?
        """,
        (token,),
    ).fetchone()

    conn.close()

    return dict(row) if row else None


def require_user(request: Request):

    user = current_user(request)

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    return user


# =========================================================
# FILE HELPERS
# =========================================================

ALLOWED_IMAGE = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

ALLOWED_VIDEO = {
    "video/mp4",
    "video/webm",
    "video/ogg",
}

ALLOWED_AUDIO = {
    "audio/webm",
    "audio/ogg",
    "audio/mpeg",
    "audio/wav",
}


async def save_upload(
    file: UploadFile,
    folder: str,
    allowed_types=None,
):

    if not file:
        return None, None

    if allowed_types and file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type",
        )

    data = await file.read()

    if len(data) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File is too large",
        )

    extension = Path(file.filename or "").suffix.lower()

    filename = (
        f"{uuid.uuid4().hex}"
        f"{extension}"
    )

    folder_path = UPLOAD_DIR / folder
    folder_path.mkdir(exist_ok=True)

    destination = folder_path / filename

    destination.write_bytes(data)

    url = f"/uploads/{folder}/{filename}"

    return url, file.content_type


# =========================================================
# BASIC
# =========================================================

@app.get("/")
def root():

    index = BASE_DIR / "index.html"

    if index.exists():
        return FileResponse(index)

    return {
        "name": "MSAFIRI GLOBAL MEDIA V3",
        "status": "online",
    }


@app.get("/api/health")
def health():

    return {
        "status": "online",
        "service": "MSAFIRI GLOBAL MEDIA V3",
        "time": now(),
    }


# =========================================================
# AUTH
# =========================================================

class RegisterRequest(BaseModel):

    name: str
    email: str
    password: str


class LoginRequest(BaseModel):

    email: str
    password: str


@app.post("/api/register")
def register(data: RegisterRequest):

    name = data.name.strip()
    email = data.email.strip().lower()
    password = data.password

    if not name or not email or not password:
        raise HTTPException(
            400,
            "All fields are required",
        )

    if len(password) < 6:
        raise HTTPException(
            400,
            "Password must contain at least 6 characters",
        )

    conn = db()

    existing = conn.execute(
        "SELECT id FROM users WHERE email=?",
        (email,),
    ).fetchone()

    if existing:
        conn.close()

        raise HTTPException(
            409,
            "Email already registered",
        )

    password_hash = hash_password(password)

    cur = conn.execute(
        """
        INSERT INTO users
        (name,email,password_hash,created_at)
        VALUES(?,?,?,?)
        """,
        (
            name,
            email,
            password_hash,
            now(),
        ),
    )

    user_id = cur.lastrowid

    conn.commit()
    conn.close()

    token = create_session(user_id)

    return {
        "message": "Account created successfully",
        "token": token,
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
        },
    }


@app.post("/api/login")
def login(data: LoginRequest):

    email = data.email.strip().lower()

    conn = db()

    user = conn.execute(
        "SELECT * FROM users WHERE email=?",
        (email,),
    ).fetchone()

    conn.close()

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

    token = create_session(user["id"])

    return {
        "message": "Login successful",
        "token": token,
        "user": dict(user),
    }


@app.post("/api/logout")
def logout(request: Request):

    token = get_token(request)

    if token:

        conn = db()

        conn.execute(
            "DELETE FROM sessions WHERE token=?",
            (token,),
        )

        conn.commit()
        conn.close()

    return {
        "message": "Logged out",
    }


@app.get("/api/me")
def me(request: Request):

    user = require_user(request)

    return user


# =========================================================
# USERS
# =========================================================

@app.get("/api/users")
def users(request: Request):

    user = require_user(request)

    conn = db()

    rows = conn.execute(
        """
        SELECT id,name,bio,avatar
        FROM users
        WHERE id != ?
        ORDER BY name
        """,
        (user["id"],),
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# =========================================================
# POSTS
# =========================================================

@app.get("/api/posts")
def get_posts():

    conn = db()

    rows = conn.execute(
        """
        SELECT
            posts.*,
            users.name AS user_name,
            users.avatar AS avatar
        FROM posts
        JOIN users
        ON posts.user_id=users.id
        ORDER BY posts.id DESC
        """
    ).fetchall()

    conn.close()

    result = []

    for row in rows:

        item = dict(row)

        item["likes"] = get_post_count(
            "likes",
            row["id"],
        )

        item["comments"] = get_post_count(
            "comments",
            row["id"],
        )

        result.append(item)

    return result


def get_post_count(table, post_id):

    conn = db()

    row = conn.execute(
        f"SELECT COUNT(*) AS count FROM {table} WHERE post_id=?",
        (post_id,),
    ).fetchone()

    conn.close()

    return row["count"]


@app.post("/api/posts")
async def create_post(
    request: Request,
    caption: str = Form(""),
    media: Optional[UploadFile] = File(None),
):

    user = require_user(request)

    media_url = ""
    media_type = ""

    if media:

        media_url, media_type = await save_upload(
            media,
            "posts",
            ALLOWED_IMAGE | ALLOWED_VIDEO,
        )

    conn = db()

    cur = conn.execute(
        """
        INSERT INTO posts
        (user_id,caption,media_url,media_type,created_at)
        VALUES(?,?,?,?,?)
        """,
        (
            user["id"],
            caption.strip(),
            media_url or "",
            media_type or "",
            now(),
        ),
    )

    post_id = cur.lastrowid

    conn.execute(
        """
        UPDATE users
        SET posts_count=posts_count+1
        WHERE id=?
        """,
        (user["id"],),
    )

    conn.commit()
    conn.close()

    return {
        "message": "Post published",
        "id": post_id,
        "media_url": media_url,
        "media_type": media_type,
    }


# =========================================================
# LIKE
# =========================================================

@app.post("/api/posts/{post_id}/like")
def like_post(
    post_id: int,
    request: Request,
):

    user = require_user(request)

    conn = db()

    exists = conn.execute(
        """
        SELECT id
        FROM likes
        WHERE user_id=? AND post_id=?
        """,
        (
            user["id"],
            post_id,
        ),
    ).fetchone()

    if exists:

        conn.execute(
            "DELETE FROM likes WHERE id=?",
            (exists["id"],),
        )

        liked = False

    else:

        conn.execute(
            """
            INSERT INTO likes(user_id,post_id)
            VALUES(?,?)
            """,
            (
                user["id"],
                post_id,
            ),
        )

        liked = True

    conn.commit()
    conn.close()

    return {
        "liked": liked,
        "likes": get_post_count(
            "likes",
            post_id,
        ),
    }


# =========================================================
# COMMENTS
# =========================================================

class CommentRequest(BaseModel):

    text: str


@app.post("/api/posts/{post_id}/comments")
def comment_post(
    post_id: int,
    data: CommentRequest,
    request: Request,
):

    user = require_user(request)

    text = data.text.strip()

    if not text:
        raise HTTPException(
            400,
            "Comment cannot be empty",
        )

    conn = db()

    cur = conn.execute(
        """
        INSERT INTO comments
        (user_id,post_id,text,created_at)
        VALUES(?,?,?,?)
        """,
        (
            user["id"],
            post_id,
            text,
            now(),
        ),
    )

    conn.commit()
    conn.close()

    return {
        "message": "Comment added",
        "id": cur.lastrowid,
    }


@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id: int):

    conn = db()

    rows = conn.execute(
        """
        SELECT
            comments.*,
            users.name,
            users.avatar
        FROM comments
        JOIN users
        ON comments.user_id=users.id
        WHERE post_id=?
        ORDER BY comments.id ASC
        """,
        (post_id,),
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# =========================================================
# SAVE
# =========================================================

@app.post("/api/posts/{post_id}/save")
def save_post(
    post_id: int,
    request: Request,
):

    user = require_user(request)

    conn = db()

    exists = conn.execute(
        """
        SELECT id
        FROM saved_posts
        WHERE user_id=? AND post_id=?
        """,
        (
            user["id"],
            post_id,
        ),
    ).fetchone()

    if exists:

        conn.execute(
            "DELETE FROM saved_posts WHERE id=?",
            (exists["id"],),
        )

        saved = False

    else:

        conn.execute(
            """
            INSERT INTO saved_posts(user_id,post_id)
            VALUES(?,?)
            """,
            (
                user["id"],
                post_id,
            ),
        )

        saved = True

    conn.commit()
    conn.close()

    return {
        "saved": saved,
    }


@app.get("/api/saved")
def saved_posts(request: Request):

    user = require_user(request)

    conn = db()

    rows = conn.execute(
        """
        SELECT
            posts.*,
            users.name AS user_name,
            users.avatar
        FROM saved_posts
        JOIN posts
        ON saved_posts.post_id=posts.id
        JOIN users
        ON posts.user_id=users.id
        WHERE saved_posts.user_id=?
        ORDER BY saved_posts.id DESC
        """,
        (user["id"],),
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# =========================================================
# RESHARE
# =========================================================

@app.post("/api/posts/{post_id}/reshare")
def reshare_post(
    post_id: int,
    request: Request,
):

    user = require_user(request)

    conn = db()

    exists = conn.execute(
        """
        SELECT id
        FROM reshares
        WHERE user_id=? AND post_id=?
        """,
        (
            user["id"],
            post_id,
        ),
    ).fetchone()

    if not exists:

        conn.execute(
            """
            INSERT INTO reshares
            (user_id,post_id,created_at)
            VALUES(?,?,?)
            """,
            (
                user["id"],
                post_id,
                now(),
            ),
        )

        conn.commit()

    conn.close()

    return {
        "message": "Post reshared",
    }


# =========================================================
# PROFILE
# =========================================================

@app.put("/api/profile")
async def update_profile(
    request: Request,
    name: str = Form(""),
    bio: str = Form(""),
    avatar: Optional[UploadFile] = File(None),
):

    user = require_user(request)

    avatar_url = None

    if avatar:

        avatar_url, _ = await save_upload(
            avatar,
            "avatars",
            ALLOWED_IMAGE,
        )

    conn = db()

    if avatar_url:

        conn.execute(
            """
            UPDATE users
            SET name=?,bio=?,avatar=?
            WHERE id=?
            """,
            (
                name.strip(),
                bio.strip(),
                avatar_url,
                user["id"],
            ),
        )

    else:

        conn.execute(
            """
            UPDATE users
            SET name=?,bio=?
            WHERE id=?
            """,
            (
                name.strip(),
                bio.strip(),
                user["id"],
            ),
        )

    conn.commit()
    conn.close()

    return {
        "message": "Profile updated",
    }


# =========================================================
# STATUS
# =========================================================

@app.get("/api/status")
def get_status():

    conn = db()

    rows = conn.execute(
        """
        SELECT
            statuses.*,
            users.name,
            users.avatar
        FROM statuses
        JOIN users
        ON statuses.user_id=users.id
        ORDER BY statuses.id DESC
        """
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


@app.post("/api/status")
async def create_status(
    request: Request,
    text: str = Form(""),
    media: Optional[UploadFile] = File(None),
    audio: Optional[UploadFile] = File(None),
):

    user = require_user(request)

    media_url = ""
    media_type = ""
    audio_url = ""

    if media:

        media_url, media_type = await save_upload(
            media,
            "status",
            ALLOWED_IMAGE | ALLOWED_VIDEO,
        )

    if audio:

        audio_url, _ = await save_upload(
            audio,
            "status_audio",
            ALLOWED_AUDIO,
        )

    conn = db()

    cur = conn.execute(
        """
        INSERT INTO statuses
        (user_id,text,media_url,media_type,audio_url,created_at)
        VALUES(?,?,?,?,?,?)
        """,
        (
            user["id"],
            text.strip(),
            media_url or "",
            media_type or "",
            audio_url or "",
            now(),
        ),
    )

    conn.commit()
    conn.close()

    return {
        "message": "Status published",
        "id": cur.lastrowid,
    }


# =========================================================
# CHAT
# =========================================================

class MessageRequest(BaseModel):

    receiver_id: int
    text: str


@app.get("/api/messages/{user_id}")
def get_messages(
    user_id: int,
    request: Request,
):

    user = require_user(request)

    conn = db()

    rows = conn.execute(
        """
        SELECT *
        FROM messages
        WHERE
        (sender_id=? AND receiver_id=?)
        OR
        (sender_id=? AND receiver_id=?)
        ORDER BY id ASC
        """,
        (
            user["id"],
            user_id,
            user_id,
            user["id"],
        ),
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]


@app.post("/api/messages")
def send_message(
    data: MessageRequest,
    request: Request,
):

    user = require_user(request)

    if not data.text.strip():
        raise HTTPException(
            400,
            "Message cannot be empty",
        )

    conn = db()

    cur = conn.execute(
        """
        INSERT INTO messages
        (sender_id,receiver_id,text,created_at)
        VALUES(?,?,?,?)
        """,
        (
            user["id"],
            data.receiver_id,
            data.text.strip(),
            now(),
        ),
    )

    conn.commit()
    conn.close()

    return {
        "message": "Message sent",
        "id": cur.lastrowid,
    }


# =========================================================
# VOICE MESSAGE
# =========================================================

@app.post("/api/messages/voice")
async def voice_message(
    request: Request,
    receiver_id: int = Form(...),
    voice: UploadFile = File(...),
):

    user = require_user(request)

    voice_url, _ = await save_upload(
        voice,
        "voice",
        ALLOWED_AUDIO,
    )

    conn = db()

    cur = conn.execute(
        """
        INSERT INTO messages
        (sender_id,receiver_id,voice_url,created_at)
        VALUES(?,?,?,?)
        """,
        (
            user["id"],
            int(receiver_id),
            voice_url,
            now(),
        ),
    )

    conn.commit()
    conn.close()

    return {
        "message": "Voice note sent",
        "voice_url": voice_url,
        "id": cur.lastrowid,
    }


# =========================================================
# AI
# =========================================================

class AIRequest(BaseModel):

    council: str
    question: str
    country: Optional[str] = None
    education_level: Optional[str] = None


@app.post("/api/ai")
def ai(data: AIRequest):

    council = data.council.strip()

    if not data.question.strip():
        raise HTTPException(
            400,
            "Question is required",
        )

    # -----------------------------------------------------
    # AI PROVIDER CONNECTION
    # -----------------------------------------------------
    #
    # This is intentionally a safe fallback.
    #
    # To connect a real AI provider, put its API call here.
    #
    # Do NOT put an API secret directly in this file.
    # Use an environment variable on your hosting service.
    #
    # -----------------------------------------------------

    if council == "Education AI":

        answer = (
            "Education AI is ready. "
            f"Curriculum: {data.country or 'Not specified'}. "
            f"Level: {data.education_level or 'Not specified'}. "
            f"Question received: {data.question}"
        )

    elif council == "Health AI":

        answer = (
            "Health AI can provide general educational "
            "health information. It cannot replace a "
            "qualified healthcare professional. "
            f"Question received: {data.question}"
        )

    elif council == "Agricultural AI":

        answer = (
            "Agricultural AI can provide educational "
            "information about crops, soil, farming, "
            "pests, irrigation and agricultural research. "
            f"Question received: {data.question}"
        )

    elif council == "Research AI":

        answer = (
            "Research AI can help with research questions, "
            "study design, literature organization, "
            "analysis ideas and academic explanations. "
            f"Question received: {data.question}"
        )

    else:

        answer = (
            f"AI Council '{council}' received your question: "
            f"{data.question}"
        )

    return {
        "answer": answer,
        "council": council,
    }


# =========================================================
# GOOGLE LOGIN FOUNDATION
# =========================================================

@app.get("/api/auth/google")
def google_login():

    google_client_id = os.getenv(
        "GOOGLE_CLIENT_ID"
    )

    if not google_client_id:

        return {
            "configured": False,
            "message": (
                "Google OAuth is not configured yet. "
                "Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET "
                "as environment variables."
            ),
        }

    return {
        "configured": True,
        "message": "Google OAuth configuration detected.",
    }


# =========================================================
# STARTUP INFO
# =========================================================

@app.get("/api")
def api_info():

    return {
        "name": "MSAFIRI GLOBAL MEDIA V3",
        "version": "3.0.0",
        "status": "online",
        "features": [
            "authentication",
            "profiles",
            "posts",
            "photo_upload",
            "video_upload",
            "likes",
            "comments",
            "saved_posts",
            "reshares",
            "status",
            "chat",
            "voice_notes",
            "AI foundation",
            "Google OAuth foundation",
        ],
    }
