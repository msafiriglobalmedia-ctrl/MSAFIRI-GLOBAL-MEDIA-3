# ============================================================
# MSAFIRI GLOBAL MEDIA — Routers Package
# Version: Media V0.0.1
# Purpose: Import and expose all route blueprints
# ============================================================

# ------------------------------------------------------------
# 1. IMPORT ALL ROUTERS (Blueprints)
# ------------------------------------------------------------
from routers.auth import auth_bp
from routers.feed import feed_bp
from routers.posts import posts_bp
from routers.stories import stories_bp
from routers.profile import profile_bp
from routers.messages import messages_bp
from routers.statuses import statuses_bp
from routers.videos import videos_bp
from routers.ping import ping_bp


# ------------------------------------------------------------
# 2. EXPORTS
# ------------------------------------------------------------
__all__ = [
    "auth_bp",
    "feed_bp",
    "posts_bp",
    "stories_bp",
    "profile_bp",
    "messages_bp",
    "statuses_bp",
    "videos_bp",
    "ping_bp"
]
