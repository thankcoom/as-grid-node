"""
AuthClient - 與官方服務通訊的客戶端

負責：
1. 啟動時註冊並獲取 API 憑證
2. 定期心跳回報狀態
3. 獲取並執行遠端命令
"""
import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Optional, Callable
import aiohttp

logger = logging.getLogger(__name__)


class AuthClient:
    """與官方 Auth Server 通訊的客戶端"""

    def __init__(
        self,
        auth_server_url: str = None,
        bitget_uid: str = None,
        node_secret: str = None,
        heartbeat_interval: int = 30
    ):
        """
        初始化 AuthClient

        Args:
            auth_server_url: 官方伺服器 URL (從環境變數讀取)
            bitget_uid: Bitget Exchange UID (從環境變數讀取)
            node_secret: Node 密鑰 (從環境變數讀取)
            heartbeat_interval: 心跳間隔（秒）
        """
        self.auth_server_url = auth_server_url or os.getenv("AUTH_SERVER_URL", "")
        self.bitget_uid = bitget_uid or os.getenv("BITGET_UID", "")
        self.node_secret = node_secret or os.getenv("NODE_SECRET", "")
        self.heartbeat_interval = heartbeat_interval

        # ═══════════════════════════════════════════════════════════════════
        # 【混合式安全設計】API 憑證從環境變數讀取，不從 Server 獲取
        #
        # 用戶需要在 Zeabur 環境變數中設定：
        # - BITGET_API_KEY
        # - BITGET_API_SECRET
        # - BITGET_PASSPHRASE
        # ═══════════════════════════════════════════════════════════════════
        self.api_key = os.getenv("BITGET_API_KEY", "")
        self.api_secret = os.getenv("BITGET_API_SECRET", "")
        self.passphrase = os.getenv("BITGET_PASSPHRASE", "")

        self.jwt_token: Optional[str] = None
        self.is_registered = False
        self.current_uid: Optional[str] = None  # UID verified from exchange
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._status_callback: Optional[Callable] = None
        self._session: Optional[aiohttp.ClientSession] = None

        # 白名單快取 (用於交易時 UID 驗證)
        self._whitelist_valid: Optional[bool] = None
        self._whitelist_cache_time: Optional[datetime] = None
        self._whitelist_cache_ttl: int = 300  # 5 分鐘
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """獲取或創建 HTTP session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session
    
    async def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
        """發送 HTTP 請求到 Auth Server"""
        session = await self._get_session()
        url = f"{self.auth_server_url}/api/v1{endpoint}"
        
        headers = {"Content-Type": "application/json"}
        if self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        
        try:
            async with session.request(method, url, json=data, headers=headers) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    error_text = await resp.text()
                    logger.error(f"API error {resp.status}: {error_text}")
                    return {"error": error_text, "status": resp.status}
        except asyncio.TimeoutError:
            logger.warning(f"Request timeout: {endpoint}")
            return {"error": "timeout"}
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return {"error": str(e)}
    
    async def register(self) -> Optional[dict]:
        """
        向官方伺服器註冊 Node，驗證白名單狀態

        使用 BITGET_UID 識別用戶

        Returns:
            成功時返回 API 憑證字典 (從環境變數讀取)，失敗返回 None
        """
        # ═══════════════════════════════════════════════════════════════════
        # 【混合式安全設計】檢查本地 API 憑證
        # ═══════════════════════════════════════════════════════════════════
        if not self.api_key or not self.api_secret:
            logger.error(
                "BITGET_API_KEY or BITGET_API_SECRET not configured! "
                "Please set these environment variables in Zeabur."
            )
            return None

        if not self.auth_server_url:
            logger.warning("AUTH_SERVER_URL not configured, running in standalone mode")
            # Standalone 模式：直接返回環境變數中的憑證
            return {
                "api_key": self.api_key,
                "api_secret": self.api_secret,
                "passphrase": self.passphrase
            }

        if not self.bitget_uid:
            logger.warning("BITGET_UID not configured, running in standalone mode")
            return {
                "api_key": self.api_key,
                "api_secret": self.api_secret,
                "passphrase": self.passphrase
            }

        logger.info(f"Registering with Auth Server: {self.auth_server_url}")
        logger.info(f"Using Bitget UID: {self.bitget_uid}")

        result = await self._request("POST", "/node/register", {
            "bitget_uid": self.bitget_uid,
            "node_secret": self.node_secret,
            "node_version": "1.0.0"
        })

        if "error" in result:
            logger.error(f"Registration failed: {result['error']}")
            # 註冊失敗可能是白名單問題，不返回憑證
            return None

        self.jwt_token = result.get("token")
        self.is_registered = True

        logger.info("Successfully registered with Auth Server")

        # 【混合式安全設計】返回本地環境變數中的憑證，不從 Server 獲取
        return {
            "api_key": self.api_key,
            "api_secret": self.api_secret,
            "passphrase": self.passphrase
        }
    
    async def heartbeat(self, status: dict) -> dict:
        """
        發送心跳回報當前狀態
        
        Args:
            status: 狀態字典，包含 running, pnl, positions 等
            
        Returns:
            伺服器回應（可能包含待執行命令）
        """
        if not self.is_registered:
            return {}
        
        result = await self._request("POST", "/node/heartbeat", {
            "status": status.get("status", "unknown"),
            "is_trading": status.get("is_trading", False),
            "total_pnl": status.get("total_pnl", 0),
            "unrealized_pnl": status.get("unrealized_pnl", 0),
            "equity": status.get("equity", 0),
            "available_balance": status.get("available_balance", 0),
            # 分離的 USDT/USDC 餘額
            "usdt_equity": status.get("usdt_equity", 0),
            "usdt_available": status.get("usdt_available", 0),
            "usdc_equity": status.get("usdc_equity", 0),
            "usdc_available": status.get("usdc_available", 0),
            "positions": status.get("positions", []),
            "symbols": status.get("symbols", []),
            "timestamp": datetime.utcnow().isoformat(),
            # Anti-Bait-and-Switch: 報告當前 API Key 的實際 UID
            "current_uid": self.current_uid or self.bitget_uid
        })
        
        return result
    
    async def report_trade(self, trade: dict) -> dict:
        """
        回報成交事件
        
        Args:
            trade: 交易資訊 {symbol, side, price, quantity, pnl}
        """
        if not self.is_registered:
            return {}
        
        return await self._request("POST", "/node/trade", trade)
    
    async def get_commands(self) -> list:
        """
        獲取待執行的遠端命令
        
        Returns:
            命令列表 [{action: "start"|"stop"|"update_config", params: {...}}]
        """
        if not self.is_registered:
            return []
        
        result = await self._request("GET", "/node/commands")
        return result.get("commands", [])
    
    def set_status_callback(self, callback: Callable):
        """設定狀態回調函數（由 BotManager 調用獲取當前狀態）"""
        self._status_callback = callback
    
    async def start_heartbeat(self):
        """啟動心跳定時器"""
        if self._heartbeat_task:
            return
        
        async def heartbeat_loop():
            while True:
                try:
                    # 獲取當前狀態
                    status = {}
                    if self._status_callback:
                        status = self._status_callback()
                    
                    # 發送心跳
                    response = await self.heartbeat(status)
                    
                    # 處理命令（如果有）
                    commands = response.get("commands", [])
                    for cmd in commands:
                        await self._handle_command(cmd)
                    
                except Exception as e:
                    logger.error(f"Heartbeat error: {e}")
                
                await asyncio.sleep(self.heartbeat_interval)
        
        self._heartbeat_task = asyncio.create_task(heartbeat_loop())
        logger.info(f"Heartbeat started (interval: {self.heartbeat_interval}s)")
    
    async def stop_heartbeat(self):
        """停止心跳定時器"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            self._heartbeat_task = None
            logger.info("Heartbeat stopped")
    
    async def _handle_command(self, cmd: dict):
        """處理遠端命令"""
        action = cmd.get("action")
        params = cmd.get("params", {})
        
        logger.info(f"Received command: {action}")
        
        # 命令處理由 BotManager 實現
        # 這裡只是記錄，實際執行由上層處理
    
    # ═══════════════════════════════════════════════════════════════════════
    # 【交易時 UID 驗證】白名單檢查方法
    # ═══════════════════════════════════════════════════════════════════════

    async def check_whitelist(self, force: bool = False) -> bool:
        """
        檢查當前 UID 是否在白名單中

        使用本地快取，減少 Server 請求頻率

        Args:
            force: 是否強制刷新快取

        Returns:
            True = 在白名單中，允許交易
            False = 不在白名單中，禁止交易
        """
        # 檢查快取是否有效
        if not force and self._whitelist_valid is not None:
            if self._whitelist_cache_time:
                cache_age = (datetime.utcnow() - self._whitelist_cache_time).total_seconds()
                if cache_age < self._whitelist_cache_ttl:
                    return self._whitelist_valid

        # Standalone 模式：直接允許
        if not self.auth_server_url or not self.bitget_uid:
            return True

        # 向 Server 查詢白名單狀態
        try:
            result = await self._request("GET", f"/whitelist/check?uid={self.bitget_uid}")

            if "error" in result:
                # 網路錯誤：使用上次快取結果 (寬容模式)
                if self._whitelist_valid is not None:
                    logger.warning(f"Whitelist check failed, using cached result: {result['error']}")
                    return self._whitelist_valid
                # 無快取時，默認拒絕
                logger.error(f"Whitelist check failed and no cache: {result['error']}")
                return False

            is_valid = result.get("valid", False)
            warning_hours = result.get("warning_hours_remaining")

            # 更新快取
            self._whitelist_valid = is_valid
            self._whitelist_cache_time = datetime.utcnow()

            # 記錄警告狀態
            if warning_hours is not None and warning_hours > 0:
                logger.warning(
                    f"⚠️ WHITELIST WARNING: UID {self.bitget_uid} will be blocked in {warning_hours:.1f} hours!"
                )

            return is_valid

        except Exception as e:
            logger.error(f"Whitelist check exception: {e}")
            # 異常時使用快取
            if self._whitelist_valid is not None:
                return self._whitelist_valid
            return False

    def is_whitelist_valid(self) -> bool:
        """
        同步檢查白名單快取狀態 (用於快速判斷)

        Returns:
            True = 快取有效且在白名單中
            False = 快取無效或不在白名單中
        """
        if self._whitelist_valid is None:
            return True  # 首次檢查前默認允許

        if self._whitelist_cache_time:
            cache_age = (datetime.utcnow() - self._whitelist_cache_time).total_seconds()
            if cache_age >= self._whitelist_cache_ttl:
                return True  # 快取過期，需要重新檢查，暫時允許

        return self._whitelist_valid

    async def close(self):
        """關閉連接"""
        await self.stop_heartbeat()
        if self._session and not self._session.closed:
            await self._session.close()


# 全局實例（可選）
auth_client: Optional[AuthClient] = None


def get_auth_client() -> AuthClient:
    """獲取全局 AuthClient 實例"""
    global auth_client
    if auth_client is None:
        auth_client = AuthClient()
    return auth_client
