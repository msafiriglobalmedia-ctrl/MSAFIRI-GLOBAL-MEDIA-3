from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User
from auth import get_current_user, require_user

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/{user_id}")
def get_profile(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user.to_dict()


@router.patch("")
def update_profile(
    full_name: str = None,
    bio: str = None,
    location: str = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
):
    if full_name is not None:
        user.full_name = full_name
    if bio is not None:
        user.bio = bio
    if location is not None:
        user.location = location
    db.commit()
    db.refresh(user)
    return user.to_dict()
