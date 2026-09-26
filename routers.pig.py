from fastapi import APIRouter
from datetime import datetime

router = APIRouter(prefix="/api/auth", tags=["ping"])


@router.get("/ping")
def ping():
    return {
        "status": "ok",
        "service": "msafiri-auth",
        "app": "MSAFIRI GLOBAL MEDIA",
        "version": "6.0.0-PHASE2",
        "time": datetime.utcnow().isoformat() + "Z",
    }
