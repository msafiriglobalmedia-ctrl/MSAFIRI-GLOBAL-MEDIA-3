import os
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from models import Status, User
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["stories"])


@router.get("/stories")
def list_stories(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    cutoff = datetime.utcnow() - timedelta(hours=24)
    stories = (
        db.query(Status)
        .filter(Status.created_at >= cutoff)
        .order_by(Status.created_at.desc())
        .all()
    )

    return {
        "stories": [
            s.to_dict() if hasattr(s, "to_dict") else s.__dict__ for s in stories
        ],
        "total": len(stories),
    }


@router.post("/stories")
async def create_story(
    media: UploadFile = File(...),
    caption: str = Form(""),
    media_type: str = Form("image"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    ext = os.path.splitext(media.filename or "")[1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    upload_dir = "uploads/stories"
    os.makedirs(upload_dir, exist_ok=True)
    filepath = os.path.join(upload_dir, filename)

    contents = await media.read()
    with open(filepath, "wb") as f:
        f.write(contents)

    story = Status(
        user_id=current_user.id,
        media_url=f"/{filepath}",
        caption=caption,
        media_type=media_type,
        created_at=datetime.utcnow(),
    )
    db.add(story)
    db.commit()
    db.refresh(story)

    return {"story": story.to_dict() if hasattr(story, "to_dict") else story.__dict__}


@router.delete("/stories/{status_id}")
def delete_story(
    status_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    story = db.query(Status).filter(Status.id == status_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    if story.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    db.delete(story)
    db.commit()
    return {"ok": True, "message": "Story deleted"}
