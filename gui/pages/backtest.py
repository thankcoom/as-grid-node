"""
回測頁面
"""

import os
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, TYPE_CHECKING

import customtkinter as ctk

from ..styles import Colors
from ..components import Card, MiniChart

if TYPE_CHECKING:
    from gui.app import ASGridApp

# 回測系統可用性標記
BACKTEST_AVAILABLE = True

# 延遲導入回測模組
def _get_backtest_module(name):
    """延遲載入回測模組"""
    global BACKTEST_AVAILABLE
    try:
        # 確保 asBack 目錄在 path 中
        asback_path = str(Path(__file__).parent.parent.parent / 'asBack')
        if asback_path not in sys.path:
            sys.path.insert(0, asback_path)

        if name == 'GridBacktester':
            from backtest_system import GridBacktester
            return GridBacktester
        elif name == 'DataLoader':
            from backtest_system import DataLoader
            return DataLoader
        elif name == 'Config':
            from backtest_system import Config
            return Config
        elif name == 'GridOptimizer':
            from backtest_system import GridOptimizer
            return GridOptimizer
    except ImportError as e:
        BACKTEST_AVAILABLE = False
        print(f"[警告] 無法載入回測系統: {e}")
        return None
    return None

class BacktestPage(ctk.CTkFrame):
    """智能優化頁面 - Optuna TPE 貝葉斯優化"""

    def __init__(self, master, app: "ASGridApp"):
        super().__init__(master, fg_color=Colors.BG_PRIMARY)
        self.app = app
        self.result_labels = {}
        self.progress_label = None
        self.is_optimizing = False
        self._data_loader = None  # 延遲初始化
        self._create_ui()

    @property
    def data_loader(self):
        """延遲載入 DataLoader，避免阻塞 UI"""
        if self._data_loader is None:
            DataLoader = _get_backtest_module('DataLoader')
            self._data_loader = DataLoader() if DataLoader else None
        return self._data_loader

    def _create_ui(self):
        # 可滾動區域
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # 頁面標題
        title_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(title_frame, text="智能參數優化", font=ctk.CTkFont(size=20, weight="bold"), text_color=Colors.TEXT_PRIMARY).pack(side="left")
        ctk.CTkLabel(title_frame, text="Optuna TPE 貝葉斯優化", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_MUTED).pack(side="left", padx=(12, 0))

        # === 基礎設定區 ===
        settings_card = Card(scroll, title="數據設定")
        settings_card.pack(fill="x", pady=(0, 12))

        # 第一行：交易對 (可輸入) + 回測天數
        row1 = ctk.CTkFrame(settings_card, fg_color="transparent")
        row1.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(row1, text="交易對", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY, width=70).pack(side="left")
        self.symbol_entry = ctk.CTkEntry(row1, width=100, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, placeholder_text="如 XRPUSDC")
        self.symbol_entry.insert(0, "XRPUSDC")
        self.symbol_entry.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(row1, text="回測天數", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY, width=70).pack(side="left")
        self.days_entry = ctk.CTkEntry(row1, width=50, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.days_entry.insert(0, "7")
        self.days_entry.pack(side="left", padx=(0, 12))

        # 快捷按鈕
        for days, label in [(7, "1W"), (14, "2W"), (30, "1M"), (90, "3M")]:
            btn = ctk.CTkButton(row1, text=label, font=ctk.CTkFont(size=10), fg_color=Colors.BG_TERTIARY, text_color=Colors.TEXT_MUTED, hover_color=Colors.BORDER, width=32, height=24, corner_radius=4, command=lambda d=days: self._set_days(d))
            btn.pack(side="left", padx=2)

        # 第二行：資金 + 每單 + 方向
        row2 = ctk.CTkFrame(settings_card, fg_color="transparent")
        row2.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(row2, text="初始資金", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY, width=70).pack(side="left")
        self.balance_entry = ctk.CTkEntry(row2, width=70, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.balance_entry.insert(0, "1000")
        self.balance_entry.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(row2, text="每單數量", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY, width=70).pack(side="left")
        self.order_value_entry = ctk.CTkEntry(row2, width=60, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.order_value_entry.insert(0, "10")  # 幣的數量 (與終端 UI initial_quantity 一致)
        self.order_value_entry.pack(side="left", padx=(0, 12))

        ctk.CTkLabel(row2, text="方向", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY, width=50).pack(side="left")
        self.dir_menu = ctk.CTkOptionMenu(row2, values=["雙向", "僅多", "僅空"], fg_color=Colors.BG_TERTIARY, button_color=Colors.BG_TERTIARY, button_hover_color=Colors.BORDER, dropdown_fg_color=Colors.BG_SECONDARY, width=70)
        self.dir_menu.pack(side="left")

        # === 優化設定區 ===
        optim_settings_card = Card(scroll, title="優化設定")
        optim_settings_card.pack(fill="x", pady=(0, 12))

        # 優化目標選擇
        obj_frame = ctk.CTkFrame(optim_settings_card, fg_color="transparent")
        obj_frame.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(obj_frame, text="優化目標", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY, width=80).pack(side="left")
        self.objective_menu = ctk.CTkOptionMenu(
            obj_frame,
            values=["Sharpe Ratio", "收益率", "Sortino Ratio", "Calmar Ratio", "風險調整收益"],
            fg_color=Colors.BG_TERTIARY,
            button_color=Colors.BG_TERTIARY,
            button_hover_color=Colors.BORDER,
            dropdown_fg_color=Colors.BG_SECONDARY,
            width=150
        )
        self.objective_menu.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(obj_frame, text="試驗次數", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY, width=80).pack(side="left")
        self.n_trials_entry = ctk.CTkEntry(obj_frame, width=60, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.n_trials_entry.insert(0, "50")
        self.n_trials_entry.pack(side="left")

        # 參數範圍設定
        range_frame = ctk.CTkFrame(optim_settings_card, fg_color="transparent")
        range_frame.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(range_frame, text="止盈範圍 (%)", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED, width=90).pack(side="left")
        self.tp_min_entry = ctk.CTkEntry(range_frame, width=50, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.tp_min_entry.insert(0, "0.1")
        self.tp_min_entry.pack(side="left")
        ctk.CTkLabel(range_frame, text="~", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED).pack(side="left", padx=4)
        self.tp_max_entry = ctk.CTkEntry(range_frame, width=50, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.tp_max_entry.insert(0, "1.5")
        self.tp_max_entry.pack(side="left", padx=(0, 16))

        ctk.CTkLabel(range_frame, text="補倉範圍 (%)", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED, width=90).pack(side="left")
        self.gs_min_entry = ctk.CTkEntry(range_frame, width=50, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.gs_min_entry.insert(0, "0.2")
        self.gs_min_entry.pack(side="left")
        ctk.CTkLabel(range_frame, text="~", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED).pack(side="left", padx=4)
        self.gs_max_entry = ctk.CTkEntry(range_frame, width=50, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.gs_max_entry.insert(0, "2.5")
        self.gs_max_entry.pack(side="left")

        # 槓桿範圍
        lev_frame = ctk.CTkFrame(optim_settings_card, fg_color="transparent")
        lev_frame.pack(fill="x", padx=16, pady=(0, 12))

        ctk.CTkLabel(lev_frame, text="槓桿範圍", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED, width=90).pack(side="left")
        self.lev_min_entry = ctk.CTkEntry(lev_frame, width=50, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.lev_min_entry.insert(0, "5")
        self.lev_min_entry.pack(side="left")
        ctk.CTkLabel(lev_frame, text="~", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED).pack(side="left", padx=4)
        self.lev_max_entry = ctk.CTkEntry(lev_frame, width=50, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.lev_max_entry.insert(0, "30")
        self.lev_max_entry.pack(side="left")

        # 當前參數 (用於快速回測)
        current_frame = ctk.CTkFrame(optim_settings_card, fg_color="transparent")
        current_frame.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(current_frame, text="快速回測", font=ctk.CTkFont(size=12, weight="bold"), text_color=Colors.TEXT_SECONDARY).pack(side="left")
        ctk.CTkLabel(current_frame, text="止盈%", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED).pack(side="left", padx=(16, 4))
        self.tp_entry = ctk.CTkEntry(current_frame, width=50, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.tp_entry.insert(0, "0.4")
        self.tp_entry.pack(side="left")

        ctk.CTkLabel(current_frame, text="補倉%", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED).pack(side="left", padx=(12, 4))
        self.gs_entry = ctk.CTkEntry(current_frame, width=50, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.gs_entry.insert(0, "0.6")
        self.gs_entry.pack(side="left")

        ctk.CTkLabel(current_frame, text="槓桿", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED).pack(side="left", padx=(12, 4))
        self.lev_entry = ctk.CTkEntry(current_frame, width=40, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY)
        self.lev_entry.insert(0, "20")
        self.lev_entry.pack(side="left")

        # === 按鈕區 ===
        btn_frame = ctk.CTkFrame(optim_settings_card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 12))

        # 下載數據
        self.download_button = ctk.CTkButton(btn_frame, text="下載數據", font=ctk.CTkFont(size=12), fg_color=Colors.BG_TERTIARY, text_color=Colors.TEXT_PRIMARY, hover_color=Colors.BORDER, height=36, corner_radius=8, width=80, command=self._download_data)
        self.download_button.pack(side="left", padx=(0, 6))

        # 快速回測
        self.quick_test_button = ctk.CTkButton(btn_frame, text="快速回測", font=ctk.CTkFont(size=12), fg_color=Colors.BG_TERTIARY, text_color=Colors.TEXT_PRIMARY, hover_color=Colors.BORDER, height=36, corner_radius=8, width=80, command=self._run_quick_backtest)
        self.quick_test_button.pack(side="left", padx=(0, 6))

        # 網格優化 (原本的優化方式)
        self.grid_optimize_button = ctk.CTkButton(btn_frame, text="網格優化", font=ctk.CTkFont(size=12), fg_color=Colors.FILL_HIGHLIGHT, text_color=Colors.TEXT_PRIMARY, hover_color=Colors.BORDER_LIGHT, height=36, corner_radius=8, width=80, command=self._run_grid_optimize)
        self.grid_optimize_button.pack(side="left", padx=(0, 6))

        # 智能優化 (Optuna TPE)
        self.optimize_button = ctk.CTkButton(btn_frame, text="智能優化", font=ctk.CTkFont(size=14, weight="bold"), fg_color=Colors.ACCENT, text_color=Colors.BG_PRIMARY, hover_color=Colors.GREEN_DARK, height=40, corner_radius=8, command=self._run_smart_optimize)
        self.optimize_button.pack(side="left", fill="x", expand=True)

        # 進度區
        progress_frame = ctk.CTkFrame(optim_settings_card, fg_color="transparent")
        progress_frame.pack(fill="x", padx=16, pady=(0, 8))

        self.progress_bar = ctk.CTkProgressBar(progress_frame, height=4, corner_radius=2, fg_color=Colors.BG_TERTIARY, progress_color=Colors.ACCENT)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(progress_frame, text="準備就緒", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED)
        self.progress_label.pack(anchor="w", pady=(4, 0))

        # === 結果區 ===
        result_card = Card(scroll, title="優化結果")
        result_card.pack(fill="x", pady=(0, 12))

        result_frame = ctk.CTkFrame(result_card, fg_color="transparent")
        result_frame.pack(fill="x", padx=16, pady=(0, 12))

        # 結果統計 (2 行 x 4 列) - 初始全部顯示 "--"
        stats = [
            ("最終權益", "--"),
            ("收益率", "--"),
            ("最大回撤", "--"),
            ("Sharpe", "--"),
            ("交易次數", "--"),
            ("勝率", "--"),
            ("盈虧比", "--"),
            ("優化耗時", "--"),
        ]

        for i, (label, value) in enumerate(stats):
            stat_frame = ctk.CTkFrame(result_frame, fg_color=Colors.BG_TERTIARY, corner_radius=6)
            stat_frame.grid(row=i // 4, column=i % 4, padx=3, pady=3, sticky="nsew")
            result_frame.grid_columnconfigure(i % 4, weight=1)

            ctk.CTkLabel(stat_frame, text=label, font=ctk.CTkFont(size=10), text_color=Colors.TEXT_MUTED).pack(anchor="w", padx=10, pady=(8, 2))
            self.result_labels[label] = ctk.CTkLabel(stat_frame, text=value, font=ctk.CTkFont(size=14, weight="bold"), text_color=Colors.TEXT_PRIMARY)
            self.result_labels[label].pack(anchor="w", padx=10, pady=(0, 8))

        # === 參數重要性 ===
        importance_frame = ctk.CTkFrame(result_card, fg_color="transparent")
        importance_frame.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(importance_frame, text="參數重要性", font=ctk.CTkFont(size=11, weight="bold"), text_color=Colors.TEXT_SECONDARY).pack(anchor="w")

        self.importance_bars_frame = ctk.CTkFrame(importance_frame, fg_color="transparent")
        self.importance_bars_frame.pack(fill="x", pady=(4, 0))

        # 預設重要性條
        for param in ["止盈間距", "補倉間距", "槓桿"]:
            bar_frame = ctk.CTkFrame(self.importance_bars_frame, fg_color="transparent", height=20)
            bar_frame.pack(fill="x", pady=1)
            bar_frame.pack_propagate(False)
            ctk.CTkLabel(bar_frame, text=param, font=ctk.CTkFont(size=10), text_color=Colors.TEXT_MUTED, width=70).pack(side="left")
            bar = ctk.CTkProgressBar(bar_frame, height=8, corner_radius=4, fg_color=Colors.BG_TERTIARY, progress_color=Colors.TEXT_MUTED)
            bar.pack(side="left", fill="x", expand=True, padx=(0, 8))
            bar.set(0)

        # === Top 5 優化結果表格 ===
        optim_card = Card(scroll, title="Top 5 參數組合")
        optim_card.pack(fill="x", pady=(0, 12))

        self.optim_table_frame = ctk.CTkFrame(optim_card, fg_color="transparent")
        self.optim_table_frame.pack(fill="x", padx=16, pady=(0, 8))

        # 表格標題
        header_frame = ctk.CTkFrame(self.optim_table_frame, fg_color=Colors.BG_TERTIARY, corner_radius=4)
        header_frame.pack(fill="x", pady=(0, 4))
        headers = ["#", "止盈%", "補倉%", "槓桿", "收益率", "Sharpe", "回撤", "交易", "勝率"]
        header_widths = [25, 50, 50, 40, 55, 50, 45, 40, 40]
        for i, h in enumerate(headers):
            ctk.CTkLabel(header_frame, text=h, font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.TEXT_SECONDARY, width=header_widths[i]).grid(row=0, column=i, padx=1, pady=4)

        self.optim_rows_frame = ctk.CTkFrame(self.optim_table_frame, fg_color="transparent")
        self.optim_rows_frame.pack(fill="x")
        self._show_empty_optim_rows()

        # === 應用區 ===
        apply_frame = ctk.CTkFrame(optim_card, fg_color="transparent")
        apply_frame.pack(fill="x", padx=16, pady=(8, 12))

        self.current_params_label = ctk.CTkLabel(apply_frame, text="當前參數: --", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED)
        self.current_params_label.pack(anchor="w")

        self.best_params_label = ctk.CTkLabel(apply_frame, text="最佳參數: --", font=ctk.CTkFont(size=12, weight="bold"), text_color=Colors.ACCENT)
        self.best_params_label.pack(anchor="w", pady=(4, 8))

        self.apply_button = ctk.CTkButton(apply_frame, text="應用最佳參數", font=ctk.CTkFont(size=13, weight="bold"), fg_color=Colors.GREEN, text_color=Colors.BG_PRIMARY, hover_color=Colors.GREEN_DARK, height=36, corner_radius=8, state="disabled", command=self._apply_best_params)
        self.apply_button.pack(fill="x")

        # 儲存狀態
        self.best_params = None
        self.current_symbol = None
        self.all_optim_results = []
        self.selected_optim_idx = 0
        self.optim_row_frames = []

    def on_page_shown(self):
        """頁面顯示時的回調（由 AppState 系統調用）

        自動處理從其他頁面傳遞過來的參數，取代 after(100) hack。
        """
        # 檢查是否有待處理的參數
        if self.app.app_state.has_pending_params():
            params, action = self.app.app_state.get_and_clear_pending_params()
            if params:
                self.load_symbol_params(params)
                # 如果有指定動作，顯示提示
                if action == 'optimize':
                    self.progress_label.configure(
                        text=f"已載入 {params.get('symbol', '')} 參數，點擊「網格優化」或「智能優化」開始"
                    )

    def load_symbol_params(self, symbol_data: dict):
        """從交易對管理頁面載入參數

        Args:
            symbol_data: 包含 symbol, tp, gs, qty, leverage 等的字典
        """
        try:
            # 設定交易對
            symbol = symbol_data.get("symbol", "XRPUSDC")
            self.symbol_entry.delete(0, "end")
            self.symbol_entry.insert(0, symbol)
            self.current_symbol = symbol

            # 設定止盈間距
            tp_str = symbol_data.get("tp", "0.4%")
            tp_value = float(tp_str.replace("%", ""))
            self.tp_entry.delete(0, "end")
            self.tp_entry.insert(0, str(tp_value))

            # 設定補倉間距
            gs_str = symbol_data.get("gs", "0.6%")
            gs_value = float(gs_str.replace("%", ""))
            self.gs_entry.delete(0, "end")
            self.gs_entry.insert(0, str(gs_value))

            # 設定每單金額
            qty = symbol_data.get("qty", 10)
            self.order_value_entry.delete(0, "end")
            self.order_value_entry.insert(0, str(qty))

            # 設定槓桿
            leverage = symbol_data.get("leverage", 20)
            self.lev_entry.delete(0, "end")
            self.lev_entry.insert(0, str(leverage))

            # 更新當前參數顯示
            self.current_params_label.configure(
                text=f"當前參數: {symbol} | TP: {tp_value}% | GS: {gs_value}% | 數量: {qty} | 槓桿: {leverage}x"
            )

            # 更新進度標籤
            self.progress_label.configure(text=f"已載入 {symbol} 的參數，可以開始回測")

        except Exception as e:
            print(f"載入參數失敗: {e}")

    def _set_days(self, days: int):
        """設定回測天數"""
        self.days_entry.delete(0, "end")
        self.days_entry.insert(0, str(days))

    def _get_symbol(self) -> str:
        """獲取交易對符號（標準化）"""
        symbol = self.symbol_entry.get().strip().upper()
        # 移除常見格式
        symbol = symbol.replace("/", "").replace(":", "").replace("-", "")
        return symbol

    def _get_days(self) -> int:
        """獲取回測天數"""
        try:
            days = int(self.days_entry.get().strip())
            return max(1, min(365, days))  # 限制 1-365 天
        except ValueError:
            return 7  # 預設 7 天

    def _get_date_range(self):
        """計算日期範圍（基於天數輸入）"""
        end_date = datetime.now()
        days = self._get_days()
        start_date = end_date - timedelta(days=days)
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

    def _download_data(self):
        """下載歷史數據"""
        if not BACKTEST_AVAILABLE:
            self._show_error("回測系統未載入")
            return

        symbol = self._get_symbol()
        if not symbol:
            self._show_error("請輸入交易對符號")
            return

        start_date, end_date = self._get_date_range()

        self.download_button.configure(text="下載中...", state="disabled")
        self.progress_label.configure(text=f"正在下載 {symbol} 數據...")

        def download():
            try:
                DataLoader = _get_backtest_module('DataLoader')
                if not DataLoader:
                    self.after(0, lambda: self.progress_label.configure(text="✗ 回測系統未載入"))
                    return
                loader = DataLoader()
                success = loader.download(symbol, start_date, end_date)
                if success:
                    self.after(0, lambda: self.progress_label.configure(text=f"✓ {symbol} 數據下載完成"))
                else:
                    self.after(0, lambda: self.progress_label.configure(text=f"✗ 下載失敗"))
            except Exception as e:
                self.after(0, lambda msg=str(e): self.progress_label.configure(text=f"✗ {msg[:50]}"))
            finally:
                self.after(0, lambda: self.download_button.configure(text="下載數據", state="normal"))

        thread = threading.Thread(target=download, daemon=True)
        thread.start()

    def _run_quick_backtest(self):
        """快速回測 - 使用當前參數"""
        if not BACKTEST_AVAILABLE:
            self._show_error("回測系統未載入")
            return

        self.quick_test_button.configure(text="回測中...", state="disabled")
        self.grid_optimize_button.configure(state="disabled")
        self.optimize_button.configure(state="disabled")
        self.progress_bar.set(0)

        symbol = self._get_symbol()
        if not symbol:
            self._show_error("請輸入交易對")
            self.quick_test_button.configure(text="快速回測", state="normal")
            return

        start_date, end_date = self._get_date_range()

        try:
            take_profit = float(self.tp_entry.get()) / 100
            grid_spacing = float(self.gs_entry.get()) / 100
            leverage = int(self.lev_entry.get())
            initial_balance = float(self.balance_entry.get())
            initial_quantity = float(self.order_value_entry.get())  # 幣的數量
        except ValueError:
            self._show_error("請輸入有效的數值")
            self.quick_test_button.configure(text="快速回測", state="normal")
            return

        # 參數驗證：止盈應小於補倉
        if take_profit >= grid_spacing:
            self._show_error("止盈間距應小於補倉間距")
            self.quick_test_button.configure(text="快速回測", state="normal")
            return

        # 參數驗證：數值範圍檢查
        if leverage < 1 or leverage > 125:
            self._show_error("槓桿應在 1-125 之間")
            self.quick_test_button.configure(text="快速回測", state="normal")
            return

        if initial_balance <= 0 or initial_quantity <= 0:
            self._show_error("資金和數量必須大於 0")
            self.quick_test_button.configure(text="快速回測", state="normal")
            return

        dir_map = {"雙向": "both", "僅多": "long", "僅空": "short"}
        direction = dir_map.get(self.dir_menu.get(), "both")

        def run_thread():
            try:
                DataLoader = _get_backtest_module('DataLoader')
                BacktestConfig = _get_backtest_module('Config')
                GridBacktester = _get_backtest_module('GridBacktester')

                if not all([DataLoader, BacktestConfig, GridBacktester]):
                    self.after(0, lambda: self._show_error("回測系統未載入"))
                    return

                self.after(0, lambda: self.progress_label.configure(text="載入數據..."))
                self.after(0, lambda: self.progress_bar.set(0.2))
                loader = DataLoader()

                try:
                    df = loader.load(symbol, start_date, end_date)
                except ValueError:
                    self.after(0, lambda: self.progress_label.configure(text="數據不存在，正在下載..."))
                    loader.download(symbol, start_date, end_date)
                    df = loader.load(symbol, start_date, end_date)

                # 檢查數據量是否足夠
                if df is None or len(df) < 100:
                    data_len = len(df) if df is not None else 0
                    self.after(0, lambda n=data_len: self._show_error(f"數據不足：僅 {n} 條，需要至少 100 條"))
                    return

                self.after(0, lambda: self.progress_bar.set(0.5))
                self.after(0, lambda n=len(df): self.progress_label.configure(text=f"執行回測... ({n:,} 條數據)"))

                # 使用終端 UI 兼容模式
                config = BacktestConfig(
                    symbol=symbol,
                    initial_balance=initial_balance,
                    initial_quantity=initial_quantity,  # 幣的數量 (與終端 UI 一致)
                    leverage=leverage,
                    take_profit_spacing=take_profit,
                    grid_spacing=grid_spacing,
                    direction=direction,
                    terminal_ui_mode=True  # 啟用終端 UI 兼容模式
                )

                bt = GridBacktester(df, config)
                result = bt.run()

                self.after(0, lambda: self.progress_bar.set(1.0))

                result_dict = {
                    "final_equity": result.final_equity,
                    "return_pct": result.return_pct * 100,
                    "max_drawdown": result.max_drawdown * 100,
                    "total_trades": result.trades_count,
                    "win_rate": result.win_rate * 100,
                    "sharpe_ratio": result.sharpe_ratio,
                    "profit_factor": result.profit_factor
                }
                self.after(0, lambda r=result_dict: self._show_results(r))
                # 快速回測完成後清空 Top5 表格，避免與優化結果混淆
                self.after(0, self._show_empty_optim_rows)
                self.after(0, lambda: self.apply_button.configure(state="disabled", text="應用選中參數"))
                self.after(0, lambda: self.best_params_label.configure(text="最佳參數: -- (需執行優化)"))

            except Exception as ex:
                self.after(0, lambda msg=str(ex): self._show_error(msg))
            finally:
                # 重置所有按鈕狀態
                self.after(0, lambda: self.quick_test_button.configure(text="快速回測", state="normal"))
                self.after(0, lambda: self.grid_optimize_button.configure(state="normal"))
                self.after(0, lambda: self.optimize_button.configure(state="normal"))

        thread = threading.Thread(target=run_thread, daemon=True)
        thread.start()

    def _run_grid_optimize(self):
        """網格優化 - 使用傳統網格搜索"""
        if self.is_optimizing:
            return

        if not BACKTEST_AVAILABLE:
            self._show_error("回測系統未載入")
            return

        self.is_optimizing = True
        self.grid_optimize_button.configure(text="優化中...", state="disabled")
        self.quick_test_button.configure(state="disabled")
        self.optimize_button.configure(state="disabled")
        self.progress_bar.set(0)

        symbol = self._get_symbol()
        if not symbol:
            self._show_error("請輸入交易對")
            self.is_optimizing = False
            self.grid_optimize_button.configure(text="網格優化", state="normal")
            self.quick_test_button.configure(state="normal")
            self.optimize_button.configure(state="normal")
            return

        start_date, end_date = self._get_date_range()

        # 獲取參數範圍
        try:
            tp_min = float(self.tp_min_entry.get()) / 100
            tp_max = float(self.tp_max_entry.get()) / 100
            gs_min = float(self.gs_min_entry.get()) / 100
            gs_max = float(self.gs_max_entry.get()) / 100
            lev_min = int(self.lev_min_entry.get())
            lev_max = int(self.lev_max_entry.get())
            initial_balance = float(self.balance_entry.get())
            order_value = float(self.order_value_entry.get())
        except ValueError:
            self._show_error("請輸入有效的數值")
            self.is_optimizing = False
            self.grid_optimize_button.configure(text="網格優化", state="normal")
            self.quick_test_button.configure(state="normal")
            self.optimize_button.configure(state="normal")
            return

        dir_map = {"雙向": "both", "僅多": "long", "僅空": "short"}
        direction = dir_map.get(self.dir_menu.get(), "both")

        # 優化目標映射 (網格優化使用)
        grid_obj_map = {
            "Sharpe Ratio": "sharpe_ratio",
            "收益率": "return_pct",
            "Sortino Ratio": "sharpe_ratio",  # GridOptimizer 不支持 Sortino，退回 Sharpe
            "Calmar Ratio": "sharpe_ratio",   # GridOptimizer 不支持 Calmar，退回 Sharpe
            "風險調整收益": "sharpe_ratio",   # GridOptimizer 不支持，退回 Sharpe
        }
        grid_metric = grid_obj_map.get(self.objective_menu.get(), "sharpe_ratio")

        def optimize_thread():
            import time
            start_time = time.time()

            try:
                DataLoader = _get_backtest_module('DataLoader')
                BacktestConfig = _get_backtest_module('Config')
                GridOptimizer = _get_backtest_module('GridOptimizer')

                if not all([DataLoader, BacktestConfig, GridOptimizer]):
                    self.after(0, lambda: self._show_error("回測系統未載入"))
                    return

                # 載入數據
                self.after(0, lambda: self.progress_label.configure(text="載入數據..."))
                loader = DataLoader()
                try:
                    df = loader.load(symbol, start_date, end_date)
                except ValueError:
                    self.after(0, lambda: self.progress_label.configure(text="數據不存在，正在下載..."))
                    loader.download(symbol, start_date, end_date)
                    df = loader.load(symbol, start_date, end_date)

                # 檢查數據量是否足夠
                if df is None or len(df) < 100:
                    data_len = len(df) if df is not None else 0
                    self.after(0, lambda n=data_len: self._show_error(f"數據不足：僅 {n} 條，需要至少 100 條"))
                    return

                self.after(0, lambda: self.progress_bar.set(0.05))
                self.after(0, lambda n=len(df): self.progress_label.configure(text=f"準備網格搜索... ({n:,} 條數據)"))

                # 建立參數範圍 (根據UI設定生成)
                # 止盈: 產生 7-10 個值
                tp_step = (tp_max - tp_min) / 8
                tp_values = [round(tp_min + i * tp_step, 4) for i in range(9)]

                # 補倉: 產生 7-10 個值
                gs_step = (gs_max - gs_min) / 8
                gs_values = [round(gs_min + i * gs_step, 4) for i in range(9)]

                # 槓桿: 根據範圍產生
                if lev_max - lev_min <= 10:
                    lev_values = list(range(lev_min, lev_max + 1, max(1, (lev_max - lev_min) // 5)))
                else:
                    lev_values = [lev_min, (lev_min + lev_max) // 2, lev_max]

                param_ranges = {
                    "take_profit_spacing": tp_values,
                    "grid_spacing": gs_values,
                    "leverage": lev_values
                }

                # 計算總組合數 (過濾 tp >= gs 的無效組合)
                valid_combos = sum(1 for tp in tp_values for gs in gs_values if tp < gs) * len(lev_values)

                # 計算並行核心數
                import os
                cpu_count = os.cpu_count() or 4
                n_jobs_display = max(1, cpu_count - 1)

                self.after(0, lambda: self.progress_label.configure(text=f"網格搜索中... (0/{valid_combos}, {n_jobs_display} 核並行)"))

                # 基礎配置 (使用終端 UI 兼容模式)
                base_config = BacktestConfig(
                    symbol=symbol,
                    initial_balance=initial_balance,
                    initial_quantity=order_value,  # 幣的數量 (與終端 UI 一致)
                    leverage=20,  # 會被覆蓋
                    direction=direction,
                    terminal_ui_mode=True  # 啟用終端 UI 兼容模式
                )

                # 創建優化器
                optimizer = GridOptimizer(df, base_config, param_ranges)

                # 進度回調
                def progress_callback(current, total):
                    progress = 0.1 + 0.8 * current / total
                    self.after(0, lambda p=progress: self.progress_bar.set(p))
                    self.after(0, lambda c=current, t=total: self.progress_label.configure(
                        text=f"網格搜索中... ({c}/{t})"
                    ))

                # 執行優化 (使用優化目標選擇, 並行加速)
                n_jobs = n_jobs_display  # 使用上面計算的核心數

                optim_result = optimizer.run(
                    metric=grid_metric,
                    ascending=False,
                    n_jobs=n_jobs,
                    progress_callback=progress_callback
                )

                self.after(0, lambda: self.progress_bar.set(1.0))

                elapsed = time.time() - start_time

                # 準備結果
                best = optim_result.best_result
                best_cfg = optim_result.best_config

                result = {
                    "final_equity": best.final_equity,
                    "return_pct": best.return_pct * 100,
                    "max_drawdown": best.max_drawdown * 100,
                    "total_trades": best.trades_count,
                    "win_rate": best.win_rate * 100,
                    "sharpe_ratio": best.sharpe_ratio,
                    "profit_factor": best.profit_factor,
                    "best_tp": best_cfg.take_profit_spacing,
                    "best_gs": best_cfg.grid_spacing,
                    "best_lev": best_cfg.leverage,
                    "elapsed": elapsed
                }

                # 更新結果
                self.after(0, lambda r=result, e=elapsed: self._show_results(r, e))

                # 更新參數重要性
                self.after(0, lambda imp=optim_result.param_importance: self._update_importance_bars(imp))

                # 顯示 Top 5 結果
                top5 = optim_result.all_results.head(5)
                self.after(0, lambda t=top5: self._show_grid_optim_results(t))

                self.after(0, lambda: self.progress_label.configure(
                    text=f"✓ 網格優化完成 ({valid_combos} 組合, {elapsed:.1f}s)"
                ))

            except Exception as ex:
                import traceback
                traceback.print_exc()
                self.after(0, lambda msg=str(ex): self._show_error(msg))
            finally:
                self.is_optimizing = False
                self.after(0, lambda: self.grid_optimize_button.configure(text="網格優化", state="normal"))
                self.after(0, lambda: self.quick_test_button.configure(state="normal"))
                self.after(0, lambda: self.optimize_button.configure(state="normal"))

        thread = threading.Thread(target=optimize_thread, daemon=True)
        thread.start()

    def _show_grid_optim_results(self, top5_df):
        """顯示網格優化 Top 5 結果"""
        for widget in self.optim_rows_frame.winfo_children():
            widget.destroy()

        self.all_optim_results = []
        self.optim_row_frames = []
        self.selected_optim_idx = 0

        # 欄位寬度 (與表頭對應)
        col_widths = [25, 50, 50, 40, 55, 50, 45, 40, 40]

        for i, (_, row) in enumerate(top5_df.iterrows()):
            tp = row.get('take_profit_spacing', 0)
            gs = row.get('grid_spacing', 0)
            lev = row.get('leverage', 20)
            ret = row.get('return_pct', 0)
            sharpe = row.get('sharpe_ratio', 0)
            dd = row.get('max_drawdown', 0)
            trades = row.get('trades', 0)
            wr = row.get('win_rate', 0)

            self.all_optim_results.append({
                'take_profit': tp,
                'grid_spacing': gs,
                'leverage': lev,
                'return_pct': ret,
                'sharpe_ratio': sharpe,
                'max_drawdown': dd,
                'trades': trades,
                'win_rate': wr
            })

            row_frame = ctk.CTkFrame(self.optim_rows_frame,
                                     fg_color=Colors.BG_TERTIARY if i == 0 else "transparent",
                                     corner_radius=4, height=28, cursor="hand2")
            row_frame.pack(fill="x", pady=2)
            row_frame.pack_propagate(False)
            self.optim_row_frames.append(row_frame)

            row_frame.bind("<Button-1>", lambda e, idx=i: self._select_optim_row(idx))

            ret_color = Colors.GREEN if ret >= 0 else Colors.RED

            values = [
                (str(i + 1), Colors.TEXT_MUTED),
                (f"{tp*100:.2f}", Colors.TEXT_PRIMARY),
                (f"{gs*100:.2f}", Colors.TEXT_PRIMARY),
                (str(int(lev)), Colors.TEXT_PRIMARY),
                (f"{ret*100:.2f}%", ret_color),
                (f"{sharpe:.2f}", Colors.TEXT_PRIMARY),
                (f"{dd*100:.1f}%", Colors.TEXT_MUTED),
                (str(int(trades)), Colors.TEXT_MUTED),
                (f"{wr*100:.0f}%", Colors.TEXT_MUTED),
            ]

            for j, (v, color) in enumerate(values):
                font_weight = "bold" if i == 0 else "normal"
                lbl = ctk.CTkLabel(row_frame, text=v, font=ctk.CTkFont(size=9, weight=font_weight),
                                   text_color=color, width=col_widths[j])
                lbl.grid(row=0, column=j, padx=1, pady=2)
                lbl.bind("<Button-1>", lambda e, idx=i: self._select_optim_row(idx))

        # 更新最佳參數和當前參數標籤
        if len(self.all_optim_results) > 0:
            best = self.all_optim_results[0]
            self.best_params = best
            self.current_symbol = self._get_symbol()
            self.best_params_label.configure(
                text=f"最佳: 止盈 {best['take_profit']*100:.3f}% / 補倉 {best['grid_spacing']*100:.3f}% / 槓桿 {best['leverage']}x"
            )
            # 更新當前參數標籤（顯示用戶輸入的快速回測參數）
            try:
                current_tp = float(self.tp_entry.get())
                current_gs = float(self.gs_entry.get())
                self.current_params_label.configure(
                    text=f"當前: 止盈 {current_tp:.2f}% / 補倉 {current_gs:.2f}%"
                )
            except ValueError:
                pass
            self.apply_button.configure(state="normal", text="應用選中參數")

    def _run_smart_optimize(self):
        """智能優化 - 使用 Optuna TPE"""
        if self.is_optimizing:
            return

        if not BACKTEST_AVAILABLE:
            self._show_error("回測系統未載入")
            return

        # 檢查是否有 SmartOptimizer
        try:
            from backtest_system import SmartOptimizer, SMART_OPTIMIZER_AVAILABLE
            if not SMART_OPTIMIZER_AVAILABLE or SmartOptimizer is None:
                self._show_error("請安裝 Optuna: pip install optuna")
                return
        except ImportError:
            self._show_error("請安裝 Optuna: pip install optuna")
            return

        self.is_optimizing = True
        self.optimize_button.configure(text="優化中...", state="disabled")
        self.quick_test_button.configure(state="disabled")
        self.grid_optimize_button.configure(state="disabled")
        self.progress_bar.set(0)

        symbol = self._get_symbol()
        if not symbol:
            self._show_error("請輸入交易對")
            self.is_optimizing = False
            self.optimize_button.configure(text="智能優化", state="normal")
            self.quick_test_button.configure(state="normal")
            self.grid_optimize_button.configure(state="normal")
            return

        start_date, end_date = self._get_date_range()

        # 獲取參數範圍
        try:
            tp_min = float(self.tp_min_entry.get()) / 100
            tp_max = float(self.tp_max_entry.get()) / 100
            gs_min = float(self.gs_min_entry.get()) / 100
            gs_max = float(self.gs_max_entry.get()) / 100
            lev_min = int(self.lev_min_entry.get())
            lev_max = int(self.lev_max_entry.get())
            n_trials = int(self.n_trials_entry.get())
            initial_balance = float(self.balance_entry.get())
            order_value = float(self.order_value_entry.get())
        except ValueError:
            self._show_error("請輸入有效的數值")
            self.is_optimizing = False
            self.optimize_button.configure(text="智能優化", state="normal")
            self.quick_test_button.configure(state="normal")
            self.grid_optimize_button.configure(state="normal")
            return

        # 優化目標映射
        obj_map = {
            "Sharpe Ratio": "sharpe",
            "收益率": "return",
            "Sortino Ratio": "sortino",
            "Calmar Ratio": "calmar",
            "風險調整收益": "risk_adjusted",
        }
        objective = obj_map.get(self.objective_menu.get(), "sharpe")

        dir_map = {"雙向": "both", "僅多": "long", "僅空": "short"}
        direction = dir_map.get(self.dir_menu.get(), "both")

        def optimize_thread():
            import time
            start_time = time.time()

            try:
                DataLoader = _get_backtest_module('DataLoader')
                BacktestConfig = _get_backtest_module('Config')

                if not DataLoader or not BacktestConfig:
                    self.after(0, lambda: self._show_error("回測系統未載入"))
                    return

                self.after(0, lambda: self.progress_label.configure(text="載入數據..."))
                self.after(0, lambda: self.progress_bar.set(0.05))
                loader = DataLoader()

                try:
                    df = loader.load(symbol, start_date, end_date)
                except ValueError:
                    self.after(0, lambda: self.progress_label.configure(text="數據不存在，正在下載..."))
                    loader.download(symbol, start_date, end_date)
                    df = loader.load(symbol, start_date, end_date)

                # 檢查數據量是否足夠
                if df is None or len(df) < 100:
                    data_len = len(df) if df is not None else 0
                    self.after(0, lambda n=data_len: self._show_error(f"數據不足：僅 {n} 條，需要至少 100 條"))
                    return

                # 計算並行核心數
                import os
                cpu_count = os.cpu_count() or 4
                n_jobs_smart = max(1, cpu_count - 1)

                self.after(0, lambda n=len(df), nt=n_trials, nj=n_jobs_smart: self.progress_label.configure(
                    text=f"開始 TPE 貝葉斯優化 ({nt} 次試驗, {nj} 核並行, {n:,} 條數據)..."
                ))
                self.after(0, lambda: self.progress_bar.set(0.1))

                # 創建基礎配置 (使用終端 UI 兼容模式)
                base_config = BacktestConfig(
                    symbol=symbol,
                    initial_balance=initial_balance,
                    initial_quantity=order_value,  # 幣的數量 (與終端 UI 一致)
                    direction=direction,
                    terminal_ui_mode=True  # 啟用終端 UI 兼容模式
                )

                # 創建智能優化器
                param_bounds = {
                    "take_profit_spacing": (tp_min, tp_max),
                    "grid_spacing": (gs_min, gs_max),
                    "leverage": (lev_min, lev_max),
                }

                optimizer = SmartOptimizer(df, base_config, param_bounds=param_bounds)

                # 進度回調
                def progress_callback(current, total, best_value):
                    progress = 0.1 + 0.85 * (current / total)
                    self.after(0, lambda p=progress: self.progress_bar.set(p))
                    self.after(0, lambda c=current, t=total, b=best_value:
                        self.progress_label.configure(text=f"優化中... {c}/{t} (最佳: {b:.4f})"))

                # 優化目標映射 (轉為 OptimizationObjective 枚舉)
                from backtest_system.smart_optimizer import OptimizationObjective, OptimizationMethod
                obj_enum_map = {
                    "sharpe": OptimizationObjective.SHARPE,
                    "return": OptimizationObjective.RETURN,
                    "sortino": OptimizationObjective.SORTINO,
                    "calmar": OptimizationObjective.CALMAR,
                    "risk_adjusted": OptimizationObjective.RISK_ADJUSTED,
                }
                objective_enum = obj_enum_map.get(objective, OptimizationObjective.SHARPE)

                # 執行優化 (使用 optimize 方法以支持進度回調, 並行加速)
                result = optimizer.optimize(
                    n_trials=n_trials,
                    objective=objective_enum,
                    method=OptimizationMethod.TPE,
                    n_jobs=n_jobs_smart,
                    progress_callback=progress_callback,
                    show_progress=False  # 不在終端顯示
                )

                elapsed = time.time() - start_time
                self.after(0, lambda: self.progress_bar.set(1.0))

                # 準備結果
                best = result.best_params
                metrics = result.best_metrics

                result_dict = {
                    "final_equity": metrics.get('return_pct', 0) * initial_balance + initial_balance,
                    "return_pct": metrics.get('return_pct', 0) * 100,
                    "max_drawdown": metrics.get('max_drawdown', 0) * 100,
                    "total_trades": metrics.get('trades_count', 0),
                    "win_rate": metrics.get('win_rate', 0) * 100,
                    "sharpe_ratio": metrics.get('sharpe_ratio', 0),
                    "profit_factor": metrics.get('profit_factor', 0),  # 保留原值，顯示時判斷
                    "optimization_time": elapsed,
                    "best_tp": best.get('take_profit_spacing', 0.004),
                    "best_gs": best.get('grid_spacing', 0.006),
                    "best_lev": best.get('leverage', 20),
                }

                self.after(0, lambda r=result_dict: self._show_smart_results(r))

                # 更新參數重要性
                self.after(0, lambda imp=result.param_importance: self._update_importance_bars(imp))

                # 顯示 Top 5 結果
                top5_df = result.get_top_n(5)
                self.after(0, lambda df=top5_df: self._show_smart_optim_results(df))

            except Exception as ex:
                import traceback
                traceback.print_exc()
                self.after(0, lambda msg=str(ex): self._show_error(msg))
            finally:
                self.after(0, self._reset_optimize_buttons)

        thread = threading.Thread(target=optimize_thread, daemon=True)
        thread.start()

    def _reset_optimize_buttons(self):
        """重置優化按鈕狀態"""
        self.is_optimizing = False
        self.optimize_button.configure(text="智能優化", state="normal")
        self.grid_optimize_button.configure(text="網格優化", state="normal")
        self.quick_test_button.configure(state="normal")

    def _show_error(self, message: str):
        """顯示錯誤"""
        self._reset_optimize_buttons()
        self.progress_label.configure(text=f"✗ {message[:80]}")
        self.progress_bar.set(0)
        for label in self.result_labels.values():
            label.configure(text="--")

    def _show_results(self, result: dict, elapsed: float = None):
        """顯示回測/優化結果

        Args:
            result: 結果字典
            elapsed: 優化耗時（可選，快速回測時為 None）
        """
        self.quick_test_button.configure(text="快速回測", state="normal")

        if "error" in result:
            self._show_error(result["error"])
            return

        # 設定進度標籤文字
        if elapsed:
            self.progress_label.configure(text=f"✓ 優化完成 (耗時 {elapsed:.1f}s)")
        else:
            self.progress_label.configure(text="✓ 回測完成")

        # 優化耗時顯示
        elapsed_str = f"{elapsed:.1f}s" if elapsed else "--"

        # 更新結果顯示
        results = {
            "最終權益": f"${result.get('final_equity', 1000):,.2f}",
            "收益率": f"{result.get('return_pct', 0):+.2f}%",
            "最大回撤": f"-{abs(result.get('max_drawdown', 0)):.2f}%",
            "Sharpe": f"{result.get('sharpe_ratio', 0):.3f}",
            "交易次數": str(int(result.get('total_trades', 0))),
            "勝率": f"{result.get('win_rate', 0):.1f}%",
            "盈虧比": f"{result.get('profit_factor', 0):.2f}" if result.get('profit_factor', 0) < 999 else "∞",
            "優化耗時": elapsed_str,
        }

        for label, value in results.items():
            if label in self.result_labels:
                self.result_labels[label].configure(text=value)
                if label == "收益率":
                    color = Colors.GREEN if result.get('return_pct', 0) >= 0 else Colors.RED
                    self.result_labels[label].configure(text_color=color)

        # 如果有最佳參數，更新標籤
        if 'best_tp' in result and 'best_gs' in result:
            tp = result['best_tp'] * 100
            gs = result['best_gs'] * 100
            lev = result.get('best_lev', 20)
            self.best_params = {
                'take_profit': result['best_tp'],
                'grid_spacing': result['best_gs'],
                'leverage': lev
            }
            self.current_symbol = self._get_symbol()
            self.best_params_label.configure(
                text=f"最佳: 止盈 {tp:.3f}% / 補倉 {gs:.3f}% / 槓桿 {lev}x"
            )
            # 更新當前參數標籤
            try:
                current_tp = float(self.tp_entry.get())
                current_gs = float(self.gs_entry.get())
                self.current_params_label.configure(
                    text=f"當前: 止盈 {current_tp:.2f}% / 補倉 {current_gs:.2f}%"
                )
            except ValueError:
                pass
            self.apply_button.configure(state="normal", text="應用選中參數")

    def _show_smart_results(self, result: dict):
        """顯示智能優化結果"""
        self._reset_optimize_buttons()

        tp = result.get('best_tp', 0) * 100
        gs = result.get('best_gs', 0) * 100
        lev = result.get('best_lev', 20)
        elapsed = result.get('optimization_time', 0)

        self.progress_label.configure(
            text=f"✓ 最佳: 止盈 {tp:.3f}% / 補倉 {gs:.3f}% / 槓桿 {lev}x (耗時 {elapsed:.1f}s)"
        )

        # 更新結果顯示
        results = {
            "最終權益": f"${result.get('final_equity', 1000):,.2f}",
            "收益率": f"{result.get('return_pct', 0):+.2f}%",
            "最大回撤": f"-{abs(result.get('max_drawdown', 0)):.2f}%",
            "Sharpe": f"{result.get('sharpe_ratio', 0):.3f}",
            "交易次數": str(int(result.get('total_trades', 0))),
            "勝率": f"{result.get('win_rate', 0):.1f}%",
            "盈虧比": f"{result.get('profit_factor', 0):.2f}" if result.get('profit_factor', 0) < 999 else "∞",
            "優化耗時": f"{elapsed:.1f}s",
        }

        for label, value in results.items():
            if label in self.result_labels:
                self.result_labels[label].configure(text=value)
                if label == "收益率":
                    color = Colors.GREEN if result.get('return_pct', 0) >= 0 else Colors.RED
                    self.result_labels[label].configure(text_color=color)

        # 儲存最佳參數
        self.best_params = {
            'take_profit': result.get('best_tp', 0.004),
            'grid_spacing': result.get('best_gs', 0.006),
            'leverage': result.get('best_lev', 20)
        }
        self.current_symbol = self._get_symbol()

        # 更新標籤
        self.current_params_label.configure(
            text=f"當前: 止盈 {float(self.tp_entry.get()):.2f}% / 補倉 {float(self.gs_entry.get()):.2f}%"
        )
        self.best_params_label.configure(
            text=f"最佳: 止盈 {tp:.3f}% / 補倉 {gs:.3f}% / 槓桿 {lev}x"
        )
        self.apply_button.configure(state="normal")

    def _update_importance_bars(self, importance: dict):
        """更新參數重要性條"""
        for widget in self.importance_bars_frame.winfo_children():
            widget.destroy()

        name_map = {
            'take_profit_spacing': '止盈間距',
            'grid_spacing': '補倉間距',
            'leverage': '槓桿'
        }

        for param, value in sorted(importance.items(), key=lambda x: -x[1]):
            bar_frame = ctk.CTkFrame(self.importance_bars_frame, fg_color="transparent", height=20)
            bar_frame.pack(fill="x", pady=1)
            bar_frame.pack_propagate(False)

            name = name_map.get(param, param)
            ctk.CTkLabel(bar_frame, text=name, font=ctk.CTkFont(size=10), text_color=Colors.TEXT_MUTED, width=70).pack(side="left")

            bar = ctk.CTkProgressBar(bar_frame, height=8, corner_radius=4, fg_color=Colors.BG_TERTIARY, progress_color=Colors.ACCENT)
            bar.pack(side="left", fill="x", expand=True, padx=(0, 4))
            bar.set(value)

            pct_label = ctk.CTkLabel(bar_frame, text=f"{value*100:.1f}%", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED, width=40)
            pct_label.pack(side="right")

    def _show_smart_optim_results(self, top5_df):
        """顯示智能優化 Top 5 結果"""
        for widget in self.optim_rows_frame.winfo_children():
            widget.destroy()

        self.all_optim_results = []
        self.optim_row_frames = []
        self.selected_optim_idx = 0

        # 欄位寬度 (與表頭對應)
        col_widths = [25, 50, 50, 40, 55, 50, 45, 40, 40]

        for i, (_, row) in enumerate(top5_df.iterrows()):
            tp = row.get('param_take_profit_spacing', 0)
            gs = row.get('param_grid_spacing', 0)
            lev = row.get('param_leverage', 20)
            ret = row.get('return_pct', 0)
            sharpe = row.get('sharpe_ratio', 0)
            dd = row.get('max_drawdown', 0)
            trades = row.get('trades_count', 0)
            wr = row.get('win_rate', 0)

            self.all_optim_results.append({
                'take_profit': tp,
                'grid_spacing': gs,
                'leverage': lev,
                'return_pct': ret,
                'sharpe_ratio': sharpe,
                'max_drawdown': dd,
                'trades': trades,
                'win_rate': wr
            })

            row_frame = ctk.CTkFrame(self.optim_rows_frame,
                                     fg_color=Colors.BG_TERTIARY if i == 0 else "transparent",
                                     corner_radius=4, height=28, cursor="hand2")
            row_frame.pack(fill="x", pady=2)
            row_frame.pack_propagate(False)
            self.optim_row_frames.append(row_frame)

            row_frame.bind("<Button-1>", lambda e, idx=i: self._select_optim_row(idx))

            ret_color = Colors.GREEN if ret >= 0 else Colors.RED

            values = [
                (str(i + 1), Colors.TEXT_MUTED),
                (f"{tp*100:.2f}", Colors.TEXT_PRIMARY),
                (f"{gs*100:.2f}", Colors.TEXT_PRIMARY),
                (str(int(lev)), Colors.TEXT_PRIMARY),
                (f"{ret*100:.2f}%", ret_color),
                (f"{sharpe:.2f}", Colors.TEXT_PRIMARY),
                (f"{dd*100:.1f}%", Colors.TEXT_MUTED),
                (str(int(trades)), Colors.TEXT_MUTED),
                (f"{wr*100:.0f}%", Colors.TEXT_MUTED),
            ]

            for j, (v, color) in enumerate(values):
                font_weight = "bold" if i == 0 else "normal"
                lbl = ctk.CTkLabel(row_frame, text=v, font=ctk.CTkFont(size=9, weight=font_weight),
                                   text_color=color, width=col_widths[j])
                lbl.grid(row=0, column=j, padx=1, pady=2)
                lbl.bind("<Button-1>", lambda e, idx=i: self._select_optim_row(idx))

        # 更新最佳參數標籤和應用按鈕 (與網格優化一致)
        if len(self.all_optim_results) > 0:
            best = self.all_optim_results[0]
            self.best_params = best
            self.current_symbol = self._get_symbol()
            self.best_params_label.configure(
                text=f"最佳: 止盈 {best['take_profit']*100:.3f}% / 補倉 {best['grid_spacing']*100:.3f}% / 槓桿 {best['leverage']}x"
            )
            self.apply_button.configure(state="normal", text="應用選中參數")

    def _show_empty_optim_rows(self):
        """顯示空的優化結果行"""
        for widget in self.optim_rows_frame.winfo_children():
            widget.destroy()

        # 欄位寬度 (與表頭對應: #, 止盈%, 補倉%, 槓桿, 收益率, Sharpe, 回撤, 交易, 勝率)
        col_widths = [25, 50, 50, 40, 55, 50, 45, 40, 40]

        for i in range(5):
            row_frame = ctk.CTkFrame(self.optim_rows_frame, fg_color="transparent", height=28)
            row_frame.pack(fill="x", pady=1)
            row_frame.pack_propagate(False)

            values = [str(i + 1), "--", "--", "--", "--", "--", "--", "--", "--"]
            for j, v in enumerate(values):
                ctk.CTkLabel(row_frame, text=v, font=ctk.CTkFont(size=9),
                            text_color=Colors.TEXT_MUTED, width=col_widths[j]).grid(row=0, column=j, padx=1, pady=2)

    def _show_optim_results(self, results_df):
        """顯示優化結果表格 (Top 5) - 可點擊選擇"""
        # 清除舊行
        for widget in self.optim_rows_frame.winfo_children():
            widget.destroy()

        # 儲存結果供選擇使用
        self.all_optim_results = results_df.head(5).to_dict('records')
        self.selected_optim_idx = 0  # 默認選中第一行
        self.optim_row_frames = []  # 儲存行框架以便更新高亮

        # 顯示 Top 5
        for i, (_, row) in enumerate(results_df.head(5).iterrows()):
            row_frame = ctk.CTkFrame(self.optim_rows_frame,
                                     fg_color=Colors.BG_TERTIARY if i == 0 else "transparent",
                                     corner_radius=4,
                                     height=32,
                                     cursor="hand2")  # 鼠標指針變成手型
            row_frame.pack(fill="x", pady=2)
            row_frame.pack_propagate(False)
            self.optim_row_frames.append(row_frame)

            # 綁定點擊事件
            row_frame.bind("<Button-1>", lambda e, idx=i: self._select_optim_row(idx))

            # 獲取數值
            tp = float(row.get('take_profit', 0))
            gs = float(row.get('grid_spacing', 0))
            ret = float(row.get('return_pct', 0))
            dd = float(row.get('max_drawdown', 0))
            trades = int(row.get('trades', 0))
            wr = float(row.get('win_rate', 0))

            # 收益率顏色
            ret_color = Colors.GREEN if ret >= 0 else Colors.RED

            values = [
                (str(i + 1), Colors.TEXT_MUTED),
                (f"{tp*100:.2f}%", Colors.TEXT_PRIMARY),
                (f"{gs*100:.2f}%", Colors.TEXT_PRIMARY),
                (f"{ret*100:.2f}%", ret_color),
                (f"{dd*100:.2f}%", Colors.TEXT_MUTED),
                (str(trades), Colors.TEXT_MUTED),
                (f"{wr*100:.1f}%", Colors.TEXT_MUTED),
            ]

            for j, (v, color) in enumerate(values):
                font_weight = "bold" if i == 0 else "normal"
                lbl = ctk.CTkLabel(row_frame, text=v, font=ctk.CTkFont(size=10, weight=font_weight),
                            text_color=color, width=60 if j > 0 else 30)
                lbl.grid(row=0, column=j, padx=4, pady=4)
                # 讓標籤也能傳遞點擊事件到父框架
                lbl.bind("<Button-1>", lambda e, idx=i: self._select_optim_row(idx))

        # 更新選中參數標籤
        if len(results_df) > 0:
            self._update_selected_params_label()
            self.current_symbol = self._get_symbol()

            # 更新當前參數標籤
            current_tp = float(self.tp_entry.get()) / 100
            current_gs = float(self.gs_entry.get()) / 100
            self.current_params_label.configure(
                text=f"當前參數: 止盈 {current_tp*100:.2f}% / 補倉 {current_gs*100:.2f}%"
            )

            # 啟用應用按鈕
            self.apply_button.configure(state="normal", text="應用選中參數")

    def _select_optim_row(self, idx):
        """選擇優化結果行"""
        if not hasattr(self, 'all_optim_results') or idx >= len(self.all_optim_results):
            return

        self.selected_optim_idx = idx

        # 更新行高亮
        for i, frame in enumerate(self.optim_row_frames):
            if i == idx:
                frame.configure(fg_color=Colors.BG_TERTIARY)
            else:
                frame.configure(fg_color="transparent")

        # 更新選中參數標籤
        self._update_selected_params_label()

        # 重新啟用應用按鈕
        self.apply_button.configure(state="normal", text="應用選中參數")

    def _update_selected_params_label(self):
        """更新選中參數標籤"""
        if not hasattr(self, 'all_optim_results') or not self.all_optim_results:
            return

        selected = self.all_optim_results[self.selected_optim_idx]
        tp = float(selected.get('take_profit', 0))
        gs = float(selected.get('grid_spacing', 0))
        lev = int(selected.get('leverage', 20))
        sharpe = float(selected.get('sharpe_ratio', 0))

        # 儲存選中參數
        self.best_params = {'take_profit': tp, 'grid_spacing': gs, 'leverage': lev}

        # 更新標籤（顯示選中的是第幾名）
        rank = self.selected_optim_idx + 1
        self.best_params_label.configure(
            text=f"#{rank}: TP {tp*100:.2f}% / GS {gs*100:.2f}% / {lev}x (Sharpe: {sharpe:.3f})"
        )

    def _apply_best_params(self):
        """應用最佳參數到交易對配置"""
        if not self.best_params or not self.current_symbol:
            return

        try:
            from as_terminal_max_bitget import GlobalConfig, SymbolConfig

            config = GlobalConfig.load()
            symbol = self.current_symbol
            is_new_symbol = symbol not in config.symbols

            # 更新或創建配置
            if is_new_symbol:
                # 創建新的交易對配置
                # 正確生成 ccxt_symbol: XRPUSDC -> XRP/USDC:USDC
                base = symbol.replace("USDC", "").replace("USDT", "")
                quote = "USDC" if "USDC" in symbol else "USDT"
                ccxt_symbol = f"{base}/{quote}:{quote}"
                config.symbols[symbol] = SymbolConfig(
                    symbol=symbol,
                    ccxt_symbol=ccxt_symbol,
                    enabled=True  # 新交易對預設啟用
                )

            # 應用最佳參數
            config.symbols[symbol].take_profit_spacing = self.best_params['take_profit']
            config.symbols[symbol].grid_spacing = self.best_params['grid_spacing']
            if 'leverage' in self.best_params:
                config.symbols[symbol].leverage = self.best_params['leverage']
            config.save()

            # 通知交易對管理頁面刷新
            if "symbols" in self.app.pages:
                symbols_page = self.app.pages["symbols"]
                if hasattr(symbols_page, '_load_config'):
                    self.after(100, symbols_page._load_config)

            # 更新輸入框
            self.tp_entry.delete(0, 'end')
            self.tp_entry.insert(0, f"{self.best_params['take_profit']*100:.2f}")
            self.gs_entry.delete(0, 'end')
            self.gs_entry.insert(0, f"{self.best_params['grid_spacing']*100:.2f}")
            if 'leverage' in self.best_params:
                self.lev_entry.delete(0, 'end')
                self.lev_entry.insert(0, str(self.best_params['leverage']))

            # 顯示成功訊息
            rank = getattr(self, 'selected_optim_idx', 0) + 1
            tp_pct = self.best_params['take_profit'] * 100
            gs_pct = self.best_params['grid_spacing'] * 100
            lev = self.best_params.get('leverage', 20)
            self.progress_label.configure(
                text=f"✓ 已應用 #{rank}: TP {tp_pct:.2f}% / GS {gs_pct:.2f}% / {lev}x"
            )
            self.apply_button.configure(text=f"已應用 #{rank}", state="disabled")

            # 2秒後恢復按鈕
            self.after(2000, lambda: self.apply_button.configure(text="應用選中參數", state="normal"))

        except Exception as ex:
            self.progress_label.configure(text=f"✗ 應用失敗: {str(ex)[:50]}")


# ═══════════════════════════════════════════════════════════════════════════
# 選幣儀表板頁面
# ═══════════════════════════════════════════════════════════════════════════
