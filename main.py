# ============================================================
# MSAFIRI GLOBAL MEDIA V4.2
# FastAPI + PostgreSQL + JWT + LiveKit
# FULL CLEAN SINGLE-FILE BACKEND
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
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
import jwt

APP_NAME = "MSAFIRI GLOBAL MEDIA V4.2"
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
AVATAR_DIR = UPLOAD_DIR / "avatars"
POST_DIR = UPLOAD_DIR / "posts"
VOICE_DIR = UPLOAD_DIR / "voice"
CHAT_FILE_DIR = UPLOAD_DIR / "chat_files"
WALLPAPER_DIR = UPLOAD_DIR / "wallpapers"

for d in (UPLOAD_DIR, AVATAR_DIR, POST_DIR, VOICE_DIR, CHAT_FILE_DIR, WALLPAPER_DIR):
    d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_THIS_SECRET_IN_RENDER")
JWT_ALGORITHM = "HS256"
TOKEN_DAYS = 30

LIVEKIT_URL = (os.getenv("LIVEKIT_URL") or "").strip()
LIVEKIT_API_KEY = (os.getenv("LIVEKIT_API_KEY") or "").strip()
LIVEKIT_API_SECRET = (os.getenv("LIVEKIT_API_SECRET") or "").strip()

# Legacy bcrypt verification + Argon2 for all new passwords.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_hasher = PasswordHasher()

app = FastAPI(title=APP_NAME, version="4.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    with get_conn() as conn:
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
        for sql in (
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS bio TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar TEXT",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ):
            conn.execute(sql)

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
        for sql in (
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ",
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS revoked BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "UPDATE sessions SET expires_at=CURRENT_TIMESTAMP + INTERVAL '30 days' WHERE expires_at IS NULL",
        ):
            conn.execute(sql)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token_hash)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id BIGSERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                caption TEXT NOT NULL DEFAULT '',
                media_url TEXT,
                media_type TEXT,
                deleted_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for sql in (
            "ALTER TABLE posts ADD COLUMN IF NOT EXISTS caption TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE posts ADD COLUMN IF NOT EXISTS media_url TEXT",
            "ALTER TABLE posts ADD COLUMN IF NOT EXISTS media_type TEXT",
            "ALTER TABLE posts ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ",
            "ALTER TABLE posts ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE posts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ):
            conn.execute(sql)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_created ON posts(created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_user ON posts(user_id)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS likes (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id,user_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                text TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS saved_posts (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id,user_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reshares (
                id BIGSERIAL PRIMARY KEY,
                post_id BIGINT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
                user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(post_id,user_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id BIGSERIAL PRIMARY KEY,
                sender_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                receiver_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                text TEXT DEFAULT '',
                media_url TEXT,
                media_type TEXT,
                voice_url TEXT,
                duration_seconds INTEGER,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_for_sender BOOLEAN NOT NULL DEFAULT FALSE,
                deleted_for_receiver BOOLEAN NOT NULL DEFAULT FALSE,
                seen BOOLEAN NOT NULL DEFAULT FALSE
            )
        """)
        for sql in (
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS text TEXT DEFAULT ''",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS media_url TEXT",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS media_type TEXT",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS voice_url TEXT",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS duration_seconds INTEGER",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS deleted_for_sender BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS deleted_for_receiver BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS seen BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE messages ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ):
            conn.execute(sql)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_sr ON messages(sender_id,receiver_id,created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_rs ON messages(receiver_id,sender_id,created_at DESC)")

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
                UNIQUE(user_id,other_user_id)
            )
        """)
        for sql in (
            "ALTER TABLE chat_settings ADD COLUMN IF NOT EXISTS wallpaper_url TEXT",
            "ALTER TABLE chat_settings ADD COLUMN IF NOT EXISTS pinned BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE chat_settings ADD COLUMN IF NOT EXISTS muted BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE chat_settings ADD COLUMN IF NOT EXISTS blocked BOOLEAN NOT NULL DEFAULT FALSE",
            "ALTER TABLE chat_settings ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
            "ALTER TABLE chat_settings ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP",
        ):
            conn.execute(sql)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS blocks (
                id BIGSERIAL PRIMARY KEY,
                blocker_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                blocked_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(blocker_id,blocked_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id BIGSERIAL PRIMARY KEY,
                reporter_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                reported_user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                post_id BIGINT REFERENCES posts(id) ON DELETE CASCADE,
                reason TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS calls (
                id BIGSERIAL PRIMARY KEY,
                caller_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                receiver_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                room_name TEXT NOT NULL,
                call_type TEXT NOT NULL DEFAULT 'video',
                status TEXT NOT NULL DEFAULT 'ringing',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                ended_at TIMESTAMPTZ
            )
        """)
        conn.commit()

@app.on_event("startup")
def startup():
    init_db()

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class ProfileRequest(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None

class MessageRequest(BaseModel):
    receiver_id: int
    text: str

class CommentRequest(BaseModel):
    text: str

class ChatSettingsRequest(BaseModel):
    pinned: Optional[bool] = None
    muted: Optional[bool] = None
    blocked: Optional[bool] = None

class ReportRequest(BaseModel):
    reason: str

class CallTokenRequest(BaseModel):
    receiver_id: int
    call_type: str = "video"

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def create_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": str(user_id), "iat": now, "exp": now + timedelta(days=TOKEN_DAYS)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

def safe_filename(filename: Optional[str]) -> str:
    return secrets.token_hex(16) + Path(filename or "file").suffix.lower()

def public_url(path: Path) -> str:
    return "/" + str(path.relative_to(BASE_DIR)).replace("\\", "/")

def get_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    return authorization[7:].strip()

def require_user(authorization: Optional[str]):
    token = get_bearer_token(authorization)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    with get_conn() as conn:
        session = conn.execute("""
            SELECT s.user_id,s.expires_at,s.revoked,
                   u.id,u.name,u.email,u.bio,u.avatar,u.created_at,u.deleted_at
            FROM sessions s
            JOIN users u ON u.id=s.user_id
            WHERE s.token_hash=%s
        """, (hash_token(token),)).fetchone()
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session")
    if session["revoked"]:
        raise HTTPException(status_code=401, detail="Session revoked")
    if session["expires_at"] and session["expires_at"] < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired")
    if session["deleted_at"] is not None:
        raise HTTPException(status_code=401, detail="Account deleted")
    return session

def user_public(row):
    if not row:
        return None
    return {
        "id": row["id"], "name": row["name"], "email": row["email"],
        "bio": row.get("bio") or "", "avatar": row.get("avatar"),
        "created_at": row.get("created_at"),
    }

async def save_upload(file: UploadFile, directory: Path, max_bytes: int):
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="File is too large")
    destination = directory / safe_filename(file.filename)
    destination.write_bytes(content)
    return public_url(destination)

@app.get("/", include_in_schema=False)
async def root():
    index_file = BASE_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(index_file)

@app.get("/api/health")
def health():
    return {
        "status": "ok", "app": APP_NAME,
        "database": "configured" if DATABASE_URL else "missing",
        "livekit": bool(LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET),
    }

@app.get("/api/health/db")
def health_db():
    try:
        with get_conn() as conn:
            row = conn.execute("SELECT CURRENT_TIMESTAMP AS server_time").fetchone()
        return {"status": "ok", "database": "postgresql", "server_time": row["server_time"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/register")
def register(data: RegisterRequest):
    name = data.name.strip()
    email = str(data.email).strip().lower()
    password = data.password
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Name is too short")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    if len(password.encode("utf-8")) > 1024:
        raise HTTPException(status_code=400, detail="Password is too long")
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE LOWER(email)=LOWER(%s) AND deleted_at IS NULL",
            (email,),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")
        password_hash = password_hasher.hash(password)
        user = conn.execute("""
            INSERT INTO users(name,email,password_hash,bio)
            VALUES(%s,%s,%s,'')
            RETURNING id,name,email,bio,avatar,created_at
        """, (name,email,password_hash)).fetchone()
        token = create_token(user["id"])
        expires_at = datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)
        conn.execute(
            "INSERT INTO sessions(user_id,token_hash,expires_at) VALUES(%s,%s,%s)",
            (user["id"],hash_token(token),expires_at),
        )
        conn.commit()
    return {"message":"Account created successfully","token":token,"access_token":token,"user":user_public(user)}

@app.post("/api/login")
def login(data: LoginRequest):
    email = str(data.email).strip().lower()
    password = data.password
    with get_conn() as conn:
        user = conn.execute("""
            SELECT id,name,email,password_hash,bio,avatar,created_at,deleted_at
            FROM users WHERE LOWER(email)=LOWER(%s)
        """, (email,)).fetchone()
        if not user or user["deleted_at"] is not None:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        stored_hash = user["password_hash"]
        password_ok = False
        if stored_hash and stored_hash.startswith("$argon2"):
            try:
                password_ok = password_hasher.verify(stored_hash, password)
            except (VerifyMismatchError, VerificationError):
                password_ok = False
        elif stored_hash and stored_hash.startswith("$2"):
            try:
                password_ok = pwd_context.verify(password, stored_hash)
            except Exception:
                password_ok = False

        if not password_ok:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_token(user["id"])
        expires_at = datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)
        conn.execute(
            "INSERT INTO sessions(user_id,token_hash,expires_at) VALUES(%s,%s,%s)",
            (user["id"],hash_token(token),expires_at),
        )
        conn.commit()
    return {"message":"Login successful","token":token,"access_token":token,"user":user_public(user)}

@app.post("/api/logout")
def logout(authorization: Optional[str] = Header(default=None)):
    token = get_bearer_token(authorization)
    if token:
        with get_conn() as conn:
            conn.execute("UPDATE sessions SET revoked=TRUE WHERE token_hash=%s",(hash_token(token),))
            conn.commit()
    return {"message":"Logged out"}

@app.get("/api/me")
def me(authorization: Optional[str] = Header(default=None)):
    return {"user": user_public(require_user(authorization))}

@app.patch("/api/profile")
def update_profile(data: ProfileRequest, authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    name = data.name.strip() if data.name is not None else user["name"]
    bio = data.bio.strip() if data.bio is not None else user["bio"] or ""
    if len(name) < 2:
        raise HTTPException(status_code=400, detail="Name is too short")
    with get_conn() as conn:
        row = conn.execute("""
            UPDATE users SET name=%s,bio=%s,updated_at=CURRENT_TIMESTAMP
            WHERE id=%s
            RETURNING id,name,email,bio,avatar,created_at
        """,(name,bio,user["id"])).fetchone()
        conn.commit()
    return {"user":user_public(row)}

@app.post("/api/profile/avatar")
async def upload_avatar(file: UploadFile = File(...), authorization: Optional[str] = Header(default=None)):
    user = require_user(authorization)
    if not (file.content_type or "").lower().startswith("image/"):
        raise HTTPException(status_code=400, detail="Avatar must be an image")
    url = await save_upload(file, AVATAR_DIR, 15*1024*1024)
    with get_conn() as conn:
        row = conn.execute("""
            UPDATE users SET avatar=%s,updated_at=CURRENT_TIMESTAMP WHERE id=%s
            RETURNING id,name,email,bio,avatar,created_at
        """,(url,user["id"])).fetchone()
        conn.commit()
    return {"message":"Avatar updated","user":user_public(row),"avatar":url}

@app.get("/api/users/{user_id}")
def get_user(user_id:int, authorization:Optional[str]=Header(default=None)):
    require_user(authorization)
    with get_conn() as conn:
        user=conn.execute("""
            SELECT id,name,email,bio,avatar,created_at FROM users
            WHERE id=%s AND deleted_at IS NULL
        """,(user_id,)).fetchone()
    if not user:
        raise HTTPException(status_code=404,detail="User not found")
    return {"user":user_public(user)}

@app.get("/api/profile/{user_id}")
def profile_alias(user_id:int,authorization:Optional[str]=Header(default=None)):
    return get_user(user_id,authorization)

@app.get("/api/search")
@app.get("/api/users")
def search_users(q:str=Query("",alias="search"),authorization:Optional[str]=Header(default=None)):
    require_user(authorization)
    q=q.strip()
    if not q: return {"users":[]}
    with get_conn() as conn:
        rows=conn.execute("""
            SELECT id,name,email,bio,avatar,created_at FROM users
            WHERE deleted_at IS NULL AND (name ILIKE %s OR email ILIKE %s)
            ORDER BY name LIMIT 50
        """,(f"%{q}%",f"%{q}%")).fetchall()
    return {"users":[user_public(r) for r in rows]}

@app.get("/api/users/search")
def search_users_alias(q:str=Query(""),authorization:Optional[str]=Header(default=None)):
    return search_users(q,authorization)

POST_SELECT = """
    SELECT p.id,p.user_id,p.caption,p.media_url,p.media_type,p.created_at,
           u.name,u.avatar,
           (SELECT COUNT(*) FROM likes l WHERE l.post_id=p.id) AS likes_count,
           (SELECT COUNT(*) FROM comments c WHERE c.post_id=p.id) AS comments_count,
           (SELECT COUNT(*) FROM reshares r WHERE r.post_id=p.id) AS reshares_count
    FROM posts p JOIN users u ON u.id=p.user_id
    WHERE p.deleted_at IS NULL AND u.deleted_at IS NULL
"""

@app.get("/api/posts")
def get_posts(authorization:Optional[str]=Header(default=None),limit:int=Query(50,ge=1,le=100),before_id:Optional[int]=Query(None)):
    require_user(authorization)
    with get_conn() as conn:
        if before_id is None:
            rows=conn.execute(POST_SELECT+" ORDER BY p.created_at DESC LIMIT %s",(limit,)).fetchall()
        else:
            rows=conn.execute(POST_SELECT+" AND p.id<%s ORDER BY p.created_at DESC LIMIT %s",(before_id,limit)).fetchall()
    return {"posts":rows}

@app.post("/api/posts")
async def create_post(caption:str=Form(""),file:Optional[UploadFile]=File(None),authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    caption=caption.strip()
    media_url=None
    media_type=None
    if file:
        ct=(file.content_type or "").lower()
        if not (ct.startswith("image/") or ct.startswith("video/") or ct.startswith("audio/")):
            raise HTTPException(status_code=400,detail="Unsupported media type")
        media_url=await save_upload(file,POST_DIR,200*1024*1024)
        media_type=ct
    if not caption and not media_url:
        raise HTTPException(status_code=400,detail="Post cannot be empty")
    with get_conn() as conn:
        row=conn.execute("""
            INSERT INTO posts(user_id,caption,media_url,media_type)
            VALUES(%s,%s,%s,%s)
            RETURNING id,user_id,caption,media_url,media_type,created_at
        """,(user["id"],caption,media_url,media_type)).fetchone()
        conn.commit()
    return {"message":"Post created","post":row}

@app.post("/api/posts/{post_id}/like")
def like_post(post_id:int,authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    with get_conn() as conn:
        post=conn.execute("SELECT id FROM posts WHERE id=%s AND deleted_at IS NULL",(post_id,)).fetchone()
        if not post: raise HTTPException(status_code=404,detail="Post not found")
        conn.execute("INSERT INTO likes(post_id,user_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",(post_id,user["id"]))
        conn.commit()
    return {"liked":True}

@app.delete("/api/posts/{post_id}/like")
def unlike_post(post_id:int,authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    with get_conn() as conn:
        conn.execute("DELETE FROM likes WHERE post_id=%s AND user_id=%s",(post_id,user["id"]))
        conn.commit()
    return {"liked":False}

@app.post("/api/posts/{post_id}/comment")
def comment_post(post_id:int,data:CommentRequest,authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization); text=data.text.strip()
    if not text: raise HTTPException(status_code=400,detail="Comment cannot be empty")
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM posts WHERE id=%s AND deleted_at IS NULL",(post_id,)).fetchone():
            raise HTTPException(status_code=404,detail="Post not found")
        row=conn.execute("""
            INSERT INTO comments(post_id,user_id,text) VALUES(%s,%s,%s)
            RETURNING id,post_id,user_id,text,created_at
        """,(post_id,user["id"],text)).fetchone()
        conn.commit()
    return {"comment":row}

@app.get("/api/posts/{post_id}/comments")
def get_comments(post_id:int,authorization:Optional[str]=Header(default=None)):
    require_user(authorization)
    with get_conn() as conn:
        rows=conn.execute("""
            SELECT c.id,c.post_id,c.user_id,c.text,c.created_at,u.name,u.avatar
            FROM comments c JOIN users u ON u.id=c.user_id
            WHERE c.post_id=%s ORDER BY c.created_at ASC
        """,(post_id,)).fetchall()
    return {"comments":rows}

@app.post("/api/posts/{post_id}/save")
def save_post(post_id:int,authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM posts WHERE id=%s AND deleted_at IS NULL",(post_id,)).fetchone():
            raise HTTPException(status_code=404,detail="Post not found")
        conn.execute("INSERT INTO saved_posts(post_id,user_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",(post_id,user["id"]))
        conn.commit()
    return {"saved":True}

@app.delete("/api/posts/{post_id}/save")
def unsave_post(post_id:int,authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    with get_conn() as conn:
        conn.execute("DELETE FROM saved_posts WHERE post_id=%s AND user_id=%s",(post_id,user["id"])); conn.commit()
    return {"saved":False}

@app.post("/api/posts/{post_id}/reshare")
def reshare_post(post_id:int,authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM posts WHERE id=%s AND deleted_at IS NULL",(post_id,)).fetchone():
            raise HTTPException(status_code=404,detail="Post not found")
        conn.execute("INSERT INTO reshares(post_id,user_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",(post_id,user["id"])); conn.commit()
    return {"reshared":True}

@app.post("/api/messages")
def send_message(data:MessageRequest,authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    if data.receiver_id==user["id"]: raise HTTPException(status_code=400,detail="Cannot message yourself")
    text=data.text.strip()
    if not text: raise HTTPException(status_code=400,detail="Message cannot be empty")
    with get_conn() as conn:
        receiver=conn.execute("SELECT id FROM users WHERE id=%s AND deleted_at IS NULL",(data.receiver_id,)).fetchone()
        if not receiver: raise HTTPException(status_code=404,detail="Receiver not found")
        row=conn.execute("""
            INSERT INTO messages(sender_id,receiver_id,text) VALUES(%s,%s,%s)
            RETURNING id,sender_id,receiver_id,text,media_url,media_type,voice_url,duration_seconds,created_at,seen
        """,(user["id"],data.receiver_id,text)).fetchone()
        conn.commit()
    return {"message":row}

@app.get("/api/messages/{other_user_id}")
def get_messages(other_user_id:int,authorization:Optional[str]=Header(default=None),limit:int=Query(100,ge=1,le=200),before_id:Optional[int]=Query(None)):
    user=require_user(authorization)
    with get_conn() as conn:
        base="""
            SELECT id,sender_id,receiver_id,text,media_url,media_type,voice_url,duration_seconds,created_at,seen
            FROM messages
            WHERE (
                (sender_id=%s AND receiver_id=%s AND deleted_for_sender=FALSE)
                OR
                (sender_id=%s AND receiver_id=%s AND deleted_for_receiver=FALSE)
            )
        """
        params=[user["id"],other_user_id,other_user_id,user["id"]]
        if before_id is not None:
            base+=" AND id<%s"; params.append(before_id)
        base+=" ORDER BY created_at DESC LIMIT %s"; params.append(limit)
        rows=conn.execute(base,tuple(params)).fetchall()
        conn.execute("""
            UPDATE messages SET seen=TRUE
            WHERE sender_id=%s AND receiver_id=%s
        """,(other_user_id,user["id"]))
        conn.commit()
    rows.reverse()
    return {"messages":rows}

@app.get("/api/messages")
def chat_list(authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    with get_conn() as conn:
        rows=conn.execute("""
            SELECT DISTINCT ON (x.other_id)
                x.other_id,u.name,u.email,u.avatar,x.last_message,x.last_message_at
            FROM (
                SELECT CASE WHEN sender_id=%s THEN receiver_id ELSE sender_id END other_id,
                       text last_message,created_at last_message_at
                FROM messages WHERE sender_id=%s OR receiver_id=%s
                ORDER BY created_at DESC
            ) x JOIN users u ON u.id=x.other_id
            WHERE u.deleted_at IS NULL
            ORDER BY x.other_id,x.last_message_at DESC
        """,(user["id"],user["id"],user["id"])).fetchall()
    return {"chats":rows}

@app.post("/api/messages/voice")
async def voice_message(receiver_id:int=Form(...),duration_seconds:int=Form(0),file:UploadFile=File(...),authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    if receiver_id==user["id"]: raise HTTPException(status_code=400,detail="Cannot send voice note to yourself")
    ct=(file.content_type or "").lower()
    if not ct.startswith("audio/"): raise HTTPException(status_code=400,detail="Voice note must be an audio file")
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM users WHERE id=%s AND deleted_at IS NULL",(receiver_id,)).fetchone():
            raise HTTPException(status_code=404,detail="Receiver not found")
    url=await save_upload(file,VOICE_DIR,25*1024*1024)
    with get_conn() as conn:
        row=conn.execute("""
            INSERT INTO messages(sender_id,receiver_id,text,media_url,voice_url,media_type,duration_seconds)
            VALUES(%s,%s,'',%s,%s,%s,%s)
            RETURNING id,sender_id,receiver_id,text,media_url,media_type,voice_url,duration_seconds,created_at,seen
        """,(user["id"],receiver_id,url,url,ct,duration_seconds)).fetchone()
        conn.commit()
    return {"message":row}

@app.post("/api/messages/file")
async def chat_file(receiver_id:int=Form(...),text:str=Form(""),file:UploadFile=File(...),authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    if receiver_id==user["id"]: raise HTTPException(status_code=400,detail="Cannot send file to yourself")
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM users WHERE id=%s AND deleted_at IS NULL",(receiver_id,)).fetchone():
            raise HTTPException(status_code=404,detail="Receiver not found")
    ct=file.content_type or mimetypes.guess_type(file.filename or "")[0] or "application/octet-stream"
    url=await save_upload(file,CHAT_FILE_DIR,100*1024*1024)
    with get_conn() as conn:
        row=conn.execute("""
            INSERT INTO messages(sender_id,receiver_id,text,media_url,media_type)
            VALUES(%s,%s,%s,%s,%s)
            RETURNING id,sender_id,receiver_id,text,media_url,media_type,duration_seconds,created_at,seen
        """,(user["id"],receiver_id,text.strip(),url,ct)).fetchone()
        conn.commit()
    return {"message":row}

@app.delete("/api/chats/{other_user_id}")
def clear_chat(other_user_id:int,authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    with get_conn() as conn:
        conn.execute("UPDATE messages SET deleted_for_sender=TRUE WHERE sender_id=%s AND receiver_id=%s",(user["id"],other_user_id))
        conn.execute("UPDATE messages SET deleted_for_receiver=TRUE WHERE sender_id=%s AND receiver_id=%s",(other_user_id,user["id"]))
        conn.commit()
    return {"message":"Chat cleared"}

def _update_chat_settings(other_user_id:int,data:ChatSettingsRequest,authorization:Optional[str]):
    user=require_user(authorization)
    with get_conn() as conn:
        old=conn.execute("SELECT * FROM chat_settings WHERE user_id=%s AND other_user_id=%s",(user["id"],other_user_id)).fetchone()
        if old:
            pinned=data.pinned if data.pinned is not None else old["pinned"]
            muted=data.muted if data.muted is not None else old["muted"]
            blocked=data.blocked if data.blocked is not None else old["blocked"]
            conn.execute("""
                UPDATE chat_settings SET pinned=%s,muted=%s,blocked=%s,updated_at=CURRENT_TIMESTAMP
                WHERE user_id=%s AND other_user_id=%s
            """,(pinned,muted,blocked,user["id"],other_user_id))
        else:
            conn.execute("""
                INSERT INTO chat_settings(user_id,other_user_id,pinned,muted,blocked)
                VALUES(%s,%s,%s,%s,%s)
            """,(user["id"],other_user_id,bool(data.pinned),bool(data.muted),bool(data.blocked)))
        row=conn.execute("""
            SELECT user_id,other_user_id,wallpaper_url,pinned,muted,blocked,updated_at
            FROM chat_settings WHERE user_id=%s AND other_user_id=%s
        """,(user["id"],other_user_id)).fetchone()
        conn.commit()
    return {"settings":row}

@app.post("/api/chats/{other_user_id}/settings")
def update_chat_settings(other_user_id:int,data:ChatSettingsRequest,authorization:Optional[str]=Header(default=None)):
    return _update_chat_settings(other_user_id,data,authorization)

@app.patch("/api/chats/{other_user_id}/settings")
def update_chat_settings_patch(other_user_id:int,data:ChatSettingsRequest,authorization:Optional[str]=Header(default=None)):
    return _update_chat_settings(other_user_id,data,authorization)

@app.post("/api/chats/{other_user_id}/wallpaper")
async def upload_wallpaper(other_user_id:int,file:UploadFile=File(...),authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    if not (file.content_type or "").lower().startswith("image/"):
        raise HTTPException(status_code=400,detail="Wallpaper must be an image")
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM users WHERE id=%s AND deleted_at IS NULL",(other_user_id,)).fetchone():
            raise HTTPException(status_code=404,detail="User not found")
    url=await save_upload(file,WALLPAPER_DIR,15*1024*1024)
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO chat_settings(user_id,other_user_id,wallpaper_url)
            VALUES(%s,%s,%s)
            ON CONFLICT(user_id,other_user_id) DO UPDATE SET
            wallpaper_url=EXCLUDED.wallpaper_url,updated_at=CURRENT_TIMESTAMP
        """,(user["id"],other_user_id,url)); conn.commit()
    return {"message":"Wallpaper updated","wallpaper_url":url}

@app.post("/api/users/{user_id}/block")
def block_user(user_id:int,authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    if user_id==user["id"]: raise HTTPException(status_code=400,detail="Cannot block yourself")
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM users WHERE id=%s AND deleted_at IS NULL",(user_id,)).fetchone():
            raise HTTPException(status_code=404,detail="User not found")
        conn.execute("INSERT INTO blocks(blocker_id,blocked_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",(user["id"],user_id)); conn.commit()
    return {"blocked":True}

@app.delete("/api/users/{user_id}/block")
def unblock_user(user_id:int,authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    with get_conn() as conn:
        conn.execute("DELETE FROM blocks WHERE blocker_id=%s AND blocked_id=%s",(user["id"],user_id)); conn.commit()
    return {"blocked":False}

@app.post("/api/users/{user_id}/report")
def report_user(user_id:int,data:ReportRequest,authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization); reason=data.reason.strip()
    if not reason: raise HTTPException(status_code=400,detail="Reason is required")
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM users WHERE id=%s AND deleted_at IS NULL",(user_id,)).fetchone():
            raise HTTPException(status_code=404,detail="User not found")
        conn.execute("INSERT INTO reports(reporter_id,reported_user_id,reason) VALUES(%s,%s,%s)",(user["id"],user_id,reason)); conn.commit()
    return {"message":"Report submitted"}

@app.post("/api/posts/{post_id}/report")
def report_post(post_id:int,data:ReportRequest,authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization); reason=data.reason.strip()
    if not reason: raise HTTPException(status_code=400,detail="Reason is required")
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM posts WHERE id=%s AND deleted_at IS NULL",(post_id,)).fetchone():
            raise HTTPException(status_code=404,detail="Post not found")
        conn.execute("INSERT INTO reports(reporter_id,post_id,reason) VALUES(%s,%s,%s)",(user["id"],post_id,reason)); conn.commit()
    return {"message":"Report submitted"}

@app.post("/api/reports")
def report_generic(data:ReportRequest,authorization:Optional[str]=Header(default=None)):
    # Generic compatibility endpoint. The frontend should prefer the
    # specific user/post report endpoints when an ID is available.
    require_user(authorization)
    reason=data.reason.strip()
    if not reason: raise HTTPException(status_code=400,detail="Reason is required")
    return {"message":"Report endpoint ready","reason":reason}

@app.post("/api/calls/token")
def call_token(data:CallTokenRequest,authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    if not (LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET):
        raise HTTPException(status_code=503,detail="LiveKit is not configured")
    if data.receiver_id==user["id"]:
        raise HTTPException(status_code=400,detail="Cannot call yourself")
    call_type=data.call_type.lower().strip()
    if call_type not in {"audio","video"}: call_type="video"
    with get_conn() as conn:
        if not conn.execute("SELECT id FROM users WHERE id=%s AND deleted_at IS NULL",(data.receiver_id,)).fetchone():
            raise HTTPException(status_code=404,detail="Receiver not found")
    try:
        from livekit import api
        room="msafiri-"+secrets.token_hex(12)
        token=(api.AccessToken(LIVEKIT_API_KEY,LIVEKIT_API_SECRET)
               .with_identity(str(user["id"]))
               .with_name(user["name"])
               .with_grants(api.VideoGrants(room_join=True,room=room))
               .to_jwt())
        with get_conn() as conn:
            call=conn.execute("""
                INSERT INTO calls(caller_id,receiver_id,room_name,call_type)
                VALUES(%s,%s,%s,%s)
                RETURNING id,room_name,call_type,status,created_at
            """,(user["id"],data.receiver_id,room,call_type)).fetchone()
            conn.commit()
        return {"token":token,"livekit_url":LIVEKIT_URL,"room_name":room,"call":call}
    except ImportError:
        raise HTTPException(status_code=500,detail="LiveKit package is not installed")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"LiveKit error: {e}")

def _end_call(call_id:int,authorization:Optional[str]):
    user=require_user(authorization)
    with get_conn() as conn:
        row=conn.execute("""
            UPDATE calls SET status='ended',ended_at=CURRENT_TIMESTAMP
            WHERE id=%s AND (caller_id=%s OR receiver_id=%s)
            RETURNING *
        """,(call_id,user["id"],user["id"])).fetchone()
        conn.commit()
    if not row: raise HTTPException(status_code=404,detail="Call not found")
    return {"call":row}

@app.post("/api/calls/{call_id}/end")
def end_call(call_id:int,authorization:Optional[str]=Header(default=None)):
    return _end_call(call_id,authorization)

@app.patch("/api/calls/{call_id}")
def end_call_patch(call_id:int,authorization:Optional[str]=Header(default=None)):
    return _end_call(call_id,authorization)

@app.delete("/api/account")
def delete_account(authorization:Optional[str]=Header(default=None)):
    user=require_user(authorization)
    with get_conn() as conn:
        conn.execute("UPDATE users SET deleted_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=%s",(user["id"],))
        conn.execute("UPDATE sessions SET revoked=TRUE WHERE user_id=%s",(user["id"],))
        conn.commit()
    return {"message":"Account deleted"}

@app.get("/api/debug/database")
def database_debug(authorization:Optional[str]=Header(default=None)):
    require_user(authorization)
    with get_conn() as conn:
        rows=conn.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema='public' ORDER BY table_name
        """).fetchall()
    return {"tables":[r["table_name"] for r in rows]}

@app.get("/uploads/{folder}/{filename}")
def uploaded_file(folder:str,filename:str):
    allowed={"avatars":AVATAR_DIR,"posts":POST_DIR,"voice":VOICE_DIR,
              "chat_files":CHAT_FILE_DIR,"wallpapers":WALLPAPER_DIR}
    directory=allowed.get(folder)
    if directory is None: raise HTTPException(status_code=404,detail="Folder not found")
    path=directory/Path(filename).name
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404,detail="File not found")
    return FileResponse(path,media_type=mimetypes.guess_type(str(path))[0] or "application/octet-stream")

@app.exception_handler(Exception)
async def global_error(request,exc):
    print("UNHANDLED ERROR:",type(exc).__name__,str(exc))
    return JSONResponse(status_code=500,content={
        "detail":"Internal Server Error","error":str(exc),"type":type(exc).__name__
    })

if __name__=="__main__":
    import uvicorn
    uvicorn.run("main:app",host="0.0.0.0",port=int(os.getenv("PORT","8000")),reload=False)
