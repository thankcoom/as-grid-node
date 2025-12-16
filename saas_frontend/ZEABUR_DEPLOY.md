# 📦 Zeabur 前端部署指南

## 前置需求

- Zeabur 帳號
- GitHub repository 已連接到 Zeabur
- Backend (auth_server) 已部署並運行在 `https://louisasgrid.zeabur.app`

## 部署步驟

### 1. 在 Zeabur 創建新的 Service

1. 登入 [Zeabur Dashboard](https://dash.zeabur.com)
2. 選擇您的項目（與 `auth_server` 相同的項目）
3. 點擊 **"Add Service"** 或 **"Create Service"**
4. 選擇 **"Git Repository"**
5. 選擇您的 GitHub repository
6. 在 **Root Directory** 設置中，選擇 `bitget_as/saas_frontend`
   - 或者根據您的 repository 結構調整路徑

### 2. 配置 Service 設定

#### 基本設定
- **Service Name**: `as-grid-frontend` (或您偏好的名稱)
- **Branch**: `main` (或您使用的分支)
- **Build Command**: 自動檢測（Zeabur 會自動使用 Dockerfile）

#### 重要提示
Zeabur 應該會自動檢測到 `Dockerfile` 並使用它來構建應用。

### 3. 設置環境變數

在 Service 設定頁面，添加以下環境變數：

| 變數名稱 | 值 | 說明 |
|---------|-----|------|
| `VITE_AUTH_API_URL` | `https://louisasgrid.zeabur.app` | Backend API URL |

**重要：**
- 確保 URL 沒有尾隨的 `/`
- 這是 frontend 用來調用 backend API 的 URL

### 4. 部署

1. 點擊 **"Deploy"** 或 **"Redeploy"**
2. Zeabur 會開始構建和部署您的應用
3. 等待部署完成（通常需要 2-5 分鐘）

### 5. 獲取 Frontend URL

部署完成後：
1. Zeabur 會自動分配一個 URL，例如 `https://as-grid-frontend.zeabur.app`
2. 記下這個 URL，您將需要：
   - 訪問您的應用
   - 在 backend CORS 配置中使用

### 6. 驗證部署

訪問您的 frontend URL（例如 `https://as-grid-frontend.zeabur.app`）：

✅ **應該看到：**
- Landing page 正常顯示
- 可以導航到登入/註冊頁面
- 頁面樣式正確加載

❌ **不應該看到：**
- "Not Found" 錯誤
- 白屏
- 樣式損壞

### 7. 測試 API 連接

1. 打開瀏覽器開發者工具（F12）
2. 切換到 **Network** 標籤
3. 在 frontend 嘗試註冊或登入
4. 檢查 Network 請求：
   - ✅ 應該看到請求發送到 `https://louisasgrid.zeabur.app/api/v1/auth/...`
   - ✅ 狀態碼應該是 200（成功）或 4xx（預期的錯誤，例如無效憑證）
   - ❌ **不應該**看到 CORS 錯誤或 "Not Found"

## 故障排除

### 問題：部署失敗

**可能原因：**
- Dockerfile 路徑不正確
- 缺少 `nginx.conf` 文件

**解決方法：**
1. 確認 Zeabur 的 Root Directory 設置正確指向 `saas_frontend`
2. 檢查 repository 中是否包含所有必要文件：
   - `Dockerfile`
   - `nginx.conf`
   - `package.json`
   - `vite.config.js`

### 問題：頁面顯示但 API 請求失敗

**可能原因：**
- `VITE_AUTH_API_URL` 環境變數未設置或設置錯誤
- Backend CORS 未允許 frontend 域名

**解決方法：**
1. 檢查 Zeabur 環境變數設置
2. 確認 backend `main.py` 的 CORS origins 包含您的 frontend URL
3. Redeploy frontend（環境變數更改需要重新部署）

### 問題：CORS 錯誤

**錯誤訊息示例：**
```
Access to XMLHttpRequest at 'https://louisasgrid.zeabur.app/api/v1/auth/login' 
from origin 'https://as-grid-frontend.zeabur.app' has been blocked by CORS policy
```

**解決方法：**
1. 檢查 backend `app/main.py` 的 CORS 配置
2. 確保 `origins` 列表包含您的 frontend URL
3. Redeploy backend

### 問題：環境變數未生效

**症狀：**
- API 請求發送到錯誤的 URL（例如 `undefined/api/v1/auth/...`）

**解決方法：**
1. 環境變數必須以 `VITE_` 開頭才能在 Vite 應用中使用
2. 環境變數更改後，必須**重新構建**應用（Redeploy）
3. 檢查 `src/config/api.js` 是否正確使用環境變數：
   ```javascript
   const API_URL = import.meta.env.VITE_AUTH_API_URL || 'http://localhost:8000';
   ```

## 後續步驟

部署成功後，您可以：

1. **設置自定義域名**（可選）
   - 在 Zeabur Service 設定中添加自定義域名
   - 更新 DNS 記錄
   - 更新 backend CORS 配置以包含自定義域名

2. **啟用 HTTPS**（Zeabur 自動提供）
   - Zeabur 會自動為您的域名配置 SSL 證書

3. **配置 CI/CD**
   - Zeabur 會自動在您推送到 GitHub 時重新部署
   - 您可以在 Zeabur 設定中配置自動部署規則

## 驗證清單

在宣布部署成功之前，請確認：

- [ ] Frontend 可以從公網訪問
- [ ] Landing page 正常顯示
- [ ] 可以導航到登入/註冊頁面
- [ ] 表單可以正常提交
- [ ] API 請求成功發送到 backend
- [ ] 無 CORS 錯誤
- [ ] 可以成功創建用戶並接收回應
- [ ] 瀏覽器控制台無錯誤訊息

## 需要幫助？

如果遇到問題：
1. 檢查 Zeabur 部署日誌
2. 檢查瀏覽器控制台錯誤
3. 檢查 Network 標籤的請求詳情
4. 參考本文檔的故障排除部分
