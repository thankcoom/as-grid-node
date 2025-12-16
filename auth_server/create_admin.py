"""
創建管理員帳號腳本

使用方式：
python create_admin.py
"""
import asyncio
import sys
sys.path.append('/Users/liutsungying/as網格/bitget_as/auth_server')

from app.db.session import SessionLocal
from app.db import models
from app.core.security import get_password_hash

async def create_admin():
    db = SessionLocal()
    try:
        # 檢查管理員是否已存在
        existing_admin = db.query(models.User).filter(
            models.User.email == "thankcoom@gmail.com"
        ).first()
        
        if existing_admin:
            print(f"⚠️  管理員已存在: {existing_admin.email}")
            print(f"   狀態: {existing_admin.status}")
            print(f"   是否為管理員: {existing_admin.is_admin}")
            
            # 更新為管理員
            if not existing_admin.is_admin:
                existing_admin.is_admin = True
                existing_admin.status = "active"
                db.commit()
                print("✅ 已將用戶升級為管理員")
            return
        
        # 創建新管理員
        admin = models.User(
            email="thankcoom@gmail.com",
            username="thankcoom",
            hashed_password=get_password_hash("louis1220"),  # bcrypt 加密
            is_active=True,
            is_admin=True,  # 設為管理員
            status="active",
            exchange="bitget"
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("✅ 管理員帳號創建成功！")
        print(f"   Email: {admin.email}")
        print(f"   Username: {admin.username}")
        print(f"   管理員權限: {admin.is_admin}")
        print(f"   狀態: {admin.status}")
        print("\n🔒 密碼已使用 bcrypt 加密儲存")
        
    except Exception as e:
        print(f"❌ 錯誤: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(create_admin())
