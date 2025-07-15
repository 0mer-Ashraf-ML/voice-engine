from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
import uuid

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    organization_name: str
    role: Optional[str] = "admin"

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    is_admin: bool
    organization_id: uuid.UUID
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse

class ApiKeyCreate(BaseModel):
    name: str

class ApiKeyResponse(BaseModel):
    id: uuid.UUID
    name: str
    key_prefix: str
    key: Optional[str] = None  # Only returned on creation
    is_active: bool
    last_used: Optional[datetime] = None
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True