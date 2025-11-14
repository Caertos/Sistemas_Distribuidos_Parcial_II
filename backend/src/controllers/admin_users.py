from typing import List, Optional
from uuid import uuid4
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from src.models.user import User
from src.auth.utils import hash_password


def create_user(db: Session, *, username: str, email: str, full_name: str, password: str, user_type: str = "patient", is_superuser: bool = False) -> User:
    # check uniqueness
    existing = db.query(User).filter((User.username == username) | (User.email == email)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User with same username or email already exists")

    u = User()
    u.id = str(uuid4())
    u.username = username
    u.email = email
    u.full_name = full_name
    u.hashed_password = hash_password(password)
    u.user_type = user_type
    u.is_superuser = bool(is_superuser)

    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def get_user(db: Session, user_id: str) -> Optional[User]:
    return db.query(User).filter(User.id == str(user_id)).first()


def list_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def update_user(db: Session, user: User, data: dict) -> User:
    # data may include password -> hash it
    if "password" in data and data.get("password"):
        user.hashed_password = hash_password(data.pop("password"))

    for k, v in data.items():
        if hasattr(user, k) and v is not None:
            setattr(user, k, v)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user: User) -> None:
    db.delete(user)
    db.commit()


def assign_role(db: Session, user: User, role: str, is_superuser: bool = False) -> User:
    # map role into user_type and is_superuser
    user.user_type = role
    user.is_superuser = bool(is_superuser)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
