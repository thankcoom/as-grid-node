from pydantic_settings import BaseSettings
from typing import Optional
import warnings
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "AS Grid SaaS"
    API_V1_STR: str = "/api/v1"
    
    # Security - MUST be set via environment variables in production
    # Temporary defaults provided for easier deployment
    SECRET_KEY: str = "INSECURE-DEFAULT-KEY-PLEASE-CHANGE-IN-PRODUCTION-MIN-32-CHARS"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    # Default to SQLite for local dev if not provided
    DATABASE_URL: str = "sqlite:///./sql_app.db"

    # Encryption Key for API Credentials (must be 32 url-safe base64-encoded bytes)
    # Temporary default provided for easier deployment
    # Generate a secure one with: cryptography.fernet.Fernet.generate_key().decode()
    ENCRYPTION_KEY: str = "INSECURE-DEFAULT-ENCRYPTION-KEY-CHANGE-THIS-IN-PRODUCTION=="

    # Default Node Secret for proxy layer (must match grid_node NODE_SECRET)
    DEFAULT_NODE_SECRET: str = "default_insecure_secret"

    class Config:
        case_sensitive = True
        env_file = ".env"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Warn if using default insecure keys
        if "INSECURE" in self.SECRET_KEY:
            warnings.warn(
                "⚠️  WARNING: Using default SECRET_KEY! Set SECRET_KEY environment variable in production!",
                UserWarning
            )
        if "INSECURE" in self.ENCRYPTION_KEY:
            warnings.warn(
                "⚠️  WARNING: Using default ENCRYPTION_KEY! Set ENCRYPTION_KEY environment variable in production!",
                UserWarning
            )
        if "insecure" in self.DEFAULT_NODE_SECRET.lower():
            warnings.warn(
                "⚠️  WARNING: Using default NODE_SECRET! Set DEFAULT_NODE_SECRET environment variable in production!",
                UserWarning
            )

settings = Settings()
