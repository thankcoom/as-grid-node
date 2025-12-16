from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.api_v1.api import api_router
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.logging_middleware import LoggingMiddleware
from app.db.session import engine
from app.db import models
from app import initial_data

# Create tables (for dev only - use Alembic in prod)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# 註冊速率限制器
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 註冊日誌中間件
app.add_middleware(LoggingMiddleware)

@app.on_event("startup")
async def startup_event():
    initial_data.init()

# CORS - Allow frontend domains
origins = [
    "http://localhost:5173",      # Local dev
    "http://localhost:5174",      # Alternative local dev
    "http://localhost:53075",     # Another local dev port
    "https://louisasgrid-web.zeabur.app",  # Production frontend (actual deployed URL)
    # Add "*" temporarily if you need to allow all origins during testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"message": "Welcome to AS Grid SaaS API"}
