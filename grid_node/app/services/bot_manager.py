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
        self.is_paused = False  # 暫停補倉狀態
        self._config: Optional[GlobalConfig] = None
        
        # 初始化 AuthClient（如果配置了官方伺服器）
        self._init_auth_client()
    
    def _init_auth_client(self):
        """初始化 AuthClient"""
        auth_server_url = os.getenv("AUTH_SERVER_URL")
        bitget_uid = os.getenv("BITGET_UID")
        
        if auth_server_url and bitget_uid:
            self.auth_client = AuthClient(
                auth_server_url=auth_server_url,
                bitget_uid=bitget_uid,
                node_secret=os.getenv("NODE_SECRET", ""),
                heartbeat_interval=30
            )
            # 設定狀態回調
            self.auth_client.set_status_callback(self._get_heartbeat_status)
            logger.info("AuthClient initialized for official server communication")
        else:
            logger.info("Running in standalone mode (no AUTH_SERVER_URL or BITGET_UID)")
    
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
    
    def _fetch_account_balance(self) -> Dict[str, Any]:
        """
        獲取帳戶餘額（不需要 bot 運行時使用）
        
        使用 ccxt 同步獲取 Bitget 合約帳戶餘額
        """
        try:
            import ccxt
            
            api_key = os.getenv("EXCHANGE_API_KEY", "")
            api_secret = os.getenv("EXCHANGE_SECRET", "")
            passphrase = os.getenv("EXCHANGE_PASSPHRASE", "")
            
            if not api_key or not api_secret:
                logger.debug("No API credentials configured")
                return {"equity": 0, "available_balance": 0, "unrealized_pnl": 0}
            
            exchange = ccxt.bitget({
                'apiKey': api_key,
                'secret': api_secret,
                'password': passphrase,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })
            
            balance = exchange.fetch_balance({'type': 'swap'})
            
            total_equity = 0
            total_available = 0
            total_unrealized = 0
            
            # 分離追蹤 USDT 和 USDC 餘額
            usdt_equity = 0
            usdt_available = 0
            usdc_equity = 0
            usdc_available = 0
            
            for currency in ['USDT', 'USDC']:
                if currency in balance:
                    info = balance[currency]
                    equity = float(info.get('total', 0) or 0)
                    available = float(info.get('free', 0) or 0)
                    
                    total_equity += equity
                    total_available += available
                    
                    # 分開儲存
                    if currency == 'USDT':
                        usdt_equity = equity
                        usdt_available = available
                    else:
                        usdc_equity = equity
                        usdc_available = available
                    
                    # Bitget unrealized PnL 可能在 info 中
                    if 'info' in info and isinstance(info['info'], dict):
                        total_unrealized += float(info['info'].get('upl', 0) or 0)
            
            logger.debug(f"Fetched balance: USDT={usdt_equity}, USDC={usdc_equity}, total={total_equity}")
            return {
                "equity": total_equity,
                "available_balance": total_available,
                "unrealized_pnl": total_unrealized,
                # 新增：分離的 USDT/USDC 餘額
                "usdt_equity": usdt_equity,
                "usdt_available": usdt_available,
                "usdc_equity": usdc_equity,
                "usdc_available": usdc_available
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch account balance: {e}")
            return {
                "equity": 0, "available_balance": 0, "unrealized_pnl": 0,
                "usdt_equity": 0, "usdt_available": 0,
                "usdc_equity": 0, "usdc_available": 0
            }
    
    def _get_heartbeat_status(self) -> Dict[str, Any]:
        """獲取心跳狀態（供 AuthClient 調用）"""
        if not self.bot:
            # 沒有交易時，嘗試獲取帳戶餘額
            balance_info = self._fetch_account_balance()
            return {
                "status": "stopped",
                "is_trading": False,
                "is_paused": self.is_paused,
                "total_pnl": 0,
                "unrealized_pnl": balance_info.get("unrealized_pnl", 0),
                "equity": balance_info.get("equity", 0),
                "available_balance": balance_info.get("available_balance", 0),
                # 新增：分離的 USDT/USDC 餘額
                "usdt_equity": balance_info.get("usdt_equity", 0),
                "usdt_available": balance_info.get("usdt_available", 0),
                "usdc_equity": balance_info.get("usdc_equity", 0),
                "usdc_available": balance_info.get("usdc_available", 0),
                "positions": [],
                "symbols": [],
                "indicators": None
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
        
        # 計算總權益 - 優先使用 state 已計算的值
        state.update_totals()  # 確保 totals 是最新的
        equity = getattr(state, 'total_equity', 0)
        available_balance = getattr(state, 'free_balance', 0)
        
        # 獲取指標數據
        indicators = self._get_indicators_data()
        
        return {
            "status": "running" if state.running else "stopped",
            "is_trading": self.is_trading,
            "is_paused": self.is_paused,
            "total_pnl": state.total_profit,
            "unrealized_pnl": getattr(state, 'total_unrealized_pnl', 0),
            "equity": equity,
            "available_balance": available_balance,
            "positions": positions,
            "symbols": symbols,
            "indicators": indicators
        }
    
    def _get_indicators_data(self) -> Dict[str, Any]:
        """獲取交易指標數據"""
        if not self.bot:
            return None
        
        indicators = {
            "funding_rate": 0,
            "ofi_value": 0,
            "volume_ratio": 1.0,
            "spread_ratio": 1.0,
            "total_positions": 0,
            "bandit_arm": 0
        }
        
        try:
            # 計算總持倉
            total_pos = 0
            for sym_state in self.bot.state.symbols.values():
                total_pos += sym_state.long_position + sym_state.short_position
            indicators["total_positions"] = int(total_pos)
            
            # 從 Bot 獲取領先指標（如果有）
            if hasattr(self.bot, 'leading_indicator_mgr') and self.bot.leading_indicator_mgr:
                li_mgr = self.bot.leading_indicator_mgr
                first_symbol = next(iter(self.bot.state.symbols.keys()), None)
                if first_symbol:
                    indicators["ofi_value"] = li_mgr.current_ofi.get(first_symbol, 0) if hasattr(li_mgr, 'current_ofi') else 0
                    indicators["volume_ratio"] = li_mgr.current_volume_ratio.get(first_symbol, 1.0) if hasattr(li_mgr, 'current_volume_ratio') else 1.0
                    indicators["spread_ratio"] = li_mgr.current_spread_ratio.get(first_symbol, 1.0) if hasattr(li_mgr, 'current_spread_ratio') else 1.0
            
            # 從 Bot 獲取 Bandit（如果有）
            if hasattr(self.bot, 'bandit_optimizer') and self.bot.bandit_optimizer:
                indicators["bandit_arm"] = getattr(self.bot.bandit_optimizer, 'current_arm_idx', 0)
            
            # Funding Rate（如果有）
            if hasattr(self.bot, 'funding_rate_mgr') and self.bot.funding_rate_mgr:
                fr_mgr = self.bot.funding_rate_mgr
                first_symbol = next(iter(self.bot.state.symbols.keys()), None)
                if first_symbol and hasattr(fr_mgr, 'current_rates'):
                    indicators["funding_rate"] = fr_mgr.current_rates.get(first_symbol, 0)
        
        except Exception as e:
            logger.warning(f"Failed to get indicators: {e}")
        
        return indicators

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
        self.is_paused = False
        
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
        self.is_paused = False
        
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

    async def close_all_positions(self) -> Dict[str, Any]:
        """
        一鍵平倉 - 關閉所有持倉
        
        Returns:
            平倉結果
        """
        if not self.bot or not self.is_trading:
            return {"status": "error", "message": "No active trading session"}
        
        try:
            logger.info("Closing all positions...")
            
            # 調用 bot 的平倉方法
            if hasattr(self.bot, 'close_all_positions'):
                result = await self.bot.close_all_positions()
                logger.info(f"Close all positions result: {result}")
                return {"status": "success", "result": result}
            else:
                # 如果 bot 沒有這個方法，嘗試直接通過交易所平倉
                closed = []
                for sym_state in self.bot.state.symbols.values():
                    symbol = sym_state.symbol
                    if sym_state.long_position > 0 or sym_state.short_position > 0:
                        # 使用 bot 的 exchange 進行平倉
                        if hasattr(self.bot, 'exchange') and self.bot.exchange:
                            try:
                                if sym_state.long_position > 0:
                                    await self.bot.exchange.create_market_sell_order(
                                        sym_state.ccxt_symbol if hasattr(sym_state, 'ccxt_symbol') else symbol,
                                        sym_state.long_position,
                                        params={'reduceOnly': True}
                                    )
                                    closed.append(f"{symbol} LONG")
                                if sym_state.short_position > 0:
                                    await self.bot.exchange.create_market_buy_order(
                                        sym_state.ccxt_symbol if hasattr(sym_state, 'ccxt_symbol') else symbol,
                                        sym_state.short_position,
                                        params={'reduceOnly': True}
                                    )
                                    closed.append(f"{symbol} SHORT")
                            except Exception as e:
                                logger.error(f"Failed to close {symbol}: {e}")
                
                return {"status": "success", "closed": closed}
        
        except Exception as e:
            logger.error(f"Close all positions failed: {e}")
            return {"status": "error", "message": str(e)}

    async def toggle_pause(self) -> Dict[str, Any]:
        """
        暫停/恢復補倉
        
        Returns:
            暫停狀態
        """
        self.is_paused = not self.is_paused
        
        if self.bot and hasattr(self.bot, 'set_pause'):
            self.bot.set_pause(self.is_paused)
        
        status = "paused" if self.is_paused else "resumed"
        logger.info(f"Trading {status}")
        
        return {
            "status": "success",
            "is_paused": self.is_paused,
            "message": f"Trading {status}"
        }

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
        
        elif action == "close_all":
            return await self.close_all_positions()
        
        elif action == "pause":
            return await self.toggle_pause()
        
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
