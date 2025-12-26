"""
SSE (Server-Sent Events) 端點 - 即時數據推送

═══════════════════════════════════════════════════════════════════════════
【P2: SSE 前端通訊】

事件類型：
- status_update    - 狀態更新 (5 秒)
- price_update     - 價格更新 (1 秒) - 未實作
- position_update  - 持倉更新 (5 秒)
- account_update   - 帳戶餘額更新 (10 秒)
- trade_executed   - 成交通知 (即時)
- error            - 錯誤通知 (即時)
- connection_status - 連線狀態變更 (即時)
═══════════════════════════════════════════════════════════════════════════
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncGenerator

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from app.services.bot_manager import bot_manager
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

# SSE 更新間隔 (秒)
STATUS_INTERVAL = 5
ACCOUNT_INTERVAL = 10


async def verify_secret_sse(x_node_secret: str = None) -> bool:
    """驗證 Node Secret (SSE 用)"""
    if not x_node_secret:
        return False
    return x_node_secret == settings.NODE_SECRET


async def event_generator(node_secret: str) -> AsyncGenerator[str, None]:
    """
    SSE 事件生成器

    持續推送交易狀態更新到前端
    """
    # 驗證
    if not await verify_secret_sse(node_secret):
        yield format_sse_event("error", {"message": "Invalid Node Secret"})
        return

    logger.info("SSE connection established")

    # 發送初始連線確認
    yield format_sse_event("connected", {
        "message": "SSE connection established",
        "timestamp": datetime.utcnow().isoformat()
    })

    last_status_time = 0
    last_account_time = 0
    last_connection_status = None

    try:
        while True:
            current_time = asyncio.get_event_loop().time()

            # 檢查連線狀態變更
            connection_status = bot_manager.get_connection_status()
            if connection_status != last_connection_status:
                yield format_sse_event("connection_status", connection_status)
                last_connection_status = connection_status.copy()

            # 狀態更新 (每 5 秒)
            if current_time - last_status_time >= STATUS_INTERVAL:
                status = bot_manager.get_status()
                yield format_sse_event("status_update", status)
                last_status_time = current_time

            # 帳戶餘額更新 (每 10 秒)
            if current_time - last_account_time >= ACCOUNT_INTERVAL:
                status = bot_manager.get_status()
                account_data = {
                    "equity": status.get("equity", 0),
                    "available_balance": status.get("available_balance", 0),
                    "unrealized_pnl": status.get("unrealized_pnl", 0),
                    "usdt_equity": status.get("usdt_equity", 0),
                    "usdt_available": status.get("usdt_available", 0),
                    "usdc_equity": status.get("usdc_equity", 0),
                    "usdc_available": status.get("usdc_available", 0),
                    "timestamp": datetime.utcnow().isoformat()
                }
                yield format_sse_event("account_update", account_data)
                last_account_time = current_time

            # 持倉更新 (與狀態更新一起)
            if bot_manager.is_trading:
                status = bot_manager.get_status()
                positions = status.get("positions", [])
                if positions:
                    yield format_sse_event("position_update", {
                        "positions": positions,
                        "timestamp": datetime.utcnow().isoformat()
                    })

            # 心跳 (防止連線超時)
            yield format_sse_event("heartbeat", {
                "timestamp": datetime.utcnow().isoformat()
            })

            await asyncio.sleep(1)

    except asyncio.CancelledError:
        logger.info("SSE connection cancelled")
    except Exception as e:
        logger.error(f"SSE error: {e}")
        yield format_sse_event("error", {"message": str(e)})
    finally:
        logger.info("SSE connection closed")


def format_sse_event(event_type: str, data: dict) -> str:
    """
    格式化 SSE 事件

    Args:
        event_type: 事件類型
        data: 事件數據

    Returns:
        SSE 格式的字串
    """
    json_data = json.dumps(data, ensure_ascii=False, default=str)
    return f"event: {event_type}\ndata: {json_data}\n\n"


@router.get("/events")
async def sse_events(x_node_secret: str = Header(None)):
    """
    SSE 事件流端點

    連接此端點以接收即時交易狀態更新

    Headers:
        X-Node-Secret: Node 驗證密鑰

    Events:
        - connected: 連線成功
        - status_update: 交易狀態更新 (每 5 秒)
        - account_update: 帳戶餘額更新 (每 10 秒)
        - position_update: 持倉更新
        - connection_status: 連線狀態變更
        - heartbeat: 心跳 (每秒)
        - error: 錯誤
    """
    return StreamingResponse(
        event_generator(x_node_secret),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx buffering off
        }
    )


@router.get("/events/status")
async def get_sse_status():
    """獲取 SSE 服務狀態 (公開端點)"""
    return {
        "sse_enabled": True,
        "status_interval": STATUS_INTERVAL,
        "account_interval": ACCOUNT_INTERVAL,
        "events": [
            "connected",
            "status_update",
            "account_update",
            "position_update",
            "connection_status",
            "heartbeat",
            "error"
        ]
    }
