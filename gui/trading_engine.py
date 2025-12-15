#!/usr/bin/env python3
"""
LouisLAB AS Grid - 交易引擎 (Bitget)
====================================

整合 as_terminal_max_bitget.py 的核心功能到 GUI
支援授權驗證和即時交易控制
交易所: Bitget Futures
"""

import sys
import os
import asyncio
import threading
import logging
from pathlib import Path
from typing import Optional, Dict, Callable, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import ssl
import certifi

# WebSocket
try:
    import websockets
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False

# 添加父目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "client"))

logger = logging.getLogger(__name__)

# 嘗試導入授權模組
try:
    from client.license_manager import LicenseManager
    from client.secure_storage import CredentialManager, check_password_strength
    LICENSE_AVAILABLE = True
except ImportError:
    LICENSE_AVAILABLE = False
    logger.warning("授權模組未安裝")


# ═══════════════════════════════════════════════════════════════════════════
# 數據結構
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Position:
    """持倉資訊"""
    symbol: str
    side: str  # "long" / "short"
    quantity: float
    entry_price: float
    unrealized_pnl: float
    margin: float
    is_dead_mode: bool = False
    is_double_tp: bool = False


@dataclass
class TradeRecord:
    """交易記錄"""
    timestamp: datetime
    symbol: str
    side: str
    quantity: float
    price: float
    pnl: float
    message: str


@dataclass
class SymbolStatus:
    """交易對狀態"""
    symbol: str
    enabled: bool
    price: float = 0.0
    long_qty: float = 0.0
    short_qty: float = 0.0
    long_entry: float = 0.0
    short_entry: float = 0.0
    long_pnl: float = 0.0
    short_pnl: float = 0.0
    long_dead: bool = False
    short_dead: bool = False
    long_2x: bool = False
    short_2x: bool = False
    dynamic_spacing: Optional[float] = None

    # 配置參數
    take_profit_spacing: float = 0.004
    grid_spacing: float = 0.006
    initial_quantity: float = 3.0
    leverage: int = 20
    limit_multiplier: float = 5.0
    threshold_multiplier: float = 20.0


@dataclass
class LearningStatus:
    """學習模組狀態"""
    bandit_enabled: bool = False
    bandit_pulls: int = 0
    current_arm: int = 0
    current_params: Dict = field(default_factory=dict)

    ofi_enabled: bool = False
    ofi_value: float = 0.0
    ofi_signal: str = ""

    volume_enabled: bool = False
    volume_ratio: float = 1.0
    volume_signal: str = ""

    spread_enabled: bool = False
    spread_ratio: float = 1.0
    spread_signal: str = ""

    dgt_enabled: bool = False
    current_boundary: str = ""


@dataclass
class AccountInfo:
    """帳戶資訊"""
    currency: str  # USDC / USDT
    equity: float = 0.0
    available: float = 0.0
    margin_ratio: float = 0.0
    unrealized_pnl: float = 0.0


@dataclass
class IndicatorData:
    """指標數據"""
    # Funding Rate
    funding_rate: float = 0.0
    funding_bias: str = "中性"  # 偏多/偏空/中性

    # 領先指標
    ofi_value: float = 0.0
    volume_ratio: float = 1.0
    spread_ratio: float = 1.0

    # Bandit
    bandit_arm: int = 0
    bandit_context: str = ""

    # 風控
    drawdown: float = 0.0
    total_positions: int = 0


# ═══════════════════════════════════════════════════════════════════════════
# 交易引擎
# ═══════════════════════════════════════════════════════════════════════════

class TradingEngine:
    """
    交易引擎 - 連接 GUI 和核心交易邏輯

    使用方式:
    ```python
    engine = TradingEngine()
    engine.set_callbacks(
        on_log=lambda msg: print(msg),
        on_trade=lambda trade: update_ui(trade),
        on_position=lambda pos: update_positions(pos)
    )
    await engine.connect(api_key, api_secret)
    await engine.start_trading("XRPUSDC")
    ```
    """

    # 驗證伺服器 URL（可配置，生產環境請使用 HTTPS）
    # TODO: 部署時請更新為實際的 Railway/Vercel URL
    LICENSE_SERVER_URL = os.environ.get("LICENSE_SERVER_URL", "https://as-grid-server-production.up.railway.app")
    APP_VERSION = "1.0.0"

    def __init__(self):
        # 狀態
        self.is_connected = False
        self.is_trading = False
        self.is_verified = False
        self.exchange = None
        self.config = None
        self.bot = None

        # API 憑證（運行時保存）- Bitget 需要額外的 passphrase
        self._api_key: Optional[str] = None
        self._api_secret: Optional[str] = None
        self._passphrase: Optional[str] = None  # Bitget 專用

        # 授權管理
        self.license_manager: Optional['LicenseManager'] = None
        self.credential_manager: Optional['CredentialManager'] = None
        self.user_info: Optional[Dict] = None

        # 數據
        self.positions: Dict[str, Position] = {}
        self.symbol_status: Dict[str, SymbolStatus] = {}
        self.trades: List[TradeRecord] = []
        self.accounts: Dict[str, AccountInfo] = {
            "USDC": AccountInfo(currency="USDC"),
            "USDT": AccountInfo(currency="USDT")
        }
        self.learning_status = LearningStatus()
        self.indicators = IndicatorData()  # 指標數據

        self.total_pnl = 0.0
        self.today_trades = 0
        self.start_time: Optional[datetime] = None

        # 回調函數
        self._on_log: Optional[Callable[[str], None]] = None
        self._on_trade: Optional[Callable[[TradeRecord], None]] = None
        self._on_position: Optional[Callable[[Dict[str, Position]], None]] = None
        self._on_symbol_status: Optional[Callable[[Dict[str, SymbolStatus]], None]] = None
        self._on_account: Optional[Callable[[Dict[str, AccountInfo]], None]] = None
        self._on_learning: Optional[Callable[[LearningStatus], None]] = None
        self._on_stats: Optional[Callable[[Dict], None]] = None
        self._on_status: Optional[Callable[[str, bool], None]] = None
        self._on_indicators: Optional[Callable[[IndicatorData], None]] = None

        # 線程
        self._trading_thread: Optional[threading.Thread] = None
        self._update_thread: Optional[threading.Thread] = None
        self._ws_thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event = threading.Event()
        self._ws_stop_event = threading.Event()

        # WebSocket (Bitget)
        self._ws_url = "wss://ws.bitget.com/v2/ws/public"
        self._private_ws_url = "wss://ws.bitget.com/v2/ws/private"
        self._listen_key: Optional[str] = None
        self._ws_connected = False

        # 配置路徑
        self.config_path = Path(__file__).parent.parent / "config" / "trading_config_max.json"

        # 初始化憑證管理器
        if LICENSE_AVAILABLE:
            self.credential_manager = CredentialManager()

    def set_callbacks(
        self,
        on_log: Callable[[str], None] = None,
        on_trade: Callable[[TradeRecord], None] = None,
        on_position: Callable[[Dict[str, Position]], None] = None,
        on_symbol_status: Callable[[Dict[str, SymbolStatus]], None] = None,
        on_account: Callable[[Dict[str, AccountInfo]], None] = None,
        on_learning: Callable[[LearningStatus], None] = None,
        on_stats: Callable[[Dict], None] = None,
        on_status: Callable[[str, bool], None] = None,
        on_indicators: Callable[[IndicatorData], None] = None
    ):
        """設定回調函數"""
        self._on_log = on_log
        self._on_trade = on_trade
        self._on_position = on_position
        self._on_symbol_status = on_symbol_status
        self._on_indicators = on_indicators
        self._on_account = on_account
        self._on_learning = on_learning
        self._on_stats = on_stats
        self._on_status = on_status

    def _log(self, message: str):
        """輸出日誌"""
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        full_msg = f"{timestamp} {message}"
        logger.info(message)
        if self._on_log:
            self._on_log(full_msg)

    def _update_status(self, status: str, is_active: bool):
        """更新狀態"""
        if self._on_status:
            self._on_status(status, is_active)

    # ═══════════════════════════════════════════════════════════════════════
    # 連接管理
    # ═══════════════════════════════════════════════════════════════════════

    async def connect(self, api_key: str, api_secret: str, passphrase: str = "", skip_license: bool = False) -> bool:
        """
        連接交易所 (Bitget)

        Args:
            api_key: Bitget API Key
            api_secret: Bitget API Secret
            passphrase: Bitget API Passphrase (必填)
            skip_license: 是否跳過授權驗證（僅用於開發測試）

        Returns:
            是否連接成功
        """
        try:
            self._log("正在連接 Bitget 交易所...")

            import ccxt.async_support as ccxt

            self.exchange = ccxt.bitget({
                'apiKey': api_key,
                'secret': api_secret,
                'password': passphrase,  # Bitget 需要 passphrase
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',  # Bitget 永續合約
                    'adjustForTimeDifference': True
                }
            })

            # 測試連接
            await self.exchange.load_markets()

            # 保存憑證（用於 MaxGridBot）
            self._api_key = api_key
            self._api_secret = api_secret
            self._passphrase = passphrase

            # 獲取帳戶資訊
            balance = await self.exchange.fetch_balance()

            self.is_connected = True
            self._log("✓ 交易所連接成功")

            # 載入配置
            self._load_config()

            # 更新帳戶資訊
            await self._update_account(balance)

            # 授權驗證
            if not skip_license and LICENSE_AVAILABLE:
                self._log("正在驗證授權...")
                self.license_manager = LicenseManager(
                    self.exchange,
                    self.LICENSE_SERVER_URL,
                    self.APP_VERSION
                )

                result = await self.license_manager.verify()

                if result.get("success"):
                    self.is_verified = True
                    self.user_info = result.get("user", {})
                    nickname = self.user_info.get("nickname", "用戶")
                    self._log(f"✓ 授權驗證成功！歡迎 {nickname}")
                    self._update_status(f"已連接 ({nickname})", True)
                else:
                    self.is_verified = False
                    reason = result.get("reason", "驗證失敗")
                    self._log(f"✗ 授權驗證失敗: {reason}")
                    self._update_status("授權失敗", False)
                    # 關閉連接
                    await self.disconnect()
                    return False
            else:
                # 跳過授權（開發模式）
                self.is_verified = True
                self._update_status("已連接 (開發模式)", True)

            # 啟動 WebSocket 即時數據
            self.start_websocket()

            return True

        except Exception as e:
            self._log(f"✗ 連接失敗: {e}")
            self._update_status("連接失敗", False)
            return False

    async def disconnect(self):
        """斷開連接"""
        # 停止 WebSocket
        self.stop_websocket()

        # 停止交易
        if self.is_trading:
            await self.stop_trading()

        # 登出授權
        if self.license_manager:
            try:
                await self.license_manager.logout()
            except Exception as e:
                logger.warning(f"登出失敗: {e}")
            self.license_manager = None

        # 關閉交易所連接
        if self.exchange:
            try:
                await self.exchange.close()
            except Exception:
                pass
            self.exchange = None

        # 清除憑證
        self._api_key = None
        self._api_secret = None
        self._passphrase = None

        self.is_connected = False
        self.is_verified = False
        self._update_status("已斷開", False)
        self._log("已斷開連接")

    # ═══════════════════════════════════════════════════════════════════════
    # WebSocket 管理
    # ═══════════════════════════════════════════════════════════════════════

    def _get_listen_key(self) -> Optional[str]:
        """Bitget 不需要 listenKey，使用 WebSocket 簽名認證"""
        # Bitget 使用 WebSocket 簽名認證，不需要 listenKey
        return None

    def _delete_listen_key(self):
        """Bitget 不需要 listenKey"""
        pass

    def start_websocket(self):
        """啟動 WebSocket 連接（在背景線程中）"""
        if not WEBSOCKET_AVAILABLE:
            self._log("WebSocket 不可用")
            return

        if self._ws_thread and self._ws_thread.is_alive():
            return  # 已在運行

        self._ws_stop_event.clear()

        def run_ws():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._websocket_loop())
            except Exception as e:
                logger.error(f"WebSocket 線程錯誤: {e}")
            finally:
                loop.close()

        self._ws_thread = threading.Thread(target=run_ws, daemon=True, name="WebSocket")
        self._ws_thread.start()
        self._log("✓ WebSocket 啟動")

    def stop_websocket(self):
        """停止 WebSocket 連接"""
        self._ws_stop_event.set()
        self._ws_connected = False

        # 等待線程結束
        if self._ws_thread:
            self._ws_thread.join(timeout=5)
            if self._ws_thread.is_alive():
                logger.warning("WebSocket 線程未能在超時內結束")
            self._ws_thread = None

        # 清理 listen key
        if self._listen_key:
            try:
                self._delete_listen_key()
            except Exception as e:
                logger.debug(f"清理 listen key 失敗: {e}")
            self._listen_key = None

        self._log("[WS] 已停止")

    async def _websocket_loop(self):
        """Bitget WebSocket 主循環 - 公共數據流"""
        ssl_context = ssl.create_default_context(cafile=certifi.where())

        while not self._ws_stop_event.is_set():
            try:
                async with websockets.connect(self._ws_url, ssl=ssl_context) as ws:
                    self._ws_connected = True
                    self._log("[WS] 已連接")

                    # Bitget 訂閱格式
                    subscribe_args = []
                    if self.config:
                        for cfg in self.config.symbols.values():
                            if cfg.enabled:
                                # Bitget ticker 訂閱格式
                                subscribe_args.append({
                                    "instType": "USDT-FUTURES",
                                    "channel": "ticker",
                                    "instId": cfg.symbol  # e.g., "BTCUSDT"
                                })

                    if subscribe_args:
                        subscribe_msg = {
                            "op": "subscribe",
                            "args": subscribe_args
                        }
                        await ws.send(json.dumps(subscribe_msg))
                        self._log(f"[WS] 訂閱 {len(subscribe_args)} 個交易對價格")

                    # 接收消息循環
                    while not self._ws_stop_event.is_set():
                        try:
                            msg = await asyncio.wait_for(ws.recv(), timeout=30)
                            data = json.loads(msg)

                            # Bitget 數據格式處理
                            if "data" in data and "arg" in data:
                                channel = data.get("arg", {}).get("channel", "")
                                if channel == "ticker":
                                    await self._handle_ws_ticker(data)
                            elif "event" in data:
                                # 訂閱確認等事件
                                event = data.get("event")
                                if event == "subscribe":
                                    logger.info(f"[WS] 訂閱成功: {data.get('arg', {})}")
                                elif event == "error":
                                    logger.error(f"[WS] 訂閱錯誤: {data}")
                                else:
                                    logger.debug(f"[WS] Event: {event}")

                        except asyncio.TimeoutError:
                            # 發送 ping 保持連接
                            await ws.ping()

            except Exception as e:
                self._ws_connected = False
                if not self._ws_stop_event.is_set():
                    logger.error(f"[WS] 錯誤: {e}")
                    await asyncio.sleep(5)

    async def _handle_ws_ticker(self, data: dict):
        """處理 Bitget ticker 數據"""
        try:
            # Bitget 數據格式: {"action": "snapshot", "arg": {...}, "data": [{"instId": "BTCUSDT", "lastPr": "xxx", ...}]}
            ticker_list = data.get("data", [])
            if not ticker_list:
                return

            ticker_data = ticker_list[0]
            inst_id = ticker_data.get("instId", "")  # e.g., "BTCUSDT"

            if not inst_id:
                return

            # Bitget v2 可能使用 lastPr 或 last
            last_price = float(ticker_data.get("last", 0) or ticker_data.get("lastPr", 0))
            bid_price = float(ticker_data.get("bidPr", 0))
            ask_price = float(ticker_data.get("askPr", 0))

            if not last_price:
                return

            # 使用 config.symbols 匹配
            if self.config:
                for sym_config in self.config.symbols.values():
                    if sym_config.enabled and sym_config.symbol == inst_id:
                        # 找到匹配的 symbol_status
                        sym_id = sym_config.symbol  # e.g., "BTCUSDT"
                        if sym_id in self.symbol_status:
                            status = self.symbol_status[sym_id]
                            status.price = last_price
                            logger.debug(f"[WS] {inst_id} 價格更新: {last_price}")

                            # 觸發回調
                            if self._on_symbol_status:
                                self._on_symbol_status(self.symbol_status)
                        break

        except Exception as e:
            logger.error(f"[WS] 處理 ticker 失敗: {e}")

    async def _handle_ws_account(self, data: dict):
        """處理帳戶更新"""
        try:
            account_data = data.get('a', {})
            balances = account_data.get('B', [])
            positions = account_data.get('P', [])

            # 更新餘額
            for bal in balances:
                asset = bal.get('a', '')
                if asset in ['USDC', 'USDT']:
                    wallet = float(bal.get('wb', 0))
                    cross_wallet = float(bal.get('cw', 0))

                    self.accounts[asset] = AccountInfo(
                        currency=asset,
                        equity=wallet,
                        available=cross_wallet,
                        margin_ratio=0,
                        unrealized_pnl=0
                    )

            # 更新持倉（使用 config.symbols 匹配）
            for pos in positions:
                symbol_raw = pos.get('s', '')  # e.g., "XRPUSDC"
                side = 'long' if pos.get('ps') == 'LONG' else 'short'
                qty = abs(float(pos.get('pa', 0)))
                entry = float(pos.get('ep', 0))
                pnl = float(pos.get('up', 0))

                # 使用 config.symbols 匹配
                if self.config:
                    for sym_config in self.config.symbols.values():
                        if sym_config.ws_symbol.upper() == symbol_raw:
                            sym_id = sym_config.symbol
                            if sym_id in self.symbol_status:
                                status = self.symbol_status[sym_id]
                                if side == 'long':
                                    status.long_qty = qty
                                    status.long_entry = entry
                                    status.long_pnl = pnl
                                else:
                                    status.short_qty = qty
                                    status.short_entry = entry
                                    status.short_pnl = pnl
                            break

            # 觸發回調
            if self._on_account:
                self._on_account(self.accounts)
            if self._on_symbol_status:
                self._on_symbol_status(self.symbol_status)

        except Exception as e:
            logger.error(f"[WS] 處理帳戶更新失敗: {e}")

    async def _handle_ws_order(self, data: dict):
        """處理訂單更新"""
        try:
            order = data.get('o', {})
            status = order.get('X', '')

            if status == 'FILLED':
                symbol = order.get('s', '')
                side = order.get('S', '')
                qty = float(order.get('q', 0))
                price = float(order.get('ap', 0))  # 平均成交價
                pnl = float(order.get('rp', 0))  # 已實現盈虧

                # 記錄交易
                trade = TradeRecord(
                    timestamp=datetime.now(),
                    symbol=symbol,
                    side=side,
                    quantity=qty,
                    price=price,
                    pnl=pnl,
                    message=f"{side} {qty} @ {price}"
                )
                self.trades.append(trade)
                self.today_trades += 1
                self.total_pnl += pnl

                if self._on_trade:
                    self._on_trade(trade)

                self._log(f"[成交] {symbol} {side} {qty} @ {price:.4f} PnL: {pnl:+.2f}")

        except Exception as e:
            logger.error(f"[WS] 處理訂單更新失敗: {e}")

    async def fetch_funding_rate(self):
        """獲取 funding rate（定期調用）"""
        if not self.exchange or not self.config:
            return

        try:
            # 獲取第一個啟用的交易對的 funding rate
            for sym_config in self.config.symbols.values():
                if sym_config.enabled:
                    funding_info = await self.exchange.fetch_funding_rate(sym_config.ccxt_symbol)
                    rate = float(funding_info.get('fundingRate', 0) or 0)

                    self.indicators.funding_rate = rate

                    # 判斷偏向
                    if rate > 0.0001:
                        self.indicators.funding_bias = "偏多"
                    elif rate < -0.0001:
                        self.indicators.funding_bias = "偏空"
                    else:
                        self.indicators.funding_bias = "中性"

                    # 觸發回調
                    if self._on_indicators:
                        self._on_indicators(self.indicators)
                    break

        except Exception as e:
            logger.warning(f"獲取 funding rate 失敗: {e}")

    def update_indicators_from_bot(self):
        """從 Bot 同步指標數據（交易中調用）"""
        if not self.bot:
            return

        try:
            # 計算總持倉
            total_pos = 0
            for status in self.symbol_status.values():
                total_pos += status.long_qty + status.short_qty
            self.indicators.total_positions = int(total_pos)

            # 從 Bot 獲取領先指標（如果有）
            if hasattr(self.bot, 'leading_indicator'):
                li = self.bot.leading_indicator
                if hasattr(li, 'get_ofi'):
                    self.indicators.ofi_value = li.get_ofi() or 0
                if hasattr(li, 'get_volume_ratio'):
                    self.indicators.volume_ratio = li.get_volume_ratio() or 1.0
                if hasattr(li, 'get_spread_ratio'):
                    self.indicators.spread_ratio = li.get_spread_ratio() or 1.0

            # 從 Bot 獲取 Bandit（如果有）
            if hasattr(self.bot, 'bandit') and self.bot.bandit:
                self.indicators.bandit_arm = self.bot.bandit.current_arm or 0

            # 觸發回調
            if self._on_indicators:
                self._on_indicators(self.indicators)

        except Exception as e:
            logger.warning(f"同步指標失敗: {e}")

    # ═══════════════════════════════════════════════════════════════════════
    # 配置管理
    # ═══════════════════════════════════════════════════════════════════════

    def _load_config(self):
        """載入配置"""
        try:
            from as_terminal_max_bitget import GlobalConfig
            self.config = GlobalConfig.load()
            self._log("✓ 配置載入成功")

            # Story 1.4: 偵測舊版明文 API 並提示遷移
            if self.config.legacy_api_detected:
                self._log("⚠️ 偵測到配置檔包含明文 API 金鑰")
                self._log("⚠️ 建議在設定頁面執行「遷移 API」以提升安全性")

            # 同步交易對狀態
            self._sync_symbol_status()

        except Exception as e:
            self._log(f"配置載入失敗: {e}")
            self.config = None

    def _sync_symbol_status(self):
        """同步配置到 symbol_status"""
        if not self.config:
            return

        for symbol_id, symbol_cfg in self.config.symbols.items():
            self.symbol_status[symbol_id] = SymbolStatus(
                symbol=symbol_id,
                enabled=symbol_cfg.enabled,
                take_profit_spacing=symbol_cfg.take_profit_spacing,
                grid_spacing=symbol_cfg.grid_spacing,
                initial_quantity=symbol_cfg.initial_quantity,
                leverage=symbol_cfg.leverage,
                limit_multiplier=symbol_cfg.limit_multiplier,
                threshold_multiplier=symbol_cfg.threshold_multiplier
            )

        if self._on_symbol_status:
            self._on_symbol_status(self.symbol_status)

    def save_config(self):
        """儲存配置"""
        if self.config:
            self.config.save()
            self._log("配置已儲存")

    def get_config(self) -> Optional[Any]:
        """獲取配置物件"""
        return self.config

    # ═══════════════════════════════════════════════════════════════════════
    # 交易對管理
    # ═══════════════════════════════════════════════════════════════════════

    def get_symbols(self) -> List[str]:
        """獲取支援的交易對"""
        return [
            "XRPUSDC", "BTCUSDC", "ETHUSDC", "SOLUSDC", "DOGEUSDC",
            "XRPUSDT", "BTCUSDT", "ETHUSDT", "SOLUSDT", "DOGEUSDT",
            "BNBUSDT", "ADAUSDT"
        ]

    def get_active_symbols(self) -> List[str]:
        """獲取已啟用的交易對"""
        if not self.config:
            return []
        return [s for s, cfg in self.config.symbols.items() if cfg.enabled]

    def add_symbol(
        self,
        symbol: str,
        take_profit: float = 0.004,
        grid_spacing: float = 0.006,
        quantity: float = 3.0,
        leverage: int = 20,
        limit_multiplier: float = 5.0,
        threshold_multiplier: float = 20.0
    ) -> bool:
        """新增交易對"""
        if not self.config:
            self._log("請先載入配置")
            return False

        try:
            from as_terminal_max_bitget import SymbolConfig

            # 建立 CCXT 格式
            base = symbol.replace("USDC", "").replace("USDT", "")
            quote = "USDC" if "USDC" in symbol else "USDT"
            ccxt_symbol = f"{base}/{quote}:{quote}"

            self.config.symbols[symbol] = SymbolConfig(
                symbol=symbol,
                ccxt_symbol=ccxt_symbol,
                enabled=True,
                take_profit_spacing=take_profit,
                grid_spacing=grid_spacing,
                initial_quantity=quantity,
                leverage=leverage,
                limit_multiplier=limit_multiplier,
                threshold_multiplier=threshold_multiplier
            )

            self.config.save()
            self._sync_symbol_status()
            self._log(f"✓ 已新增交易對: {symbol}")
            return True

        except Exception as e:
            self._log(f"新增交易對失敗: {e}")
            return False

    def update_symbol(self, symbol: str, **kwargs) -> bool:
        """更新交易對配置"""
        if not self.config or symbol not in self.config.symbols:
            return False

        try:
            symbol_cfg = self.config.symbols[symbol]
            for key, value in kwargs.items():
                if hasattr(symbol_cfg, key):
                    setattr(symbol_cfg, key, value)

            self.config.save()
            self._sync_symbol_status()
            self._log(f"配置已更新: {symbol}")
            return True

        except Exception as e:
            self._log(f"更新失敗: {e}")
            return False

    def toggle_symbol(self, symbol: str) -> bool:
        """切換交易對啟用狀態"""
        if not self.config or symbol not in self.config.symbols:
            return False

        cfg = self.config.symbols[symbol]
        cfg.enabled = not cfg.enabled
        self.config.save()
        self._sync_symbol_status()

        status = "啟用" if cfg.enabled else "停用"
        self._log(f"{symbol} 已{status}")
        return True

    def delete_symbol(self, symbol: str) -> bool:
        """刪除交易對"""
        if not self.config or symbol not in self.config.symbols:
            return False

        del self.config.symbols[symbol]
        if symbol in self.symbol_status:
            del self.symbol_status[symbol]

        self.config.save()
        self._log(f"已刪除交易對: {symbol}")
        return True

    # ═══════════════════════════════════════════════════════════════════════
    # MAX 增強功能設定
    # ═══════════════════════════════════════════════════════════════════════

    def get_max_enhancement_config(self) -> Dict:
        """獲取 MAX 增強功能配置"""
        if not self.config:
            return {}

        max_cfg = self.config.max_enhancement
        return {
            "all_enabled": max_cfg.all_enhancements_enabled,
            "funding_rate": {
                "enabled": max_cfg.funding_rate_enabled,
                "threshold": max_cfg.funding_rate_threshold,
                "bias": max_cfg.funding_rate_position_bias
            },
            "glft": {
                "enabled": max_cfg.glft_enabled,
                "gamma": max_cfg.gamma,
                "inventory_target": max_cfg.inventory_target
            },
            "dynamic_grid": {
                "enabled": max_cfg.dynamic_grid_enabled,
                "atr_period": max_cfg.atr_period,
                "atr_multiplier": max_cfg.atr_multiplier,
                "min_spacing": max_cfg.min_spacing,
                "max_spacing": max_cfg.max_spacing
            }
        }

    def update_max_enhancement(self, **kwargs) -> bool:
        """更新 MAX 增強功能配置"""
        if not self.config:
            return False

        try:
            max_cfg = self.config.max_enhancement
            for key, value in kwargs.items():
                if hasattr(max_cfg, key):
                    setattr(max_cfg, key, value)

            self.config.save()
            self._log("MAX 增強功能設定已更新")
            return True
        except Exception as e:
            self._log(f"更新失敗: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════
    # 學習模組設定
    # ═══════════════════════════════════════════════════════════════════════

    def get_bandit_config(self) -> Dict:
        """獲取 Bandit 配置"""
        if not self.config:
            return {}

        cfg = self.config.bandit
        return {
            "enabled": cfg.enabled,
            "window_size": cfg.window_size,
            "exploration_factor": cfg.exploration_factor,
            "update_interval": cfg.update_interval,
            "cold_start_enabled": cfg.cold_start_enabled,
            "contextual_enabled": cfg.contextual_enabled,
            "thompson_enabled": cfg.thompson_enabled
        }

    def update_bandit_config(self, **kwargs) -> bool:
        """更新 Bandit 配置"""
        if not self.config:
            return False

        try:
            cfg = self.config.bandit
            for key, value in kwargs.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, value)

            self.config.save()
            self._log("Bandit 設定已更新")
            return True
        except Exception as e:
            self._log(f"更新失敗: {e}")
            return False

    def get_leading_indicator_config(self) -> Dict:
        """獲取領先指標配置"""
        if not self.config:
            return {}

        cfg = self.config.leading_indicator
        return {
            "enabled": cfg.enabled,
            "ofi_enabled": cfg.ofi_enabled,
            "ofi_threshold": cfg.ofi_threshold,
            "volume_enabled": cfg.volume_enabled,
            "volume_surge_threshold": cfg.volume_surge_threshold,
            "spread_enabled": cfg.spread_enabled,
            "spread_surge_threshold": cfg.spread_surge_threshold
        }

    def update_leading_indicator_config(self, **kwargs) -> bool:
        """更新領先指標配置"""
        if not self.config:
            return False

        try:
            cfg = self.config.leading_indicator
            for key, value in kwargs.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, value)

            self.config.save()
            self._log("領先指標設定已更新")
            return True
        except Exception as e:
            self._log(f"更新失敗: {e}")
            return False

    def get_dgt_config(self) -> Dict:
        """獲取 DGT 配置"""
        if not self.config:
            return {}

        cfg = self.config.dgt
        return {
            "enabled": cfg.enabled,
            "reset_threshold": cfg.reset_threshold,
            "profit_reinvest_ratio": cfg.profit_reinvest_ratio,
            "boundary_buffer": cfg.boundary_buffer
        }

    def update_dgt_config(self, **kwargs) -> bool:
        """更新 DGT 配置"""
        if not self.config:
            return False

        try:
            cfg = self.config.dgt
            for key, value in kwargs.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, value)

            self.config.save()
            self._log("DGT 設定已更新")
            return True
        except Exception as e:
            self._log(f"更新失敗: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════
    # 風險管理設定
    # ═══════════════════════════════════════════════════════════════════════

    def get_risk_config(self) -> Dict:
        """獲取風險管理配置"""
        if not self.config:
            return {}

        cfg = self.config.risk
        return {
            "enabled": cfg.enabled,
            "margin_threshold": cfg.margin_threshold,
            "trailing_start_profit": cfg.trailing_start_profit,
            "trailing_drawdown_pct": cfg.trailing_drawdown_pct,
            "trailing_min_drawdown": cfg.trailing_min_drawdown
        }

    def update_risk_config(self, **kwargs) -> bool:
        """更新風險管理配置"""
        if not self.config:
            return False

        try:
            cfg = self.config.risk
            for key, value in kwargs.items():
                if hasattr(cfg, key):
                    setattr(cfg, key, value)

            self.config.save()
            self._log("風險管理設定已更新")
            return True
        except Exception as e:
            self._log(f"更新失敗: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════
    # 交易控制
    # ═══════════════════════════════════════════════════════════════════════

    async def start_trading(self, symbols: List[str] = None) -> bool:
        """
        開始交易

        Args:
            symbols: 交易對列表，None 表示使用配置中已啟用的
        """
        if not self.is_connected:
            self._log("請先連接交易所")
            return False

        if not self.is_verified:
            self._log("請先完成授權驗證")
            return False

        if self.is_trading:
            self._log("交易已在運行中")
            return False

        try:
            active_symbols = symbols or self.get_active_symbols()
            if not active_symbols:
                self._log("沒有可用的交易對")
                return False

            self._log(f"啟動交易: {', '.join(active_symbols)}")

            # 確保配置包含 API 憑證 (Bitget 需要 passphrase)
            if self.config and self._api_key and self._api_secret and self._passphrase:
                self.config.api_key = self._api_key
                self.config.api_secret = self._api_secret
                self.config.passphrase = self._passphrase

            self.is_trading = True
            self.start_time = datetime.now()
            self._stop_event.clear()
            self._update_status("交易中", True)

            # 在背景線程運行交易
            self._start_trading_thread()

            # 在另一個線程運行 UI 更新
            self._start_update_thread()

            return True

        except Exception as e:
            self._log(f"啟動失敗: {e}")
            self.is_trading = False
            self._update_status("啟動失敗", False)
            return False

    def _start_trading_thread(self):
        """在背景線程啟動 MaxGridBot"""
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._run_bot())
            except Exception as e:
                logger.error(f"交易線程錯誤: {e}")
            finally:
                loop.close()

        self._trading_thread = threading.Thread(target=run, daemon=True, name="TradingBot")
        self._trading_thread.start()

    async def _run_bot(self):
        """運行 MaxGridBot (Bitget)"""
        try:
            from as_terminal_max_bitget import MaxGridBot

            self._log("正在初始化 Bitget 交易機器人...")

            # 確保 API 憑證已設定 (Bitget 需要 passphrase)
            if not self.config.api_key or not self.config.api_secret or not self.config.passphrase:
                self._log("[錯誤] API 憑證未設定 (需要 API Key, Secret, Passphrase)!")
                return

            # 顯示啟用的交易對
            enabled = [s.symbol for s in self.config.symbols.values() if s.enabled]
            self._log(f"啟用交易對: {enabled}")
            self._log(f"API Key (前8碼): {self.config.api_key[:8]}...")

            # 創建 Bot 實例
            self.bot = MaxGridBot(self.config)

            # 設定回調
            self._setup_bot_callbacks()

            self._log("✓ 交易機器人啟動")

            # 運行 Bot（阻塞直到停止）
            await self.bot.run()

        except Exception as e:
            self._log(f"交易機器人錯誤: {e}")
            logger.error(f"Bot error: {e}", exc_info=True)
        finally:
            self._log("交易機器人已停止")
            self.is_trading = False
            self._update_status("已停止", False)

    def _setup_bot_callbacks(self):
        """設定 Bot 的回調函數"""
        if not self.bot:
            return

        # 同步 Bot 狀態到 GUI
        # Bot 的 state 包含所有交易狀態
        pass  # Bot 使用內部狀態，我們通過 _update_thread 讀取

    def _start_update_thread(self):
        """啟動 UI 更新線程"""
        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._update_loop())
            finally:
                loop.close()

        self._update_thread = threading.Thread(target=run, daemon=True, name="UIUpdater")
        self._update_thread.start()

    async def _update_loop(self):
        """UI 更新循環 - 定期同步 Bot 狀態到 GUI"""
        self._log("UI 更新循環啟動")

        import ccxt.async_support as ccxt

        # 創建獨立的 async exchange 用於 UI 更新 (Bitget 版本)
        update_exchange = ccxt.bitget({
            'apiKey': self._api_key,
            'secret': self._api_secret,
            'password': self._passphrase,  # Bitget 需要 passphrase
            'enableRateLimit': True,
            'options': {'defaultType': 'swap'}  # Bitget 永續合約
        })

        try:
            await update_exchange.load_markets()

            while self.is_trading and not self._stop_event.is_set():
                try:
                    # 更新持倉
                    await self._update_positions_from_exchange(update_exchange)

                    # 更新帳戶
                    balance = await update_exchange.fetch_balance()
                    await self._update_account(balance)

                    # 同步 Bot 狀態（如果可用）
                    self._sync_bot_state()

                    # 更新統計
                    self._update_stats()

                    # 更新授權心跳統計
                    if self.license_manager:
                        self.license_manager.update_stats(
                            symbols=self.get_active_symbols(),
                            total_trades=self.today_trades,
                            total_pnl=self.total_pnl
                        )

                except Exception as e:
                    logger.warning(f"更新循環錯誤: {e}")

                # 每秒更新一次
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"UI 更新循環錯誤: {e}")
        finally:
            try:
                await update_exchange.close()
            except Exception:
                pass
            self._log("UI 更新循環結束")

    async def _update_positions_from_exchange(self, exchange):
        """從交易所更新持倉"""
        try:
            positions = await exchange.fetch_positions()

            self.positions.clear()
            for pos in positions:
                if pos['contracts'] > 0:
                    symbol = pos['symbol'].replace('/', '').replace(':USDC', '').replace(':USDT', '')
                    side = "long" if pos['side'] == 'long' else "short"

                    self.positions[f"{symbol}_{side}"] = Position(
                        symbol=symbol,
                        side=side,
                        quantity=pos['contracts'],
                        entry_price=pos['entryPrice'] or 0,
                        unrealized_pnl=pos['unrealizedPnl'] or 0,
                        margin=pos['initialMargin'] or 0
                    )

                    # 更新 symbol_status
                    if symbol in self.symbol_status:
                        status = self.symbol_status[symbol]
                        if side == "long":
                            status.long_qty = pos['contracts']
                            status.long_entry = pos['entryPrice'] or 0
                            status.long_pnl = pos['unrealizedPnl'] or 0
                        else:
                            status.short_qty = pos['contracts']
                            status.short_entry = pos['entryPrice'] or 0
                            status.short_pnl = pos['unrealizedPnl'] or 0

            if self._on_position:
                self._on_position(self.positions)

            if self._on_symbol_status:
                self._on_symbol_status(self.symbol_status)

        except Exception as e:
            logger.warning(f"更新持倉失敗: {e}")

    def _sync_bot_state(self):
        """同步 Bot 狀態到 GUI"""
        if not self.bot or not hasattr(self.bot, 'state'):
            return

        state = self.bot.state

        # 同步交易對狀態
        for ccxt_symbol, sym_state in state.symbols.items():
            # 轉換 symbol 格式
            symbol = ccxt_symbol.replace('/', '').replace(':USDC', '').replace(':USDT', '')

            if symbol in self.symbol_status:
                status = self.symbol_status[symbol]
                status.price = sym_state.latest_price
                status.long_dead = sym_state.long_dead_mode
                status.short_dead = sym_state.short_dead_mode
                # SymbolState 沒有 double_tp 屬性，設為 False
                status.long_2x = False
                status.short_2x = False

        # 同步學習狀態
        if hasattr(self.bot, 'bandit_optimizer') and self.config.bandit.enabled:
            bandit = self.bot.bandit_optimizer
            self.learning_status.bandit_enabled = True
            self.learning_status.bandit_pulls = bandit.total_pulls
            self.learning_status.current_arm = bandit.current_arm_index

        if hasattr(self.bot, 'leading_indicator') and self.config.leading_indicator.enabled:
            leading = self.bot.leading_indicator
            self.learning_status.ofi_enabled = self.config.leading_indicator.ofi_enabled
            # 可以從 leading indicator 獲取更多狀態

        if self._on_learning:
            self._on_learning(self.learning_status)

        if self._on_symbol_status:
            self._on_symbol_status(self.symbol_status)


    async def _update_account(self, balance: Dict):
        """更新帳戶資訊"""
        try:
            for currency in ["USDC", "USDT"]:
                if currency in balance:
                    info = balance[currency]
                    total = info.get('total', 0) or 0
                    available = info.get('free', 0) or 0
                    # 計算保證金率: used_margin / total
                    used_margin = max(0, total - available)
                    margin_ratio = used_margin / total if total > 0 else 0

                    self.accounts[currency] = AccountInfo(
                        currency=currency,
                        equity=total,
                        available=available,
                        margin_ratio=margin_ratio,
                        unrealized_pnl=info.get('unrealizedPnl', 0) if 'unrealizedPnl' in info else 0
                    )

            if self._on_account:
                self._on_account(self.accounts)

        except Exception as e:
            logger.error(f"更新帳戶失敗: {e}")

    def _update_stats(self):
        """更新統計數據"""
        if not self.start_time:
            return

        runtime = datetime.now() - self.start_time
        hours, remainder = divmod(int(runtime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)

        # 計算總未實現盈虧
        unrealized_pnl = sum(p.unrealized_pnl for p in self.positions.values())

        stats = {
            "total_pnl": self.total_pnl,
            "unrealized_pnl": unrealized_pnl,
            "today_trades": self.today_trades,
            "runtime": f"{hours:02d}:{minutes:02d}:{seconds:02d}",
            "positions_count": len(self.positions),
            "active_symbols": len(self.get_active_symbols())
        }

        if self._on_stats:
            self._on_stats(stats)

    async def stop_trading(self):
        """停止交易"""
        if not self.is_trading:
            return

        self._log("停止交易...")

        # 設置停止標誌
        self._stop_event.set()
        self.is_trading = False

        # 停止 Bot
        if self.bot:
            try:
                await self.bot.stop()
            except Exception as e:
                logger.warning(f"停止 Bot 錯誤: {e}")
            self.bot = None

        # 等待線程結束
        if self._trading_thread and self._trading_thread.is_alive():
            self._trading_thread.join(timeout=5)

        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=3)

        self._update_status("已停止", False)
        self._log("交易已停止")

    def stop_trading_sync(self):
        """同步版本的停止交易（用於 GUI 按鈕）"""
        if not self.is_trading:
            return

        self._log("停止交易...")
        self._stop_event.set()
        self.is_trading = False

        # 停止 WebSocket
        self.stop_websocket()

        # 停止 Bot（在新線程中執行）
        def stop_bot():
            if self.bot:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    loop.run_until_complete(self.bot.stop())
                except Exception as e:
                    logger.warning(f"停止 Bot 錯誤: {e}")
                finally:
                    loop.close()
                self.bot = None

        stop_thread = threading.Thread(target=stop_bot, daemon=True)
        stop_thread.start()
        stop_thread.join(timeout=5)

        # 等待其他線程結束
        if self._trading_thread and self._trading_thread.is_alive():
            self._trading_thread.join(timeout=3)
            self._trading_thread = None

        if self._update_thread and self._update_thread.is_alive():
            self._update_thread.join(timeout=2)
            self._update_thread = None

        self._update_status("已停止", False)
        self._log("交易已停止")

    # ═══════════════════════════════════════════════════════════════════════
    # 快捷操作
    # ═══════════════════════════════════════════════════════════════════════

    async def close_all_positions(self):
        """一鍵平倉"""
        if not self.exchange:
            self._log("請先連接交易所")
            return

        self._log("執行一鍵平倉...")

        try:
            positions = await self.exchange.fetch_positions()

            for pos in positions:
                if pos['contracts'] > 0:
                    symbol = pos['symbol']
                    side = "sell" if pos['side'] == 'long' else "buy"
                    quantity = pos['contracts']

                    await self.exchange.create_market_order(
                        symbol=symbol,
                        side=side,
                        amount=quantity,
                        params={'reduceOnly': True}
                    )
                    self._log(f"平倉: {symbol} {quantity}")

            self._log("一鍵平倉完成")

        except Exception as e:
            self._log(f"平倉失敗: {e}")

    def pause_averaging(self, symbol: str):
        """暫停指定交易對的補倉"""
        # TODO: 實作補倉暫停邏輯
        self._log(f"暫停 {symbol} 補倉")

    def resume_averaging(self, symbol: str):
        """恢復指定交易對的補倉"""
        # TODO: 實作補倉恢復邏輯
        self._log(f"恢復 {symbol} 補倉")

    # ═══════════════════════════════════════════════════════════════════════
    # 回測功能
    # ═══════════════════════════════════════════════════════════════════════

    async def run_backtest(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        params: Dict = None
    ) -> Dict:
        """
        執行回測

        Args:
            symbol: 交易對
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            params: 參數配置

        Returns:
            回測結果
        """
        try:
            from as_terminal_max_bitget import BacktestManager, GridStrategy

            self._log(f"開始回測: {symbol} ({start_date} ~ {end_date})")

            # 建立回測管理器
            bt = BacktestManager()

            # 下載/載入數據
            data = await bt.load_or_download(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )

            if data is None or len(data) == 0:
                return {"error": "無法載入數據"}

            # 執行回測
            result = bt.run_backtest(
                data=data,
                params=params or {}
            )

            self._log(f"回測完成 - 收益: {result.get('return_pct', 0):.2f}%")

            return result

        except Exception as e:
            self._log(f"回測失敗: {e}")
            return {"error": str(e)}

    async def run_optimization(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        param_ranges: Dict = None
    ) -> List[Dict]:
        """
        執行參數優化

        Args:
            symbol: 交易對
            start_date: 開始日期
            end_date: 結束日期
            param_ranges: 參數範圍

        Returns:
            優化結果列表（按收益排序）
        """
        try:
            from as_terminal_max_bitget import BacktestManager

            self._log(f"開始參數優化: {symbol}")

            bt = BacktestManager()

            # 下載/載入數據
            data = await bt.load_or_download(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date
            )

            if data is None:
                return [{"error": "無法載入數據"}]

            # 執行優化
            results = bt.run_optimization(
                data=data,
                param_ranges=param_ranges or {}
            )

            self._log(f"優化完成 - 找到 {len(results)} 組結果")

            return results

        except Exception as e:
            self._log(f"優化失敗: {e}")
            return [{"error": str(e)}]

    # ═══════════════════════════════════════════════════════════════════════
    # 憑證管理（用於 GUI 授權對話框）
    # ═══════════════════════════════════════════════════════════════════════

    def is_credentials_configured(self) -> bool:
        """檢查是否已設定 API 憑證"""
        if not LICENSE_AVAILABLE or not self.credential_manager:
            return False
        return self.credential_manager.is_configured()

    def setup_credentials(self, api_key: str, api_secret: str, password: str, passphrase: str = "") -> Tuple[bool, str]:
        """
        首次設定 API 憑證 (Bitget 版本)

        Args:
            api_key: Bitget API Key
            api_secret: Bitget API Secret
            password: 加密密碼
            passphrase: Bitget Passphrase (必填)

        Returns:
            (成功, 錯誤訊息)
        """
        if not LICENSE_AVAILABLE or not self.credential_manager:
            return False, "授權模組未安裝"

        try:
            self.credential_manager.setup(api_key, api_secret, password, passphrase)
            return True, ""
        except ValueError as e:
            return False, str(e)
        except Exception as e:
            return False, f"設定失敗: {e}"

    def unlock_credentials(self, password: str) -> Tuple[bool, str, str, str, str]:
        """
        解鎖 API 憑證 (Bitget 版本)

        Args:
            password: 密碼

        Returns:
            (成功, 錯誤訊息, api_key, api_secret, passphrase)
        """
        if not LICENSE_AVAILABLE or not self.credential_manager:
            return False, "授權模組未安裝", "", "", ""

        try:
            api_key, api_secret, passphrase = self.credential_manager.unlock(password)
            return True, "", api_key, api_secret, passphrase
        except ValueError:
            return False, "密碼錯誤", "", "", ""
        except Exception as e:
            return False, f"解鎖失敗: {e}", "", "", ""

    def change_password(self, old_password: str, new_password: str) -> Tuple[bool, str]:
        """更換密碼"""
        if not LICENSE_AVAILABLE or not self.credential_manager:
            return False, "授權模組未安裝"

        try:
            self.credential_manager.change_password(old_password, new_password)
            return True, ""
        except ValueError:
            return False, "舊密碼錯誤"
        except Exception as e:
            return False, f"更換失敗: {e}"

    def reset_credentials(self) -> bool:
        """重置憑證（刪除加密檔案）"""
        if not LICENSE_AVAILABLE or not self.credential_manager:
            return False

        try:
            self.credential_manager.reset()
            return True
        except Exception:
            return False

    @staticmethod
    def check_password_strength(password: str) -> Tuple[int, str, List[str]]:
        """
        檢查密碼強度

        Returns:
            (分數 0-4, 等級名稱, 建議列表)
        """
        if not LICENSE_AVAILABLE:
            return 0, "未知", []

        return check_password_strength(password)


# ═══════════════════════════════════════════════════════════════════════════
# 單例模式
# ═══════════════════════════════════════════════════════════════════════════

_engine_instance: Optional[TradingEngine] = None


def get_engine() -> TradingEngine:
    """獲取交易引擎單例"""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = TradingEngine()
    return _engine_instance
