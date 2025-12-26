# Bug 修復日誌

> 記錄系統開發過程中發現並解決的問題

---

## 2025-12-26 修復紀錄

### 1. WebSocket 連接失敗

**問題**：`module 'ccxt.async_support' has no attribute 'websockets'`

**原因**：新版 ccxt 已移除 `websockets` 子模組，需使用原生 `websockets` 庫

**修復**：

| 檔案 | 修復內容 |
|-----|---------|
| [bot.py](file:///Users/liutsungying/as網格/bitget_as/trading_core/bot.py) | 新增 `import websockets` |
| [bot.py](file:///Users/liutsungying/as網格/bitget_as/trading_core/bot.py) | 將 `ccxt_async.websockets.connect` 改為 `websockets.connect` |

---

### 2. SymbolState 缺少均價屬性

**問題**：`'SymbolState' object has no attribute 'long_avg_price'`

**原因**：`SymbolState` 類別未定義 `long_avg_price` 和 `short_avg_price` 屬性，但 `bot_manager.py` 心跳回報時需要使用

**修復**：

| 檔案 | 修復內容 |
|-----|---------|
| [models.py](file:///Users/liutsungying/as網格/bitget_as/trading_core/models.py) | 新增 `long_avg_price: float = 0` |
| [models.py](file:///Users/liutsungying/as網格/bitget_as/trading_core/models.py) | 新增 `short_avg_price: float = 0` |

---

### 3. 選幣 API 方法不存在

**問題**：`'SymbolScanner' object has no attribute 'scan_usdc_symbols'`

**原因**：`SymbolScanner` 實際使用 `scan_with_amplitude` 方法，而非 `scan_usdc_symbols`

**修復**：

| 檔案 | 修復內容 |
|-----|---------|
| [coin.py](file:///Users/liutsungying/as網格/bitget_as/grid_node/app/api/coin.py) | 改用 `scan_with_amplitude(exchange, quote_currency='USDC')` |

---

## 2025-12-18 修復紀錄

### 1. BotManager 使用錯誤的用戶識別碼參數

**問題**：Grid Node 啟動時報錯 `TypeError: AuthClient.__init__() got an unexpected keyword argument 'user_id'`

**原因**：`AuthClient` 已重構為使用 `bitget_uid`，但 `BotManager._init_auth_client()` 仍使用舊的 `user_id` 參數

**修復**：

| 檔案 | 行號 | 修復前 | 修復後 |
|-----|-----|-------|-------|
| [bot_manager.py](file:///Users/liutsungying/as網格/bitget_as/grid_node/app/services/bot_manager.py) | 38-45 | `os.getenv("USER_ID")` | `os.getenv("BITGET_UID")` |
| [bot_manager.py](file:///Users/liutsungying/as網格/bitget_as/grid_node/app/services/bot_manager.py) | 41 | `user_id=user_id` | `bitget_uid=bitget_uid` |

---

### 2. Zeabur 模板 Icon 無法顯示

**問題**：Zeabur 模板頁面的 icon 顯示為破圖

**原因**：`template.yaml` 使用錯誤的 icon URL

**修復**：

| 檔案 | 修復前 | 修復後 |
|-----|-------|-------|
| [template.yaml](file:///Users/liutsungying/as網格/bitget_as/grid_node/template.yaml) | `.../marketplace/umami.svg` | `https://louisasgrid-web.zeabur.app/logo.png` |

---

### 3. Zeabur 模板使用錯誤的環境變數

**問題**：`zeabur.json` 仍使用 `USER_ID` 而非 `BITGET_UID`

**修復**：

| 檔案 | 行號 | 修復前 | 修復後 |
|-----|-----|-------|-------|
| [zeabur.json](file:///Users/liutsungying/as網格/bitget_as/grid_node/zeabur.json) | 11-14 | `USER_ID` | `BITGET_UID` |

---

### 4. 回測 API limit 參數超出範圍

**問題**：回測下載歷史數據時報錯 `"limit should be between (0, 1000]"`

**原因**：`fetch_ohlcv` 的 `limit=1500` 超出 Bitget API 限制

**修復**：

| 檔案 | 行號 | 修復前 | 修復後 |
|-----|-----|-------|-------|
| [backtest.py](file:///Users/liutsungying/as網格/bitget_as/grid_node/trading_core/backtest.py) | 114 | `limit=1500` | `limit=1000` |

---

### 5. SetupAPI 頁面安全說明文案錯誤

**問題**：UI 顯示「不會儲存您的憑證」，但實際上系統會加密儲存

**修復**：

| 檔案 | 語言 | 修復前 | 修復後 |
|-----|-----|-------|-------|
| [I18nContext.jsx](file:///Users/liutsungying/as網格/bitget_as/saas_frontend/src/context/I18nContext.jsx) | EN (L299) | "Credentials are not stored" | "Your credentials are encrypted and securely stored" |
| [I18nContext.jsx](file:///Users/liutsungying/as網格/bitget_as/saas_frontend/src/context/I18nContext.jsx) | ZH (L601) | "不會儲存您的憑證" | "您的憑證將加密儲存，供交易節點安全使用" |

---

### 6. 管理員帳號 API 憑證未儲存（診斷結果）

**問題**：Dashboard 顯示 $0.00 餘額，Node 以 `standalone` 模式運行

**診斷**：

```sql
-- 查詢結果
cred_id = NULL  -- API 憑證未儲存
```

**根本原因**：管理員帳號是用 `create_admin.py` 直接建立，跳過了 SetupAPI 流程

**解決方案**：在 Settings 頁面使用「更換 API」功能輸入憑證

---

## 新增功能

### 管理員診斷端點

**檔案**：[admin.py](file:///Users/liutsungying/as網格/bitget_as/auth_server/app/api/api_v1/endpoints/admin.py)

**端點**：`GET /admin/diagnostic/{uid}`

**功能**：檢查指定 UID 的用戶是否存在、是否有憑證儲存、解密是否成功

---

## Git Commits

| 時間 | Commit | 說明 |
|-----|--------|-----|
| 2025-12-18 16:27 | `df4e5c3` | fix: update icon URLs and use BITGET_UID instead of USER_ID |
| 2025-12-18 16:27 | `61a8c98` | fix: use correct domain for icon URLs |
| 2025-12-18 16:47 | `7a3e65a` | feat: add diagnostic endpoint for checking user credentials status |
| 2025-12-18 17:00 | `721d6b6` | fix: change fetch_ohlcv limit from 1500 to 1000 |
| 2025-12-18 17:06 | `a513392` | fix: update security note to accurately reflect credentials ARE stored |
