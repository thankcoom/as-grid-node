"""
管理員 API 端點
用於用戶審核和群組管理
"""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api import deps
from app.db import models
from app import schemas

router = APIRouter()


def get_admin_user(
    current_user: models.User = Depends(deps.get_current_user)
) -> models.User:
    """驗證管理員權限"""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# ═══════════════════════════════════════════════════════════════════════════
# Dashboard Stats
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/stats")
def get_admin_stats(
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """獲取管理後台統計數據"""
    total_users = db.query(models.User).count()
    pending_users = db.query(models.User).filter(models.User.status == "pending_approval").count()
    active_users = db.query(models.User).filter(models.User.status == "active").count()
    rejected_users = db.query(models.User).filter(models.User.status == "rejected").count()
    total_groups = db.query(models.Group).count()
    
    return {
        "total_users": total_users,
        "pending_users": pending_users,
        "active_users": active_users,
        "rejected_users": rejected_users,
        "total_groups": total_groups
    }


# ═══════════════════════════════════════════════════════════════════════════
# User Management
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/users", response_model=List[schemas.AdminUser])
def get_all_users(
    status: str = None,
    group_id: str = None,
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """獲取所有用戶列表"""
    query = db.query(models.User)
    
    if status:
        query = query.filter(models.User.status == status)
    if group_id:
        query = query.filter(models.User.group_id == group_id)
    
    users = query.order_by(models.User.created_at.desc()).all()
    
    # 添加 group_name
    result = []
    for user in users:
        user_dict = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "status": user.status,
            "exchange_uid": user.exchange_uid,
            "zeabur_url": user.zeabur_url,
            "group_id": user.group_id,
            "group_name": user.group.name if user.group else None,
            "api_verified_at": user.api_verified_at,
            "approved_at": user.approved_at,
            "created_at": user.created_at
        }
        result.append(schemas.AdminUser(**user_dict))
    
    return result


@router.get("/users/pending", response_model=List[schemas.PendingUser])
def get_pending_users(
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """獲取待審核用戶列表"""
    return db.query(models.User).filter(
        models.User.status == "pending_approval"
    ).order_by(models.User.api_verified_at.desc()).all()


@router.post("/users/{user_id}/approve")
def approve_user(
    user_id: str,
    group_id: str = None,
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """批准用戶"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = "active"
    user.approved_at = datetime.utcnow()
    user.approved_by = admin.id
    
    if group_id:
        user.group_id = group_id
    
    db.commit()
    
    return {"message": "User approved", "email": user.email, "uid": user.exchange_uid}


@router.post("/users/{user_id}/reject")
def reject_user(
    user_id: str,
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """拒絕用戶"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = "rejected"
    db.commit()
    
    return {"message": "User rejected", "email": user.email}


@router.post("/users/{user_id}/group")
def assign_user_to_group(
    user_id: str,
    group_id: str,
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """分配用戶到群組"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if group_id:
        group = db.query(models.Group).filter(models.Group.id == group_id).first()
        if not group:
            raise HTTPException(status_code=404, detail="Group not found")
    
    user.group_id = group_id if group_id else None
    db.commit()
    
    return {"message": "User group updated", "group_id": group_id}


# ═══════════════════════════════════════════════════════════════════════════
# Group Management
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/groups", response_model=List[schemas.Group])
def get_all_groups(
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """獲取所有群組"""
    groups = db.query(models.Group).all()
    
    result = []
    for group in groups:
        user_count = db.query(models.User).filter(models.User.group_id == group.id).count()
        result.append(schemas.Group(
            id=group.id,
            name=group.name,
            description=group.description,
            created_at=group.created_at,
            user_count=user_count
        ))
    
    return result


@router.post("/groups", response_model=schemas.Group)
def create_group(
    group_in: schemas.GroupCreate,
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """創建新群組"""
    existing = db.query(models.Group).filter(models.Group.name == group_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Group name already exists")
    
    group = models.Group(
        name=group_in.name,
        description=group_in.description
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    
    return schemas.Group(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        user_count=0
    )


@router.put("/groups/{group_id}", response_model=schemas.Group)
def update_group(
    group_id: str,
    group_in: schemas.GroupUpdate,
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """更新群組"""
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    if group_in.name is not None:
        group.name = group_in.name
    if group_in.description is not None:
        group.description = group_in.description
    
    db.commit()
    db.refresh(group)
    
    user_count = db.query(models.User).filter(models.User.group_id == group.id).count()
    
    return schemas.Group(
        id=group.id,
        name=group.name,
        description=group.description,
        created_at=group.created_at,
        user_count=user_count
    )


@router.delete("/groups/{group_id}")
def delete_group(
    group_id: str,
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """刪除群組"""
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    # 移除群組內用戶的關聯
    db.query(models.User).filter(models.User.group_id == group_id).update({"group_id": None})
    
    db.delete(group)
    db.commit()
    
    return {"message": "Group deleted"}


@router.get("/groups/{group_id}/users", response_model=List[schemas.AdminUser])
def get_group_users(
    group_id: str,
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """獲取群組內的用戶"""
    group = db.query(models.Group).filter(models.Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    users = db.query(models.User).filter(models.User.group_id == group_id).all()
    
    result = []
    for user in users:
        user_dict = {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "status": user.status,
            "exchange_uid": user.exchange_uid,
            "zeabur_url": user.zeabur_url,
            "group_id": user.group_id,
            "group_name": group.name,
            "api_verified_at": user.api_verified_at,
            "approved_at": user.approved_at,
            "created_at": user.created_at
        }
        result.append(schemas.AdminUser(**user_dict))
    
    return result


# ═══════════════════════════════════════════════════════════════════════════
# UID Whitelist Management
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/whitelist")
def add_uid_to_whitelist(
    uid: str,
    email: str = None,
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """
    手動添加 UID 到白名單
    - 如果 UID 已存在用戶，將其狀態設為 active
    - 如果 UID 不存在，創建預審核記錄（InviteCode 表）
    """
    # 檢查是否已有此 UID 的用戶
    existing_user = db.query(models.User).filter(models.User.exchange_uid == uid).first()
    
    if existing_user:
        # 用戶已存在，直接批准
        existing_user.status = "active"
        existing_user.approved_at = datetime.utcnow()
        existing_user.approved_by = admin.id
        db.commit()
        return {
            "message": "User found and approved",
            "uid": uid,
            "email": existing_user.email,
            "action": "approved"
        }
    
    # 用戶不存在，創建預審核白名單記錄
    existing_whitelist = db.query(models.InviteCode).filter(
        models.InviteCode.exchange_uid == uid
    ).first()
    
    if existing_whitelist:
        return {
            "message": "UID already in whitelist",
            "uid": uid,
            "action": "already_exists"
        }
    
    # 創建新的白名單記錄
    whitelist_entry = models.InviteCode(
        code=f"PRE_{uid}",  # 使用 UID 生成唯一碼
        exchange_uid=uid,
        exchange="bitget",
        is_used=False
    )
    db.add(whitelist_entry)
    db.commit()
    
    return {
        "message": "UID added to whitelist",
        "uid": uid,
        "email": email,
        "action": "added"
    }


@router.get("/whitelist")
def get_whitelist(
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """獲取白名單列表"""
    entries = db.query(models.InviteCode).filter(
        models.InviteCode.code.like("PRE_%")
    ).all()
    
    return [
        {
            "id": e.id,
            "uid": e.exchange_uid,
            "created_at": e.created_at,
            "is_used": e.is_used
        }
        for e in entries
    ]


@router.delete("/whitelist/{uid}")
def remove_from_whitelist(
    uid: str,
    db: Session = Depends(deps.get_db),
    admin: models.User = Depends(get_admin_user)
):
    """從白名單移除 UID"""
    entry = db.query(models.InviteCode).filter(
        models.InviteCode.exchange_uid == uid
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="UID not found in whitelist")
    
    db.delete(entry)
    db.commit()
    
    return {"message": "UID removed from whitelist", "uid": uid}
