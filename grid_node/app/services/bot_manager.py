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

        # ═══════════════════════════════════════════════════════════════════
        # 【交易時 UID 驗證】白名單狀態
        # ═══════════════════════════════════════════════════════════════════
        self._whitelist_blocked = False  # 是否被白名單阻止
        self._whitelist_warning = False  # 是否在警告期
        self._whitelist_check_task: Optional[asyncio.Task] = None

        # ═══════════════════════════════════════════════════════════════════
        # 【P1: Node 離線處理】連線狀態追蹤
        # ═══════════════════════════════════════════════════════════════════
        self._server_connected = True  # 與 Auth Server 的連線狀態
        self._exchange_connected = True  # 與交易所的連線狀態
        self._reconnect_attempts = 0  # 重連嘗試次數
        self._max_reconnect_attempts = 10  # 最大重連次數
        self._last_error_time: Optional[float] = None

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
                
                # === Anti-Bait-and-Switch: 獲取 API Key 的實際 UID ===
                actual_uid = self._fetch_actual_uid()
                if actual_uid:
                    self.auth_client.current_uid = actual_uid
                    logger.info(f"Verified actual UID from exchange: {actual_uid}")
                    result["verified_uid"] = actual_uid
                else:
                    logger.warning("Could not fetch actual UID from exchange")
                
                # 啟動心跳
                await self.auth_client.start_heartbeat()

                # ═══════════════════════════════════════════════════════════════
                # 【交易時 UID 驗證】啟動定期白名單檢查
                # ═══════════════════════════════════════════════════════════════
                await self._start_whitelist_check()

            else:
                result["message"] = "Failed to connect, running standalone"

        return result

    async def _start_whitelist_check(self):
        """啟動定期白名單檢查 (每 5 分鐘)"""
        if self._whitelist_check_task:
            return

        async def check_loop():
            while True:
                try:
                    if self.auth_client:
                        is_valid = await self.auth_client.check_whitelist()

                        if not is_valid:
                            if not self._whitelist_blocked:
                                logger.error("⛔ WHITELIST BLOCKED: Trading will be stopped!")
                                self._whitelist_blocked = True

                                # 如果正在交易，停止交易
                                if self.is_trading:
                                    logger.warning("Stopping trading due to whitelist block...")
                                    await self.stop()
                        else:
                            self._whitelist_blocked = False

                except Exception as e:
                    logger.error(f"Whitelist check loop error: {e}")

                await asyncio.sleep(300)  # 5 分鐘檢查一次

        self._whitelist_check_task = asyncio.create_task(check_loop())
        logger.info("Whitelist check loop started (interval: 5 min)")

    # ═══════════════════════════════════════════════════════════════════════
    # 【P1: Node 離線處理】離線處理方法
    # ═══════════════════════════════════════════════════════════════════════

    def _calculate_backoff(self) -> float:
        """
        計算指數退避時間

        Returns:
            等待時間（秒）：1, 2, 4, 8, 16, 30 (最大)
        """
        base = 1
        max_wait = 30
        wait = min(base * (2 ** self._reconnect_attempts), max_wait)
        return wait

    async def _handle_server_disconnect(self):
        """
        處理與 Auth Server 斷線

        策略：寬容模式 - 繼續交易，使用快取的白名單狀態
        """
        if self._server_connected:
            self._server_connected = False
            logger.warning(
                "⚠️ AUTH SERVER DISCONNECTED: Running in tolerance mode. "
                "Trading will continue with cached whitelist status."
            )

        # 不中斷交易，繼續運行

    async def _handle_server_reconnect(self):
        """處理與 Auth Server 重新連線"""
        if not self._server_connected:
            self._server_connected = True
            self._reconnect_attempts = 0
            logger.info("✅ AUTH SERVER RECONNECTED: Back to normal mode.")

            # 強制刷新白名單狀態
            if self.auth_client:
                await self.auth_client.check_whitelist(force=True)

    async def _handle_exchange_disconnect(self):
        """
        處理與交易所斷線

        策略：
        1. 自動重連（指數退避）
        2. 3 次失敗後暫停新開倉
        3. 10 次失敗後發送告警
        4. 保留現有倉位（不平倉）
        """
        self._exchange_connected = False
        self._reconnect_attempts += 1

        wait_time = self._calculate_backoff()
        logger.warning(
            f"⚠️ EXCHANGE DISCONNECTED: Attempt {self._reconnect_attempts}/{self._max_reconnect_attempts}. "
            f"Waiting {wait_time}s before retry..."
        )

        # 3 次失敗後暫停新開倉
        if self._reconnect_attempts >= 3 and not self.is_paused:
            logger.warning("Pausing new positions due to connection issues...")
            self.is_paused = True
            if self.bot and hasattr(self.bot, 'set_pause'):
                self.bot.set_pause(True)

        # 10 次失敗後發送告警
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error(
                f"🚨 CRITICAL: Exchange reconnection failed after {self._max_reconnect_attempts} attempts! "
                "Manual intervention may be required."
            )
            # TODO: 發送通知到 Server / 用戶

        await asyncio.sleep(wait_time)

    async def _handle_exchange_reconnect(self):
        """處理與交易所重新連線"""
        if not self._exchange_connected:
            self._exchange_connected = True
            self._reconnect_attempts = 0
            logger.info("✅ EXCHANGE RECONNECTED: Connection restored.")

            # 如果之前因為斷線而暫停，恢復交易
            if self.is_paused and self._reconnect_attempts == 0:
                logger.info("Resuming trading after reconnection...")
                self.is_paused = False
                if self.bot and hasattr(self.bot, 'set_pause'):
                    self.bot.set_pause(False)

    async def recover_state_on_restart(self) -> Dict[str, Any]:
        """
        Node 重啟後恢復狀態

        步驟：
        1. 從交易所讀取現有倉位
        2. 比對本地 config 的交易對
        3. 恢復交易狀態
        """
        result = {
            "recovered": False,
            "positions": [],
            "message": ""
        }

        try:
            import ccxt

            api_key = os.getenv("EXCHANGE_API_KEY", "")
            api_secret = os.getenv("EXCHANGE_SECRET", "")
            passphrase = os.getenv("EXCHANGE_PASSPHRASE", "")

            if not api_key or not api_secret:
                result["message"] = "No API credentials configured"
                return result

            exchange = ccxt.bitget({
                'apiKey': api_key,
                'secret': api_secret,
                'password': passphrase,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })

            # 獲取所有持倉
            positions = exchange.fetch_positions()
            active_positions = []

            for pos in positions:
                if pos.get('contracts', 0) > 0 or pos.get('contractSize', 0) > 0:
                    active_positions.append({
                        "symbol": pos.get('symbol'),
                        "side": pos.get('side'),
                        "contracts": pos.get('contracts', 0),
                        "unrealizedPnl": pos.get('unrealizedPnl', 0)
                    })

            result["positions"] = active_positions
            result["recovered"] = True
            result["message"] = f"Found {len(active_positions)} active positions"

            if active_positions:
                logger.info(f"Recovered {len(active_positions)} positions on restart:")
                for p in active_positions:
                    logger.info(f"  - {p['symbol']} {p['side']}: {p['contracts']} contracts")

        except Exception as e:
            logger.error(f"Failed to recover state: {e}")
            result["message"] = str(e)

        return result

    def get_connection_status(self) -> Dict[str, Any]:
        """獲取連線狀態"""
        return {
            "server_connected": self._server_connected,
            "exchange_connected": self._exchange_connected,
            "reconnect_attempts": self._reconnect_attempts,
            "is_trading": self.is_trading,
            "is_paused": self.is_paused,
            "whitelist_blocked": self._whitelist_blocked
        }

    def _fetch_actual_uid(self) -> Optional[str]:
        """
        從交易所 API 獲取當前 API Key 的實際 UID
        
        Returns:
            UID 字串，失敗時返回 None
        """
        try:
            import ccxt
            
            api_key = os.getenv("EXCHANGE_API_KEY", "")
            api_secret = os.getenv("EXCHANGE_SECRET", "")
            passphrase = os.getenv("EXCHANGE_PASSPHRASE", "")
            
            if not api_key or not api_secret:
                return None
            
            exchange = ccxt.bitget({
                'apiKey': api_key,
                'secret': api_secret,
                'password': passphrase,
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}
            })
            
            # 方法 1: 使用 fetch_accounts 獲取帳戶資訊
            try:
                accounts = exchange.fetch_accounts()
                for acc in accounts:
                    if acc.get('info') and acc['info'].get('userId'):
                        return str(acc['info']['userId'])
            except Exception:
                pass
            
            # 方法 2: 使用 private_spot_get_v2_spot_account_info
            try:
                result = exchange.private_spot_get_v2_spot_account_info()
                if result.get('data') and result['data'].get('userId'):
                    return str(result['data']['userId'])
            except Exception:
                pass
            
            # 方法 3: 使用 fetch_balance 並從 info 中提取
            try:
                balance = exchange.fetch_balance({'type': 'swap'})
                if 'info' in balance and isinstance(balance['info'], dict):
                    # Bitget 可能在不同欄位中放 userId
                    for key in ['userId', 'uid', 'user_id']:
                        if balance['info'].get(key):
                            return str(balance['info'][key])
            except Exception:
                pass
            
            logger.warning("Could not find UID in any API response")
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch actual UID: {e}")
            return None
    
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

    async def start(self, symbol: str, quantity: float) -> Dict[str, str]:
        """啟動交易"""
        # ═══════════════════════════════════════════════════════════════════
        # 【交易時 UID 驗證】啟動前檢查白名單
        # ═══════════════════════════════════════════════════════════════════
        if self._whitelist_blocked:
            logger.error("Cannot start trading: blocked by whitelist")
            raise ValueError("Trading blocked: Your account is not in the whitelist. Please contact support.")

        if self.auth_client:
            is_valid = await self.auth_client.check_whitelist()
            if not is_valid:
                logger.error("Cannot start trading: whitelist check failed")
                raise ValueError("Trading blocked: Whitelist verification failed. Please contact support.")

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

        # 停止白名單檢查
        if self._whitelist_check_task:
            self._whitelist_check_task.cancel()
            try:
                await self._whitelist_check_task
            except asyncio.CancelledError:
                pass
            self._whitelist_check_task = None

        if self.auth_client:
            await self.auth_client.close()
        logger.info("BotManager shutdown complete")


# 全局實例
bot_manager = BotManager()
