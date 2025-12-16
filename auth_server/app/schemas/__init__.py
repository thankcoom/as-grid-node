from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- Token ---
class Token(BaseModel):
    access_token: str
    token_type: str
    status: Optional[str] = None  # For pending_api redirect

class TokenData(BaseModel):
    user_id: Optional[str] = None

# --- User Registration ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str

# --- User (for responses) ---
class UserBase(BaseModel):
    email: EmailStr
    username: Optional[str] = None

class User(UserBase):
    id: str
    is_active: bool
    is_admin: bool = False
    status: str
    exchange_uid: Optional[str] = None
    zeabur_url: Optional[str] = None
    group_id: Optional[str] = None
    api_verified_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    zeabur_url: Optional[str] = None
    username: Optional[str] = None

# --- Admin: User Management ---
class AdminUser(BaseModel):
    """Full user info for admin"""
    id: str
    email: EmailStr
    username: Optional[str] = None
    is_active: bool
    is_admin: bool
    status: str
    exchange_uid: Optional[str] = None
    zeabur_url: Optional[str] = None
    group_id: Optional[str] = None
    group_name: Optional[str] = None
    api_verified_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AdminUserUpdate(BaseModel):
    """Schema for admin updating user"""
    email: Optional[EmailStr] = None
    exchange_uid: Optional[str] = None
    status: Optional[str] = None
    group_id: Optional[str] = None

class PendingUser(BaseModel):
    id: str
    email: EmailStr
    exchange_uid: Optional[str] = None
    api_verified_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

# --- Groups ---
class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None

class GroupCreate(GroupBase):
    pass

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Group(GroupBase):
    id: str
    created_at: datetime
    user_count: Optional[int] = 0

    class Config:
        from_attributes = True

# --- API Verification ---
class APICredentials(BaseModel):
    api_key: str
    api_secret: str
    passphrase: str

class VerifyAPIResponse(BaseModel):
    uid: str
    status: str
    message: Optional[str] = None

# --- Legacy ---
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    invite_code: str

class APICredentialBase(BaseModel):
    api_key: str
    api_secret: str
    passphrase: Optional[str] = None

class APICredentialCreate(APICredentialBase):
    pass

class APICredentialUpdate(BaseModel):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None

class GridConfig(BaseModel):
    symbol: str
    quantity: float
    leverage: int = 20
