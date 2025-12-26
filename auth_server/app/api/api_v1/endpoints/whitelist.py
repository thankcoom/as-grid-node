"""
Whitelist API 端點 - 交易時 UID 驗證

═══════════════════════════════════════════════════════════════════════════
【交易時 UID 驗證】白名單檢查機制

設計說明：
1. Node 在每筆交易前調用 /whitelist/check?uid=xxx 檢查白名單
2. 使用本地快取減少請求頻率 (TTL 5 分鐘)
3. 用戶被移出白名單後有 24 小時緩衝期
4. 緩衝期內發送警告但允許交易，超時後禁止交易
═══════════════════════════════════════════════════════════════════════════
"""
from datetime import datetime, timedelta
from typing import Any
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api import deps
from app.db import models

logger = logging.getLogger(__name__)
router = APIRouter()

# 警告緩衝期 (小時)
WARNING_BUFFER_HOURS = 24


@router.get("/check")
def check_whitelist(
    uid: str = Query(..., description="Bitget Exchange UID"),
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    檢查 UID 是否在白名單中

    此端點用於 Grid Node 在交易前驗證用戶狀態

    Returns:
        {
            "valid": bool,           # 是否允許交易
            "status": str,           # 用戶狀態
            "warning": bool,         # 是否在警告期
            "warning_hours_remaining": float | None,  # 剩餘警告時間 (小時)
            "message": str           # 訊息
        }
    """
    # 查找用戶
    user = db.query(models.User).filter(
        models.User.exchange_uid == uid
    ).first()

    # UID 不存在
    if not user:
        logger.warning(f"Whitelist check: UID {uid} not found")
        return {
            "valid": False,
            "status": "not_found",
            "warning": False,
            "warning_hours_remaining": None,
            "message": "UID not registered"
        }

    # 用戶狀態為 active = 在白名單中
    if user.status == "active":
        # 清除任何之前的警告
        if user.whitelist_warning_at:
            user.whitelist_warning_at = None
            db.commit()

        return {
            "valid": True,
            "status": "active",
            "warning": False,
            "warning_hours_remaining": None,
            "message": "OK"
        }

    # 用戶狀態不是 active (pending_api, pending_approval, rejected, suspended)
    # 檢查是否在 24 小時緩衝期內

    # 如果沒有警告時間戳，設定一個
    if not user.whitelist_warning_at:
        user.whitelist_warning_at = datetime.utcnow()
        db.commit()
        logger.warning(f"Whitelist warning started for UID {uid}, status: {user.status}")

    # 計算剩餘緩衝時間
    warning_elapsed = datetime.utcnow() - user.whitelist_warning_at
    warning_remaining = timedelta(hours=WARNING_BUFFER_HOURS) - warning_elapsed
    hours_remaining = warning_remaining.total_seconds() / 3600

    if hours_remaining > 0:
        # 還在緩衝期內 - 發送警告但允許交易
        logger.warning(
            f"Whitelist warning: UID {uid} has {hours_remaining:.1f} hours remaining. "
            f"Status: {user.status}"
        )
        return {
            "valid": True,  # 緩衝期內仍允許交易
            "status": user.status,
            "warning": True,
            "warning_hours_remaining": round(hours_remaining, 2),
            "message": f"Warning: Your account status is '{user.status}'. "
                       f"Trading will be blocked in {hours_remaining:.1f} hours."
        }
    else:
        # 緩衝期已過 - 禁止交易
        logger.error(f"Whitelist blocked: UID {uid} exceeded 24hr buffer. Status: {user.status}")
        return {
            "valid": False,
            "status": user.status,
            "warning": False,
            "warning_hours_remaining": 0,
            "message": f"Trading blocked. Account status: '{user.status}'. Please contact support."
        }


@router.get("/status/{uid}")
def get_whitelist_status(
    uid: str,
    db: Session = Depends(deps.get_db)
) -> Any:
    """
    獲取 UID 的詳細白名單狀態 (無需認證，用於調試)
    """
    user = db.query(models.User).filter(
        models.User.exchange_uid == uid
    ).first()

    if not user:
        return {"found": False, "uid": uid}

    return {
        "found": True,
        "uid": uid,
        "email": user.email,
        "status": user.status,
        "is_active": user.is_active,
        "approved_at": user.approved_at.isoformat() if user.approved_at else None,
        "whitelist_warning_at": user.whitelist_warning_at.isoformat() if user.whitelist_warning_at else None,
        "api_verified_at": user.api_verified_at.isoformat() if user.api_verified_at else None
    }
