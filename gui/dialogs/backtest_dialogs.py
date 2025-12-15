"""
回測相關對話框

包含:
- BacktestDialog: 完整回測功能對話框
- OptimizeDialog: 參數優化對話框
"""

import logging
import sys
import threading
from pathlib import Path
import customtkinter as ctk
from typing import Dict
from ..styles import Colors
from ..components import MiniChart
from .base import ConfirmDialog

logger = logging.getLogger(__name__)


def _ensure_backtest_path():
    """確保 asBack/backtest_system 路徑已加入 sys.path"""
    # 找到 gui 目錄的父目錄（項目根目錄）
    gui_dir = Path(__file__).parent.parent  # gui/dialogs -> gui
    project_root = gui_dir.parent  # gui -> 項目根目錄
    asback_path = project_root / "asBack"

    if asback_path.exists() and str(asback_path) not in sys.path:
        sys.path.insert(0, str(asback_path))
        logger.debug(f"Added asBack to sys.path: {asback_path}")
        return True
    return asback_path.exists()


def _get_backtest_module(name: str):
    """動態載入回測模組"""
    # 確保路徑已設置
    _ensure_backtest_path()

    try:
        if name == 'GridBacktester':
            from backtest_system import GridBacktester
            return GridBacktester
        elif name == 'GridOptimizer':
            from backtest_system import GridOptimizer
            return GridOptimizer
        elif name == 'DataLoader':
            from backtest_system import DataLoader
            return DataLoader
        elif name == 'Config':
            from backtest_system import Config
            return Config
    except ImportError as e:
        logger.warning(f"無法導入 {name}: {e}")
        return None
    return None


class BacktestDialog(ctk.CTkToplevel):
    """回測對話框 - 完整回測功能"""

    def __init__(self, parent, symbol_data: Dict):
        super().__init__(parent)
        self.parent = parent
        self.symbol_data = symbol_data
        self.symbol = symbol_data["symbol"]
        self.result = None

        self.title(f"回測 {self.symbol}")
        self.geometry("600x700")
        self.configure(fg_color=Colors.BG_PRIMARY)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        # 置中
        self.update_idletasks()
        x = self.winfo_toplevel().winfo_x() + 50
        y = self.winfo_toplevel().winfo_y() + 50
        self.geometry(f"600x700+{x}+{y}")

        self._create_ui()

    def _create_ui(self):
        # 可滾動區域
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=16, pady=16)

        # 標題
        ctk.CTkLabel(
            scroll,
            text=f"🔬 {self.symbol} 回測",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(0, 16))

        # === 回測參數區 ===
        param_frame = ctk.CTkFrame(scroll, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        param_frame.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            param_frame,
            text="回測參數",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(anchor="w", padx=12, pady=(12, 8))

        # 參數輸入
        params_grid = ctk.CTkFrame(param_frame, fg_color="transparent")
        params_grid.pack(fill="x", padx=12, pady=(0, 12))

        # 時間範圍
        row1 = ctk.CTkFrame(params_grid, fg_color="transparent")
        row1.pack(fill="x", pady=4)

        ctk.CTkLabel(row1, text="時間範圍:", width=100, text_color=Colors.TEXT_SECONDARY).pack(side="left")
        self.days_var = ctk.StringVar(value="30")
        days_menu = ctk.CTkOptionMenu(
            row1,
            values=["7", "14", "30", "60", "90"],
            variable=self.days_var,
            width=80,
            fg_color=Colors.BG_TERTIARY,
            button_color=Colors.BG_TERTIARY
        )
        days_menu.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(row1, text="天", text_color=Colors.TEXT_MUTED).pack(side="left", padx=(4, 0))

        # 時間框架 - 預設 1m (與實盤一致)
        ctk.CTkLabel(row1, text="K線:", width=60, text_color=Colors.TEXT_SECONDARY).pack(side="left", padx=(16, 0))
        self.timeframe_var = ctk.StringVar(value="1m")
        tf_menu = ctk.CTkOptionMenu(
            row1,
            values=["1m", "5m", "15m", "30m", "1h", "4h"],
            variable=self.timeframe_var,
            width=80,
            fg_color=Colors.BG_TERTIARY,
            button_color=Colors.BG_TERTIARY
        )
        tf_menu.pack(side="left", padx=(8, 0))

        # 止盈/補倉間距
        row2 = ctk.CTkFrame(params_grid, fg_color="transparent")
        row2.pack(fill="x", pady=4)

        ctk.CTkLabel(row2, text="止盈間距:", width=100, text_color=Colors.TEXT_SECONDARY).pack(side="left")
        self.tp_entry = ctk.CTkEntry(row2, width=80, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.tp_entry.insert(0, self.symbol_data.get('tp', '0.4%').replace('%', ''))
        self.tp_entry.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(row2, text="%", text_color=Colors.TEXT_MUTED).pack(side="left", padx=(4, 0))

        ctk.CTkLabel(row2, text="補倉間距:", width=80, text_color=Colors.TEXT_SECONDARY).pack(side="left", padx=(16, 0))
        self.gs_entry = ctk.CTkEntry(row2, width=80, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.gs_entry.insert(0, self.symbol_data.get('gs', '0.6%').replace('%', ''))
        self.gs_entry.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(row2, text="%", text_color=Colors.TEXT_MUTED).pack(side="left", padx=(4, 0))

        # 數量/槓桿
        row3 = ctk.CTkFrame(params_grid, fg_color="transparent")
        row3.pack(fill="x", pady=4)

        ctk.CTkLabel(row3, text="每單數量:", width=100, text_color=Colors.TEXT_SECONDARY).pack(side="left")
        self.qty_entry = ctk.CTkEntry(row3, width=80, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.qty_entry.insert(0, str(self.symbol_data.get('qty', 30)))
        self.qty_entry.pack(side="left", padx=(8, 0))

        ctk.CTkLabel(row3, text="槓桿:", width=80, text_color=Colors.TEXT_SECONDARY).pack(side="left", padx=(16, 0))
        self.leverage_entry = ctk.CTkEntry(row3, width=80, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.leverage_entry.insert(0, str(self.symbol_data.get('leverage', 20)))
        self.leverage_entry.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(row3, text="x", text_color=Colors.TEXT_MUTED).pack(side="left", padx=(4, 0))

        # 初始資金
        row4 = ctk.CTkFrame(params_grid, fg_color="transparent")
        row4.pack(fill="x", pady=4)

        ctk.CTkLabel(row4, text="初始資金:", width=100, text_color=Colors.TEXT_SECONDARY).pack(side="left")
        self.balance_entry = ctk.CTkEntry(row4, width=100, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.balance_entry.insert(0, "10000")
        self.balance_entry.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(row4, text="USDC", text_color=Colors.TEXT_MUTED).pack(side="left", padx=(4, 0))

        # 執行按鈕
        btn_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(0, 16))

        self.run_btn = ctk.CTkButton(
            btn_frame,
            text="▶ 執行回測",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            height=40,
            command=self._run_backtest
        )
        self.run_btn.pack(side="left", padx=(0, 8))

        self.status_label = ctk.CTkLabel(
            btn_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_MUTED
        )
        self.status_label.pack(side="left")

        # === 結果區 ===
        self.result_frame = ctk.CTkFrame(scroll, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        self.result_frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            self.result_frame,
            text="回測結果",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(anchor="w", padx=12, pady=(12, 8))

        self.result_content = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        self.result_content.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        ctk.CTkLabel(
            self.result_content,
            text="點擊「執行回測」開始",
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_MUTED
        ).pack(pady=40)

    def _run_backtest(self):
        """執行回測"""
        self.run_btn.configure(state="disabled", text="回測中...")
        self.status_label.configure(text="載入數據中...")

        def do_backtest():
            try:
                GridBacktester = _get_backtest_module('GridBacktester')
                DataLoader = _get_backtest_module('DataLoader')
                Config = _get_backtest_module('Config')

                if not all([GridBacktester, DataLoader, Config]):
                    self.after(0, lambda: self._show_error("回測系統不可用"))
                    return

                # 獲取參數
                days = int(self.days_var.get())
                timeframe = self.timeframe_var.get()
                tp = float(self.tp_entry.get()) / 100
                gs = float(self.gs_entry.get()) / 100
                qty = float(self.qty_entry.get())
                leverage = int(self.leverage_entry.get())
                balance = float(self.balance_entry.get())

                # 載入數據
                self.after(0, lambda: self.status_label.configure(text=f"載入 {days} 天 {timeframe} 數據..."))
                loader = DataLoader()
                df = loader.load_symbol_data(self.symbol, timeframe=timeframe, days=days)

                if df is None or len(df) < 100:
                    self.after(0, lambda: self._show_error(f"數據不足 (需要至少 100 根 K 線)"))
                    return

                # 從 symbol_data 讀取 limit_mult 和 threshold_mult（避免硬編碼）
                limit_mult = float(self.symbol_data.get('limit_mult', 5.0))
                threshold_mult = float(self.symbol_data.get('threshold_mult', 20.0))

                # 創建配置
                config = Config(
                    symbol=self.symbol,
                    initial_balance=balance,
                    leverage=leverage,
                    order_value=qty,
                    take_profit_spacing=tp,
                    grid_spacing=gs,
                    position_limit=int(qty * limit_mult),
                    position_threshold=int(qty * threshold_mult)
                )

                # 執行回測
                self.after(0, lambda: self.status_label.configure(text="執行回測中..."))
                backtester = GridBacktester(df, config)
                bt_result = backtester.run()

                # 轉換 BacktestResult 為字典
                result = {
                    'total_return': bt_result.return_pct * 100,  # 轉為百分比
                    'total_trades': bt_result.trades_count,
                    'win_rate': bt_result.win_rate,
                    'max_drawdown': bt_result.max_drawdown,
                    'sharpe_ratio': bt_result.sharpe_ratio,
                    'final_equity': bt_result.final_equity,
                    'equity_curve': bt_result.equity_curve,
                }

                self.result = result
                self.after(0, lambda: self._show_result(result))

            except Exception as ex:
                error_msg = str(ex)
                self.after(0, lambda err=error_msg: self._show_error(err))

        threading.Thread(target=do_backtest, daemon=True).start()

    def _show_error(self, error: str):
        """顯示錯誤"""
        self.run_btn.configure(state="normal", text="▶ 執行回測")
        self.status_label.configure(text=f"錯誤: {error}", text_color=Colors.RED)

    def _show_result(self, result: Dict):
        """顯示回測結果"""
        self.run_btn.configure(state="normal", text="▶ 重新回測")
        self.status_label.configure(text="回測完成", text_color=Colors.GREEN)

        # 清空結果區
        for widget in self.result_content.winfo_children():
            widget.destroy()

        # 關鍵指標
        total_return = result.get('total_return', 0)
        total_trades = result.get('total_trades', 0)
        win_rate = result.get('win_rate', 0) * 100
        max_drawdown = result.get('max_drawdown', 0) * 100
        sharpe = result.get('sharpe_ratio', 0)
        final_equity = result.get('final_equity', 10000)

        # 總收益 (大字)
        return_color = Colors.GREEN if total_return > 0 else Colors.RED if total_return < 0 else Colors.TEXT_MUTED
        ctk.CTkLabel(
            self.result_content,
            text=f"{total_return:+.2f}%",
            font=ctk.CTkFont(size=36, weight="bold"),
            text_color=return_color
        ).pack(pady=(8, 4))

        ctk.CTkLabel(
            self.result_content,
            text=f"最終權益: ${final_equity:,.2f}",
            font=ctk.CTkFont(size=14),
            text_color=Colors.TEXT_SECONDARY
        ).pack(pady=(0, 16))

        # 指標網格
        metrics_frame = ctk.CTkFrame(self.result_content, fg_color="transparent")
        metrics_frame.pack(fill="x", pady=(0, 16))

        metrics = [
            ("總交易數", f"{total_trades}"),
            ("勝率", f"{win_rate:.1f}%"),
            ("最大回撤", f"{max_drawdown:.2f}%"),
            ("夏普比率", f"{sharpe:.2f}"),
        ]

        for i, (label, value) in enumerate(metrics):
            col = ctk.CTkFrame(metrics_frame, fg_color=Colors.BG_TERTIARY, corner_radius=4)
            col.pack(side="left", fill="x", expand=True, padx=2)

            ctk.CTkLabel(
                col,
                text=label,
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED
            ).pack(pady=(8, 2))

            ctk.CTkLabel(
                col,
                text=value,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=Colors.TEXT_PRIMARY
            ).pack(pady=(0, 8))

        # 權益曲線
        equity_curve = result.get('equity_curve', [])
        if equity_curve:
            chart_frame = ctk.CTkFrame(self.result_content, fg_color=Colors.BG_TERTIARY, corner_radius=4)
            chart_frame.pack(fill="x", pady=(0, 16))

            ctk.CTkLabel(
                chart_frame,
                text="權益曲線",
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED
            ).pack(anchor="w", padx=8, pady=(8, 4))

            # 使用更大的 MiniChart
            chart = MiniChart(chart_frame, width=540, height=120)
            chart.pack(padx=8, pady=(0, 8))
            chart.set_data(equity_curve)

        # 應用按鈕
        apply_btn = ctk.CTkButton(
            self.result_content,
            text="應用此參數",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            height=36,
            command=self._apply_params
        )
        apply_btn.pack(pady=(8, 0))

    def _apply_params(self):
        """應用參數到交易對設定"""
        self.symbol_data['tp'] = f"{self.tp_entry.get()}%"
        self.symbol_data['gs'] = f"{self.gs_entry.get()}%"
        self.symbol_data['qty'] = float(self.qty_entry.get())
        self.symbol_data['leverage'] = int(self.leverage_entry.get())

        # 更新到 GlobalConfig
        if hasattr(self.parent, 'update_symbol_in_config'):
            self.parent.update_symbol_in_config(self.symbol, self.symbol_data)

        # 刷新頁面
        if hasattr(self.parent, 'refresh'):
            self.parent.refresh()

        self.destroy()


class OptimizeDialog(ctk.CTkToplevel):
    """參數優化對話框 - 交易對快速優化"""

    def __init__(self, parent, row_or_symbol, engine=None):
        """
        初始化優化對話框

        Args:
            parent: 父視窗
            row_or_symbol: 可以是 row 物件（有 row.data 屬性）或字符串 symbol
            engine: 交易引擎（可選，用於從 CoinSelectionPage 調用時傳入）
        """
        super().__init__(parent)
        self.parent = parent
        self.engine = engine
        self.best_params = None
        self.is_running = False

        # 支援兩種輸入方式：row 物件或字符串
        if isinstance(row_or_symbol, str):
            # 從 CoinSelectionPage 調用，傳入的是 symbol 字符串
            self.symbol = row_or_symbol
            self.row = None
            # 建立預設資料
            self.symbol_data = {
                'symbol': row_or_symbol,
                'qty': '1',
                'leverage': '20',
                'tp': '0.4%',
                'gs': '0.6%',
                'limit_mult': 5.0,
                'threshold_mult': 20.0
            }
        else:
            # 從 SymbolsPage 調用，傳入的是 row 物件
            self.row = row_or_symbol
            self.symbol = row_or_symbol.data["symbol"]
            self.symbol_data = row_or_symbol.data

        self.title(f"參數優化 - {self.symbol}")
        self.geometry("500x550")
        self.configure(fg_color=Colors.BG_PRIMARY)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._create_ui()

    def _create_ui(self):
        # 標題
        ctk.CTkLabel(
            self,
            text=f"🎯 {self.symbol} 參數優化",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(20, 8))

        ctk.CTkLabel(
            self,
            text="使用 UCB Bandit 算法尋找最優間距參數",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED
        ).pack(pady=(0, 16))

        # 當前參數
        current_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        current_frame.pack(fill="x", padx=24, pady=(0, 16))

        ctk.CTkLabel(
            current_frame,
            text="當前參數",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", padx=16, pady=(12, 4))

        current_params = f"止盈: {self.symbol_data['tp']} | 補倉: {self.symbol_data['gs']} | 槓桿: {self.symbol_data['leverage']}x"
        ctk.CTkLabel(
            current_frame,
            text=current_params,
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_PRIMARY
        ).pack(anchor="w", padx=16, pady=(0, 12))

        # 優化設定
        settings_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        settings_frame.pack(fill="x", padx=24, pady=(0, 16))

        ctk.CTkLabel(
            settings_frame,
            text="優化設定",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", padx=16, pady=(12, 8))

        # 回測天數
        days_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        days_row.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(days_row, text="回測天數", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED).pack(side="left")
        self.days_entry = ctk.CTkEntry(days_row, width=60, height=28, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.days_entry.insert(0, "30")
        self.days_entry.pack(side="right")

        # 迭代次數
        iter_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        iter_row.pack(fill="x", padx=16, pady=4)
        ctk.CTkLabel(iter_row, text="優化迭代", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED).pack(side="left")
        self.iter_entry = ctk.CTkEntry(iter_row, width=60, height=28, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.iter_entry.insert(0, "20")
        self.iter_entry.pack(side="right")

        # 間距範圍
        range_row = ctk.CTkFrame(settings_frame, fg_color="transparent")
        range_row.pack(fill="x", padx=16, pady=(4, 12))
        ctk.CTkLabel(range_row, text="搜索範圍", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED).pack(side="left")
        ctk.CTkLabel(range_row, text="TP: 0.2-0.8% | GS: 0.3-1.0%", font=ctk.CTkFont(size=10), text_color=Colors.TEXT_SECONDARY).pack(side="right")

        # 進度和結果
        result_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        result_frame.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        ctk.CTkLabel(
            result_frame,
            text="優化結果",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", padx=16, pady=(12, 8))

        # 進度條
        self.progress_bar = ctk.CTkProgressBar(result_frame, width=400, height=8, progress_color=Colors.ACCENT)
        self.progress_bar.pack(padx=16, pady=(0, 8))
        self.progress_bar.set(0)

        # 狀態標籤
        self.status_label = ctk.CTkLabel(
            result_frame,
            text="點擊「開始優化」進行參數搜索",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED
        )
        self.status_label.pack(pady=(0, 8))

        # 最佳參數顯示
        self.best_frame = ctk.CTkFrame(result_frame, fg_color=Colors.BG_TERTIARY, corner_radius=6)
        self.best_frame.pack(fill="x", padx=16, pady=(0, 12))

        self.best_tp_label = ctk.CTkLabel(self.best_frame, text="最佳止盈: --", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY)
        self.best_tp_label.pack(anchor="w", padx=12, pady=(8, 2))

        self.best_gs_label = ctk.CTkLabel(self.best_frame, text="最佳補倉: --", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY)
        self.best_gs_label.pack(anchor="w", padx=12, pady=2)

        self.best_return_label = ctk.CTkLabel(self.best_frame, text="預期收益: --", font=ctk.CTkFont(size=12, weight="bold"), text_color=Colors.TEXT_PRIMARY)
        self.best_return_label.pack(anchor="w", padx=12, pady=(2, 8))

        # 按鈕區
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=(0, 20))

        ctk.CTkButton(
            btn_frame,
            text="取消",
            fg_color=Colors.BG_TERTIARY,
            hover_color=Colors.BORDER,
            width=100,
            command=self.destroy
        ).pack(side="left")

        self.apply_btn = ctk.CTkButton(
            btn_frame,
            text="套用參數",
            fg_color=Colors.BG_TERTIARY,
            hover_color=Colors.BORDER,
            width=100,
            state="disabled",
            command=self._apply_params
        )
        self.apply_btn.pack(side="right", padx=(8, 0))

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="開始優化",
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            width=100,
            command=self._start_optimization
        )
        self.start_btn.pack(side="right")

    def _start_optimization(self):
        """開始優化"""
        if self.is_running:
            return

        self.is_running = True
        self.start_btn.configure(state="disabled")
        self.status_label.configure(text="正在載入數據...", text_color=Colors.TEXT_SECONDARY)
        self.progress_bar.set(0)

        def run_optimization():
            try:
                GridOptimizer = _get_backtest_module('GridOptimizer')
                DataLoader = _get_backtest_module('DataLoader')
                Config = _get_backtest_module('Config')

                if not all([GridOptimizer, DataLoader, Config]):
                    self.after(0, lambda: self._show_error("回測系統不可用"))
                    return

                days = int(self.days_entry.get())
                iterations = int(self.iter_entry.get())

                # 載入數據 (使用 1m K 線與實盤一致)
                self.after(0, lambda: self.status_label.configure(text=f"載入 {self.symbol} 數據中..."))
                loader = DataLoader()
                df = loader.load_symbol_data(self.symbol, timeframe='1m', days=days)

                if df is None or len(df) < 100:
                    self.after(0, lambda: self._show_error("數據不足，無法進行優化"))
                    return

                self.after(0, lambda: self.progress_bar.set(0.1))

                # 從 symbol_data 讀取參數（避免硬編碼）
                qty = float(self.symbol_data['qty'])
                limit_mult = float(self.symbol_data.get('limit_mult', 5.0))
                threshold_mult = float(self.symbol_data.get('threshold_mult', 20.0))

                # 創建基礎配置
                base_config = Config(
                    symbol=self.symbol,
                    initial_balance=1000,  # 使用合理的預設值（可配置）
                    leverage=int(self.symbol_data['leverage']),
                    order_value=qty,
                    position_limit=int(qty * limit_mult),
                    position_threshold=int(qty * threshold_mult)
                )

                # 執行優化
                self.after(0, lambda: self.status_label.configure(text=f"優化中 (0/{iterations})..."))

                best_result = None
                best_return = -float('inf')

                for i in range(iterations):
                    # 生成參數組合
                    tp = 0.002 + (i % 7) * 0.001  # 0.2% - 0.8%
                    gs = 0.003 + (i // 7) * 0.001  # 0.3% - 1.0%

                    if i >= 49:  # 超出網格範圍，隨機採樣
                        import random
                        tp = random.uniform(0.002, 0.008)
                        gs = random.uniform(0.003, 0.010)

                    base_config.take_profit_spacing = tp
                    base_config.grid_spacing = gs

                    # 運行回測
                    from backtest_system import GridBacktester
                    backtester = GridBacktester(df, base_config)
                    bt_result = backtester.run()

                    total_return = bt_result.return_pct * 100
                    if total_return > best_return:
                        best_return = total_return
                        best_result = {
                            'tp': tp,
                            'gs': gs,
                            'return': total_return,
                            'trades': bt_result.trades_count,
                            'win_rate': bt_result.win_rate
                        }

                    # 更新進度
                    progress = 0.1 + 0.9 * (i + 1) / iterations
                    self.after(0, lambda p=progress, n=i+1: self._update_progress(p, n, iterations))

                # 保存最佳結果
                self.best_params = best_result
                self.after(0, lambda: self._show_result(best_result))

            except Exception as ex:
                error_msg = f"優化失敗: {str(ex)[:50]}"
                self.after(0, lambda err=error_msg: self._show_error(err))
            finally:
                self.is_running = False
                self.after(0, lambda: self.start_btn.configure(state="normal"))

        threading.Thread(target=run_optimization, daemon=True).start()

    def _update_progress(self, progress, current, total):
        """更新進度"""
        self.progress_bar.set(progress)
        self.status_label.configure(text=f"優化中 ({current}/{total})...")

    def _show_result(self, result):
        """顯示優化結果"""
        if result:
            self.best_tp_label.configure(text=f"最佳止盈: {result['tp']*100:.2f}%", text_color=Colors.TEXT_PRIMARY)
            self.best_gs_label.configure(text=f"最佳補倉: {result['gs']*100:.2f}%", text_color=Colors.TEXT_PRIMARY)

            return_color = Colors.GREEN if result['return'] > 0 else Colors.RED
            self.best_return_label.configure(text=f"預期收益: {result['return']:+.2f}%", text_color=return_color)

            self.status_label.configure(text=f"優化完成！交易次數: {result['trades']}, 勝率: {result['win_rate']:.1f}%", text_color=Colors.GREEN)
            self.apply_btn.configure(state="normal", fg_color=Colors.ACCENT, text_color=Colors.BG_PRIMARY)
        else:
            self.status_label.configure(text="未找到更優參數", text_color=Colors.YELLOW)

    def _show_error(self, msg):
        """顯示錯誤"""
        self.status_label.configure(text=msg, text_color=Colors.RED)
        self.is_running = False
        self.start_btn.configure(state="normal")

    def _apply_params(self):
        """套用最佳參數 - 需要確認"""
        if not self.best_params:
            return

        # 計算變更內容
        old_tp = self.symbol_data.get('tp', '0.4%')
        old_gs = self.symbol_data.get('gs', '0.6%')
        new_tp = f"{self.best_params['tp']*100:.2f}%"
        new_gs = f"{self.best_params['gs']*100:.2f}%"

        details = (
            f"止盈間距: {old_tp} → {new_tp}\n"
            f"補倉間距: {old_gs} → {new_gs}\n"
            f"預期收益: {self.best_params['return']:+.2f}%"
        )

        def do_apply():
            # 更新 symbol_data
            self.symbol_data['tp'] = new_tp
            self.symbol_data['gs'] = new_gs

            if self.row:
                # 從 SymbolsPage 調用，更新 row 物件
                self.row.data['tp'] = self.symbol_data['tp']
                self.row.data['gs'] = self.symbol_data['gs']

                # 持久化到 GlobalConfig
                if hasattr(self.parent, 'update_symbol_in_config'):
                    self.parent.update_symbol_in_config(self.symbol_data['symbol'], self.symbol_data)
                if hasattr(self.parent, 'refresh'):
                    self.parent.refresh()
            else:
                # 從 CoinSelectionPage 調用，直接更新 GlobalConfig
                try:
                    from as_terminal_max_bitget import GlobalConfig
                    config = GlobalConfig.load()
                    symbol = self.symbol_data['symbol']
                    if symbol in config.symbols:
                        config.symbols[symbol].take_profit_spacing = self.best_params['tp']
                        config.symbols[symbol].grid_spacing = self.best_params['gs']
                        config.save()
                except Exception:
                    import logging
                    logging.getLogger(__name__).warning("更新配置失敗")

            # 關閉對話框
            self.destroy()

        ConfirmDialog(
            self,
            title="套用優化參數",
            message=f"確定要套用 {self.symbol} 的優化參數？",
            details=details,
            confirm_text="套用",
            on_confirm=do_apply
        )
