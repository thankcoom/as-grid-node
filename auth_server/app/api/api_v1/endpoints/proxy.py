"""
代理層 - 轉發前端請求到用戶的 Grid Node

這層的目的：
1. 用戶不需要知道 Node URL
2. 統一認證（JWT）
3. 隱藏 Node Secret
"""
from datetime import datetime, timedelta
from typing import Any
import logging
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import httpx
import asyncio

from app.api import deps
from app.db import models
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_node_url(user_id: str, db: Session, allow_offline: bool = False) -> tuple[str, str]:
    """
    獲取用戶的 Node URL 和 Secret

    Args:
        user_id: 用戶 ID
        db: 資料庫 session
        allow_offline: 是否允許離線節點（測試連接時使用）

    Returns:
        (node_url, node_secret)
    """
    node_status = db.query(models.NodeStatus).filter(
        models.NodeStatus.user_id == user_id
    ).first()

    if not node_status:
        raise HTTPException(404, "Node not registered. Please deploy your node first.")

    if not node_status.node_url:
        raise HTTPException(404, "Node URL not configured")

    # 檢查是否在線（放寬到 10 分鐘，並可以跳過）
    if not allow_offline and node_status.last_heartbeat:
        offline_threshold = datetime.utcnow() - timedelta(minutes=10)
        if node_status.last_heartbeat < offline_threshold:
            logger.warning(f"Node appears offline. Last heartbeat: {node_status.last_heartbeat}")
            raise HTTPException(503, "Node appears to be offline")

    # 使用用戶自己的 NODE_SECRET (Node 註冊時保存)
    if not node_status.node_secret:
        # 向後兼容：如果沒有保存 node_secret，使用預設值
        logger.warning(f"Node secret not found for user {user_id}, using default")
        node_secret = getattr(settings, 'DEFAULT_NODE_SECRET', 'default_insecure_secret')
    else:
        node_secret = node_status.node_secret

    return node_status.node_url, node_secret


# ═══════════════════════════════════════════════════════════════════════════
# 具體路由必須放在 catch-all 路由之前！
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/node/url")
async def set_node_url(
    node_url: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    設定用戶的 Node URL
    
    Node 在 Zeabur 部署後，需要設定 URL 才能代理
    """
    # 確保 URL 有 https:// 前綴
    if not node_url.startswith('http'):
        node_url = 'https://' + node_url
    
    # 獲取或創建 NodeStatus
    node_status = db.query(models.NodeStatus).filter(
        models.NodeStatus.user_id == current_user.id
    ).first()
    
    if not node_status:
        node_status = models.NodeStatus(user_id=current_user.id)
        db.add(node_status)
    
    node_status.node_url = node_url
    db.commit()
    
    logger.info(f"Set Node URL for user {current_user.email}: {node_url}")
    
    return {"status": "ok", "node_url": node_url}


@router.get("/node/test")
async def test_node_connection(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    測試 Node 連接（忽略心跳狀態，直接測試實際連接）
    """
    try:
        # 允許離線狀態，因為我們會直接測試
        node_url, node_secret = await get_node_url(current_user.id, db, allow_offline=True)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{node_url}/api/v1/health",
                headers={"X-Node-Secret": node_secret}
            )
        
        if response.status_code == 200:
            return {
                "status": "connected",
                "node_url": node_url,
                "node_response": response.json()
            }
        else:
            return {
                "status": "error",
                "node_url": node_url,
                "error": f"Node returned {response.status_code}"
            }
    
    except HTTPException as e:
        return {"status": "not_configured", "error": e.detail}
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════
# SSE 代理端點 - 即時數據推送
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/sse/events")
async def proxy_sse_events(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    SSE 代理端點 - 轉發 Node 的 SSE 事件到前端

    此端點作為 auth_server 與 Node 之間的 SSE 代理:
    1. 前端使用 JWT 認證連接此端點
    2. auth_server 使用 NODE_SECRET 連接到 Node
    3. 轉發所有 SSE 事件給前端

    優點:
    - 前端不需要知道 NODE_SECRET
    - 統一認證 (JWT)
    - 可以在 auth_server 層面過濾/處理事件
    """
    try:
        node_url, node_secret = await get_node_url(current_user.id, db)
    except HTTPException as e:
        # 如果 Node 不可用，返回錯誤事件
        async def error_generator():
            yield f"event: error\ndata: {{\"message\": \"{e.detail}\"}}\n\n"
        return StreamingResponse(
            error_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    sse_url = f"{node_url}/api/v1/sse/events"
    logger.info(f"SSE proxy connecting to {sse_url} for user {current_user.email}")

    async def sse_generator():
        """SSE 事件生成器 - 從 Node 讀取並轉發"""
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "GET",
                    sse_url,
                    headers={
                        "X-Node-Secret": node_secret,
                        "Accept": "text/event-stream",
                        "Cache-Control": "no-cache",
                    }
                ) as response:
                    if response.status_code != 200:
                        yield f"event: error\ndata: {{\"message\": \"Node returned {response.status_code}\"}}\n\n"
                        return

                    # 轉發所有從 Node 收到的 SSE 事件
                    async for chunk in response.aiter_bytes():
                        yield chunk.decode('utf-8')

        except httpx.ConnectError:
            yield f"event: error\ndata: {{\"message\": \"Cannot connect to Node\"}}\n\n"
        except httpx.TimeoutException:
            yield f"event: error\ndata: {{\"message\": \"Node connection timeout\"}}\n\n"
        except asyncio.CancelledError:
            logger.info(f"SSE connection cancelled for user {current_user.email}")
        except Exception as e:
            logger.error(f"SSE proxy error: {e}")
            yield f"event: error\ndata: {{\"message\": \"{str(e)}\"}}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx buffering off
        }
    )


# ═══════════════════════════════════════════════════════════════════════════
# Catch-all 代理路由 - 必須放在最後！
# ═══════════════════════════════════════════════════════════════════════════

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_to_node(
    path: str,
    request: Request,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
):
    """
    代理請求到用戶的 Node
    
    使用方式：
    - GET /proxy/grid/status → 轉發到 Node GET /api/v1/grid/status
    - POST /proxy/coin/scan → 轉發到 Node POST /api/v1/coin/scan
    - GET /proxy/symbols → 轉發到 Node GET /api/v1/symbols
    """
    node_url, node_secret = await get_node_url(current_user.id, db)
    
    target_url = f"{node_url}/api/v1/{path}"
    
    # 準備請求
    headers = {
        "X-Node-Secret": node_secret,
        "Content-Type": request.headers.get("Content-Type", "application/json")
    }
    
    # 獲取請求體
    body = await request.body()
    
    logger.info(f"Proxying {request.method} /{path} to {target_url}")
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body if body else None,
                params=dict(request.query_params)
            )
        
        # 返回 Node 的響應
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type")
        )
    
    except httpx.ConnectError:
        raise HTTPException(503, "Cannot connect to Node. Please check if it's running.")
    except httpx.TimeoutException:
        raise HTTPException(504, "Node request timeout")
    except Exception as e:
        logger.error(f"Proxy error: {e}")
        raise HTTPException(500, f"Proxy error: {str(e)}")
