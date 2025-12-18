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
        
        self.jwt_token: Optional[str] = None
        self.is_registered = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._status_callback: Optional[Callable] = None
        self._session: Optional[aiohttp.ClientSession] = None
        
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
        向官方伺服器註冊 Node，獲取 API 憑證
        
        使用 BITGET_UID 識別用戶
        
        Returns:
            成功時返回 API 憑證字典，失敗返回 None
        """
        if not self.auth_server_url:
            logger.warning("AUTH_SERVER_URL not configured, running in standalone mode")
            return None
        
        if not self.bitget_uid:
            logger.warning("BITGET_UID not configured, running in standalone mode")
            return None
        
        logger.info(f"Registering with Auth Server: {self.auth_server_url}")
        logger.info(f"Using Bitget UID: {self.bitget_uid}")
        
        result = await self._request("POST", "/node/register", {
            "bitget_uid": self.bitget_uid,
            "node_secret": self.node_secret,
            "node_version": "1.0.0"
        })
        
        if "error" in result:
            logger.error(f"Registration failed: {result['error']}")
            return None
        
        self.jwt_token = result.get("token")
        self.is_registered = True
        
        logger.info("Successfully registered with Auth Server")
        
        # 返回 API 憑證（從官方解密獲取）
        return result.get("credentials")
    
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
            "timestamp": datetime.utcnow().isoformat()
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
