"""
BotManager - 交易機器人管理器

整合：
1. MaxGridBot 交易核心
2. AuthClient 心跳回報
3. 遠端命令執行
"""
import asyncio
import os
import logging
from typing import Optional, Dict, Any
from trading_core.bot import MaxGridBot
from trading_core.models import GlobalConfig, SymbolConfig
from .auth_client import AuthClient

logger = logging.getLogger(__name__)


class BotManager:
    """交易機器人管理器 - 整合交易核心與官方通訊"""
    
    def __init__(self):
        self.bot: Optional[MaxGridBot] = None
        self.task: Optional[asyncio.Task] = None
        self.auth_client: Optional[AuthClient] = None
        self.is_trading = False
        self._config: Optional[GlobalConfig] = None
        
        # 初始化 AuthClient（如果配置了官方伺服器）
        self._init_auth_client()
    
    def _init_auth_client(self):
        """初始化 AuthClient"""
        auth_server_url = os.getenv("AUTH_SERVER_URL")
        user_id = os.getenv("USER_ID")
        
        if auth_server_url and user_id:
            self.auth_client = AuthClient(
                auth_server_url=auth_server_url,
                user_id=user_id,
                node_secret=os.getenv("NODE_SECRET", ""),
                heartbeat_interval=30
            )
            # 設定狀態回調
            self.auth_client.set_status_callback(self._get_heartbeat_status)
            logger.info("AuthClient initialized for official server communication")
        else:
            logger.info("Running in standalone mode (no AUTH_SERVER_URL)")
    
    async def initialize(self) -> Dict[str, Any]:
        """
        初始化 Node，向官方註冊並獲取 API 憑證
        
        Returns:
            初始化結果
        """
        result = {"mode": "standalone"}
        
        if self.auth_client:
            credentials = await self.auth_client.register()
            if credentials:
                # 使用從官方獲取的 API 憑證
                os.environ["EXCHANGE_API_KEY"] = credentials.get("api_key", "")
                os.environ["EXCHANGE_SECRET"] = credentials.get("api_secret", "")
                os.environ["EXCHANGE_PASSPHRASE"] = credentials.get("passphrase", "")
                result["mode"] = "connected"
                result["message"] = "Connected to official server"
                
                # 啟動心跳
                await self.auth_client.start_heartbeat()
            else:
                result["message"] = "Failed to connect, running standalone"
        
        return result
    
    def _get_heartbeat_status(self) -> Dict[str, Any]:
        """獲取心跳狀態（供 AuthClient 調用）"""
        if not self.bot:
            return {
                "status": "stopped",
                "is_trading": False,
                "total_pnl": 0,
                "unrealized_pnl": 0,
                "equity": 0,
                "positions": [],
                "symbols": []
            }
        
        state = self.bot.state
        positions = []
        symbols = []
        
        for sym_state in state.symbols.values():
            positions.append({
                "symbol": sym_state.symbol,
                "long": sym_state.long_position,
                "short": sym_state.short_position,
                "long_avg_price": sym_state.long_avg_price,
                "short_avg_price": sym_state.short_avg_price,
                "unrealized_pnl": getattr(sym_state, 'unrealized_pnl', 0)
            })
            symbols.append(sym_state.symbol)
        
        # 計算總權益
        equity = 0
        for acc in state.accounts.values():
            equity += getattr(acc, 'equity', 0)
        
        return {
            "status": "running" if state.running else "stopped",
            "is_trading": self.is_trading,
            "total_pnl": state.total_profit,
            "unrealized_pnl": sum(p.get("unrealized_pnl", 0) for p in positions),
            "equity": equity,
            "positions": positions,
            "symbols": symbols
        }

    def start(self, symbol: str, quantity: float) -> Dict[str, str]:
        """啟動交易"""
        if self.bot and self.bot.state.running:
            raise ValueError("Bot is already running")

        api_key = os.getenv("EXCHANGE_API_KEY")
        api_secret = os.getenv("EXCHANGE_SECRET")
        passphrase = os.getenv("EXCHANGE_PASSPHRASE")

        if not api_key or not api_secret:
            raise ValueError("API Keys not found in environment variables")

        config = GlobalConfig()
        config.api_key = api_key
        config.api_secret = api_secret
        config.passphrase = passphrase
        config.symbols.clear()
        
        coin = symbol.replace("USDT", "").replace("USDC", "")
        
        # 判斷合約類型
        if "USDC" in symbol:
            ccxt_symbol = f"{coin}/USDC:USDC"
        else:
            ccxt_symbol = f"{coin}/USDT:USDT"
        
        config.symbols[symbol] = SymbolConfig(
            symbol=symbol,
            ccxt_symbol=ccxt_symbol,
            enabled=True,
            initial_quantity=quantity
        )

        self._config = config
        self.bot = MaxGridBot(config)
        self.is_trading = True
        
        async def run():
            try:
                await self.bot.run()
            except Exception as e:
                logger.error(f"Bot crashed: {e}")
            finally:
                self.is_trading = False
                self.bot = None

        self.task = asyncio.create_task(run())
        
        logger.info(f"Trading started: {symbol} qty={quantity}")
        return {"status": "started", "symbol": symbol}

    async def stop(self) -> Dict[str, str]:
        """停止交易"""
        self.is_trading = False
        
        if self.bot:
            await self.bot.stop()
        if self.task:
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        self.bot = None
        
        logger.info("Trading stopped")
        return {"status": "stopped"}

    def get_status(self) -> Dict[str, Any]:
        """獲取當前狀態"""
        return self._get_heartbeat_status()
    
    async def handle_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """
        處理遠端命令
        
        Args:
            command: {action: "start"|"stop"|"update_config", params: {...}}
        """
        action = command.get("action")
        params = command.get("params", {})
        
        logger.info(f"Handling command: {action}")
        
        if action == "start":
            symbol = params.get("symbol", "XRPUSDC")
            quantity = params.get("quantity", 30)
            return self.start(symbol, quantity)
        
        elif action == "stop":
            return await self.stop()
        
        elif action == "update_config":
            # 更新配置（未來擴展）
            return {"status": "config_updated"}
        
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def shutdown(self):
        """關閉 Node"""
        await self.stop()
        if self.auth_client:
            await self.auth_client.close()
        logger.info("BotManager shutdown complete")


# 全局實例
bot_manager = BotManager()
