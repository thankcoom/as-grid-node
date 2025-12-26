from datetime import datetime, timedelta
from typing import Any
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.core.config import settings
from app.core.rate_limit import limiter
from app.db import models
from app import schemas

logger = logging.getLogger(__name__)
router = APIRouter()


# ═══════════════════════════════════════════════════════════════════════════
# New Flow: Register (email+password) → Verify API → Get UID → Admin Approval
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/register", response_model=schemas.User)
@limiter.limit("3/minute")
def register_user(
    request: Request,
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserRegister,
) -> Any:
    """
    Register new user with email + password only.
    User status will be 'pending_api' - they must set up API next.
    """
    # Check if email already exists
    existing = db.query(models.User).filter(
        models.User.email == user_in.email
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="This email is already registered.",
        )

    # Create user with pending_api status
    user = models.User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        is_active=True,
        status="pending_api",  # Must set up API next
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    logger.info(f"New user registered: {user.email}, status: pending_api")
    
    return user


@router.post("/verify_api", response_model=schemas.VerifyAPIResponse)
async def verify_api(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
    creds: schemas.APICredentials,
) -> Any:
    """
    Verify Bitget API credentials and get UID.
    - For pending_api/rejected users: Changes status to 'pending_approval'
    - For active users: Updates API credentials (allows changing API)
    """
    import ccxt.async_support as ccxt
    
    # Check if user is allowed to verify/update API
    is_update = current_user.status == "active"
    if current_user.status not in ["pending_api", "rejected", "active"]:
        raise HTTPException(
            status_code=400,
            detail="Cannot update API in current status.",
        )
    
    try:
        # Connect to Bitget and get account info
        exchange = ccxt.bitget({
            'apiKey': creds.api_key,
            'secret': creds.api_secret,
            'password': creds.passphrase,
            'options': {
                'defaultType': 'swap',
            }
        })
        
        
        # Load markets first
        await exchange.load_markets()
        
        # Get UID from Bitget API (multiple fallback methods)
        uid = None
        errors = []
        
        # Method 1: V2 Spot Account API (recommended)
        try:
            account_info = await exchange.privateSpotGetV2SpotAccountInfo()
            logger.debug(f"V2 Spot Account Info: {account_info}")
            if account_info and account_info.get('code') == '00000':
                data = account_info.get('data', {})
                uid = str(data.get('userId', '') or data.get('uid', ''))
                if uid and uid.isdigit():
                    logger.info(f"Got UID from V2 Spot API: {uid}")
        except Exception as e1:
            errors.append(f"V2 Spot: {str(e1)[:50]}")
            logger.debug(f"V2 Spot failed: {e1}")
        
        # Method 2: V2 Mix (Futures) Account API
        if not uid or not uid.isdigit():
            try:
                mix_info = await exchange.privateMixGetV2MixAccountAccounts({
                    'productType': 'USDT-FUTURES'
                })
                logger.debug(f"V2 Mix Account Info: {mix_info}")
                if mix_info and mix_info.get('code') == '00000':
                    data = mix_info.get('data', [])
                    if isinstance(data, list) and len(data) > 0:
                        uid = str(data[0].get('userId', '') or data[0].get('uid', ''))
                        if uid and uid.isdigit():
                            logger.info(f"Got UID from V2 Mix API: {uid}")
            except Exception as e2:
                errors.append(f"V2 Mix: {str(e2)[:50]}")
                logger.debug(f"V2 Mix failed: {e2}")
        
        # Method 3: V1 Spot Account API
        if not uid or not uid.isdigit():
            try:
                account_info_v1 = await exchange.privateSpotGetSpotV1AccountGetInfo()
                logger.debug(f"V1 Spot Account Info: {account_info_v1}")
                if account_info_v1 and 'data' in account_info_v1:
                    data = account_info_v1.get('data', {})
                    uid = str(data.get('userId', '') or data.get('uid', ''))
                    if uid and uid.isdigit():
                        logger.info(f"Got UID from V1 Spot API: {uid}")
            except Exception as e3:
                errors.append(f"V1 Spot: {str(e3)[:50]}")
                logger.debug(f"V1 Spot failed: {e3}")
        
        # Method 4: fetch_balance with info extraction
        if not uid or not uid.isdigit():
            try:
                balance = await exchange.fetch_balance()
                info = balance.get('info', {})
                logger.debug(f"fetch_balance info: {info}")
                if isinstance(info, dict):
                    uid = str(info.get('userId', '') or info.get('uid', ''))
                    if uid and uid.isdigit():
                        logger.info(f"Got UID from fetch_balance: {uid}")
            except Exception as e4:
                errors.append(f"Balance: {str(e4)[:50]}")
                logger.debug(f"fetch_balance failed: {e4}")
        
        # Method 5: User Fee Query API
        if not uid or not uid.isdigit():
            try:
                fee_info = await exchange.privateUserGetUserV1FeeQuery()
                logger.debug(f"Fee Query Info: {fee_info}")
                if fee_info and 'data' in fee_info:
                    data = fee_info.get('data', {})
                    uid = str(data.get('userId', '') or data.get('uid', ''))
                    if uid and uid.isdigit():
                        logger.info(f"Got UID from Fee Query: {uid}")
            except Exception as e5:
                errors.append(f"Fee: {str(e5)[:50]}")
                logger.debug(f"Fee Query failed: {e5}")
        
        # Method 6: V1 Mix Account
        if not uid or not uid.isdigit():
            try:
                mix_v1 = await exchange.privateMixGetMixV1AccountAccounts({
                    'productType': 'umcbl'  # USDT-M
                })
                logger.debug(f"V1 Mix Account: {mix_v1}")
                if mix_v1 and 'data' in mix_v1:
                    data = mix_v1.get('data', [])
                    if isinstance(data, list) and len(data) > 0:
                        uid = str(data[0].get('userId', '') or data[0].get('uid', ''))
                        if uid and uid.isdigit():
                            logger.info(f"Got UID from V1 Mix: {uid}")
            except Exception as e6:
                errors.append(f"V1Mix: {str(e6)[:50]}")
                logger.debug(f"V1 Mix failed: {e6}")
        
        
        # Final check: ensure we got a valid numeric UID
        if not uid or not uid.isdigit():
            await exchange.close()
            error_details = '; '.join(errors) if errors else "No specific error"
            logger.error(f"Failed to get valid UID from Bitget. Errors: {error_details}")
            raise HTTPException(
                status_code=400,
                detail=f"Unable to retrieve account UID from Bitget API. Please ensure: 1) API has proper permissions (Spot + Futures read access), 2) You have an active Bitget account with some balance or trading history. Technical details: {error_details[:100]}"
            )
        
        # Close exchange connection
        await exchange.close()
        
        # Check if UID already used by another user
        existing = db.query(models.User).filter(
            models.User.exchange_uid == uid,
            models.User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="This exchange account is already registered by another user.",
            )
        
        # 【安全限制】Active 用戶更換 API 時，必須使用相同的 UID
        # 這確保用戶只能更換自己帳戶的 API 密鑰，而不能換成別人的帳戶
        if is_update and current_user.exchange_uid:
            if uid != current_user.exchange_uid:
                raise HTTPException(
                    status_code=400,
                    detail=f"UID mismatch. Your registered UID is {current_user.exchange_uid}, but this API belongs to UID {uid}. You can only update API credentials for your registered Bitget account.",
                )
        
        # Update user
        current_user.exchange_uid = uid
        current_user.api_verified_at = datetime.utcnow()

        # ═══════════════════════════════════════════════════════════════════
        # 【混合式安全設計】API 憑證不再存儲於 Server
        #
        # 原因：
        # 1. 用戶的 API 憑證只存在用戶自己的 Zeabur 環境變數中
        # 2. 官方伺服器永遠無法獲取用戶的 API Key
        # 3. 即使官方 DB 被入侵，用戶資金也是安全的
        #
        # 用戶需要在部署 Grid Node 時，在 Zeabur 環境變數中設定：
        # - BITGET_API_KEY
        # - BITGET_API_SECRET
        # - BITGET_PASSPHRASE
        # ═══════════════════════════════════════════════════════════════════

        # 根據用戶狀態決定下一步
        if is_update:
            # Active user updating API - keep status as active
            db.commit()
            logger.info(f"User {current_user.email} updated API credentials. UID: {uid}")
            return schemas.VerifyAPIResponse(
                uid=uid,
                status="active",
                message="API credentials updated successfully. Node will fetch new credentials on next heartbeat."
            )
        else:
            # New user - change to pending_approval
            current_user.status = "pending_approval"
            db.commit()
            
            # 🔔 Send notification to admin
            logger.warning(
                f"🔔 ADMIN NOTIFICATION: New user waiting for approval!\n"
                f"   Email: {current_user.email}\n"
                f"   UID: {uid}\n"
                f"   Time: {datetime.now()}"
            )
            
            return schemas.VerifyAPIResponse(
                uid=uid,
                status="pending_approval",
                message="Your account is pending admin approval."
            )
        
    except Exception as e:
        error_msg = str(e)
        if "authentication" in error_msg.lower() or "invalid" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Invalid API credentials. Please check your API Key, Secret, and Passphrase.",
            )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to verify API: {error_msg}",
        )


@router.post("/login", response_model=schemas.Token)
@limiter.limit("5/minute")
def login_access_token(
    request: Request,
    db: Session = Depends(deps.get_db), form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login.
    Returns different errors based on user status.
    """
    # Find user by email (using username field for OAuth2 compatibility)
    user = db.query(models.User).filter(models.User.email == form_data.username).first()
    
    # Also try username if email didn't match
    if not user:
        user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Account is disabled")

    # 🆕 Return different errors based on status
    if user.status == "pending_api":
        # Return token so user can access API setup page
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        return {
            "access_token": security.create_access_token(
                data={"sub": user.id}, expires_delta=access_token_expires
            ),
            "token_type": "bearer",
            "status": "pending_api",  # Frontend will redirect to API setup
        }
    
    if user.status == "pending_approval":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail={
                "code": "PENDING_APPROVAL",
                "message": "Your account is pending admin approval.",
                "uid": user.exchange_uid
            }
        )
    
    if user.status == "rejected":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail={
                "code": "REJECTED",
                "message": "Access denied. Please contact admin."
            }
        )
        
    # status == "active"
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(
            data={"sub": user.id}, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }


# ═══════════════════════════════════════════════════════════════════════════
# Admin APIs for managing user approvals
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/pending", response_model=list[schemas.PendingUser])
def get_pending_users(
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Get list of users pending approval.
    Requires admin privileges.
    """
    return db.query(models.User).filter(
        models.User.status == "pending_approval"
    ).all()


@router.post("/approve/{user_id}")
def approve_user(
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Approve a user (add to whitelist).
    Requires admin privileges.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = "active"
    user.approved_at = datetime.utcnow()
    user.approved_by = current_user.id
    db.commit()
    
    logger.info(f"User approved: {user.email} (UID: {user.exchange_uid})")
    
    return {"status": "approved", "email": user.email, "uid": user.exchange_uid}


@router.post("/reject/{user_id}")
def reject_user(
    user_id: str,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_admin_user),
) -> Any:
    """
    Reject a user.
    Requires admin privileges.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = "rejected"
    db.commit()
    
    logger.info(f"User rejected: {user.email} (UID: {user.exchange_uid})")
    
    return {"status": "rejected", "email": user.email}


# ═══════════════════════════════════════════════════════════════════════════
# Legacy endpoint (kept for backward compatibility)
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/register_legacy", response_model=schemas.User)
def register_user_legacy(
    *,
    db: Session = Depends(deps.get_db),
    user_in: schemas.UserCreate,
) -> Any:
    """
    Legacy: Create new user with invite code (DEPRECATED AND DISABLED)
    This endpoint is kept for API compatibility but is no longer functional.
    Use /register and /verify_api instead.
    """
    raise HTTPException(
        status_code=410,
        detail="This registration method is deprecated. Please use /register and /verify_api."
    )
