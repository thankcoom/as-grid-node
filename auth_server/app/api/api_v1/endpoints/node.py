"""
Node API 端點 - 用戶 Grid Node 通訊

端點：
- POST /node/register - Node 註冊
- POST /node/heartbeat - 心跳回報
- POST /node/trade - 交易事件
- GET /node/commands - 獲取待執行命令
"""
from datetime import datetime, timedelta
from typing import Any, Optional, List
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api import deps
from app.db import models
from app.core import security
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# Schemas
# ═══════════════════════════════════════════════════════════════════════════

class NodeRegisterRequest(BaseModel):
    # 支援兩種識別方式：優先使用 bitget_uid（更簡單），兼容舊的 user_id
    bitget_uid: Optional[str] = None  # Bitget Exchange UID (推薦)
    user_id: Optional[str] = None     # System UUID (兼容舊版)
    node_secret: str
    node_version: str = "1.0.0"


class NodeRegisterResponse(BaseModel):
    token: str
    credentials: Optional[dict] = None
    message: str


class HeartbeatRequest(BaseModel):
    status: str
    is_trading: bool = False
    total_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    equity: float = 0.0
    available_balance: float = 0.0
    positions: List[dict] = []
    symbols: List[str] = []
    timestamp: Optional[str] = None


class TradeReport(BaseModel):
    symbol: str
    side: str
    price: float
    quantity: float
    pnl: float = 0.0


class CommandResponse(BaseModel):
    commands: List[dict] = []


# ═══════════════════════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/register", response_model=NodeRegisterResponse)
def register_node(
    req: NodeRegisterRequest,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    Node 註冊端點
    
    支援兩種識別方式：
    1. bitget_uid: Bitget Exchange UID（推薦，更簡單）
    2. user_id: System UUID（兼容舊版）
    
    返回：
    1. JWT token 供後續認證
    2. 解密的 API 憑證
    """
    user = None
    
    # 優先使用 bitget_uid 查找用戶
    if req.bitget_uid:
        user = db.query(models.User).filter(
            models.User.exchange_uid == req.bitget_uid
        ).first()
        if not user:
            raise HTTPException(
                status_code=404, 
                detail=f"No user found with Bitget UID: {req.bitget_uid}"
            )
        logger.info(f"Node register using Bitget UID: {req.bitget_uid}")
    
    # 兼容舊版 user_id
    elif req.user_id:
        user = db.query(models.User).filter(
            models.User.id == req.user_id
        ).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        logger.info(f"Node register using System UUID: {req.user_id}")
    
    else:
        raise HTTPException(
            status_code=400, 
            detail="Either bitget_uid or user_id must be provided"
        )
    
    # 驗證用戶狀態
    if user.status != "active":
        raise HTTPException(
            status_code=403, 
            detail=f"User not approved. Status: {user.status}"
        )
    
    # 獲取並解密 API 憑證（可選 - 如果失敗則 credentials = None）
    credentials = None
    if user.credentials:
        logger.info(f"User {user.email} has credentials stored, attempting decryption...")
        try:
            from cryptography.fernet import Fernet, InvalidToken
            # 嘗試使用 ENCRYPTION_KEY 解密
            fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            
            api_key = fernet.decrypt(user.credentials.api_key_encrypted.encode()).decode()
            api_secret = fernet.decrypt(user.credentials.api_secret_encrypted.encode()).decode()
            passphrase = ""
            if user.credentials.passphrase_encrypted:
                passphrase = fernet.decrypt(user.credentials.passphrase_encrypted.encode()).decode()
            
            credentials = {
                "api_key": api_key,
                "api_secret": api_secret,
                "passphrase": passphrase
            }
            logger.info(f"Successfully decrypted credentials for user {user.email}")
        except (InvalidToken, ValueError, Exception) as e:
            # 解密失敗不阻止註冊，只是沒有憑證
            logger.error(f"DECRYPTION FAILED for user {user.email}: {e}")
            logger.error(f"ENCRYPTION_KEY starts with: {settings.ENCRYPTION_KEY[:20]}...")
    else:
        logger.warning(f"User {user.email} has NO credentials stored in database!")
    
    # 創建或更新 NodeStatus
    node_status = db.query(models.NodeStatus).filter(
        models.NodeStatus.user_id == user.id
    ).first()
    
    if not node_status:
        node_status = models.NodeStatus(
            user_id=user.id,
            node_version=req.node_version,
            is_online=True,
            last_heartbeat=datetime.utcnow()
        )
        db.add(node_status)
    else:
        node_status.is_online = True
        node_status.node_version = req.node_version
        node_status.last_heartbeat = datetime.utcnow()
    
    db.commit()
    
    # 生成 JWT token
    access_token = security.create_access_token(
        data={"sub": user.id, "type": "node"},
        expires_delta=timedelta(days=30)  # Node token 有效期較長
    )
    
    logger.info(f"Node registered for user: {user.email}")
    
    return NodeRegisterResponse(
        token=access_token,
        credentials=credentials,
        message="Node registered successfully"
    )


@router.post("/heartbeat")
def node_heartbeat(
    req: HeartbeatRequest,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:
    """
    心跳端點 - 更新 Node 狀態
    """
    # 獲取或創建 NodeStatus
    node_status = db.query(models.NodeStatus).filter(
        models.NodeStatus.user_id == current_user.id
    ).first()
    
    if not node_status:
        node_status = models.NodeStatus(user_id=current_user.id)
        db.add(node_status)
    
    # 更新狀態
    node_status.is_online = True
    node_status.is_trading = req.is_trading
    node_status.total_pnl = req.total_pnl
    node_status.unrealized_pnl = req.unrealized_pnl
    node_status.equity = req.equity
    node_status.available_balance = req.available_balance
    node_status.positions = json.dumps(req.positions)
    node_status.symbols = json.dumps(req.symbols)
    node_status.last_heartbeat = datetime.utcnow()
    
    db.commit()
    
    # 檢查是否有待執行命令（未來擴展）
    commands = []
    
    return {"status": "ok", "commands": commands}


@router.post("/trade")
def report_trade(
    trade: TradeReport,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:
    """
    交易事件回報
    """
    logger.info(
        f"Trade reported by {current_user.email}: "
        f"{trade.symbol} {trade.side} @ {trade.price} qty={trade.quantity} pnl={trade.pnl}"
    )
    
    # 可以存入 GridExecution 表（未來擴展）
    
    return {"status": "recorded"}


@router.get("/commands", response_model=CommandResponse)
def get_commands(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:
    """
    獲取待執行命令
    
    命令存儲在某處（例如 Redis 或資料庫），Node 定期拉取
    """
    # 目前返回空列表，未來可以實現命令隊列
    commands = []
    
    return CommandResponse(commands=commands)


@router.get("/status/{user_id}")
def get_node_status(
    user_id: str,
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(deps.get_current_admin_user)
) -> Any:
    """
    (管理員) 獲取指定用戶的 Node 狀態
    """
    node_status = db.query(models.NodeStatus).filter(
        models.NodeStatus.user_id == user_id
    ).first()
    
    if not node_status:
        return {"status": "not_registered"}
    
    # 檢查是否離線（超過 2 分鐘無心跳）
    is_online = False
    if node_status.last_heartbeat:
        is_online = (datetime.utcnow() - node_status.last_heartbeat) < timedelta(minutes=2)
    
    return {
        "is_online": is_online,
        "is_trading": node_status.is_trading,
        "total_pnl": node_status.total_pnl,
        "unrealized_pnl": node_status.unrealized_pnl,
        "equity": node_status.equity,
        "available_balance": node_status.available_balance,
        "positions": json.loads(node_status.positions) if node_status.positions else [],
        "symbols": json.loads(node_status.symbols) if node_status.symbols else [],
        "last_heartbeat": node_status.last_heartbeat.isoformat() if node_status.last_heartbeat else None,
        "node_version": node_status.node_version
    }


@router.get("/my-status")
def get_my_node_status(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user)
) -> Any:
    """
    (用戶) 獲取自己的 Node 狀態
    """
    node_status = db.query(models.NodeStatus).filter(
        models.NodeStatus.user_id == current_user.id
    ).first()
    
    if not node_status:
        return {
            "status": "not_registered",
            "message": "Node has not been deployed yet"
        }
    
    # 檢查是否離線
    is_online = False
    if node_status.last_heartbeat:
        is_online = (datetime.utcnow() - node_status.last_heartbeat) < timedelta(minutes=2)
    
    return {
        "is_online": is_online,
        "is_trading": node_status.is_trading,
        "total_pnl": node_status.total_pnl,
        "unrealized_pnl": node_status.unrealized_pnl,
        "equity": node_status.equity,
        "available_balance": node_status.available_balance,
        "positions": json.loads(node_status.positions) if node_status.positions else [],
        "symbols": json.loads(node_status.symbols) if node_status.symbols else [],
        "last_heartbeat": node_status.last_heartbeat.isoformat() if node_status.last_heartbeat else None,
        "node_url": node_status.node_url
    }
