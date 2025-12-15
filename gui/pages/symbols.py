"""
交易對管理頁面
"""

import asyncio
import logging
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, TYPE_CHECKING

import customtkinter as ctk
import numpy as np

from ..styles import Colors
from ..components import Card, MiniChart, RiskBadge
from ..dialogs import (
    ConfirmDialog, AddSymbolDialog, EditSymbolDialog,
    BacktestDialog, OptimizeDialog
)

# 全局線程池（限制並發數量，避免同時啟動過多線程造成卡頓）
_thread_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="symbols_bg")

if TYPE_CHECKING:
    from gui.app import ASGridApp

# 設置 logger
logger = logging.getLogger("as_grid_gui")

# 導入 GridStrategy（統一使用終端 UI 的邏輯 - Bitget 版本）
try:
    from as_terminal_max_bitget import GridStrategy
    GRID_STRATEGY_AVAILABLE = True
except ImportError:
    GridStrategy = None
    GRID_STRATEGY_AVAILABLE = False
    logger.warning("無法導入 GridStrategy，回測功能可能受限")

# 延遲導入回測系統
_backtest_modules = {}

# 使用統一的路徑解析器（2025 最佳實踐）
try:
    from core.path_resolver import get_asback_path, ensure_backtest_module_path
    # 確保 backtest_system 路徑已設置
    ensure_backtest_module_path()
    _PATH_RESOLVER_AVAILABLE = True
except ImportError:
    _PATH_RESOLVER_AVAILABLE = False
    logger.warning("無法導入 core.path_resolver，使用備用路徑解析")

def _get_asback_path():
    """獲取 asBack 路徑（支援打包後的環境）"""
    # 優先使用統一路徑解析器
    if _PATH_RESOLVER_AVAILABLE:
        path = get_asback_path()
        if path:
            return str(path)

    # 備用方案：手動搜索
    possible_paths = [
        Path(__file__).parent.parent.parent / 'asBack',
        Path(sys.executable).parent / 'asBack',
        Path(sys.executable).parent.parent / 'Resources' / 'asBack',
        Path.cwd() / 'asBack',
    ]

    for path in possible_paths:
        if path.exists() and (path / 'backtest_system').exists():
            logger.info(f"找到 asBack 路徑: {path}")
            return str(path)

    logger.warning("無法找到有效的 asBack 路徑")
    return None

def _get_backtest_module(name):
    """延遲載入回測模組"""
    global _backtest_modules
    if name not in _backtest_modules:
        try:
            # 使用統一路徑解析器確保路徑已設置
            if _PATH_RESOLVER_AVAILABLE:
                ensure_backtest_module_path()
            else:
                asback_path = _get_asback_path()
                if asback_path and asback_path not in sys.path:
                    sys.path.insert(0, asback_path)
                    logger.info(f"成功添加 asBack 路徑到 sys.path: {asback_path}")

            if name == 'Config':
                from backtest_system import Config as BacktestConfig
                _backtest_modules['Config'] = BacktestConfig
            elif name == 'DataLoader':
                from backtest_system import DataLoader
                _backtest_modules['DataLoader'] = DataLoader
            elif name == 'GridBacktester':
                from backtest_system import GridBacktester
                _backtest_modules['GridBacktester'] = GridBacktester
            elif name == 'GridOptimizer':
                from backtest_system import GridOptimizer
                _backtest_modules['GridOptimizer'] = GridOptimizer

            logger.info(f"成功載入回測模組: {name}")
        except ImportError as e:
            logger.error(f"無法載入回測系統模組 {name}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    return _backtest_modules.get(name)

class SymbolsPage(ctk.CTkFrame):
    """交易對管理頁面 - 綁定 GlobalConfig"""

    def __init__(self, master, app: "ASGridApp"):
        super().__init__(master, fg_color=Colors.BG_PRIMARY)
        self.app = app
        self.config = None
        self._load_config()
        self._create_ui()

    def _load_config(self):
        """載入配置"""
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from as_terminal_max_bitget import GlobalConfig
            self.config = GlobalConfig.load()
        except Exception as e:
            logger.error(f"載入配置失敗: {e}")
            self.config = None

    def _save_config(self):
        """儲存配置"""
        if self.config:
            try:
                self.config.save()
                # ★ 通知交易頁面刷新交易對列表
                self._notify_trading_page_refresh()
            except Exception as e:
                logger.error(f"儲存配置失敗: {e}")

    def _notify_trading_page_refresh(self):
        """通知交易頁面刷新交易對列表"""
        try:
            # 透過 app 取得交易頁面並刷新
            if hasattr(self, 'app') and hasattr(self.app, 'pages'):
                trading_page = self.app.pages.get('trading')
                if trading_page and hasattr(trading_page, '_load_symbol_rows'):
                    trading_page._load_symbol_rows()
        except Exception as e:
            logger.debug(f"刷新交易頁面失敗: {e}")

    def _create_ui(self):
        # 標題區
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(header, text="交易對管理", font=ctk.CTkFont(size=20, weight="bold"), text_color=Colors.TEXT_PRIMARY).pack(side="left")

        ctk.CTkButton(
            header,
            text="+ 新增交易對",
            font=ctk.CTkFont(size=13),
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            height=36,
            corner_radius=8,
            command=self._add_symbol
        ).pack(side="right")

        # 交易對列表
        self.symbols_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.symbols_frame.pack(fill="both", expand=True)

        # 從 GlobalConfig 載入交易對
        self._load_symbols_from_config()

    def _load_symbols_from_config(self):
        """從 GlobalConfig 載入交易對"""
        if self.config and self.config.symbols:
            for raw_symbol, sym_cfg in self.config.symbols.items():
                data = {
                    "symbol": raw_symbol,
                    "enabled": sym_cfg.enabled,
                    "tp": f"{sym_cfg.take_profit_spacing * 100:.1f}%",
                    "gs": f"{sym_cfg.grid_spacing * 100:.1f}%",
                    "qty": sym_cfg.initial_quantity,
                    "leverage": sym_cfg.leverage,
                    "limit_mult": getattr(sym_cfg, 'limit_multiplier', 5.0),
                    "threshold_mult": getattr(sym_cfg, 'threshold_multiplier', 20.0)
                }
                self._create_symbol_row(data)
        else:
            # 如果沒有配置，顯示預設範例
            symbols = [
                {"symbol": "XRPUSDC", "enabled": True, "tp": "0.4%", "gs": "0.6%", "qty": 30, "leverage": 20},
            ]
            for s in symbols:
                self._create_symbol_row(s)

    def _create_symbol_row(self, data: Dict):
        """創建增強版交易對卡片 - 含迷你圖表、評分和優化按鈕"""
        row = ctk.CTkFrame(self.symbols_frame, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        row.pack(fill="x", pady=4, padx=2)
        row.data = data  # 儲存數據

        # 使用 grid 佈局確保對齊
        row.grid_columnconfigure(0, weight=0, minsize=180)  # 左側：交易對資訊
        row.grid_columnconfigure(1, weight=0, minsize=140)  # 中間：圖表
        row.grid_columnconfigure(2, weight=1)               # 彈性空間
        row.grid_columnconfigure(3, weight=0)               # 右側：按鈕

        # ======== 左側：交易對基本資訊 ========
        left = ctk.CTkFrame(row, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w", padx=(16, 8), pady=10)

        # 交易對名稱 + 狀態 + 評分徽章
        name_row = ctk.CTkFrame(left, fg_color="transparent")
        name_row.pack(anchor="w")

        # 狀態指示燈
        status_color = Colors.STATUS_ON if data["enabled"] else Colors.STATUS_OFF
        ctk.CTkLabel(
            name_row, text="●",
            font=ctk.CTkFont(size=10),
            text_color=status_color
        ).pack(side="left", padx=(0, 4))

        ctk.CTkLabel(
            name_row,
            text=data["symbol"],
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(side="left")

        # 風險評分徽章
        row.risk_badge = RiskBadge(name_row, score=0)
        row.risk_badge.pack(side="left", padx=(8, 0))

        # 參數摘要 (分兩行顯示)
        ctk.CTkLabel(
            left,
            text=f"TP: {data['tp']} | GS: {data['gs']}",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED
        ).pack(anchor="w")

        ctk.CTkLabel(
            left,
            text=f"數量: {data['qty']} | 槓桿: {data['leverage']}x",
            font=ctk.CTkFont(size=10),
            text_color=Colors.TEXT_MUTED
        ).pack(anchor="w")

        # ======== 中間：7日回測預覽 (橫向布局：左圖右數據，不框住) ========
        center = ctk.CTkFrame(row, fg_color="transparent")
        center.grid(row=0, column=1, sticky="w", padx=8, pady=8)

        # 左側：迷你曲線圖 (只有這個有框)
        chart_frame = ctk.CTkFrame(
            center,
            fg_color=Colors.FILL_POSITIVE,
            corner_radius=4,
            border_width=1,
            border_color=Colors.BORDER,
            cursor="hand2"
        )
        chart_frame.pack(side="left", padx=(0, 10))
        chart_frame.bind("<Button-1>", lambda e, r=row: self._run_quick_backtest(r))

        row.mini_chart = MiniChart(
            chart_frame,
            width=100,
            height=50,
            clickable=True,
            on_click=lambda r=row: self._run_quick_backtest(r)
        )
        row.mini_chart.pack(padx=3, pady=3)

        # 右側：數據區 (無框，直接顯示)
        data_frame = ctk.CTkFrame(center, fg_color="transparent")
        data_frame.pack(side="left", fill="y")

        # 標題 + 收益率
        title_row = ctk.CTkFrame(data_frame, fg_color="transparent")
        title_row.pack(fill="x")

        ctk.CTkLabel(
            title_row,
            text="30日",
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=Colors.TEXT_MUTED
        ).pack(side="left")

        row.return_label = ctk.CTkLabel(
            title_row,
            text="--",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEXT_MUTED
        )
        row.return_label.pack(side="left", padx=(4, 0))

        # 載入狀態標籤
        row.backtest_label = ctk.CTkLabel(
            title_row,
            text="載入中...",
            font=ctk.CTkFont(size=8),
            text_color=Colors.TEXT_MUTED
        )
        row.backtest_label.pack(side="left", padx=(6, 0))

        # 第一行數據：交易 + 勝率
        row1 = ctk.CTkFrame(data_frame, fg_color="transparent")
        row1.pack(fill="x", pady=(2, 0))

        row.trades_label = ctk.CTkLabel(
            row1, text="交易: --",
            font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED
        )
        row.trades_label.pack(side="left", padx=(0, 8))

        row.winrate_label = ctk.CTkLabel(
            row1, text="勝率: --",
            font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED
        )
        row.winrate_label.pack(side="left")

        # 第二行數據：夏普 + 回撤
        row2 = ctk.CTkFrame(data_frame, fg_color="transparent")
        row2.pack(fill="x", pady=(1, 0))

        row.sharpe_label = ctk.CTkLabel(
            row2, text="夏普: --",
            font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED
        )
        row.sharpe_label.pack(side="left", padx=(0, 8))

        row.drawdown_label = ctk.CTkLabel(
            row2, text="回撤: --",
            font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED
        )
        row.drawdown_label.pack(side="left")

        # ======== 右側：操作按鈕組 ========
        right = ctk.CTkFrame(row, fg_color="transparent")
        right.grid(row=0, column=3, sticky="e", padx=(8, 12), pady=10)

        # 按鈕分組：主要操作 | 設定 | 危險操作
        # 主要操作按鈕組
        primary_btns = ctk.CTkFrame(right, fg_color="transparent")
        primary_btns.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            primary_btns, text="詳情",
            font=ctk.CTkFont(size=11),
            fg_color=Colors.FILL_HIGHLIGHT,
            hover_color=Colors.BORDER_LIGHT,
            text_color=Colors.TEXT_PRIMARY,
            width=48, height=28,
            corner_radius=4,
            command=lambda r=row: self._goto_backtest_page(r)
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            primary_btns, text="優化",
            font=ctk.CTkFont(size=11),
            fg_color=Colors.FILL_POSITIVE,
            hover_color=Colors.FILL_HIGHLIGHT,
            text_color=Colors.TEXT_SECONDARY,
            width=48, height=28,
            corner_radius=4,
            command=lambda r=row: self._open_quick_optimize(r)
        ).pack(side="left")

        # 分隔線
        sep = ctk.CTkFrame(right, fg_color=Colors.BORDER, width=1, height=24)
        sep.pack(side="left", padx=8)

        # 設定按鈕組
        config_btns = ctk.CTkFrame(right, fg_color="transparent")
        config_btns.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            config_btns, text="編輯",
            font=ctk.CTkFont(size=11),
            fg_color=Colors.BG_TERTIARY,
            hover_color=Colors.BORDER,
            width=48, height=28,
            corner_radius=4,
            command=lambda: self._edit_symbol(data)
        ).pack(side="left", padx=(0, 4))

        # 切換開關
        row.toggle_btn = ctk.CTkButton(
            config_btns,
            text="啟用" if data["enabled"] else "停用",
            font=ctk.CTkFont(size=11),
            fg_color=Colors.STATUS_ON if data["enabled"] else Colors.BG_TERTIARY,
            hover_color=Colors.BORDER,
            text_color=Colors.BG_PRIMARY if data["enabled"] else Colors.TEXT_MUTED,
            width=48, height=28,
            corner_radius=4,
            command=lambda r=row: self._toggle_symbol(r)
        )
        row.toggle_btn.pack(side="left")

        # 分隔線
        sep2 = ctk.CTkFrame(right, fg_color=Colors.BORDER, width=1, height=24)
        sep2.pack(side="left", padx=8)

        # 危險操作
        ctk.CTkButton(
            right, text="刪除",
            font=ctk.CTkFont(size=11),
            fg_color=Colors.BG_TERTIARY,
            hover_color=Colors.BORDER,
            text_color=Colors.TEXT_MUTED,
            width=48, height=28,
            corner_radius=4,
            command=lambda r=row: self._delete_symbol(r)
        ).pack(side="left")

        # 自動載入評分和 30 日回測預覽 (非同步)
        self._load_coin_score(row)
        self._load_30day_preview(row)

    def _load_coin_score(self, row):
        """載入幣種評分 (非同步)"""
        symbol = row.data["symbol"]
        page_self = self

        # 在主線程中先檢查頁面和行是否存在
        try:
            if not page_self.winfo_exists() or not row.winfo_exists():
                return
        except Exception:
            return

        def fetch_score():
            try:
                if hasattr(page_self.app, 'engine') and page_self.app.engine:
                    engine = page_self.app.engine

                    # 等待 engine 完全連接後才進行評分
                    # 這避免了與連接過程的 event loop 衝突
                    if not getattr(engine, 'is_connected', False):
                        # 尚未連接，延遲重試（需要在主線程中調用 after）
                        try:
                            page_self.after(2000, lambda: page_self._load_coin_score(row))
                        except RuntimeError:
                            pass  # 頁面可能已銷毀
                        return

                    # 獲取 API 憑證（如果有的話）
                    api_key = getattr(engine, '_api_key', None)
                    api_secret = getattr(engine, '_api_secret', None)
                    api_passphrase = getattr(engine, '_api_passphrase', None)

                    if api_key and api_secret:
                        from coin_selection import CoinScorer
                        import ccxt.async_support as ccxt_async

                        async def get_score():
                            # 為每個線程創建獨立的 exchange 實例
                            local_exchange = ccxt_async.bitget({
                                'apiKey': api_key,
                                'secret': api_secret,
                                'password': api_passphrase,
                                'enableRateLimit': True,
                                'options': {
                                    'defaultType': 'swap',
                                    'adjustForTimeDifference': True
                                }
                            })
                            try:
                                scorer = CoinScorer()
                                ccxt_symbol = symbol.replace("USDC", "/USDC:USDC").replace("USDT", "/USDT:USDT")
                                score = await scorer.score_coin(ccxt_symbol, local_exchange)
                                return score.final_score
                            finally:
                                await local_exchange.close()

                        # 為此線程創建新的 event loop
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            score = loop.run_until_complete(get_score())

                            def update_score():
                                try:
                                    if not page_self.winfo_exists():
                                        return
                                    if row.winfo_exists() and hasattr(row, 'risk_badge') and row.risk_badge.winfo_exists():
                                        row.risk_badge.set_score(score)
                                except Exception as ui_e:
                                    logger.debug(f"更新評分 UI 跳過 ({symbol}): {ui_e}")

                            try:
                                page_self.after(0, update_score)
                            except RuntimeError:
                                pass
                        except Exception as e:
                            logger.error(f"獲取評分時發生錯誤 ({symbol}): {e}")
                        finally:
                            loop.close()
            except Exception as e:
                logger.debug(f"載入評分失敗 ({symbol}): {e}")

        _thread_pool.submit(fetch_score)

    def _load_30day_preview(self, row, retry_after_download=False):
        """載入近 30 日回測預覽 (使用與終端 UI 完全相同的 GridStrategy 逻辑)"""
        symbol = row.data["symbol"]
        page_self = self  # 保存對頁面的引用，用於安全的 UI 更新

        # 在主執行緒中先檢查頁面是否存在（避免 "main thread is not in main loop" 錯誤）
        try:
            if not page_self.winfo_exists():
                return
        except Exception:
            return

        def load_preview():
            try:
                # 不在背景執行緒中調用 winfo_exists()，因為這會導致
                # "main thread is not in main loop" 錯誤
                # 改為使用 try-except 來處理 UI 更新失敗的情況
                pass  # 頁面存在性檢查已移至主執行緒

                DataLoader = _get_backtest_module('DataLoader')
                if not DataLoader:
                    def show_module_error():
                        try:
                            if not page_self.winfo_exists():
                                return
                            if hasattr(row, 'backtest_label') and row.winfo_exists():
                                row.backtest_label.configure(text="模块加载失败", text_color=Colors.TEXT_MUTED)
                        except Exception as e:
                            logger.debug(f"更新 UI 跳過 ({symbol}): {e}")
                    try:
                        page_self.after(0, show_module_error)
                    except RuntimeError:
                        pass
                    return

                # 載入 30 日數據
                loader = DataLoader()
                df = loader.load_symbol_data(symbol, timeframe='1m', days=30)

                # 改進的數據不足處理：如果數據缺失且還沒嘗試下載，則自動下載
                if df is None and not retry_after_download:
                    # 顯示正在下載的狀態
                    def show_downloading():
                        try:
                            if not page_self.winfo_exists():
                                return
                            if hasattr(row, 'backtest_label') and row.winfo_exists():
                                row.backtest_label.configure(text="下載數據中...", text_color=Colors.TEXT_MUTED)
                        except Exception as e:
                            logger.debug(f"更新 UI 跳過 ({symbol}): {e}")
                    try:
                        page_self.after(0, show_downloading)
                    except RuntimeError:
                        pass

                    # 嘗試自動下載數據
                    try:
                        logger.info(f"自動下載 {symbol} 回測數據...")
                        download_success = loader.download(
                            symbol=symbol,
                            start_date=__import__('datetime').datetime.now() - __import__('datetime').timedelta(days=30),
                            end_date=__import__('datetime').datetime.now(),
                            interval='1m'
                        )

                        if download_success:
                            # 下載成功，重新載入
                            def retry_load():
                                try:
                                    if page_self.winfo_exists() and row.winfo_exists():
                                        page_self._load_30day_preview(row, retry_after_download=True)
                                except Exception as e:
                                    logger.debug(f"重試載入跳過 ({symbol}): {e}")
                            try:
                                page_self.after(0, retry_load)
                            except RuntimeError:
                                pass
                            return
                    except Exception as download_error:
                        logger.warning(f"自動下載 {symbol} 失敗: {download_error}")

                    # 下載失敗，顯示無數據
                    def show_no_data():
                        try:
                            if not page_self.winfo_exists():
                                return
                            if hasattr(row, 'backtest_label') and row.winfo_exists():
                                row.backtest_label.configure(text="无数据", text_color=Colors.TEXT_MUTED)
                            if hasattr(row, 'return_label') and row.winfo_exists():
                                row.return_label.configure(text="--")
                        except Exception as e:
                            logger.debug(f"更新 UI 跳過 ({symbol}): {e}")
                    try:
                        page_self.after(0, show_no_data)
                    except RuntimeError:
                        pass
                    return

                # 數據仍然為 None（下載後重試仍失敗）
                if df is None:
                    def show_no_data():
                        try:
                            if not page_self.winfo_exists():
                                return
                            if hasattr(row, 'backtest_label') and row.winfo_exists():
                                row.backtest_label.configure(text="无数据", text_color=Colors.TEXT_MUTED)
                            if hasattr(row, 'return_label') and row.winfo_exists():
                                row.return_label.configure(text="--")
                        except Exception as e:
                            logger.debug(f"更新 UI 跳過 ({symbol}): {e}")
                    try:
                        page_self.after(0, show_no_data)
                    except RuntimeError:
                        pass
                    return

                if len(df) < 100:  # 統一使用 100 根 K 線作為最低閾值
                    actual_days = len(df) // 1440 if len(df) >= 1440 else 0
                    def show_insufficient_data():
                        try:
                            if not page_self.winfo_exists():
                                return
                            if hasattr(row, 'backtest_label') and row.winfo_exists():
                                if actual_days > 0:
                                    row.backtest_label.configure(text=f"仅{actual_days}日", text_color=Colors.TEXT_MUTED)
                                else:
                                    row.backtest_label.configure(text="数据不足", text_color=Colors.TEXT_MUTED)
                            if hasattr(row, 'return_label') and row.winfo_exists():
                                row.return_label.configure(text="--")
                        except Exception as e:
                            logger.debug(f"更新 UI 跳過 ({symbol}): {e}")
                    try:
                        page_self.after(0, show_insufficient_data)
                    except RuntimeError:
                        pass
                    return

                # 數據取樣優化：限制 K 線數量以加速預覽回測
                # 15000 條約等於 10 天的 1 分鐘 K 線，足夠顯示預覽效果
                MAX_PREVIEW_KLINES = 15000
                if len(df) > MAX_PREVIEW_KLINES:
                    # 取最近的數據進行預覽
                    df = df.tail(MAX_PREVIEW_KLINES).reset_index(drop=True)
                    logger.debug(f"{symbol} 數據取樣: {len(df)} 條用於預覽")

                # GridStrategy 已在檔案頂部從 as_terminal_max 導入，確保 GUI 與終端邏輯一致
                if not GRID_STRATEGY_AVAILABLE:
                    def show_no_strategy():
                        try:
                            if not page_self.winfo_exists():
                                return
                            if hasattr(row, 'backtest_label') and row.winfo_exists():
                                row.backtest_label.configure(text="策略不可用", text_color=Colors.TEXT_MUTED)
                        except Exception as e:
                            logger.debug(f"更新 UI 跳過 ({symbol}): {e}")
                    try:
                        page_self.after(0, show_no_strategy)
                    except RuntimeError:
                        pass
                    return

                # 解析參數 (與終端 UI 一致)
                tp = float(row.data['tp'].replace('%', '')) / 100
                gs = float(row.data['gs'].replace('%', '')) / 100
                initial_quantity = float(row.data['qty'])  # 幣的數量
                leverage = int(row.data['leverage'])
                limit_mult = float(row.data.get('limit_mult', 5.0))
                threshold_mult = float(row.data.get('threshold_mult', 20.0))

                # 計算 position_threshold 和 position_limit (與終端 UI 一致)
                position_threshold = initial_quantity * threshold_mult
                position_limit = initial_quantity * limit_mult

                # === 回測邏輯 (與終端 UI BacktestManager.run_backtest 完全一致) ===
                balance = 1000.0
                max_equity = balance
                order_value = initial_quantity * df['close'].iloc[0]  # 幣數量 × 價格
                fee_pct = 0.0004

                long_positions = []
                short_positions = []
                trades = []
                equity_curve = []

                last_long_price = df['close'].iloc[0]
                last_short_price = df['close'].iloc[0]

                for _, kline in df.iterrows():
                    price = kline['close']

                    # 計算當前持倉量
                    long_position = sum(p["qty"] for p in long_positions)
                    short_position = sum(p["qty"] for p in short_positions)

                    # === 多頭網格 (使用 GridStrategy 統一邏輯) ===
                    long_decision = GridStrategy.get_grid_decision(
                        price=last_long_price,
                        my_position=long_position,
                        opposite_position=short_position,
                        position_threshold=position_threshold,
                        position_limit=position_limit,
                        base_qty=initial_quantity,
                        take_profit_spacing=tp,
                        grid_spacing=gs,
                        side='long'
                    )

                    sell_price = long_decision['tp_price']
                    long_tp_qty = long_decision['tp_qty']
                    long_dead_mode = long_decision['dead_mode']
                    buy_price = long_decision['entry_price'] if long_decision['entry_price'] else last_long_price * (1 - gs)

                    if not long_dead_mode:
                        # 【正常模式】補倉邏輯
                        if price <= buy_price:
                            qty = order_value / price
                            margin = (qty * price) / leverage
                            fee = qty * price * fee_pct
                            if margin + fee < balance:
                                balance -= (margin + fee)
                                long_positions.append({"price": price, "qty": qty, "margin": margin})
                                last_long_price = price

                    # 止盈邏輯 (兩種模式都執行)
                    if price >= sell_price and long_positions:
                        remaining_tp = long_tp_qty
                        while long_positions and remaining_tp > 0:
                            pos = long_positions[0]
                            if pos["qty"] <= remaining_tp:
                                long_positions.pop(0)
                                gross_pnl = (price - pos["price"]) * pos["qty"]
                                fee = pos["qty"] * price * fee_pct
                                net_pnl = gross_pnl - fee
                                balance += pos["margin"] + net_pnl
                                trades.append({"pnl": net_pnl, "type": "long"})
                                remaining_tp -= pos["qty"]
                            else:
                                close_ratio = remaining_tp / pos["qty"]
                                close_qty = remaining_tp
                                close_margin = pos["margin"] * close_ratio
                                gross_pnl = (price - pos["price"]) * close_qty
                                fee = close_qty * price * fee_pct
                                net_pnl = gross_pnl - fee
                                balance += close_margin + net_pnl
                                trades.append({"pnl": net_pnl, "type": "long"})
                                pos["qty"] -= close_qty
                                pos["margin"] -= close_margin
                                remaining_tp = 0
                        last_long_price = price

                    # === 空頭網格 (使用 GridStrategy 統一邏輯) ===
                    short_decision = GridStrategy.get_grid_decision(
                        price=last_short_price,
                        my_position=short_position,
                        opposite_position=long_position,
                        position_threshold=position_threshold,
                        position_limit=position_limit,
                        base_qty=initial_quantity,
                        take_profit_spacing=tp,
                        grid_spacing=gs,
                        side='short'
                    )

                    cover_price = short_decision['tp_price']
                    short_tp_qty = short_decision['tp_qty']
                    short_dead_mode = short_decision['dead_mode']
                    sell_short_price = short_decision['entry_price'] if short_decision['entry_price'] else last_short_price * (1 + gs)

                    if not short_dead_mode:
                        # 【正常模式】補倉邏輯
                        if price >= sell_short_price:
                            qty = order_value / price
                            margin = (qty * price) / leverage
                            fee = qty * price * fee_pct
                            if margin + fee < balance:
                                balance -= (margin + fee)
                                short_positions.append({"price": price, "qty": qty, "margin": margin})
                                last_short_price = price

                    # 止盈邏輯 (兩種模式都執行)
                    if price <= cover_price and short_positions:
                        remaining_tp = short_tp_qty
                        while short_positions and remaining_tp > 0:
                            pos = short_positions[0]
                            if pos["qty"] <= remaining_tp:
                                short_positions.pop(0)
                                gross_pnl = (pos["price"] - price) * pos["qty"]
                                fee = pos["qty"] * price * fee_pct
                                net_pnl = gross_pnl - fee
                                balance += pos["margin"] + net_pnl
                                trades.append({"pnl": net_pnl, "type": "short"})
                                remaining_tp -= pos["qty"]
                            else:
                                close_ratio = remaining_tp / pos["qty"]
                                close_qty = remaining_tp
                                close_margin = pos["margin"] * close_ratio
                                gross_pnl = (pos["price"] - price) * close_qty
                                fee = close_qty * price * fee_pct
                                net_pnl = gross_pnl - fee
                                balance += close_margin + net_pnl
                                trades.append({"pnl": net_pnl, "type": "short"})
                                pos["qty"] -= close_qty
                                pos["margin"] -= close_margin
                                remaining_tp = 0
                        last_short_price = price

                    # 計算淨值
                    unrealized = sum((price - p["price"]) * p["qty"] for p in long_positions)
                    unrealized += sum((p["price"] - price) * p["qty"] for p in short_positions)
                    equity = balance + unrealized
                    max_equity = max(max_equity, equity)
                    equity_curve.append(equity)

                # 計算結果
                final_price = df['close'].iloc[-1]
                unrealized_pnl = sum((final_price - p["price"]) * p["qty"] for p in long_positions)
                unrealized_pnl += sum((p["price"] - final_price) * p["qty"] for p in short_positions)
                final_equity = balance + unrealized_pnl

                winning = [t for t in trades if t["pnl"] > 0]
                final_return = (final_equity - 1000) / 1000 * 100
                max_drawdown = (1 - min(equity_curve) / max_equity) * 100 if equity_curve else 0
                win_rate = len(winning) / len(trades) * 100 if trades else 0

                # 計算夏普比率 (基於權益曲線收益率，年化)
                # 正確公式: Sharpe = (平均收益率 / 收益率標準差) × √(年化因子)
                sharpe_ratio = 0.0
                if len(equity_curve) > 1:
                    # 計算逐期收益率
                    returns = []
                    for i in range(1, len(equity_curve)):
                        prev_equity = equity_curve[i - 1]
                        curr_equity = equity_curve[i]
                        if prev_equity > 0:
                            returns.append((curr_equity - prev_equity) / prev_equity)

                    if len(returns) > 1:
                        mean_return = np.mean(returns)
                        std_return = np.std(returns, ddof=1)  # 使用樣本標準差

                        if std_return > 0:
                            # 數據是 1 分鐘 K 線，一年約 525600 分鐘
                            # 但權益曲線按 K 線更新，所以年化因子 = √(525600)
                            periods_per_year = 525600
                            sharpe_ratio = (mean_return / std_return) * np.sqrt(periods_per_year)
                        else:
                            sharpe_ratio = 0.0

                # 取樣曲線 (確保包含最後一個數據點)
                if len(equity_curve) > 30:
                    step = len(equity_curve) // 30
                    sampled_curve = equity_curve[::step]
                    # 確保包含最後一個點（最終權益）
                    if sampled_curve[-1] != equity_curve[-1]:
                        sampled_curve.append(equity_curve[-1])
                else:
                    sampled_curve = equity_curve

                return_text = f"{final_return:+.1f}%"
                return_color = Colors.GREEN if final_return > 0 else Colors.RED if final_return < 0 else Colors.TEXT_MUTED

                # 更新 UI (使用 page_self.after 而不是 row.after 避免線程錯誤)
                def update_ui():
                    try:
                        # 檢查頁面和 row 是否仍然存在
                        if not page_self.winfo_exists():
                            return
                        if not row.winfo_exists():
                            return
                        if hasattr(row, 'mini_chart') and row.mini_chart.winfo_exists():
                            row.mini_chart.set_data(sampled_curve)
                        if hasattr(row, 'return_label') and row.return_label.winfo_exists():
                            row.return_label.configure(text=return_text, text_color=return_color)
                        if hasattr(row, 'sharpe_label') and row.sharpe_label.winfo_exists():
                            row.sharpe_label.configure(text=f"夏普: {sharpe_ratio:.2f}")
                        if hasattr(row, 'trades_label') and row.trades_label.winfo_exists():
                            row.trades_label.configure(text=f"交易: {len(trades)}")
                        if hasattr(row, 'winrate_label') and row.winrate_label.winfo_exists():
                            row.winrate_label.configure(text=f"勝率: {win_rate:.0f}%")
                        if hasattr(row, 'drawdown_label') and row.drawdown_label.winfo_exists():
                            row.drawdown_label.configure(text=f"回撤: {max_drawdown:.1f}%")
                        if hasattr(row, 'backtest_label') and row.backtest_label.winfo_exists():
                            row.backtest_label.configure(text="")
                    except Exception as e:
                        logger.debug(f"更新 UI 跳過 ({symbol}): {e}")

                try:
                    page_self.after(0, update_ui)
                except RuntimeError:
                    # 主執行緒已關閉，跳過 UI 更新
                    pass

            except Exception as e:
                logger.error(f"載入回測預覽失败 ({symbol}): {e}")
                import traceback
                logger.error(traceback.format_exc())
                def show_error():
                    try:
                        if not page_self.winfo_exists():
                            return
                        if row.winfo_exists():
                            if hasattr(row, 'backtest_label') and row.backtest_label.winfo_exists():
                                row.backtest_label.configure(text="载入失败", text_color=Colors.TEXT_MUTED)
                            if hasattr(row, 'return_label') and row.return_label.winfo_exists():
                                row.return_label.configure(text="--")
                    except Exception as ui_e:
                        logger.debug(f"显示错误讯息跳過 ({symbol}): {ui_e}")
                try:
                    page_self.after(0, show_error)
                except RuntimeError:
                    pass

        # 使用線程池執行（限制並發數量）
        _thread_pool.submit(load_preview)

    def _goto_backtest_page(self, row):
        """跳轉到回測頁面並帶入參數（可進行回測或優化）"""
        symbol_data = row.data
        # 使用 AppState 系統傳遞參數，取代 after(100) hack
        self.app.show_page("backtest", params=symbol_data, action='backtest')

    def _open_quick_optimize(self, row):
        """打開快速優化對話框（不跳轉頁面）"""
        OptimizeDialog(self, row)

    def _add_symbol(self):
        """新增交易對對話框"""
        AddSymbolDialog(self)

    def _edit_symbol(self, data: Dict):
        """編輯交易對"""
        EditSymbolDialog(self, data)

    def _toggle_symbol(self, row):
        """切換交易對狀態並持久化"""
        row.data["enabled"] = not row.data["enabled"]
        enabled = row.data["enabled"]

        # 更新切換按鈕樣式
        if hasattr(row, 'toggle_btn'):
            row.toggle_btn.configure(
                text="啟用" if enabled else "停用",
                fg_color=Colors.STATUS_ON if enabled else Colors.BG_TERTIARY,
                text_color=Colors.BG_PRIMARY if enabled else Colors.TEXT_MUTED
            )

        # 持久化到 GlobalConfig
        if self.config and row.data["symbol"] in self.config.symbols:
            self.config.symbols[row.data["symbol"]].enabled = enabled
            self._save_config()

    def _delete_symbol(self, row):
        """刪除交易對 - 需要確認"""
        symbol = row.data["symbol"]

        def do_delete():
            row.destroy()
            # 持久化到 GlobalConfig
            if self.config and symbol in self.config.symbols:
                del self.config.symbols[symbol]
                self._save_config()

        ConfirmDialog(
            self,
            title="刪除交易對",
            message=f"確定要刪除 {symbol}？",
            details="刪除後此交易對的所有設定將被清除，此操作無法復原。",
            confirm_text="刪除",
            danger=True,
            on_confirm=do_delete
        )

    def add_symbol_to_config(self, data: Dict):
        """新增交易對到 GlobalConfig 並持久化"""
        if not self.config:
            return

        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from as_terminal_max_bitget import SymbolConfig

            raw = data["symbol"]
            # 轉換 symbol 格式
            coin = raw.replace("USDC", "").replace("USDT", "")
            base = "USDC" if "USDC" in raw else "USDT"
            ccxt = f"{coin}/{base}:{base}"

            self.config.symbols[raw] = SymbolConfig(
                symbol=raw,
                ccxt_symbol=ccxt,
                enabled=data["enabled"],
                take_profit_spacing=float(data['tp'].replace('%', '')) / 100,
                grid_spacing=float(data['gs'].replace('%', '')) / 100,
                initial_quantity=float(data['qty']),
                leverage=int(data['leverage']),
                limit_multiplier=float(data.get('limit_mult', 5.0)),
                threshold_multiplier=float(data.get('threshold_mult', 20.0))
            )
            self._save_config()
        except Exception as e:
            print(f"新增交易對失敗: {e}")

    def update_symbol_in_config(self, symbol: str, data: Dict):
        """更新 GlobalConfig 中的交易對並持久化"""
        if self.config and symbol in self.config.symbols:
            sym_cfg = self.config.symbols[symbol]
            sym_cfg.enabled = data["enabled"]
            sym_cfg.take_profit_spacing = float(data['tp'].replace('%', '')) / 100
            sym_cfg.grid_spacing = float(data['gs'].replace('%', '')) / 100
            sym_cfg.initial_quantity = float(data['qty'])
            sym_cfg.leverage = int(data['leverage'])
            sym_cfg.limit_multiplier = float(data.get('limit_mult', 5.0))
            sym_cfg.threshold_multiplier = float(data.get('threshold_mult', 20.0))
            self._save_config()

    def refresh(self):
        """刷新列表"""
        for widget in self.symbols_frame.winfo_children():
            widget.destroy()
        self._load_config()
        self._load_symbols_from_config()
