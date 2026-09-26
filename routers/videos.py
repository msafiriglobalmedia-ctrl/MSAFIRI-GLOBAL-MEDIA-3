from fastapi import APIRouter

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("")
def list_videos():
    return {"videos": []}
