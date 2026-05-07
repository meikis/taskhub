from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List
from app.database import get_session
from app.models import UserCreate, UserRead, User
from app.crud import create_user, list_users, get_user_by_username
from app.api.auth import get_current_admin

router = APIRouter(prefix="/users", tags=["users"])

@router.post("", response_model=UserRead)
def register(user: UserCreate, db: Session = Depends(get_session)):
    if get_user_by_username(db, user.username):
        raise HTTPException(status_code=400, detail="Username already registered")
    return create_user(db, user)

@router.get("", response_model=List[UserRead])
def get_users(db: Session = Depends(get_session), _=Depends(get_current_admin)):
    return list_users(db)

@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Session = Depends(get_session)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user