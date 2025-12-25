## 完整SaaS框架（從註冊到網格執行）

### **架構層次**
```
前端（React/Vue）→ FastAPI後端 → 資料庫（PostgreSQL）→ 交易所API
                                   ↓
                            Celery背景任務（grid邏輯）
                                   ↓
                            用戶隔離容器/實例
```

***

## **第一步：UID 白名單驗證註冊**

邀請碼機制已改為 **Bitget UID 白名單** 機制。確保用戶是透過官方推薦連結註冊，或已獲得授權。

系統運作邏輯：
1.  **用戶註冊**：不需輸入邀請碼。
2.  **API 驗證**：用戶在系統內輸入 Bitget API Key。
3.  **UID 比對**：系統從 API 獲取 UID，並檢查是否在白名單 (`InviteCode` 表作為白名單使用) 中。
4.  **自動開通**：若 UID 在白名單內，狀態自動改為 `active`；否則為 `pending_approval` 或 `rejected`。

```python
# 後端邏輯概念 (參考 auth_server/app/api/api_v1/endpoints/auth.py)

@app.post("/register")
async def register(
    user_in: UserCreate,
    db: Session = Depends(get_db)
):
    # 1. 建立基本 User 記錄
    user = User(
        email=user_in.email,
        password=hash_password(user_in.password),
        status="pending_api"  # 初始狀態：等待 API 驗證
    )
    db.add(user)
    db.commit()
    
    return {"message": "註冊成功，請繼續進行 API 驗證"}

# API 驗證與白名單檢查 (參考 auth_server/app/services/exchange_service.py)
async def verify_user_uid(user, api_key, api_secret, passphrase):
    # 1. 呼叫 Bitget API 獲取 UID
    uid = bitget_client.get_uid(api_key, api_secret, passphrase)
    
    # 2. 檢查白名單
    whitelist_entry = db.query(InviteCode).filter(
        InviteCode.exchange_uid == uid
    ).first()
    
    if whitelist_entry:
        user.status = "active"
        user.group_id = whitelist_entry.group_id  # 若有分組
    else:
        user.status = "pending_approval" # 進入人工審核
        
    user.exchange_uid = uid
    db.commit()
```

***

## **第二步：登入與JWT驗證**

```python
# 後端：fastapi_backend/routes/auth.py

from datetime import datetime, timedelta
from typing import Optional

@app.post("/login")
async def login(username: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")
    
    # 生成JWT token（有效期24小時）
    token = jwt.encode(
        {
            "user_id": user.id,
            "email": user.email,
            "exchange_uid": user.exchange_uid,
            "exp": datetime.utcnow() + timedelta(hours=24)
        },
        JWT_SECRET,
        algorithm="HS256"
    )
    
    return {
        "token": token,
        "user_id": user.id,
        "username": user.username,
        "exchange": user.exchange
    }

# 驗證token的依賴
def verify_token(token: str = Depends(HTTPBearer())):
    try:
        payload = jwt.decode(token.credentials, JWT_SECRET, algorithms=["HS256"])
        user_id: str = payload.get("user_id")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token已過期，請重新登入")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token無效")
```

***

## **第三步：加密API Key存儲**

用戶登入後輸入交易所API Key和Secret，系統加密存儲：

```python
# 後端：fastapi_backend/routes/credentials.py

from cryptography.fernet import Fernet
import os

# 讀取加密金鑰（存環境變數或AWS Secrets Manager）
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")  # 應該用aws秘密管理器
cipher_suite = Fernet(ENCRYPTION_KEY)

@app.post("/api-credentials")
async def store_api_credentials(
    api_key: str,
    api_secret: str,
    passphrase: Optional[str] = None,  # OKX需要
    current_user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == current_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    # 加密API Key和Secret
    api_key_encrypted = cipher_suite.encrypt(api_key.encode()).decode()
    api_secret_encrypted = cipher_suite.encrypt(api_secret.encode()).decode()
    
    # 刪除舊credentials（如有）
    db.query(APICredential).filter(
        APICredential.user_id == current_user_id
    ).delete()
    
    # 存新credentials
    credential = APICredential(
        user_id=current_user_id,
        api_key_encrypted=api_key_encrypted,
        api_secret_encrypted=api_secret_encrypted,
        passphrase_encrypted=cipher_suite.encrypt(passphrase.encode()).decode() if passphrase else None,
        exchange=user.exchange
    )
    db.add(credential)
    db.commit()
    
    return {"message": "API憑證已安全存儲"}

# 內部函數：給grid邏輯使用
def get_user_api_key(user_id: str, db: Session):
    """背景任務讀取已加密的API Key"""
    credential = db.query(APICredential).filter(
        APICredential.user_id == user_id
    ).first()
    if not credential:
        return None
    
    return {
        "api_key": cipher_suite.decrypt(credential.api_key_encrypted.encode()).decode(),
        "api_secret": cipher_suite.decrypt(credential.api_secret_encrypted.encode()).decode(),
        "passphrase": cipher_suite.decrypt(credential.passphrase_encrypted.encode()).decode() if credential.passphrase_encrypted else None,
        "exchange": credential.exchange
    }
```

***

## **第四步：網格工具與用戶隔離**

核心：**每個用戶的Python grid邏輯在獨立背景任務中運行，不會互相干擾**

```python
# 後端：fastapi_backend/grid_engine.py

from celery import Celery, Task
from celery_beat import schedule
import ccxt

app_celery = Celery('grid_trading')

@app_celery.task(bind=True)
def run_user_grid(user_id: str, grid_config: dict):
    """
    為特定用戶運行grid邏輯（獨立進程）
    grid_config = {
        'trading_pair': 'BTC/USDT',
        'lower_price': 40000,
        'upper_price': 50000,
        'grid_count': 10,
        'order_size': 0.01
    }
    """
    db = SessionLocal()
    
    try:
        # 1. 獲取用戶的加密API Key
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise Exception(f"用戶{user_id}不存在")
        
        api_creds = get_user_api_key(user_id, db)
        if not api_creds:
            raise Exception(f"用戶{user_id}未設置API憑證")
        
        # 2. 初始化交易所連接（每用戶獨立）
        exchange_class = getattr(ccxt, user.exchange)  # ccxt.okx, ccxt.bybit...
        exchange = exchange_class({
            'apiKey': api_creds['api_key'],
            'secret': api_creds['api_secret'],
            'password': api_creds.get('passphrase'),  # OKX用
            'enableRateLimit': True
        })
        
        # 3. 執行AS Grid邏輯（你的演算法）
        result = execute_as_grid(
            exchange=exchange,
            user_id=user_id,
            grid_config=grid_config
        )
        
        # 4. 存結果到資料庫（用戶專屬表格）
        grid_record = GridExecution(
            user_id=user_id,
            trading_pair=grid_config['trading_pair'],
            buy_orders=result['buy_count'],
            sell_orders=result['sell_count'],
            pnl=result['pnl'],
            executed_at=datetime.utcnow()
        )
        db.add(grid_record)
        db.commit()
        
        return {"status": "success", "user_id": user_id, "pnl": result['pnl']}
    
    except Exception as e:
        # 錯誤日誌（用戶隔離，不混淆）
        log_error(user_id, str(e))
        raise
    finally:
        db.close()

def execute_as_grid(exchange, user_id: str, grid_config: dict):
    """你的AS Grid演算法核心邏輯"""
    # 這裡放你Python gui版本的網格邏輯
    # 包括：多空對沖、FR偏向、GLFT庫存控制、領先指標UCB優化
    # 返回 {'buy_count', 'sell_count', 'pnl'...}
    pass
```

***

## **第五步：前端儀表板**

用戶登入後看到個人網格界面（React/Vue）：

```javascript
// frontend/src/pages/Dashboard.jsx

import React, { useEffect, useState } from 'react';
import axios from 'axios';

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [gridStatus, setGridStatus] = useState(null);
  const token = localStorage.getItem('auth_token');
  
  useEffect(() => {
    // 獲取用戶資訊
    axios.get('/api/user/me', {
      headers: { Authorization: `Bearer ${token}` }
    }).then(res => setUser(res.data));
    
    // 獲取用戶的grid執行歷史
    axios.get('/api/grid/status', {
      headers: { Authorization: `Bearer ${token}` }
    }).then(res => setGridStatus(res.data));
  }, []);
  
  const startGrid = async (config) => {
    await axios.post('/api/grid/start', config, {
      headers: { Authorization: `Bearer ${token}` }
    });
    alert('Grid已啟動');
  };
  
  return (
    <div className="dashboard">
      <h1>歡迎 {user?.username} 👋</h1>
      <p>交易所: {user?.exchange} | UID: {user?.exchange_uid}</p>
      
      <section className="grid-config">
        <h2>AS Grid 設置</h2>
        <input type="text" placeholder="交易對（如BTC/USDT）" />
        <input type="number" placeholder="下限價格" />
        <input type="number" placeholder="上限價格" />
        <input type="number" placeholder="網格數" />
        <button onClick={() => startGrid({...})}>啟動Grid</button>
      </section>
      
      <section className="grid-performance">
        <h2>今日績效</h2>
        {gridStatus && (
          <>
            <p>PnL: ${gridStatus.pnl}</p>
            <p>買單: {gridStatus.buy_count}</p>
            <p>賣單: {gridStatus.sell_count}</p>
            hart data={gridStatus.hourly_pnl} />
          </>
        )}
      </section>
      
      <div className="risk-warning">
        ⚠️ 本平台僅供工具使用，API被盜風險由用戶承擔。
        建議定期更換API Key。
      </div>
    </div>
  );
}
```

***

## **第六步：風險揭露實作**

```python
# 後端：fastapi_backend/routes/compliance.py

@app.get("/compliance/risk-disclaimer")
async def get_risk_disclaimer():
    """首頁和登入後都要展示"""
    return {
        "disclaimer": """
        【AS Grid 網格交易平台使用條款】
        
        1. 本平台為交易工具軟體，用戶自行決定交易對、金額與API連線。
        2. 不建議使用真實資金執行。建議先用測試資金或demo帳戶驗證。
        3. 不保證任何金融收益。過往績效不代表未來表現。
        4. API Key風險：用戶須自行保管API Key，定期更換（建議30-90天）。
           - 若API被盜，交易所可能執行未授權交易，造成資產損失。
           - 本平台採AES-256加密存儲，但用戶應啟用API白名單（Bybit/OKX）。
        5. 伺服器宕機風險：市場巨幅波動期間可能超時，自動停損可能失效。
        6. 網格被掃穿風險：單邊行情跌穿整個網格範圍，將持有虧損倉位。
        7. 資安聲明：本平台非金融機構，不受金管會直接監管。
           用戶應了解使用第三方API服務的風險。
        
        用戶點擊「我已讀且同意」表示理解上述風險。
        """
    }

class UserAgreement(Base):
    __tablename__ = "user_agreements"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    agreed_at = Column(DateTime, default=datetime.utcnow)
    agreement_version = Column(String)

@app.post("/compliance/agree")
async def agree_to_terms(
    current_user_id: str = Depends(verify_token),
    db: Session = Depends(get_db)
):
    # 記錄用戶同意時間和版本
    agreement = UserAgreement(
        user_id=current_user_id,
        agreement_version="1.0"
    )
    db.add(agreement)
    db.commit()
    return {"message": "已記錄同意"}
```

***

## **第七步：部署（Cloud Run）**

```bash
# 1. Dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

# 2. requirements.txt
fastapi==0.104.0
uvicorn==0.24.0
sqlalchemy==2.0.0
psycopg2-binary==2.9.0
cryptography==41.0.0
pyjwt==2.8.0
bcrypt==4.1.0
celery==5.3.0
ccxt==4.0.0

# 3. 部署到Google Cloud Run
gcloud run deploy grid-saas \
  --source . \
  --region asia-east1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars JWT_SECRET=xxx,ENCRYPTION_KEY=xxx
```

***

## **完整流程總結**

| 步驟 | 用戶操作 | 系統動作 | 資料結構 |
|------|--------|---------|---------|
| 1 | 進網站，輸入邀碼+帳密 | 驗證邀碼→綁UID→建User表 | `users.exchange_uid` |
| 2 | 點登入 | JWT驗證→發Token | `jwt.encode(user_id, exp)` |
| 3 | 輸入API Key | AES加密→存`api_credentials` | `credential.api_key_encrypted` |
| 4 | 設定交易對、參數 | 存到`grid_config` | 用戶專屬欄位 |
| 5 | 點「啟動Grid」 | Celery啟獨立任務 | 每用戶隔離進程 |
| 6 | 實時看Dashboard | 從DB拉該用戶PnL | React拉`/api/grid/status` |

***

## **關鍵優勢**

✅ **無需打包應用** - 純網頁即開即用  
✅ **用戶完全隔離** - 各自API Key、參數、執行進程  
✅ **合規** - 風險聲明強制同意，保護你  
✅ **免費邀碼模式** - 限定交易所（高返佣），低KYC  
✅ **可擴展** - Celery + Cloud Run應對千用戶  

準備好寫code了嗎？[memory updated: completed SaaS architecture design for grid trading platform]

[1](https://testdriven.io/blog/fastapi-jwt-auth/)
[2](https://blog.gitguardian.com/secrets-api-management/)
[3](https://coredevsltd.com/articles/5-best-ai-trading-bots-in-2025/)
[4](https://www.freecodecamp.org/news/how-to-add-jwt-authentication-in-fastapi/)
[5](https://www.serverion.com/uncategorized/checklist-for-secure-api-key-management/)
[6](https://www.biz4group.com/blog/how-to-create-an-ai-trading-bot)
[7](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/)
[8](https://www.tokenmetrics.com/blog/essential-security-practices-using-apis-exchange-keys)
[9](https://shamlatech.com/build-an-automated-ai-crypto-trading-bot/)
[10](https://www.youtube.com/watch?v=0A_GCXBCNUQ)