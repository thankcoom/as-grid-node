"""
獨立管理員創建腳本 - 直接連接 Zeabur PostgreSQL

使用方式：
1. 先安裝依賴: pip install psycopg2-binary bcrypt
2. 運行: python create_admin_standalone.py
"""
import psycopg2
import bcrypt
import uuid

# Zeabur PostgreSQL 連接資訊
# 從 Zeabur Dashboard → postgresql 服務 → 環境變數獲取
DB_CONFIG = {
    'host': 'sjc1.clusters.zeabur.com',
    'port': '24079',
    'database': 'zeabur',
    'user': 'root',
    'password': '0E8kuLQyzJOVe4ia9H1s7Y2nC6o5MTS3'  # 您的密碼
}

def create_admin():
    """創建管理員帳號"""
    try:
        # 連接資料庫
        print("🔗 連接 Zeabur PostgreSQL...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        email = "thankcoom@gmail.com"
        username = "thankcoom"
        password = "louis1220"
        
        # 檢查用戶是否已存在
        cursor.execute("SELECT id, email, is_admin, status FROM users WHERE email = %s", (email,))
        existing = cursor.fetchone()
        
        if existing:
            user_id, user_email, is_admin, status = existing
            print(f"⚠️  用戶已存在:")
            print(f"   Email: {user_email}")
            print(f"   管理員: {is_admin}")
            print(f"   狀態: {status}")
            
            # 升級為管理員
            if not is_admin:
                cursor.execute(
                    "UPDATE users SET is_admin = TRUE, status = 'active' WHERE email = %s",
                    (email,)
                )
                conn.commit()
                print("✅ 已升級為管理員")
            else:
                print("✅ 已經是管理員")
            
            cursor.close()
            conn.close()
            return
        
        # 加密密碼（bcrypt）
        print("🔐 加密密碼...")
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # 創建新管理員
        user_id = str(uuid.uuid4())
        cursor.execute(
            """
            INSERT INTO users (id, email, username, hashed_password, is_active, is_admin, status, exchange, created_at)
            VALUES (%s, %s, %s, %s, TRUE, TRUE, 'active', 'bitget', NOW())
            """,
            (user_id, email, username, hashed_password)
        )
        
        conn.commit()
        
        print("✅ 管理員帳號創建成功！")
        print(f"   Email: {email}")
        print(f"   Username: {username}")
        print(f"   密碼: {password}")
        print(f"   管理員權限: True")
        print(f"   UUID: {user_id}")
        print("\n🔒 密碼已使用 bcrypt 加密儲存")
        print("\n🌐 登入網址: https://louisasgrid-web.zeabur.app/login")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"❌ 資料庫錯誤: {e}")
    except Exception as e:
        print(f"❌ 錯誤: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Louis AS Grid - 管理員帳號創建工具")
    print("=" * 60)
    create_admin()
