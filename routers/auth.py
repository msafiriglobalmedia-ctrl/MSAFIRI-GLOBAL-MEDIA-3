from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from database import get_db
from models import User
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str = ""


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="Username taken")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"user": user.to_dict(), "access_token": token, "token_type": "bearer"}


@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(
        (User.username == data.username) | (User.email == data.username)
    ).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": str(user.id)})
    return {"user": user.to_dict(), "access_token": token, "token_type": "bearer"}


@router.post("/logout")
def logout():
    return {"ok": True}


@router.get("/me")
def me(user: User = Depends(require_user)):
    return user.to_dict()


@router.get("/ping")
def ping():
    from datetime import datetime
    return {
        "status": "ok",
        "service": "msafiri-auth",
        "time": datetime.utcnow().isoformat() + "Z",
    }
