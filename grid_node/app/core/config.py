import os

class Settings:
    PROJECT_NAME: str = "AS Grid Node"
    API_V1_STR: str = "/api/v1"
    NODE_SECRET: str = os.getenv("NODE_SECRET", "default_insecure_secret")

settings = Settings()
