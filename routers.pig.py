"""
routers/ping.py
MSAFIRI GLOBAL MEDIA — Ping / Health Router
Inatoa /api/auth/ping kwa frontend
"""

from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/auth", tags=["ping"])


@router.get("/ping")
def ping():
    """Frontend inaita hii kuhakikisha backend inafanya kazi."""
    return {
        "status": "ok",
        "service": "msafiri-auth",
        "app": "MSAFIRI GLOBAL MEDIA",
        "version": "6.0.0-PHASE2",
        "time": datetime.utcnow().isoformat() + "Z",
    }
