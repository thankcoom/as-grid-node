from pydantic_settings import BaseSettings
from typing import Optional
import warnings
import os

# 開發用固定密鑰（有效的 Fernet 格式）
# 生產環境必須設定 ENCRYPTION_KEY 環境變數！
# 生成命令: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
DEV_ENCRYPTION_KEY = "YWJjZGVmZ2hpamtsbW5vcHFyc3R1dnd4eXoxMjM0NTY="

class Settings(BaseSettings):
    PROJECT_NAME: str = "AS Grid SaaS"
    API_V1_STR: str = "/api/v1"
    
    # Security - MUST be set via environment variables in production
    SECRET_KEY: str = "INSECURE-DEFAULT-KEY-PLEASE-CHANGE-IN-PRODUCTION-MIN-32-CHARS"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Database
    DATABASE_URL: str = "sqlite:///./sql_app.db"

    # Encryption Key for API Credentials (must be 32 url-safe base64-encoded bytes)
    # MUST be set in production! Generate with:
    # python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPTION_KEY: str = ""

    # Default Node Secret for proxy layer (must match grid_node NODE_SECRET)
    DEFAULT_NODE_SECRET: str = "default_insecure_secret"

    class Config:
        case_sensitive = True
        env_file = ".env"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Handle ENCRYPTION_KEY - MUST be set from environment or use dev key
        env_key = os.getenv("ENCRYPTION_KEY", "")
        if env_key:
            self.ENCRYPTION_KEY = env_key
        else:
            # 使用固定的開發用 key（不是每次生成新的）
            self.ENCRYPTION_KEY = DEV_ENCRYPTION_KEY
            warnings.warn(
                "⚠️  WARNING: ENCRYPTION_KEY not set! Using DEV key. "
                "This MUST be set in production!",
                UserWarning
            )
        
        # Validate Fernet key format
        try:
            from cryptography.fernet import Fernet
            Fernet(self.ENCRYPTION_KEY.encode())
        except Exception as e:
            raise ValueError(
                f"Invalid ENCRYPTION_KEY format: {e}\n"
                "Generate a valid key with:\n"
                "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        
        # Warn if using default insecure keys
        if "INSECURE" in self.SECRET_KEY:
            warnings.warn(
                "⚠️  WARNING: Using default SECRET_KEY! Set SECRET_KEY environment variable in production!",
                UserWarning
            )
        if "insecure" in self.DEFAULT_NODE_SECRET.lower():
            warnings.warn(
                "⚠️  WARNING: Using default NODE_SECRET! Set DEFAULT_NODE_SECRET environment variable in production!",
                UserWarning
            )

settings = Settings()
