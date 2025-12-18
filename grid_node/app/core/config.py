import os
import warnings

class Settings:
    PROJECT_NAME: str = "AS Grid Node"
    API_V1_STR: str = "/api/v1"
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

settings = Settings()
