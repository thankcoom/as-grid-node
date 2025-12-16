from datetime import datetime, timedelta
from typing import Optional, Union, Tuple
from jose import jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# --- Data Encryption (for API Keys) ---

def get_fernet() -> Fernet:
    """Lazy loader for Fernet suite"""
    try:
        return Fernet(settings.ENCRYPTION_KEY.encode())
    except Exception as e:
        raise ValueError(f"Invalid encryption key: {e}")

def encrypt_data(data: str) -> str:
    """Encrypt a string (like an API Key)"""
    if not data: return None
    f = get_fernet()
    return f.encrypt(data.encode()).decode()

def decrypt_data(token: str) -> str:
    """Decrypt a string"""
    if not token: return None
    f = get_fernet()
    return f.decrypt(token.encode()).decode()
