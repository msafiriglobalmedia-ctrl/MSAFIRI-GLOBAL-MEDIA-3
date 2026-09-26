from fastapi import APIRouter

router = APIRouter(prefix="/api/messages", tags=["messages"])


@router.get("")
def chat_list():
    return {"chats": []}
