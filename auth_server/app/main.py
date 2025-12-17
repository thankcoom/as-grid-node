from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import inspect, text

from app.api.api_v1.api import api_router
from app.core.config import settings
from app.core.rate_limit import limiter
from app.core.logging_middleware import LoggingMiddleware
from app.db.session import engine
from app.db import models
from app import initial_data

# Create tables (for dev only - use Alembic in prod)
models.Base.metadata.create_all(bind=engine)

# Auto-migrate: add missing columns to existing tables
def auto_migrate():
    """Add missing columns that create_all doesn't handle"""
    inspector = inspect(engine)
    
    # Check node_status table for available_balance column
    if 'node_status' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('node_status')]
        with engine.connect() as conn:
            if 'available_balance' not in columns:
                try:
                    conn.execute(text('ALTER TABLE node_status ADD COLUMN available_balance FLOAT DEFAULT 0.0'))
                    conn.commit()
                    print("✅ Added available_balance column to node_status")
                except Exception as e:
                    print(f"⚠️ Could not add available_balance column: {e}")

auto_migrate()

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
