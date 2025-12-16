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
from sqlalchemy.orm import Session
import httpx

from app.api import deps
from app.db import models
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_node_url(user_id: str, db: Session) -> tuple[str, str]:
    """
    獲取用戶的 Node URL 和 Secret
    
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
    
    # 檢查是否在線
    if node_status.last_heartbeat:
        offline_threshold = datetime.utcnow() - timedelta(minutes=5)
        if node_status.last_heartbeat < offline_threshold:
            raise HTTPException(503, "Node appears to be offline")
    
    # Node Secret 存儲在環境變數中，或者使用用戶特定的 secret
    # 這裡暫時使用全局 secret
    node_secret = settings.DEFAULT_NODE_SECRET if hasattr(settings, 'DEFAULT_NODE_SECRET') else "default"
    
    return node_status.node_url, node_secret


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
    測試 Node 連接
    """
    try:
        node_url, node_secret = await get_node_url(current_user.id, db)
        
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
