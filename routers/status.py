from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from models import Status, User
from auth import get_current_user, require_user

router = APIRouter(prefix="/api/statuses", tags=["statuses"])


@router.get("")
def list_statuses(db: Session = Depends(get_db)):
    statuses = db.query(Status).order_by(Status.created_at.desc()).limit(50).all()
    return {"statuses": [s.to_dict() for s in statuses]}


@router.post("")
def create_status(
    caption: str = Form(""),
    media_url: str = Form(""),
    media_type: str = Form("image"),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    status = Status(
        user_id=user.id,
        caption=caption,
        media_url=media_url,
        media_type=media_type,
    )
    db.add(status)
    db.commit()
    db.refresh(status)
    return status.to_dict()


@router.delete("/{status_id}")
def delete_status(
    status_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    status = db.query(Status).filter(Status.id == status_id).first()
    if status and status.user_id == user.id:
        db.delete(status)
        db.commit()
    return {"ok": True}
