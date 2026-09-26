import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from database import get_db, Base, engine
from models import User

from routers import auth, posts, statuses, messages, profile, videos
from routers import feed, stories, ping


APP_VERSION = "6.0.0-PHASE2"
APP_NAME = "MSAFIRI GLOBAL MEDIA"
APP_TAGLINE = "Connect beyond — Media V0.0.1"
FOUNDER = "MSAFIRI WILLIAM MUNGA"
COMPANY = "ZetroLink Technology Limited"

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description=f"{APP_TAGLINE}\n\nFounded by {FOUNDER}\n{COMPANY}",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    try:
        Base.metadata.create_all(bind=engine)
        print(f"{APP_NAME} v{APP_VERSION} started")
        print(f"Founder: {FOUNDER}")
        print(f"Company: {COMPANY}")
    except Exception as e:
        print(f"Database error: {e}")


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


app.include_router(auth.router)
print("auth router mounted")

app.include_router(posts.router)
print("posts router mounted")

app.include_router(statuses.router)
print("statuses router mounted")

app.include_router(messages.router)
print("messages router mounted")

app.include_router(profile.router)
print("profile router mounted")

app.include_router(videos.router)
print("videos router mounted")

app.include_router(feed.router)
print("feed router mounted")

app.include_router(stories.router)
print("stories router mounted")

app.include_router(ping.router)
print("ping router mounted")


@app.get("/api/discovery", tags=["discovery"])
def get_discovery():
    return {
        "cards": [
            {"id": "ai-council",      "icon": "📖", "title": "AI Council",      "desc": "Education, Health, Agriculture, Research"},
            {"id": "creative-studio", "icon": "🖼️", "title": "Creative Studio", "desc": "Image, Video, Documents"},
            {"id": "market",          "icon": "🛍️", "title": "Market",           "desc": "Products, Services, Digital"},
            {"id": "world-map",       "icon": "🌍", "title": "World Map",        "desc": "Explore the world"},
            {"id": "channels",        "icon": "📺", "title": "Channels",         "desc": "BBC, CNN, Aljazeera and more"},
            {"id": "communities",     "icon": "👥", "title": "Communities",      "desc": "Join groups and communities"},
            {"id": "videos",          "icon": "▶️", "title": "Videos",           "desc": "Short videos feed"},
            {"id": "settings",        "icon": "⚙️", "title": "Settings",         "desc": "App preferences"},
        ]
    }


@app.get("/api/ai-council", tags=["discovery"])
def ai_council_list():
    return {
        "ais": [
            {"id": "education",   "icon": "📖", "title": "Education AI",   "desc": "Study notes, syllabus, past papers"},
            {"id": "health",      "icon": "❤️", "title": "Health AI",      "desc": "General health information"},
            {"id": "agriculture", "icon": "🌿", "title": "Agriculture AI", "desc": "Crops, soil, farming"},
            {"id": "research",    "icon": "🔍", "title": "Research AI",    "desc": "Methodology, citations"},
            {"id": "canvas",      "icon": "📐", "title": "AI Canvas",      "desc": "Workspace with documents"},
        ]
    }


@app.get("/api/ai-council/countries", tags=["discovery"])
def ai_council_countries():
    return {
        "countries": [
            "Tanzania", "Kenya", "Uganda", "Rwanda", "Burundi",
            "South Africa", "Nigeria", "Ghana",
            "UK", "USA", "Canada", "Australia",
            "India", "China", "Japan",
            "Germany", "France", "Brazil",
        ]
    }


@app.get("/api/ai-council/levels", tags=["discovery"])
def ai_council_levels():
    return {
        "levels": [
            "Nursery / Early Childhood", "Primary", "Secondary", "High School",
            "Certificate", "Diploma", "Degree", "Master", "PhD",
        ]
    }


@app.get("/api/ai-council/content-types", tags=["discovery"])
def ai_council_content_types():
    return {
        "content_types": ["Notes", "Books", "Past Papers", "Marking Schemes"]
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
        "context": {"country": country, "level": level, "content": content},
        "question": q,
        "reply": (
            f"Hello! I'm your {content} assistant for {level} curriculum in "
            f"{country}. Ask me anything about a subject or topic."
        ),
        "phase": "placeholder",
    }


@app.get("/api/studio", tags=["discovery"])
def studio_tools():
    return {
        "tools": [
            {"id": "image",     "icon": "🖼️", "title": "Image Creator",    "desc": "Posters, social graphics, covers, thumbnails"},
            {"id": "video",     "icon": "🎬", "title": "Video Creator",    "desc": "Short videos, editing, social content"},
            {"id": "document",  "icon": "📄", "title": "Document Creator", "desc": "Documents, digital resources, educational material"},
            {"id": "assistant", "icon": "✨", "title": "Design Assistant", "desc": "AI-assisted creative ideas"},
        ]
    }


@app.get("/api/market/categories", tags=["discovery"])
def market_categories():
    return {
        "categories": [
            {"id": "products", "title": "Products", "desc": "Goods for sale"},
            {"id": "services", "title": "Services", "desc": "Professional services"},
            {"id": "digital",  "title": "Digital",  "desc": "Digital products"},
            {"id": "business", "title": "Business", "desc": "Business opportunities"},
        ]
    }


@app.get("/api/market/items", tags=["discovery"])
def market_items(category: str = Query("products")):
    return {"category": category, "items": [], "phase": "placeholder"}


@app.get("/api/world-map/countries", tags=["discovery"])
def world_map_countries():
    return {
        "countries": [
            {"name": "Tanzania", "users": 0, "posts": 0},
            {"name": "Kenya",    "users": 0, "posts": 0},
            {"name": "Uganda",   "users": 0, "posts": 0},
        ],
        "phase": "placeholder",
    }


@app.get("/api/channels", tags=["discovery"])
def channels_list():
    return {
        "channels": [
            {"id": "bbc",       "name": "BBC News",             "color": "red",    "desc": "Global news from UK"},
            {"id": "cnn",       "name": "CNN",                  "color": "red",    "desc": "Cable News Network"},
            {"id": "aljazeera", "name": "Al Jazeera",           "color": "orange", "desc": "Qatar-based news"},
            {"id": "itv",       "name": "ITV News",             "color": "blue",   "desc": "UK broadcaster"},
            {"id": "msafiri",   "name": "Msafiri Global Media", "color": "blue",   "desc": "Our own channel"},
        ]
    }


@app.get("/api/communities/categories", tags=["discovery"])
def communities_categories():
    return {
        "categories": [
            {"id": "education",     "title": "Education",     "desc": "Study groups"},
            {"id": "technology",    "title": "Technology",    "desc": "Tech discussions"},
            {"id": "business",      "title": "Business",      "desc": "Entrepreneurship"},
            {"id": "health",        "title": "Health",        "desc": "Health tips"},
            {"id": "agriculture",   "title": "Agriculture",   "desc": "Farmers"},
            {"id": "entertainment", "title": "Entertainment", "desc": "Music, movies"},
            {"id": "sports",        "title": "Sports",        "desc": "Football, athletics"},
            {"id": "religion",      "title": "Religion",      "desc": "Faith-based"},
            {"id": "language",      "title": "Language",      "desc": "English, Swahili learning"},
        ]
    }

.get("/api/user-manual", tags=["settings"])
def user_manual():
    return {
        "app": APP_NAME,
        "tagline": APP_TAGLINE,
        "version": APP_VERSION,
        "founder": FOUNDER,
        "company": COMPANY,
        "about": (
            f"{APP_NAME} is a social, communication, and AI app. "
            f"Founded by {FOUNDER} under {COMPANY}. Version: {APP_VERSION}"
        ),
        "sections": {
            "home":      "Feed, Stories, Posts",
            "discovery": "AI Council, Studio, Market, World Map, Channels, Communities",
            "chats":     "Messaging (WhatsApp-style)",
            "profile":   "Your profile",
        },
        "how_to_use": {
            "create_account": "Register, fill details, Create Account",
            "post_content":   "Create (+), caption, Photo/Video/File, Post",
            "share_story":    "\"+ My Story\", media, Post Story",
            "chat":           "Profile, Message icon, type or record",
            "explore_ai":     "Discovery, AI Council, choose AI",
        },
        "support": f"Contact {COMPANY}",
    }


@app.get("/api/settings", tags=["settings"])
def settings():
    return {
        "theme": "light",
        "language": "en",
        "version": APP_VERSION,
        "logout_url": "/api/auth/logout",
    }


if os.path.isdir("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")
    print("static mounted")


@app.get("/", include_in_schema=False)
async def root():
    index_path = "static/index.html"
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return JSONResponse({
        "app": APP_NAME,
        "version": APP_VERSION,
        "message": "Frontend not found",
        "docs": "/docs",
    })


@app.get("/{full_path:path}", include_in_schema=False)
async def spa_fallback(full_path: str, request: Request):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail=f"API route '{full_path}' not found")

    index_path = "static/index.html"
    if os.path.isfile(index_path):
        return FileResponse(index_path)

    raise HTTPException(status_code=404, detail="Not found")


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=404,
            content={"detail": exc.detail if hasattr(exc, "detail") else "Not found"},
        )
    if os.path.isfile("static/index.html"):
        return FileResponse("static/index.html")
    return JSONResponse(status_code=404, content={"detail": "Not found"})

@app.get("/admin/reset-db-temp-secret")
def reset_db():
    from database import engine, Base
    from models import User, Post, Follow, Status
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    return {"ok": True, "message": "Database reset done"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
