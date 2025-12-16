"""
AS Grid Node - 用戶端交易節點 API

端點：
- /api/v1/grid/* - 交易控制
- /api/v1/coin/* - 選幣系統
- /api/v1/symbols/* - 交易對管理
- /api/v1/backtest/* - 回測系統
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from app.core.config import settings
from app.services.bot_manager import bot_manager

# API 路由
from app.api import coin, symbols, backtest

import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時初始化
    logger.info("Initializing Grid Node...")
    result = await bot_manager.initialize()
    logger.info(f"Initialization result: {result}")
    
    yield
    
    # 關閉時清理
    logger.info("Shutting down Grid Node...")
    await bot_manager.shutdown()


app = FastAPI(
    title="AS Grid Node",
    description="用戶端交易節點 - 完整 GUI 功能 API 版本",
    version="1.0.0",
    lifespan=lifespan
)

# CORS - Allow frontend to connect from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊 API 路由
app.include_router(coin.router, prefix="/api/v1/coin", tags=["coin"])
app.include_router(symbols.router, prefix="/api/v1/symbols", tags=["symbols"])
app.include_router(backtest.router, prefix="/api/v1/backtest", tags=["backtest"])


async def verify_secret(x_node_secret: str = Header(...)):
    """驗證 Node Secret"""
    if x_node_secret != settings.NODE_SECRET:
        raise HTTPException(status_code=403, detail="Invalid Node Secret")


class StartRequest(BaseModel):
    symbol: str
    quantity: float


class CommandRequest(BaseModel):
    action: str
    params: dict = {}


# ═══════════════════════════════════════════════════════════════════════════
# Grid 交易控制端點
# ═══════════════════════════════════════════════════════════════════════════

@app.post("/api/v1/grid/start", dependencies=[Depends(verify_secret)])
def start_grid(req: StartRequest):
    """啟動網格交易"""
    try:
        return bot_manager.start(req.symbol, req.quantity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/v1/grid/stop", dependencies=[Depends(verify_secret)])
async def stop_grid():
    """停止網格交易"""
    return await bot_manager.stop()


@app.get("/api/v1/grid/status", dependencies=[Depends(verify_secret)])
def get_status():
    """獲取交易狀態"""
    return bot_manager.get_status()


@app.post("/api/v1/grid/command", dependencies=[Depends(verify_secret)])
async def execute_command(req: CommandRequest):
    """執行遠端命令"""
    return await bot_manager.handle_command({
        "action": req.action,
        "params": req.params
    })


# ═══════════════════════════════════════════════════════════════════════════
# 系統端點
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/api/v1/node/info")
def get_node_info():
    """獲取 Node 基本資訊（公開端點）"""
    return {
        "version": "1.0.0",
        "name": settings.PROJECT_NAME,
        "connected_to_server": bot_manager.auth_client is not None and bot_manager.auth_client.is_registered,
        "features": ["trading", "coin_selection", "backtest", "symbols"]
    }


@app.get("/api/v1/health")
def health_check():
    """健康檢查"""
    status = bot_manager.get_status()
    return {
        "status": "ok",
        "trading": status.get("is_trading", False),
        "connected": bot_manager.auth_client.is_registered if bot_manager.auth_client else False
    }


@app.get("/")
def root():
    """根端點"""
    return {
        "name": "AS Grid Node",
        "version": "1.0.0",
        "docs": "/docs"
    }

