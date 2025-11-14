from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: str
    password: str = Field(..., min_length=6)
    user_type: Optional[str] = "patient"
    is_superuser: Optional[bool] = False


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=6)
    user_type: Optional[str] = None
    is_superuser: Optional[bool] = None


class UserOut(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    full_name: str
    user_type: str
    is_superuser: bool

    class Config:
        orm_mode = True


class RoleAssign(BaseModel):
    role: str
    is_superuser: Optional[bool] = False


class ActionRequest(BaseModel):
    target: str
    options: Optional[dict] = {}


class BackupRequest(BaseModel):
    name: Optional[str] = None
    include_data: Optional[bool] = True


class RestoreRequest(BaseModel):
    backup_name: str
    force: Optional[bool] = False


class LogQuery(BaseModel):
    service: Optional[str] = None
    tail: Optional[int] = 200


class MetricQuery(BaseModel):
    since_minutes: Optional[int] = 60
    metrics: Optional[List[str]] = None
