# 🔧 修復步驟：解決無法註冊/登入問題

## 問題診斷結果

Frontend 已成功部署到 `https://louisasgrid-web.zeabur.app/`，但 API 請求配置錯誤。

### 發現的錯誤

**錯誤的 API 請求 URL：**
```
https://louisasgrid-web.zeabur.app/VITE_AUTH_API_URL=https://louisasgrid.zeabur.app/api/v1/auth/register
```

**應該是：**
```
https://louisasgrid.zeabur.app/api/v1/auth/register
```

### 根本原因

1. **Frontend API 配置錯誤**：`api.js` 中的 `baseURL` 配置假設環境變數已包含 `/api/v1`，但實際上環境變數應該只包含域名
2. **CORS 域名不匹配**：Backend CORS 允許的域名是 `as-grid-frontend.zeabur.app`，但實際 frontend 部署在 `louisasgrid-web.zeabur.app`

---

## 已完成的修復

### 1. 修復 Frontend API 配置

#### 文件：[src/services/api.js](file:///Users/liutsungying/as網格/bitget_as/saas_frontend/src/services/api.js)

```diff
-  baseURL: import.meta.env.VITE_AUTH_API_URL || 'http://localhost:8000/api/v1',
+  // VITE_AUTH_API_URL should be just the domain (e.g., https://louisasgrid.zeabur.app)
+  baseURL: `${import.meta.env.VITE_AUTH_API_URL || 'http://localhost:8000'}/api/v1`,
```

**變更說明：**
- 現在代碼會自動在環境變數後面添加 `/api/v1`
- `VITE_AUTH_API_URL` 應該只包含域名：`https://louisasgrid.zeabur.app`

### 2. 更新 Backend CORS 配置

#### 文件：[auth_server/app/main.py](file:///Users/liutsungying/as網格/bitget_as/auth_server/app/main.py)

```diff
-    "https://as-grid-frontend.zeabur.app",  # Production frontend
+    "https://louisasgrid-web.zeabur.app",  # Production frontend (actual deployed URL)
```

**變更說明：**
- 更新為實際的 frontend 域名
- Backend 現在會接受來自正確域名的請求

---

## 📦 部署步驟（必須執行）

### 步驟 1：推送代碼到 GitHub

```bash
cd /Users/liutsungying/as網格/bitget_as

# 如果需要設置認證（使用 Personal Access Token）
git remote set-url origin https://YOUR_GITHUB_TOKEN@github.com/thankcoom/louis-as-grid.git

# 或使用 SSH（如果已配置）
git remote set-url origin git@github.com:thankcoom/louis-as-grid.git

# 推送更改
git push origin main
```

> [!IMPORTANT]
> **獲取 GitHub Personal Access Token**
>
> 如果您還沒有 token：
> 1. 前往 https://github.com/settings/tokens
> 2. 點擊 "Generate new token (classic)"
> 3. 選擇 `repo` 權限
> 4. 生成並複製 token
> 5. 在上述命令中替換 `YOUR_GITHUB_TOKEN`

### 步驟 2：在 Zeabur 重新部署 Frontend

由於修改了 `api.js`，需要重新構建 frontend：

1. 登入 [Zeabur Dashboard](https://dash.zeabur.com)
2. 找到 frontend service（部署在 `louisasgrid-web.zeabur.app`）
3. 點擊 **"Redeploy"** 或 **"重新部署"**
4. 等待構建完成（2-5 分鐘）

### 步驟 3：在 Zeabur 重新部署 Backend

由於更新了 CORS 配置：

1. 在 Zeabur Dashboard 找到 backend service（`louisasgrid.zeabur.app`）
2. 點擊 **"Redeploy"** 或 **"重新部署"**
3. 等待部署完成

### 步驟 4：驗證環境變數（重要！）

確認 frontend service 的環境變數設置正確：

1. 在 Zeabur 找到 frontend service
2. 進入 **"Environment Variables"** 或 **"環境變數"**
3. 確認 `VITE_AUTH_API_URL` 的值為：
   ```
   https://louisasgrid.zeabur.app
   ```
   
   **注意：沒有 `/api/v1`，只有域名！**

4. 如果值不正確，更新後需要重新部署 frontend

---

## ✅ 驗證步驟

完成所有部署後，測試註冊和登入：

### 1. 測試註冊

1. 訪問 https://louisasgrid-web.zeabur.app/register
2. 填寫註冊表單：
   - Email: `newuser@example.com`
   - Password: `test123456`
3. 點擊「建立帳號」

**預期結果：**
- [ ] 成功創建帳號
- [ ] 顯示「等待審核」或被重定向到下一頁
- [ ] **沒有**錯誤訊息

### 2. 檢查 Network 請求（開發者工具）

1. 按 F12 打開開發者工具
2. 切換到 **Network** 標籤
3. 嘗試註冊
4. 檢查請求：

**應該看到：**
- [ ] POST 請求到 `https://louisasgrid.zeabur.app/api/v1/auth/register`
- [ ] Status 200 或 201（成功）
- [ ] **沒有** CORS 錯誤
- [ ] **沒有** 405 錯誤
- [ ] **沒有** URL 中包含 "VITE_AUTH_API_URL" 的奇怪請求

### 3. 測試登入（如果有現有帳號）

如果您之前創建過管理員帳號：

1. 訪問 https://louisasgrid-web.zeabur.app/login
2. 使用管理員憑證登入
3. 應該成功登入並進入 Dashboard

---

## 🎯 快速檢查清單

- [ ] 代碼已推送到 GitHub
- [ ] Frontend 已重新部署
- [ ] Backend 已重新部署
- [ ] 環境變數 `VITE_AUTH_API_URL=https://louisasgrid.zeabur.app` 設置正確
- [ ] 註冊功能正常
- [ ] 登入功能正常
- [ ] 無 Console 錯誤

---

## ❓ 故障排除

### 問題：仍然無法註冊

1. **檢查 Network 請求 URL**
   - 打開 F12 → Network
   - 請求應該是 `https://louisasgrid.zeabur.app/api/v1/auth/register`
   - 如果還是錯誤的 URL，frontend 可能沒有重新部署

2. **檢查 CORS 錯誤**
   - Console 中如果看到 CORS 錯誤
   - Backend 可能沒有重新部署
   - 或 CORS origins 配置有誤

3. **檢查環境變數**
   - 在 Zeabur frontend service 中確認 `VITE_AUTH_API_URL`
   - 值應該是 `https://louisasgrid.zeabur.app`（沒有 `/api/v1`）
   - 更改環境變數後需要 Redeploy

### 問題：Console 顯示錯誤

打開瀏覽器 Console（F12 → Console），查看具體錯誤訊息，並告訴我錯誤內容。

---

## 📝 修改摘要

| 文件 | 更改 | 狀態 |
|------|------|------|
| `saas_frontend/src/services/api.js` | 修復 API baseURL 配置 | ✅ 已提交 |
| `auth_server/app/main.py` | 更新 CORS 域名 | ✅ 已提交 |

Commit: `fix: Correct API base URL configuration and update CORS for actual frontend domain`
