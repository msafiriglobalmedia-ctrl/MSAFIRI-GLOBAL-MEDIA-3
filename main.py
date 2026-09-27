# ============================================================
# MSAFIRI GLOBAL MEDIA
# main.py — PHASE 2 / SOCIAL CORE
# ============================================================

import os
import uuid
import shutil
from datetime import datetime
from typing import Optional

from fastapi import (
    FastAPI,
    HTTPException,
    Depends,
    Query,
    Request,
    UploadFile,
    File,
    Form,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.orm import Session

from database import get_db, Base, engine
from models import User, Post, Status, Follow
from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    require_user,
)

# Optional routers
try:
    from routers import auth as auth_router
except Exception:
    auth_router = None

try:
    from routers import posts as posts_router
except Exception:
    posts_router = None

try:
    from routers import statuses as statuses_router
except Exception:
    statuses_router = None

try:
    from routers import messages as messages_router
except Exception:
    messages_router = None

try:
    from routers import profile as profile_router
except Exception:
    profile_router = None

try:
    from routers import videos as videos_router
except Exception:
    videos_router = None

try:
    from routers import feed as feed_router
except Exception:
    feed_router = None

try:
    from routers import stories as stories_router
except Exception:
    stories_router = None

try:
    from routers import ping as ping_router
except Exception:
    ping_router = None


# ============================================================
# APP CONFIG
# ============================================================

APP_NAME = "MSAFIRI GLOBAL MEDIA"
APP_VERSION = "6.0.0-PHASE2"
APP_TAGLINE = "Connect beyond — Media V0.0.1"
FOUNDER = "MSAFIRI WILLIAM MUNGA"
COMPANY = "ZetroLink Technology Limited"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
MEDIA_DIR = os.path.join(STATIC_DIR, "uploads")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(MEDIA_DIR, exist_ok=True)


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=f"""
{APP_TAGLINE}

Founded by {FOUNDER}
{COMPANY}
""",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
async def startup():
    try:
        Base.metadata.create_all(bind=engine)

        create_social_tables()

        print("==============================================")
        print(f"{APP_NAME}")
        print(f"Version: {APP_VERSION}")
        print(f"Founder: {FOUNDER}")
        print(f"Company: {COMPANY}")
        print("Database initialized")
        print("Social tables initialized")
        print("==============================================")

    except Exception as e:
        print("STARTUP DATABASE ERROR:", e)


# ============================================================
# EXTRA SOCIAL TABLES
# ============================================================

def create_social_tables():
    """
    Creates tables required by:
    Likes
    Comments
    Saves
    Shares
    """

    statements = [

        """
        CREATE TABLE IF NOT EXISTS post_likes (
            id SERIAL PRIMARY KEY,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(post_id, user_id)
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS post_saves (
            id SERIAL PRIMARY KEY,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(post_id, user_id)
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS post_shares (
            id SERIAL PRIMARY KEY,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS post_comments (
            id SERIAL PRIMARY KEY,
            post_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            comment TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """,
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


# ============================================================
# HEALTH
# ============================================================

@app.get("/health", tags=["health"])
def health():
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "time": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/api/health", tags=["health"])
def api_health():
    return {
        "status": "ok",
        "service": "msafiri-api",
        "version": APP_VERSION,
        "uptime": "running",
    }


# ============================================================
# AUTH — FALLBACK AUTH API
# ============================================================

class RegisterIn(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str = ""


class LoginIn(BaseModel):
    username: str
    password: str


@app.post("/api/auth/register", tags=["auth"])
def register(
    data: RegisterIn,
    db: Session = Depends(get_db),
):
    existing_email = (
        db.query(User)
        .filter(User.email == data.email)
        .first()
    )

    if existing_email:
        raise HTTPException(
            status_code=400,
            detail="Email already registered",
        )

    existing_username = (
        db.query(User)
        .filter(User.username == data.username)
        .first()
    )

    if existing_username:
        raise HTTPException(
            status_code=400,
            detail="Username already taken",
        )

    user = User(
        username=data.username.strip(),
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name.strip(),
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({
        "sub": str(user.id)
    })

    return {
        "ok": True,
        "user": user.to_dict(),
        "access_token": token,
        "token_type": "bearer",
    }


@app.post("/api/auth/login", tags=["auth"])
def login(
    data: LoginIn,
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .filter(
            (User.username == data.username)
            | (User.email == data.username)
        )
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    if not verify_password(
        data.password,
        user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
        )

    token = create_access_token({
        "sub": str(user.id)
    })

    return {
        "ok": True,
        "user": user.to_dict(),
        "access_token": token,
        "token_type": "bearer",
    }


@app.post("/api/auth/logout", tags=["auth"])
def logout():
    return {
        "ok": True,
        "message": "Logged out"
    }


@app.get("/api/auth/me", tags=["auth"])
def me(
    user: User = Depends(require_user),
):
    return user.to_dict()


# ============================================================
# MEDIA UPLOAD
# ============================================================

ALLOWED_IMAGE = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/gif",
}

ALLOWED_VIDEO = {
    "video/mp4",
    "video/webm",
    "video/quicktime",
}


def save_upload(file: UploadFile) -> tuple[str, str]:

    if not file.content_type:
        raise HTTPException(
            status_code=400,
            detail="File type missing",
        )

    if (
        file.content_type not in ALLOWED_IMAGE
        and file.content_type not in ALLOWED_VIDEO
    ):
        raise HTTPException(
            status_code=400,
            detail="Only image and video files are supported",
        )

    extension = ""

    if "." in file.filename:
        extension = "." + file.filename.split(".")[-1].lower()

    filename = f"{uuid.uuid4().hex}{extension}"

    filepath = os.path.join(
        MEDIA_DIR,
        filename,
    )

    try:
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {e}",
        )

    media_type = (
        "video"
        if file.content_type in ALLOWED_VIDEO
        else "image"
    )

    return (
        f"/static/uploads/{filename}",
        media_type,
    )


@app.post("/api/upload", tags=["media"])
async def upload_media(
    file: UploadFile = File(...),
    user: User = Depends(require_user),
):
    url, media_type = save_upload(file)

    return {
        "ok": True,
        "url": url,
        "media_url": url,
        "media_type": media_type,
        "filename": file.filename,
    }


# ============================================================
# POSTS — CREATE
# ============================================================

@app.post("/api/posts", tags=["posts"])
async def create_post(
    caption: str = Form(""),
    file: Optional[UploadFile] = File(None),
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    media_url = ""
    media_type = "text"

    if file:
        media_url, media_type = save_upload(file)

    post = Post(
        user_id=user.id,
        caption=caption.strip(),
        media_url=media_url,
        media_type=media_type,
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    return {
        "ok": True,
        "message": "Post published successfully",
        "post": serialize_post(post, db),
    }


# ============================================================
# POSTS — CREATE JSON
# ============================================================

class TextPostIn(BaseModel):
    caption: str = ""
    media_url: str = ""
    media_type: str = "text"


@app.post("/api/posts/text", tags=["posts"])
def create_text_post(
    data: TextPostIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    post = Post(
        user_id=user.id,
        caption=data.caption.strip(),
        media_url=data.media_url,
        media_type=data.media_type,
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    return {
        "ok": True,
        "post": serialize_post(post, db),
    }


# ============================================================
# POST SERIALIZER
# ============================================================

def serialize_post(
    post: Post,
    db: Session,
):
    likes = db.execute(
        text("""
            SELECT COUNT(*)
            FROM post_likes
            WHERE post_id = :post_id
        """),
        {"post_id": post.id},
    ).scalar() or 0

    comments = db.execute(
        text("""
            SELECT COUNT(*)
            FROM post_comments
            WHERE post_id = :post_id
        """),
        {"post_id": post.id},
    ).scalar() or 0

    saves = db.execute(
        text("""
            SELECT COUNT(*)
            FROM post_saves
            WHERE post_id = :post_id
        """),
        {"post_id": post.id},
    ).scalar() or 0

    shares = db.execute(
        text("""
            SELECT COUNT(*)
            FROM post_shares
            WHERE post_id = :post_id
        """),
        {"post_id": post.id},
    ).scalar() or 0

    username = "User"
    full_name = ""

    try:
        owner = (
            db.query(User)
            .filter(User.id == post.user_id)
            .first()
        )

        if owner:
            username = owner.username
            full_name = owner.full_name or owner.username

    except Exception:
        pass

    return {
        "id": post.id,
        "user_id": post.user_id,
        "username": username,
        "full_name": full_name,
        "caption": post.caption or "",
        "media_url": post.media_url or "",
        "media_type": post.media_type or "text",
        "created_at": (
            post.created_at.isoformat()
            if post.created_at
            else None
        ),
        "likes": int(likes),
        "comments": int(comments),
        "saves": int(saves),
        "shares": int(shares),
    }


# ============================================================
# GET POSTS
# ============================================================

@app.get("/api/posts", tags=["posts"])
def get_posts(
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    posts = (
        db.query(Post)
        .order_by(Post.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "ok": True,
        "posts": [
            serialize_post(post, db)
            for post in posts
        ],
        "count": len(posts),
    }


# ============================================================
# FEED
# ============================================================

@app.get("/api/feed", tags=["feed"])
def get_feed(
    type: str = Query("for-you"),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    posts = (
        db.query(Post)
        .order_by(Post.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "ok": True,
        "type": type,
        "posts": [
            serialize_post(post, db)
            for post in posts
        ],
    }


# ============================================================
# LIKE
# ============================================================

@app.post("/api/posts/{post_id}/like", tags=["posts"])
def like_post(
    post_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    existing = db.execute(
        text("""
            SELECT id
            FROM post_likes
            WHERE post_id = :post_id
            AND user_id = :user_id
        """),
        {
            "post_id": post_id,
            "user_id": user.id,
        },
    ).first()

    if existing:
        db.execute(
            text("""
                DELETE FROM post_likes
                WHERE post_id = :post_id
                AND user_id = :user_id
            """),
            {
                "post_id": post_id,
                "user_id": user.id,
            },
        )

        liked = False

    else:
        db.execute(
            text("""
                INSERT INTO post_likes
                (post_id, user_id)
                VALUES (:post_id, :user_id)
            """),
            {
                "post_id": post_id,
                "user_id": user.id,
            },
        )

        liked = True

    db.commit()

    count = db.execute(
        text("""
            SELECT COUNT(*)
            FROM post_likes
            WHERE post_id = :post_id
        """),
        {"post_id": post_id},
    ).scalar() or 0

    return {
        "ok": True,
        "liked": liked,
        "likes": int(count),
    }


# ============================================================
# LIKE STATUS
# ============================================================

@app.get("/api/posts/{post_id}/like", tags=["posts"])
def get_like_status(
    post_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    row = db.execute(
        text("""
            SELECT id
            FROM post_likes
            WHERE post_id = :post_id
            AND user_id = :user_id
        """),
        {
            "post_id": post_id,
            "user_id": user.id,
        },
    ).first()

    count = db.execute(
        text("""
            SELECT COUNT(*)
            FROM post_likes
            WHERE post_id = :post_id
        """),
        {"post_id": post_id},
    ).scalar() or 0

    return {
        "liked": row is not None,
        "likes": int(count),
    }


# ============================================================
# SAVE / UNSAVE
# ============================================================

@app.post("/api/posts/{post_id}/save", tags=["posts"])
def save_post(
    post_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    existing = db.execute(
        text("""
            SELECT id
            FROM post_saves
            WHERE post_id = :post_id
            AND user_id = :user_id
        """),
        {
            "post_id": post_id,
            "user_id": user.id,
        },
    ).first()

    if existing:

        db.execute(
            text("""
                DELETE FROM post_saves
                WHERE post_id = :post_id
                AND user_id = :user_id
            """),
            {
                "post_id": post_id,
                "user_id": user.id,
            },
        )

        saved = False

    else:

        db.execute(
            text("""
                INSERT INTO post_saves
                (post_id, user_id)
                VALUES (:post_id, :user_id)
            """),
            {
                "post_id": post_id,
                "user_id": user.id,
            },
        )

        saved = True

    db.commit()

    return {
        "ok": True,
        "saved": saved,
    }


# ============================================================
# SHARE
# ============================================================

@app.post("/api/posts/{post_id}/share", tags=["posts"])
def share_post(
    post_id: int,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    db.execute(
        text("""
            INSERT INTO post_shares
            (post_id, user_id)
            VALUES (:post_id, :user_id)
        """),
        {
            "post_id": post_id,
            "user_id": user.id,
        },
    )

    db.commit()

    count = db.execute(
        text("""
            SELECT COUNT(*)
            FROM post_shares
            WHERE post_id = :post_id
        """),
        {"post_id": post_id},
    ).scalar() or 0

    return {
        "ok": True,
        "shared": True,
        "shares": int(count),
    }


# ============================================================
# COMMENTS
# ============================================================

class CommentIn(BaseModel):
    comment: str


@app.post("/api/posts/{post_id}/comments", tags=["comments"])
def add_comment(
    post_id: int,
    data: CommentIn,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    post = (
        db.query(Post)
        .filter(Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(
            status_code=404,
            detail="Post not found",
        )

    comment = data.comment.strip()

    if not comment:
        raise HTTPException(
            status_code=400,
            detail="Comment cannot be empty",
        )

    result = db.execute(
        text("""
            INSERT INTO post_comments
            (post_id, user_id, comment)
            VALUES (:post_id, :user_id, :comment)
            RETURNING id, created_at
        """),
        {
            "post_id": post_id,
            "user_id": user.id,
            "comment": comment,
        },
    )

    row = result.first()

    db.commit()

    return {
        "ok": True,
        "comment": {
            "id": row[0],
            "post_id": post_id,
            "user_id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "comment": comment,
            "created_at": (
                row[1].isoformat()
                if row[1]
                else None
            ),
        },
    }


@app.get("/api/posts/{post_id}/comments", tags=["comments"])
def get_comments(
    post_id: int,
    db: Session = Depends(get_db),
):
    rows = db.execute(
        text("""
            SELECT
                pc.id,
                pc.post_id,
                pc.user_id,
                pc.comment,
                pc.created_at,
                u.username,
                u.full_name
            FROM post_comments pc
            LEFT JOIN users u
                ON u.id = pc.user_id
            WHERE pc.post_id = :post_id
            ORDER BY pc.created_at ASC
        """),
        {"post_id": post_id},
    ).mappings().all()

    return {
        "ok": True,
        "comments": [
            {
                "id": row["id"],
                "post_id": row["post_id"],
                "user_id": row["user_id"],
                "username": row["username"],
                "full_name": row["full_name"],
                "comment": row["comment"],
                "created_at": (
                    row["created_at"].isoformat()
                    if row["created_at"]
                    else None
                ),
            }
            for row in rows
        ],
    }


# ============================================================
# STORIES
# ============================================================

@app.get("/api/stories", tags=["stories"])
def get_stories(
    db: Session = Depends(get_db),
):
    statuses = (
        db.query(Status)
        .order_by(Status.created_at.desc())
        .limit(50)
        .all()
    )

    return {
        "ok": True,
        "stories": [
            status.to_dict()
            for status in statuses
        ],
    }


# ============================================================
# DISCOVERY
# ============================================================

@app.get("/api/discovery", tags=["discovery"])
def discovery():
    return {
        "cards": [
            {
                "id": "ai-council",
                "icon": "📖",
                "title": "AI Council",
                "desc": "Education, Health, Agriculture, Research",
            },
            {
                "id": "creative-studio",
                "icon": "🖼️",
                "title": "Creative Studio",
                "desc": "Image, Video, Documents",
            },
            {
                "id": "market",
                "icon": "🛍️",
                "title": "Market",
                "desc": "Products, Services, Digital",
            },
            {
                "id": "world-map",
                "icon": "🌍",
                "title": "World Map",
                "desc": "Explore the world",
            },
            {
                "id": "channels",
                "icon": "📺",
                "title": "Channels",
                "desc": "BBC, CNN, Aljazeera and more",
            },
            {
                "id": "communities",
                "icon": "👥",
                "title": "Communities",
                "desc": "Join groups and communities",
            },
            {
                "id": "videos",
                "icon": "▶️",
                "title": "Videos",
                "desc": "Short videos feed",
            },
            {
                "id": "settings",
                "icon": "⚙️",
                "title": "Settings",
                "desc": "App preferences",
            },
        ]
    }


# ============================================================
# AI COUNCIL
# ============================================================

@app.get("/api/ai-council", tags=["discovery"])
def ai_council():
    return {
        "ais": [
            {
                "id": "education",
                "icon": "📖",
                "title": "Education AI",
                "desc": "Study notes, syllabus, past papers",
            },
            {
                "id": "health",
                "icon": "❤️",
                "title": "Health AI",
                "desc": "General health information",
            },
            {
                "id": "agriculture",
                "icon": "🌿",
                "title": "Agriculture AI",
                "desc": "Crops, soil, farming",
            },
            {
                "id": "research",
                "icon": "🔍",
                "title": "Research AI",
                "desc": "Methodology, citations",
            },
            {
                "id": "canvas",
                "icon": "📐",
                "title": "AI Canvas",
                "desc": "Workspace with documents",
            },
        ]
    }


@app.get("/api/ai-council/countries", tags=["discovery"])
def ai_council_countries():
    return {
        "countries": [
            "Tanzania",
            "Kenya",
            "Uganda",
            "Rwanda",
            "Burundi",
            "South Africa",
            "Nigeria",
            "Ghana",
            "UK",
            "USA",
            "Canada",
            "Australia",
            "India",
            "China",
            "Japan",
            "Germany",
            "France",
            "Brazil",
        ]
    }


@app.get("/api/ai-council/levels", tags=["discovery"])
def ai_council_levels():
    return {
        "levels": [
            "Nursery / Early Childhood",
            "Primary",
            "Secondary",
            "High School",
            "Certificate",
            "Diploma",
            "Degree",
            "Master",
            "PhD",
        ]
    }


@app.get("/api/ai-council/content-types", tags=["discovery"])
def ai_council_content_types():
    return {
        "content_types": [
            "Notes",
            "Books",
            "Past Papers",
            "Marking Schemes",
        ]
    }


@app.get("/api/ai-council/chat", tags=["discovery"])
def ai_council_chat(
    ai: str = Query("education"),
    country: str = Query("Tanzania"),
    level: str = Query("Degree"),
    content: str = Query("Notes"),
    q: str = Query(""),
):
    return {
        "ai": ai,
        "context": {
            "country": country,
            "level": level,
            "content": content,
        },
        "question": q,
        "reply": (
            f"Hello! I'm your {content} assistant for "
            f"{level} curriculum in {country}. "
            f"Ask me anything about a subject or topic."
        ),
        "phase": "placeholder",
    }


# ============================================================
# CREATIVE STUDIO
# ============================================================

@app.get("/api/studio", tags=["discovery"])
def studio_tools():
    return {
        "tools": [
            {
                "id": "image",
                "icon": "🖼️",
                "title": "Image Creator",
                "desc": "Posters, social graphics, covers, thumbnails",
            },
            {
                "id": "video",
                "icon": "🎬",
                "title": "Video Creator",
                "desc": "Short videos, editing, social content",
            },
            {
                "id": "document",
                "icon": "📄",
                "title": "Document Creator",
                "desc": "Documents and digital resources",
            },
            {
                "id": "assistant",
                "icon": "✨",
                "title": "Design Assistant",
                "desc": "AI-assisted creative ideas",
            },
        ]
    }


# ============================================================
# MARKET
# ============================================================

@app.get("/api/market/categories", tags=["discovery"])
def market_categories():
    return {
        "categories": [
            {
                "id": "products",
                "title": "Products",
                "desc": "Goods for sale",
            },
            {
                "id": "services",
                "title": "Services",
                "desc": "Professional services",
            },
            {
                "id": "digital",
                "title": "Digital",
                "desc": "Digital products",
            },
            {
                "id": "business",
                "title": "Business",
                "desc": "Business opportunities",
            },
        ]
    }


@app.get("/api/market/items", tags=["discovery"])
def market_items(
    category: str = Query("products")
):
    return {
        "category": category,
        "items": [],
        "phase": "placeholder",
    }


# ============================================================
# WORLD MAP
# ============================================================

@app.get("/api/world-map/countries", tags=["discovery"])
def world_map_countries():
    return {
        "countries": [
            {
                "name": "Tanzania",
                "users": 0,
                "posts": 0,
            },
            {
                "name": "Kenya",
                "users": 0,
                "posts": 0,
            },
            {
                "name": "Uganda",
                "users": 0,
                "posts": 0,
            },
        ]
    }


# ============================================================
# CHANNELS
# ============================================================

@app.get("/api/channels", tags=["discovery"])
def channels():
    return {
        "channels": [
            {
                "id": "bbc",
                "name": "BBC News",
                "color": "red",
                "desc": "Global news from UK",
            },
            {
                "id": "cnn",
                "name": "CNN",
                "color": "red",
                "desc": "Cable News Network",
            },
            {
                "id": "aljazeera",
                "name": "Al Jazeera",
                "color": "orange",
                "desc": "Qatar-based news",
            },
            {
                "id": "itv",
                "name": "ITV News",
                "color": "blue",
                "desc": "UK broadcaster",
            },
            {
                "id": "msafiri",
                "name": "Msafiri Global Media",
                "color": "blue",
                "desc": "Our own channel",
            },
        ]
    }


# ============================================================
# COMMUNITIES
# ============================================================

@app.get("/api/communities/categories", tags=["discovery"])
def communities():
    return {
        "categories": [
            {
                "id": "education",
                "title": "Education",
                "desc": "Study groups",
            },
            {
                "id": "technology",
                "title": "Technology",
                "desc": "Tech discussions",
            },
            {
                "id": "business",
                "title": "Business",
                "desc": "Entrepreneurship",
            },
            {
                "id": "health",
                "title": "Health",
                "desc": "Health tips",
            },
            {
                "id": "agriculture",
                "title": "Agriculture",
                "desc": "Farmers",
            },
            {
                "id": "entertainment",
                "title": "Entertainment",
                "desc": "Music, movies",
            },
            {
                "id": "sports",
                "title": "Sports",
                "desc": "Football, athletics",
            },
            {
                "id": "religion",
                "title": "Religion",
                "desc": "Faith-based",
            },
            {
                "id": "language",
                "title": "Language",
                "desc": "English, Swahili learning",
            },
        ]
    }


# ============================================================
# USER MANUAL
# ============================================================

@app.get("/api/user-manual", tags=["settings"])
def user_manual():
    return {
        "app": APP_NAME,
        "tagline": APP_TAGLINE,
        "version": APP_VERSION,
        "founder": FOUNDER,
        "company": COMPANY,

        "about": (
            f"{APP_NAME} is a social, communication, "
            f"and AI application. Founded by {FOUNDER} "
            f"under {COMPANY}."
        ),

        "sections": {
            "home": "Feed, Stories, Posts",
            "discovery": (
                "AI Council, Studio, Market, World Map, "
                "Channels, Communities"
            ),
            "chats": "Messaging",
            "profile": "Your profile",
        },

        "how_to_use": {
            "create_account":
                "Register, fill details and create account",

            "post_content":
                "Create (+), caption, Photo/Video/File, Post",

            "share_story":
                "My Story, select media, publish",

            "chat":
                "Open Chats and select a user",

            "explore_ai":
                "Discovery, AI Council, choose AI",
        },

        "support": COMPANY,
    }


# ============================================================
# SETTINGS
# ============================================================

@app.get("/api/settings", tags=["settings"])
def settings():
    return {
        "theme": "light",
        "language": "en",
        "version": APP_VERSION,
        "logout_url": "/api/auth/logout",
    }


# ============================================================
# STATIC FILES
# ============================================================

if os.path.isdir(STATIC_DIR):

    app.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR),
        name="static",
    )


# ============================================================
# FRONTEND ROOT
# ============================================================

@app.get("/", include_in_schema=False)
async def root():

    index_path = os.path.join(
        STATIC_DIR,
        "index.html",
    )

    if os.path.isfile(index_path):
        return FileResponse(index_path)

    return JSONResponse({
        "app": APP_NAME,
        "version": APP_VERSION,
        "message": "Frontend not found",
        "docs": "/docs",
    })


# ============================================================
# SPA FALLBACK
# ============================================================

@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(
    full_path: str,
    request: Request,
):

    if full_path.startswith("api/"):
        raise HTTPException(
            status_code=404,
            detail=f"API route '{full_path}' not found",
        )

    index_path = os.path.join(
        STATIC_DIR,
        "index.html",
    )

    if os.path.isfile(index_path):
        return FileResponse(index_path)

    raise HTTPException(
        status_code=404,
        detail="Not found",
    )


# ============================================================
# 404 HANDLER
# ============================================================

@app.exception_handler(404)
async def not_found_handler(
    request: Request,
    exc,
):

    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={
                "detail": (
                    exc.detail
                    if hasattr(exc, "detail")
                    else "Not found"
                )
            },
        )

    index_path = os.path.join(
        STATIC_DIR,
        "index.html",
    )

    if os.path.isfile(index_path):
        return FileResponse(index_path)

    return JSONResponse(
        status_code=404,
        content={"detail": "Not found"},
    )


# ============================================================
# ADMIN — DATABASE RESET
# ============================================================

@app.get(
    "/admin/reset-db-temp-secret",
    tags=["admin"],
)
def reset_db():

    with engine.begin() as conn:

        conn.execute(
            text(
                "DROP TABLE IF EXISTS "
                "post_comments CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS "
                "post_shares CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS "
                "post_saves CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS "
                "post_likes CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS "
                "statuses CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS "
                "posts CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS "
                "follows CASCADE"
            )
        )

        conn.execute(
            text(
                "DROP TABLE IF EXISTS "
                "users CASCADE"
            )
        )

    Base.metadata.create_all(bind=engine)
    create_social_tables()

    return {
        "ok": True,
        "message": "Database reset completed",
    }


# ============================================================
# ADMIN — FIX USERS TABLE
# ============================================================

@app.get(
    "/admin/fix-users-table",
    tags=["admin"],
)
def fix_users_table():

    with engine.begin() as conn:

        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS
            hashed_password VARCHAR(255)
        """))

        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS
            full_name VARCHAR(100) DEFAULT ''
        """))

        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS
            bio TEXT DEFAULT ''
        """))

        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS
            location VARCHAR(100) DEFAULT ''
        """))

        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS
            avatar_url VARCHAR(500) DEFAULT ''
        """))

        conn.execute(text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS
            created_at TIMESTAMP DEFAULT NOW()
        """))

        result = conn.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'users'
            ORDER BY ordinal_position
        """))

        columns = [
            row[0]
            for row in result
        ]

    return {
        "ok": True,
        "message": "Users table checked",
        "columns": columns,
    }


# ============================================================
# OPTIONAL ROUTERS
# ============================================================

# IMPORTANT:
# Do NOT mount routers that already define the same routes
# as the fallback APIs above.
#
# We intentionally do not include auth/posts/feed routers here
# to avoid duplicate endpoint conflicts.
#
# If you have separate routers for messages/profile/videos,
# they can be mounted below if they do not conflict.

if messages_router is not None:
    try:
        app.include_router(messages_router.router)
        print("messages router mounted")
    except Exception as e:
        print("messages router skipped:", e)

if profile_router is not None:
    try:
        app.include_router(profile_router.router)
        print("profile router mounted")
    except Exception as e:
        print("profile router skipped:", e)

if videos_router is not None:
    try:
        app.include_router(videos_router.router)
        print("videos router mounted")
    except Exception as e:
        print("videos router skipped:", e)

if ping_router is not None:
    try:
        app.include_router(ping_router.router)
        print("ping router mounted")
    except Exception as e:
        print("ping router skipped:", e)


# ============================================================
# UVICORN
# ============================================================

if __name__ == "__main__":

    import uvicorn

    port = int(
        os.environ.get(
            "PORT",
            "10000",
        )
    )

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
