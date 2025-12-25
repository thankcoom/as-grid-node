# 系統診斷與根本原因分析報告 (RCA)

**日期**: 2025-12-23
**狀態**: 🔴 系統暫停 (等待部署與遷移)

---

## 1. 產品經理 (PM) 視角：用戶體驗與功能阻礙

**問題現狀**：用戶無法執行交易，且儀表板顯示資訊錯誤。

- **核心問題**：
    1. **信任度喪失**：儀表板顯示 USDC $99.69，但用戶持有的是 USDT。這種數據錯誤會讓用戶不敢開啟交易。
    2. **流程斷點**：管理員帳號是 "後門" 建立的，跳過了正常的 API 綁定流程，導致系統認為 "沒有憑證"，無法啟動機器人。
    3. **回測不可用**：雖然按鈕存在，但因為底層數據獲取邏輯有誤（已修復但未部署），導致無法產出結果。

**PM 結論**：目前的產品處於 "開發完成但配置錯誤" 的狀態。功能代碼都在，但因為數據流（API Key -> DB -> Node）中斷，導致前端看起來像壞掉一樣。

---

## 2. 測試經理 (QA) 視角：缺陷與驗證

**已識別缺陷 (Bugs)**：

| 嚴重度 | 問題描述 | 狀態 | 根本原因 |
|-------|---------|------|---------|
| 🔴 Critical | **餘額顯示錯誤** | 🛠 代碼已修 (待部署) | Node 返回了合併後的 `equity`，沒有區分 USDT/USDC。Dashboard 只能顯示到預設欄位。 |
| 🔴 Critical | **無法啟動交易** | 🔍 數據缺失 | 資料庫 `api_credentials` 表為空。用戶跳過 SetupAPI 流程。 |
| 🟡 Major | **回測報錯** | ✅ 已修復 | Bitget API `fetch_ohlcv` 的 `limit` 參數設為 1500，超過上限 1000。 |
| 🔴 Critical | **資料庫 schema 不匹配** | ⏳ 等待遷移 | 代碼新增了 `usdt_equity` 欄位，但資料庫表結構尚未更新，會導致 500 Error。 |

**QA 結論**：目前的測試阻塞點在於 **環境不一致**。代碼已經修復了邏輯，但運行環境（Zeabur）的資料庫結構落後於代碼版本。

---

## 3. 流程部門 (Process/DevOps) 視角：部署與維運

**為什麼現在不能執行？**

我們違反了標準的 CI/CD 流程中的幾個關鍵點：

1. **手動流程風險**：
    - 使用 `create_admin.py` 腳本建立帳號，而非通過標準註冊流程。這導致該帳號處於 "半初始化" 狀態（有 User 記錄但無 API Credential 記錄）。
    
2. **資料庫遷移策略缺失**：
    - 我們修改了 `models.py` (新增 USDT/USDC 欄位)，但沒有自動化的 Migration 腳本 (如 Alembic)。
    - **後果**：新代碼部署上去後，寫入資料庫時會因為 "找不到欄位" 而崩潰。

3. **版本同步問題**：
    - Grid Node 和 Auth Server 必須同時更新。如果只更新一邊，心跳數據結構不匹配會導致通訊失敗。

---

## 🚑 立即修復行動計劃

為了讓系統恢復 "可執行" 狀態，必須依序執行以下步驟：

### Step 1: 資料庫遷移 (Process 部門)
在 Zeabur 的 PostgreSQL 執行 SQL 以匹配新代碼：
```sql
ALTER TABLE node_status ADD COLUMN usdt_equity FLOAT DEFAULT 0.0;
ALTER TABLE node_status ADD COLUMN usdt_available FLOAT DEFAULT 0.0;
ALTER TABLE node_status ADD COLUMN usdc_equity FLOAT DEFAULT 0.0;
ALTER TABLE node_status ADD COLUMN usdc_available FLOAT DEFAULT 0.0;
```

### Step 2: 重新部署 (DevOps)
1. 確保所有 Git commit 已推送 (已完成)。
2. 在 Zeabur 上 Redeploy **Auth Server**。
3. 在 Zeabur 上 Redeploy **Grid Node**。

### Step 3: 補充數據 (User/PM)
1. 登入 SaaS 前端。
2. 進入 **Settings** 頁面。
3. 執行 **更換 API** 流程，輸入 Bitget API Key。這會修正 "數據缺失" 的問題。

---

**總結**：系統不能執行的原因不是單一的代碼錯誤，而是 **代碼變更** 與 **資料庫狀態** 及 **用戶數據** 三者脫節。執行上述三步後，系統將恢復正常。
