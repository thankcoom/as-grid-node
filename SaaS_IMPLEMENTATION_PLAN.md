# AS Grid x Zeabur SaaS 實施與架構藍圖

此文檔定義了 AS Grid 的最終系統架構：**混合式 SaaS (Hybrid SaaS)**。
結合官方集中式管理與用戶自託管 (BYOC - Bring Your Own Cloud) 執行節點，實現資安隔離與算力分散。

## 1. 系統架構全貌 (System Architecture)

系統分為兩個完全獨立的運行環境：

### A. 官方營運環境 (Official / Central)
由我們（官方）部署與維護，負責用戶管理與授權。

*   **Auth Server (驗證中心)**:
    *   **職責**: 處理註冊、登入、UID 白名單驗證、記錄用戶的節點網址。
    *   **資料庫**: 儲存 User Profile (Email, Zeabur URL, Whitelist Status)。
    *   **限制**: **絕不接觸** 用戶的 API Key 或交易策略參數。
*   **SaaS Frontend (官網前端)**:
    *   **職責**: 用戶操作介面 (Dashboard)。
    *   **特性**: 具備「雙向連線」能力。登入時連線 Auth Server；交易操作時連線用戶的 Grid Node。

### B. 用戶執行環境 (User / Edge)
由用戶通過 Zeabur 一鍵部署，運行在用戶的雲端帳號上。

*   **Grid Node (交易節點)**:
    *   **職責**: 執行網格策略、回測運算、AI 選幣。
    *   **核心**: 包含完整的 `trading_core` (MaxGridBot)。
    *   **資安**:
        *   API Key 儲存於該節點的環境變數 (Env Vars)，外部無法存取。
        *   透過 `NODE_SECRET` 驗證來自前端的指令。

## 2. 用戶操作流程 (User Journey)

### 階段一：資格取得
### 階段一：資格取得 (UID Whitelist)
1.  **註冊**: 用戶透過官方推薦連結註冊 Bitget 帳號。
2.  **驗證**:
    *   用戶登入系統，輸入 Bitget API Key 進行驗證。
    *   系統獲取 UID 並檢查是否在 **UID 白名單** 中。
    *   若在白名單內，自動開通使用權限；否則進入審核隊列。
3.  **登入**: 用戶登入官網 Dashboard。

### 階段二：節點部署 (Zeabur Integration)
1.  **引導**: 登入後，若系統檢測到用戶尚未綁定節點，顯示「部署引導頁面」。
2.  **一鍵部署**:
    *   用戶點擊「Deploy to Zeabur」按鈕。
    *   跳轉至 Zeabur，自動帶入 Git Template。
3.  **配置**: 用戶在 Zeabur 填入：
    *   `NODE_SECRET`: 自訂連線密碼。
    *   `EXCHANGE_API_KEY`: 交易所 API Key。
    *   `EXCHANGE_SECRET`: 交易所 Secret。
4.  **上線**: 部署完成，Zeabur 提供網址 (如 `https://user-node.zeabur.app`)。

### 階段三：綁定與交易
1.  **綁定**:
    *   用戶回到官網「設定」頁面。
    *   填入 `Node URL` 與 `NODE_SECRET`。
    *   前端測試連線成功後，將 `Node URL` 存回官方 Auth Server (方便跨裝置同步)。
    *   `NODE_SECRET` 僅儲存於用戶瀏覽器 (localStorage)，確保零知識 (Zero-Knowledge) 安全。
2.  **交易**:
    *   用戶在 Dashboard 點擊「啟動網格」。
    *   前端直接發送 API 請求至 `Node URL`。
    *   Grid Node 收到請求，開始執行交易。

## 3. 專案目錄結構 (Project Structure)

```text
bitget_as/
├── auth_server/            # [官方] 驗證中心 (FastAPI)
│   ├── app/
│   │   ├── api/            # Auth, Users API
│   │   ├── db/             # User, InviteCode Models
│   │   └── main.py
│   └── Dockerfile
├── grid_node/              # [用戶] 執行節點 (FastAPI + Trading Core)
│   ├── app/                # Grid, Backtest API
│   ├── trading_core/       # 核心交易邏輯 (共用)
│   ├── coin_selection/     # 選幣模組
│   └── Dockerfile
├── saas_frontend/          # [官方] 前端介面 (React)
│   ├── src/
│   │   ├── services/       # api.js (連 Auth), nodeApi.js (連 Node)
│   │   └── pages/          # Login, Dashboard, Settings
│   └── Dockerfile
└── deploy/
    └── zeabur.json         # Zeabur 部署模板設定
```

## 4. 開發進度與狀態 (Status)

| 階段 | 任務 | 狀態 | 說明 |
| :--- | :--- | :--- | :--- |
| **Phase 1** | **核心封裝** | ✅ 完成 | `grid_node` 已獨立封裝，包含交易核心。 |
| **Phase 2** | **驗證中心** | ✅ 完成 | `auth_server` 已建立，含 UID 白名單驗證邏輯。 |
| **Phase 3** | **前端整合** | ✅ 完成 | 前端支援動態切換連線 (Direct Connect)。 |
| **Phase 4** | **部署準備** | ✅ 完成 | `zeabur.json` 與 Dockerfile 已備妥。 |
| **Phase 5** | **本地模擬** | ✅ 完成 | `docker-compose` 可同時模擬三方角色進行測試。 |

## 5. 部署指引 (Deployment Guide)

### 官方營運部署
1.  將 `auth_server` 與 `saas_frontend` 部署至您的伺服器 (或 Zeabur)。
2.  設定環境變數 (`DATABASE_URL`, `SECRET_KEY`)。
3.  初始化資料庫並設定第一批白名單 UID。

### 用戶節點發布
1.  建立一個新的 Git Repository。
2.  將 `grid_node` 資料夾內容 (含 Dockerfile) 推送至該 Repo。
3.  在 Zeabur 建立 Template 連結，指向該 Repo。
4.  將 Template 連結更新至 `saas_frontend` 的 Dashboard 頁面。
