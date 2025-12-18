import os
import warnings

class Settings:
    PROJECT_NAME: str = "AS Grid Node"
    API_V1_STR: str = "/api/v1"
    
    # Auth Server 連接配置
    AUTH_SERVER_URL: str = os.getenv("AUTH_SERVER_URL", "")
    BITGET_UID: str = os.getenv("BITGET_UID", "")
    NODE_SECRET: str = os.getenv("NODE_SECRET", "default_insecure_secret")
    
    # CORS - comma-separated list of allowed origins, defaults to "*" for dev
    # In production, set to specific frontend domains
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
    
    def __init__(self):
        if "insecure" in self.NODE_SECRET.lower():
            warnings.warn(
                "⚠️  WARNING: Using default NODE_SECRET! Set NODE_SECRET environment variable!",
                UserWarning
            )
        if not self.BITGET_UID:
            warnings.warn(
                "⚠️  WARNING: BITGET_UID not set! Node will run in standalone mode.",
                UserWarning
            )
        if not self.AUTH_SERVER_URL:
            warnings.warn(
                "⚠️  WARNING: AUTH_SERVER_URL not set! Node will run in standalone mode.",
                UserWarning
            )

settings = Settings()

