"""
交易控制台頁面
"""

import asyncio
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, TYPE_CHECKING

import customtkinter as ctk

from ..styles import Colors
from ..components import Card
from ..dialogs import ConfirmDialog

if TYPE_CHECKING:
    from gui.app import ASGridApp

class TradingPage(ctk.CTkFrame):
    """交易控制台頁面"""

    def __init__(self, master, app: "ASGridApp"):
        super().__init__(master, fg_color=Colors.BG_PRIMARY)
        self.app = app

        # 交易引擎
        self.engine = None
        self._trading_thread = None
        self._bot = None
        self._bot_loop = None
        self._update_timer = None

        self._create_ui()

    def _create_ui(self):
        # ========== 頂部：帳戶 + 控制 ==========
        top_frame = ctk.CTkFrame(self, fg_color="transparent")
        top_frame.pack(fill="x", pady=(0, 8))

        # 左側：帳戶表格 (緊湊版)
        account_frame = ctk.CTkFrame(top_frame, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        account_frame.pack(side="left", fill="y", padx=(0, 8))

        # 表格式帳戶顯示
        account_table = ctk.CTkFrame(account_frame, fg_color="transparent")
        account_table.pack(fill="x", padx=12, pady=8)

        # 設定列寬
        account_table.grid_columnconfigure(0, weight=0, minsize=50)  # 標籤
        account_table.grid_columnconfigure(1, weight=1, minsize=80)  # USDC
        account_table.grid_columnconfigure(2, weight=1, minsize=80)  # USDT

        # 標題行
        ctk.CTkLabel(account_table, text="", font=ctk.CTkFont(size=9)).grid(row=0, column=0)
        ctk.CTkLabel(account_table, text="USDC", font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.GREEN).grid(row=0, column=1, sticky="e", padx=4)
        ctk.CTkLabel(account_table, text="USDT", font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.YELLOW).grid(row=0, column=2, sticky="e", padx=4)

        # 權益行
        ctk.CTkLabel(account_table, text="權益", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).grid(row=1, column=0, sticky="w")
        self.usdc_equity = ctk.CTkLabel(account_table, text="--", font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.TEXT_PRIMARY)
        self.usdc_equity.grid(row=1, column=1, sticky="e", padx=4)
        self.usdt_equity = ctk.CTkLabel(account_table, text="--", font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.TEXT_PRIMARY)
        self.usdt_equity.grid(row=1, column=2, sticky="e", padx=4)

        # 可用行
        ctk.CTkLabel(account_table, text="可用", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).grid(row=2, column=0, sticky="w")
        self.usdc_available = ctk.CTkLabel(account_table, text="--", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_SECONDARY)
        self.usdc_available.grid(row=2, column=1, sticky="e", padx=4)
        self.usdt_available = ctk.CTkLabel(account_table, text="--", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_SECONDARY)
        self.usdt_available.grid(row=2, column=2, sticky="e", padx=4)

        # 保證金率行
        ctk.CTkLabel(account_table, text="保證金", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).grid(row=3, column=0, sticky="w")
        self.usdc_margin = ctk.CTkLabel(account_table, text="--", font=ctk.CTkFont(size=9), text_color=Colors.GREEN)
        self.usdc_margin.grid(row=3, column=1, sticky="e", padx=4)
        self.usdt_margin = ctk.CTkLabel(account_table, text="--", font=ctk.CTkFont(size=9), text_color=Colors.GREEN)
        self.usdt_margin.grid(row=3, column=2, sticky="e", padx=4)

        # 浮盈行
        ctk.CTkLabel(account_table, text="浮盈", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).grid(row=4, column=0, sticky="w")
        self.usdc_pnl = ctk.CTkLabel(account_table, text="--", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED)
        self.usdc_pnl.grid(row=4, column=1, sticky="e", padx=4)
        self.usdt_pnl = ctk.CTkLabel(account_table, text="--", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED)
        self.usdt_pnl.grid(row=4, column=2, sticky="e", padx=4)

        # 右側：控制按鈕 + 統計 (在同一行)
        control_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        control_frame.pack(side="left", fill="both", expand=True)

        # 控制按鈕
        btn_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        btn_frame.pack(fill="x")

        self.start_button = ctk.CTkButton(
            btn_frame,
            text="▶ 開始交易",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            height=36,
            width=100,
            corner_radius=6,
            command=self._toggle_trading
        )
        self.start_button.pack(side="left", padx=(0, 6))

        self.pause_button = ctk.CTkButton(
            btn_frame,
            text="暫停補倉",
            font=ctk.CTkFont(size=11),
            fg_color=Colors.BG_TERTIARY,
            hover_color=Colors.BORDER,
            height=36,
            width=80,
            corner_radius=6,
            command=self._toggle_pause
        )
        self.pause_button.pack(side="left", padx=(0, 6))
        self.is_paused = False

        ctk.CTkButton(
            btn_frame,
            text="一鍵平倉",
            font=ctk.CTkFont(size=11),
            fg_color=Colors.TEXT_MUTED,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.TEXT_SECONDARY,
            height=36,
            width=80,
            corner_radius=6,
            command=self._close_all_positions
        ).pack(side="left", padx=(0, 6))

        # 統計 (同一行右側)
        stats_frame = ctk.CTkFrame(btn_frame, fg_color=Colors.BG_SECONDARY, corner_radius=6)
        stats_frame.pack(side="right")

        self.runtime_label = ctk.CTkLabel(stats_frame, text="00:00:00", font=ctk.CTkFont(size=10), text_color=Colors.TEXT_SECONDARY)
        self.runtime_label.pack(side="left", padx=8, pady=6)

        self.trades_label = ctk.CTkLabel(stats_frame, text="交易: 0", font=ctk.CTkFont(size=10), text_color=Colors.TEXT_SECONDARY)
        self.trades_label.pack(side="left", padx=8, pady=6)

        self.total_pnl_label = ctk.CTkLabel(stats_frame, text="+0.00", font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.GREEN)
        self.total_pnl_label.pack(side="left", padx=8, pady=6)

        # ========== Bandit + 領先指標面板 ==========
        indicators_frame = ctk.CTkFrame(self, fg_color="transparent")
        indicators_frame.pack(fill="x", pady=(0, 12))

        # === Bandit 狀態 ===
        bandit_card = ctk.CTkFrame(indicators_frame, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        bandit_card.pack(side="left", fill="y", padx=(0, 8))

        ctk.CTkLabel(bandit_card, text="Bandit", font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.TEXT_MUTED).pack(padx=12, pady=(8, 4))

        bandit_inner = ctk.CTkFrame(bandit_card, fg_color="transparent")
        bandit_inner.pack(padx=12, pady=(0, 8))

        ctk.CTkLabel(bandit_inner, text="Arm:", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).pack(side="left")
        self.bandit_arm_label = ctk.CTkLabel(bandit_inner, text="--", font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.GREEN)
        self.bandit_arm_label.pack(side="left", padx=(4, 12))

        ctk.CTkLabel(bandit_inner, text="Context:", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).pack(side="left")
        self.bandit_context_label = ctk.CTkLabel(bandit_inner, text="--", font=ctk.CTkFont(size=10), text_color=Colors.TEXT_SECONDARY)
        self.bandit_context_label.pack(side="left", padx=(4, 0))

        # === 領先指標 ===
        leading_card = ctk.CTkFrame(indicators_frame, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        leading_card.pack(side="left", fill="y", padx=(0, 8))

        ctk.CTkLabel(leading_card, text="領先指標", font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.TEXT_MUTED).pack(padx=12, pady=(8, 4))

        leading_inner = ctk.CTkFrame(leading_card, fg_color="transparent")
        leading_inner.pack(padx=12, pady=(0, 8))

        # OFI
        ctk.CTkLabel(leading_inner, text="OFI:", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).pack(side="left")
        self.ofi_label = ctk.CTkLabel(leading_inner, text="0.00", font=ctk.CTkFont(size=10), text_color=Colors.TEXT_SECONDARY)
        self.ofi_label.pack(side="left", padx=(4, 12))

        # Volume
        ctk.CTkLabel(leading_inner, text="Vol:", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).pack(side="left")
        self.volume_ratio_label = ctk.CTkLabel(leading_inner, text="1.0x", font=ctk.CTkFont(size=10), text_color=Colors.TEXT_SECONDARY)
        self.volume_ratio_label.pack(side="left", padx=(4, 12))

        # Spread
        ctk.CTkLabel(leading_inner, text="Spread:", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).pack(side="left")
        self.spread_ratio_label = ctk.CTkLabel(leading_inner, text="1.0x", font=ctk.CTkFont(size=10), text_color=Colors.TEXT_SECONDARY)
        self.spread_ratio_label.pack(side="left", padx=(4, 0))

        # === Funding Rate ===
        funding_card = ctk.CTkFrame(indicators_frame, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        funding_card.pack(side="left", fill="y", padx=(0, 8))

        ctk.CTkLabel(funding_card, text="Funding Rate", font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.TEXT_MUTED).pack(padx=12, pady=(8, 4))

        funding_inner = ctk.CTkFrame(funding_card, fg_color="transparent")
        funding_inner.pack(padx=12, pady=(0, 8))

        self.funding_rate_label = ctk.CTkLabel(funding_inner, text="+0.0000%", font=ctk.CTkFont(size=11, weight="bold"), text_color=Colors.TEXT_SECONDARY)
        self.funding_rate_label.pack(side="left")

        ctk.CTkLabel(funding_inner, text=" → ", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).pack(side="left")

        self.funding_bias_label = ctk.CTkLabel(funding_inner, text="中性", font=ctk.CTkFont(size=10), text_color=Colors.TEXT_SECONDARY)
        self.funding_bias_label.pack(side="left")

        # === 風控狀態 ===
        risk_card = ctk.CTkFrame(indicators_frame, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        risk_card.pack(side="left", fill="y")

        ctk.CTkLabel(risk_card, text="風控", font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.TEXT_MUTED).pack(padx=12, pady=(8, 4))

        risk_inner = ctk.CTkFrame(risk_card, fg_color="transparent")
        risk_inner.pack(padx=12, pady=(0, 8))

        ctk.CTkLabel(risk_inner, text="DD:", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).pack(side="left")
        self.drawdown_label = ctk.CTkLabel(risk_inner, text="0.0%", font=ctk.CTkFont(size=10), text_color=Colors.GREEN)
        self.drawdown_label.pack(side="left", padx=(4, 12))

        ctk.CTkLabel(risk_inner, text="Pos:", font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).pack(side="left")
        self.total_position_label = ctk.CTkLabel(risk_inner, text="0", font=ctk.CTkFont(size=10), text_color=Colors.TEXT_SECONDARY)
        self.total_position_label.pack(side="left", padx=(4, 0))

        # ========== 下方區域 ==========
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.pack(fill="both", expand=True)

        # 左側：交易對監控
        left_card = Card(bottom_frame, title="交易對監控")
        left_card.pack(side="left", fill="both", expand=True, padx=(0, 8))

        # 表頭
        header_frame = ctk.CTkFrame(left_card, fg_color=Colors.BG_TERTIARY, corner_radius=6, height=32)
        header_frame.pack(fill="x", padx=16, pady=(0, 4))
        header_frame.pack_propagate(False)

        # 完整欄位: 交易對 | 價格 | 多 | 空 | 浮盈 | 狀態 | TP/GS
        headers = [("交易對", 80), ("價格", 65), ("多", 45), ("空", 45), ("浮盈", 60), ("狀態", 60), ("TP/GS", 70)]
        for text, width in headers:
            ctk.CTkLabel(
                header_frame, text=text, width=width,
                font=ctk.CTkFont(size=10), text_color=Colors.TEXT_MUTED
            ).pack(side="left", padx=2, pady=6)

        # 可滾動的交易對列表
        self.symbols_scroll = ctk.CTkScrollableFrame(
            left_card, fg_color="transparent",
            scrollbar_button_color=Colors.BG_TERTIARY,
            scrollbar_button_hover_color=Colors.BORDER
        )
        self.symbols_scroll.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # 交易對行存儲
        self.symbol_rows: Dict[str, Dict] = {}

        # 載入初始交易對
        self._load_symbol_rows()

        # 右側：日誌 + 成交記錄
        right_card = ctk.CTkFrame(bottom_frame, fg_color=Colors.BG_SECONDARY, corner_radius=12, width=360)
        right_card.pack(side="right", fill="y")
        right_card.pack_propagate(False)

        # 標籤頁按鈕
        tab_frame = ctk.CTkFrame(right_card, fg_color="transparent")
        tab_frame.pack(fill="x", padx=16, pady=(12, 8))

        self._log_tab_active = True

        def switch_to_log():
            self._log_tab_active = True
            self.log_text.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            self.trades_frame.pack_forget()
            log_tab_btn.configure(fg_color=Colors.BG_TERTIARY)
            trades_tab_btn.configure(fg_color="transparent")

        def switch_to_trades():
            self._log_tab_active = False
            self.log_text.pack_forget()
            self.trades_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            log_tab_btn.configure(fg_color="transparent")
            trades_tab_btn.configure(fg_color=Colors.BG_TERTIARY)

        log_tab_btn = ctk.CTkButton(
            tab_frame, text="日誌", width=60, height=28,
            font=ctk.CTkFont(size=11), fg_color=Colors.BG_TERTIARY,
            hover_color=Colors.BORDER, corner_radius=6,
            command=switch_to_log
        )
        log_tab_btn.pack(side="left", padx=(0, 4))

        trades_tab_btn = ctk.CTkButton(
            tab_frame, text="成交", width=60, height=28,
            font=ctk.CTkFont(size=11), fg_color="transparent",
            hover_color=Colors.BORDER, corner_radius=6,
            command=switch_to_trades
        )
        trades_tab_btn.pack(side="left")

        # 日誌區
        self.log_text = ctk.CTkTextbox(
            right_card,
            fg_color=Colors.BG_TERTIARY,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(family="Menlo", size=11),
            corner_radius=8
        )
        self.log_text.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.log_text.insert("end", "[系統] 等待交易啟動...\n")

        # 成交記錄區
        self.trades_frame = ctk.CTkScrollableFrame(
            right_card,
            fg_color=Colors.BG_TERTIARY,
            corner_radius=8,
            scrollbar_button_color=Colors.BG_TERTIARY,
            scrollbar_button_hover_color=Colors.BORDER
        )
        # 成交記錄表頭
        trades_header = ctk.CTkFrame(self.trades_frame, fg_color="transparent", height=24)
        trades_header.pack(fill="x", pady=(0, 4))
        trades_header.pack_propagate(False)
        for text, width in [("時間", 60), ("交易對", 55), ("方向", 35), ("價格", 55), ("盈虧", 50)]:
            ctk.CTkLabel(trades_header, text=text, width=width, font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).pack(side="left", padx=1)

        # 成交記錄列表容器
        self.trades_list_frame = ctk.CTkFrame(self.trades_frame, fg_color="transparent")
        self.trades_list_frame.pack(fill="both", expand=True)
        self.trade_records: List[Dict] = []

    def _toggle_trading(self):
        """切換交易狀態"""
        if self.app.is_trading:
            # 停止交易 - 需要確認
            ConfirmDialog(
                self,
                title="停止交易",
                message="確定要停止交易？",
                details="停止後所有掛單將被取消，但現有持倉不會被平倉。",
                confirm_text="停止",
                danger=True,
                on_confirm=self._stop_trading
            )
        else:
            # 開始交易
            self._start_trading()

    def _start_trading(self):
        """啟動交易"""
        # 使用 app 的 engine
        engine = self.app.engine

        # 檢查連接狀態
        if not engine.is_connected:
            self.add_log("[錯誤] 交易所未連接")
            return

        if not engine.is_verified:
            self.add_log("[錯誤] 授權未驗證")
            return

        # 檢查是否有啟用的交易對
        active_symbols = engine.get_active_symbols()
        if not active_symbols:
            self.add_log("[錯誤] 沒有啟用的交易對")
            return

        self.add_log("啟動 MAX 網格交易...")
        self.add_log(f"啟用的交易對: {', '.join(active_symbols)}")

        # 設置引擎回調
        engine.set_callbacks(
            on_log=lambda msg: self.after(0, lambda m=msg: self.add_log(m)),
            on_position=lambda pos: self.after(0, lambda p=pos: self._update_positions(p)),
            on_symbol_status=lambda st: self.after(0, lambda s=st: self._update_symbol_rows(s)),
            on_account=lambda acc: self.after(0, lambda a=acc: self._update_accounts(a)),
            on_stats=lambda stats: self.after(0, lambda s=stats: self._update_stats(s)),
            on_learning=lambda ls: self.after(0, lambda l=ls: self._update_learning(l)),
            on_status=lambda st, active: self.after(0, lambda s=st, a=active: self._update_status(s, a)),
            on_indicators=lambda ind: self.after(0, lambda i=ind: self._update_indicators(i))
        )

        # 啟動交易（在背景線程中）
        import asyncio
        import threading

        def start():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(engine.start_trading())
                self.after(0, lambda: self._on_trading_started(success))
            except Exception as ex:
                error_msg = f"[錯誤] 啟動失敗: {ex}"
                self.after(0, lambda err=error_msg: self.add_log(err))
            finally:
                loop.close()

        threading.Thread(target=start, daemon=True).start()

    def _on_trading_started(self, success: bool):
        """交易啟動結果回調"""
        if success:
            self.app.is_trading = True
            self.start_button.configure(
                text="■  停止交易",
                fg_color=Colors.BG_TERTIARY,
                text_color=Colors.TEXT_PRIMARY,
                hover_color=Colors.BORDER
            )
            self._start_ui_updates()
        else:
            self.add_log("[錯誤] 交易啟動失敗")

    def _stop_trading(self):
        """停止交易"""
        self.add_log("停止交易...")

        # 停止 UI 更新
        if self._update_timer:
            self.after_cancel(self._update_timer)
            self._update_timer = None

        # 使用 engine 停止交易（同步版本）
        engine = self.app.engine
        engine.stop_trading_sync()

        self.app.is_trading = False

        # 更新 UI
        self.start_button.configure(
            text="▶  開始交易",
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK
        )
        self.add_log("交易已停止")

    def _update_positions(self, positions: dict):
        """更新持倉顯示"""
        # 由引擎回調調用，已整合到 symbol_rows
        pass

    def _update_symbol_rows(self, symbol_status: dict):
        """更新交易對狀態顯示"""
        for symbol, status in symbol_status.items():
            # 找到對應的 row
            row = self.symbol_rows.get(symbol)
            if not row:
                # 嘗試部分匹配
                for key, r in self.symbol_rows.items():
                    if key in symbol or symbol in key:
                        row = r
                        break
            if not row:
                continue

            # 更新價格
            if status.price > 0:
                row['price'].configure(text=f"{status.price:.4f}")

            # 更新多頭持倉
            if status.long_qty > 0:
                row['long'].configure(text=f"{status.long_qty:.3f}")
            else:
                row['long'].configure(text="0")

            # 更新空頭持倉
            if status.short_qty > 0:
                row['short'].configure(text=f"{status.short_qty:.3f}")
            else:
                row['short'].configure(text="0")

            # 更新浮盈
            total_pnl = status.long_pnl + status.short_pnl
            pnl_color = Colors.GREEN if total_pnl >= 0 else Colors.RED
            pnl_prefix = "+" if total_pnl >= 0 else ""
            row['pnl'].configure(text=f"{pnl_prefix}{total_pnl:.2f}", text_color=pnl_color)

            # 更新狀態 (裝死/加倍/正常)
            status_parts = []
            if status.long_dead:
                status_parts.append("多裝死")
            if status.short_dead:
                status_parts.append("空裝死")
            if status.long_2x:
                status_parts.append("多2x")
            if status.short_2x:
                status_parts.append("空2x")

            if status_parts:
                status_text = "/".join(status_parts)
                status_color = Colors.YELLOW  # 黃色警示
            else:
                status_text = "正常"
                status_color = Colors.GREEN

            row['status'].configure(text=status_text, text_color=status_color)

            # 更新 TP/GS (如果有動態間距則顯示動態值)
            if status.dynamic_spacing:
                tpgs_text = f"{status.take_profit_spacing*100:.1f}/{status.dynamic_spacing*100:.1f}*"
            else:
                tpgs_text = f"{status.take_profit_spacing*100:.1f}/{status.grid_spacing*100:.1f}"
            row['tpgs'].configure(text=tpgs_text)

    def _update_accounts(self, accounts: dict):
        """更新帳戶顯示"""
        for currency, info in accounts.items():
            if currency == "USDC":
                self.usdc_equity.configure(text=f"{info.equity:.2f}")
                self.usdc_available.configure(text=f"{info.available:.2f}")
                margin_ratio = info.margin_ratio
                margin_color = Colors.GREEN if margin_ratio < 0.3 else (Colors.YELLOW if margin_ratio < 0.6 else Colors.RED)
                self.usdc_margin.configure(text=f"{margin_ratio*100:.1f}%", text_color=margin_color)
                pnl = info.unrealized_pnl
                self.usdc_pnl.configure(
                    text=f"{'+' if pnl >= 0 else ''}{pnl:.2f}",
                    text_color=Colors.GREEN if pnl >= 0 else Colors.RED
                )
            elif currency == "USDT":
                self.usdt_equity.configure(text=f"{info.equity:.2f}")
                self.usdt_available.configure(text=f"{info.available:.2f}")
                margin_ratio = info.margin_ratio
                margin_color = Colors.GREEN if margin_ratio < 0.3 else (Colors.YELLOW if margin_ratio < 0.6 else Colors.RED)
                self.usdt_margin.configure(text=f"{margin_ratio*100:.1f}%", text_color=margin_color)
                pnl = info.unrealized_pnl
                self.usdt_pnl.configure(
                    text=f"{'+' if pnl >= 0 else ''}{pnl:.2f}",
                    text_color=Colors.GREEN if pnl >= 0 else Colors.RED
                )

    def _update_stats(self, stats: dict):
        """更新統計顯示"""
        if "runtime" in stats:
            self.runtime_label.configure(text=f"運行: {stats['runtime']}")
        if "today_trades" in stats:
            self.trades_label.configure(text=f"交易: {stats['today_trades']}")
        if "unrealized_pnl" in stats:
            pnl = stats["unrealized_pnl"]
            self.total_pnl_label.configure(
                text=f"浮盈: {'+' if pnl >= 0 else ''}{pnl:.2f}",
                text_color=Colors.GREEN if pnl >= 0 else Colors.RED
            )

    def _update_learning(self, learning_status):
        """更新學習模組顯示"""
        if learning_status.bandit_enabled:
            self.bandit_arm_label.configure(text=str(learning_status.current_arm))
        if learning_status.ofi_enabled:
            self.ofi_label.configure(text=f"{learning_status.ofi_value:.2f}")
        if learning_status.volume_enabled:
            self.volume_ratio_label.configure(text=f"{learning_status.volume_ratio:.1f}x")
        if learning_status.spread_enabled:
            self.spread_ratio_label.configure(text=f"{learning_status.spread_ratio:.1f}x")

    def _update_indicators(self, indicators):
        """更新指標顯示（來自 IndicatorData 回調）"""
        # Funding Rate
        rate_pct = indicators.funding_rate * 100
        rate_color = Colors.GREEN if indicators.funding_rate > 0 else (Colors.RED if indicators.funding_rate < 0 else Colors.TEXT_SECONDARY)
        self.funding_rate_label.configure(text=f"{rate_pct:+.4f}%", text_color=rate_color)

        # Funding 偏向
        bias = indicators.funding_bias
        if bias == "偏多":
            self.funding_bias_label.configure(text="偏多", text_color=Colors.GREEN)
        elif bias == "偏空":
            self.funding_bias_label.configure(text="偏空", text_color=Colors.RED)
        else:
            self.funding_bias_label.configure(text="中性", text_color=Colors.TEXT_SECONDARY)

        # OFI
        ofi = indicators.ofi_value
        ofi_color = Colors.GREEN if ofi > 0.3 else (Colors.RED if ofi < -0.3 else Colors.TEXT_SECONDARY)
        self.ofi_label.configure(text=f"{ofi:+.2f}", text_color=ofi_color)

        # Volume Ratio
        vol_ratio = indicators.volume_ratio
        vol_color = Colors.YELLOW if vol_ratio > 2.0 else Colors.TEXT_SECONDARY
        self.volume_ratio_label.configure(text=f"{vol_ratio:.1f}x", text_color=vol_color)

        # Spread Ratio
        spread_ratio = indicators.spread_ratio
        spread_color = Colors.YELLOW if spread_ratio > 1.5 else Colors.TEXT_SECONDARY
        self.spread_ratio_label.configure(text=f"{spread_ratio:.1f}x", text_color=spread_color)

        # Bandit Arm
        self.bandit_arm_label.configure(text=f"#{indicators.bandit_arm}")

        # Drawdown
        drawdown = indicators.drawdown
        dd_color = Colors.GREEN if drawdown < 10 else (Colors.YELLOW if drawdown < 30 else Colors.RED)
        self.drawdown_label.configure(text=f"{drawdown:.1f}%", text_color=dd_color)

        # Total Positions
        self.total_position_label.configure(text=f"{indicators.total_positions}")

    def _update_status(self, status: str, is_active: bool):
        """更新連接狀態"""
        self.app.set_connected(is_active)

    def refresh_account_display(self):
        """從引擎刷新帳戶顯示（連接後但未交易時使用）"""
        engine = self.app.engine
        if not engine or not engine.is_connected:
            return

        accounts = engine.accounts
        if not accounts:
            return

        for currency, info in accounts.items():
            if currency == "USDC":
                self.usdc_equity.configure(text=f"{info.equity:.2f}")
                self.usdc_available.configure(text=f"{info.available:.2f}")
                margin_ratio = info.margin_ratio
                margin_color = Colors.GREEN if margin_ratio < 0.3 else (Colors.YELLOW if margin_ratio < 0.6 else Colors.RED)
                self.usdc_margin.configure(text=f"{margin_ratio*100:.1f}%", text_color=margin_color)
                pnl = info.unrealized_pnl
                self.usdc_pnl.configure(
                    text=f"{'+' if pnl >= 0 else ''}{pnl:.2f}",
                    text_color=Colors.GREEN if pnl >= 0 else Colors.RED
                )
            elif currency == "USDT":
                self.usdt_equity.configure(text=f"{info.equity:.2f}")
                self.usdt_available.configure(text=f"{info.available:.2f}")
                margin_ratio = info.margin_ratio
                margin_color = Colors.GREEN if margin_ratio < 0.3 else (Colors.YELLOW if margin_ratio < 0.6 else Colors.RED)
                self.usdt_margin.configure(text=f"{margin_ratio*100:.1f}%", text_color=margin_color)
                pnl = info.unrealized_pnl
                self.usdt_pnl.configure(
                    text=f"{'+' if pnl >= 0 else ''}{pnl:.2f}",
                    text_color=Colors.GREEN if pnl >= 0 else Colors.RED
                )

    def _start_ui_updates(self):
        """啟動 UI 更新定時器（交易模式）"""
        self._start_time = datetime.now()
        self._is_trading_mode = True
        if not hasattr(self, '_ui_timer_running') or not self._ui_timer_running:
            self._ui_timer_running = True
            self._update_ui()

    def start_connection_timer(self):
        """啟動連接計時器（連接後立即調用）"""
        self._connect_time = datetime.now()
        self._is_trading_mode = False
        if not hasattr(self, '_ui_timer_running') or not self._ui_timer_running:
            self._ui_timer_running = True
            self._update_ui()

    def _update_ui(self):
        """定期更新 UI - 支援連接模式和交易模式"""
        engine = self.app.engine
        is_connected = engine and engine.is_connected if engine else False

        # 如果未連接，停止更新
        if not is_connected:
            self._ui_timer_running = False
            return

        is_trading = getattr(self, '_is_trading_mode', False) and self.app.is_trading

        # 更新運行/連接時間
        if is_trading and hasattr(self, '_start_time'):
            runtime = datetime.now() - self._start_time
            hours, remainder = divmod(int(runtime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.runtime_label.configure(text=f"交易: {hours:02d}:{minutes:02d}:{seconds:02d}")
        elif hasattr(self, '_connect_time'):
            runtime = datetime.now() - self._connect_time
            hours, remainder = divmod(int(runtime.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.runtime_label.configure(text=f"連接: {hours:02d}:{minutes:02d}:{seconds:02d}")

        # 從引擎獲取 bot 引用
        bot = engine.bot if engine else None

        # === 交易模式更新（需要 bot） ===
        # 注意：帳戶餘額/浮盈由 WebSocket _update_accounts 回調處理，避免重複更新導致閃爍
        if is_trading and bot:
            try:
                # 更新各交易對持倉和價格
                if hasattr(bot, 'state') and hasattr(bot.state, 'symbols'):
                    for symbol, sym_state in bot.state.symbols.items():
                        # 找到對應的 row (可能名稱不同)
                        row = None
                        for key, r in self.symbol_rows.items():
                            if key in symbol or symbol in key:
                                row = r
                                break
                        if not row:
                            continue

                        # 更新價格
                        if hasattr(sym_state, 'latest_price') and sym_state.latest_price:
                            row['price'].configure(text=f"{sym_state.latest_price:.4f}")
                        # 更新多頭數量
                        if hasattr(sym_state, 'long_position'):
                            row['long'].configure(text=f"{sym_state.long_position:.0f}")
                        # 更新空頭數量
                        if hasattr(sym_state, 'short_position'):
                            row['short'].configure(text=f"{sym_state.short_position:.0f}")
                        # 更新浮盈
                        if hasattr(sym_state, 'unrealized_pnl'):
                            pnl = sym_state.unrealized_pnl
                            row['pnl'].configure(
                                text=f"{'+' if pnl >= 0 else ''}{pnl:.1f}",
                                text_color=Colors.GREEN if pnl >= 0 else Colors.RED
                            )

                        # 更新狀態 (裝死/加倍/正常)
                        if 'config' in row:
                            cfg = row['config']
                            long_pos = getattr(sym_state, 'long_position', 0)
                            short_pos = getattr(sym_state, 'short_position', 0)

                            status_parts = []
                            if long_pos > cfg.position_threshold:
                                status_parts.append("多裝死")
                                status_color = Colors.RED
                            elif long_pos > cfg.position_limit:
                                status_parts.append("多×2")
                                status_color = Colors.YELLOW
                            if short_pos > cfg.position_threshold:
                                status_parts.append("空裝死")
                                status_color = Colors.RED
                            elif short_pos > cfg.position_limit:
                                status_parts.append("空×2")
                                status_color = Colors.YELLOW

                            if not status_parts:
                                # 計算持倉百分比
                                if cfg.position_limit > 0:
                                    pct = max(long_pos, short_pos) / cfg.position_limit * 100
                                    if pct > 50:
                                        row['status'].configure(text=f"{pct:.0f}%", text_color=Colors.TEXT_MUTED)
                                    else:
                                        row['status'].configure(text="正常", text_color=Colors.GREEN)
                                else:
                                    row['status'].configure(text="正常", text_color=Colors.GREEN)
                            else:
                                row['status'].configure(text=" ".join(status_parts), text_color=status_color)

                        # 更新動態 TP/GS
                        if hasattr(sym_state, 'dynamic_take_profit') and sym_state.dynamic_take_profit > 0:
                            dtp = sym_state.dynamic_take_profit * 100
                            dgs = getattr(sym_state, 'dynamic_grid_spacing', sym_state.dynamic_take_profit) * 100
                            row['tpgs'].configure(text=f"{dtp:.2f}/{dgs:.2f}", text_color=Colors.GREEN)

                # 從 bot 獲取交易次數
                if hasattr(bot, 'state') and hasattr(bot.state, 'total_trades'):
                    self.trades_label.configure(text=f"交易: {bot.state.total_trades}")

                # === 更新 Bandit 狀態 ===
                if hasattr(bot, 'bandit_optimizer') and bot.bandit_optimizer:
                    bandit = bot.bandit_optimizer
                    # 當前 Arm
                    arm_idx = getattr(bandit, 'current_arm_idx', 0)
                    self.bandit_arm_label.configure(text=f"#{arm_idx}")
                    # 市場狀態
                    context = getattr(bandit, 'current_context', 'RANGING')
                    context_map = {'RANGING': '震盪', 'TRENDING_UP': '上漲', 'TRENDING_DOWN': '下跌', 'HIGH_VOLATILITY': '高波動'}
                    self.bandit_context_label.configure(text=context_map.get(str(context), str(context)))

                # === 更新領先指標 ===
                if hasattr(bot, 'leading_indicator_mgr') and bot.leading_indicator_mgr:
                    li_mgr = bot.leading_indicator_mgr
                    # 取第一個交易對的數據
                    first_symbol = next(iter(self.symbol_rows.keys()), None)
                    if first_symbol:
                        # OFI
                        ofi = li_mgr.current_ofi.get(first_symbol, 0)
                        ofi_color = Colors.GREEN if ofi > 0.3 else (Colors.RED if ofi < -0.3 else Colors.TEXT_SECONDARY)
                        self.ofi_label.configure(text=f"{ofi:+.2f}", text_color=ofi_color)
                        # Volume Ratio
                        vol_ratio = li_mgr.current_volume_ratio.get(first_symbol, 1.0)
                        vol_color = Colors.YELLOW if vol_ratio > 2.0 else Colors.TEXT_SECONDARY
                        self.volume_ratio_label.configure(text=f"{vol_ratio:.1f}x", text_color=vol_color)
                        # Spread Ratio
                        spread_ratio = li_mgr.current_spread_ratio.get(first_symbol, 1.0)
                        spread_color = Colors.YELLOW if spread_ratio > 1.5 else Colors.TEXT_SECONDARY
                        self.spread_ratio_label.configure(text=f"{spread_ratio:.1f}x", text_color=spread_color)

                # === 更新 Funding Rate ===
                if hasattr(bot, 'funding_rate_mgr') and bot.funding_rate_mgr:
                    fr_mgr = bot.funding_rate_mgr
                    first_symbol = next(iter(self.symbol_rows.keys()), None)
                    if first_symbol:
                        rate = fr_mgr.current_rates.get(first_symbol, 0) if hasattr(fr_mgr, 'current_rates') else 0
                        rate_pct = rate * 100
                        rate_color = Colors.GREEN if rate > 0 else (Colors.RED if rate < 0 else Colors.TEXT_SECONDARY)
                        self.funding_rate_label.configure(text=f"{rate_pct:+.4f}%", text_color=rate_color)
                        # Funding 偏向
                        if rate > 0.0005:
                            self.funding_bias_label.configure(text="偏空", text_color=Colors.RED)
                        elif rate < -0.0005:
                            self.funding_bias_label.configure(text="偏多", text_color=Colors.GREEN)
                        else:
                            self.funding_bias_label.configure(text="中性", text_color=Colors.TEXT_SECONDARY)

                # === 更新風控狀態 ===
                # 計算回撤 (使用 peak_equity 和 total_equity)
                if hasattr(bot, 'state'):
                    state = bot.state
                    initial = getattr(state, 'initial_equity', 0) or 0
                    current = getattr(state, 'total_equity', 0) or 0
                    peak = getattr(state, 'peak_equity', initial) or initial
                    if peak > 0:
                        # 回撤 = (峰值 - 當前) / 峰值
                        drawdown = (peak - current) / peak * 100 if current < peak else 0
                        dd_color = Colors.GREEN if drawdown < 10 else (Colors.YELLOW if drawdown < 30 else Colors.RED)
                        self.drawdown_label.configure(text=f"{drawdown:.1f}%", text_color=dd_color)
                # 總持倉數
                total_pos = 0
                for row in self.symbol_rows.values():
                    long_text = row['long'].cget('text')
                    short_text = row['short'].cget('text')
                    try:
                        total_pos += float(long_text) + float(short_text)
                    except ValueError:
                        pass
                self.total_position_label.configure(text=f"{total_pos:.0f}")

            except Exception:
                pass  # 忽略更新錯誤

        # === 連接模式更新（無 bot，顯示配置狀態） ===
        elif is_connected and not is_trading:
            try:
                # 從 engine.indicators 獲取基本指標（通過回調已更新）
                if engine and hasattr(engine, 'indicators'):
                    ind = engine.indicators
                    # 顯示 Bandit 配置狀態
                    if engine.config and engine.config.bandit.enabled:
                        self.bandit_arm_label.configure(text="#-", text_color=Colors.TEXT_MUTED)
                        self.bandit_context_label.configure(text="待交易", text_color=Colors.TEXT_MUTED)
                    else:
                        self.bandit_arm_label.configure(text="停用", text_color=Colors.TEXT_MUTED)
                        self.bandit_context_label.configure(text="-", text_color=Colors.TEXT_MUTED)

                    # 顯示領先指標配置狀態
                    if engine.config and engine.config.leading_indicator.enabled:
                        self.ofi_label.configure(text="0.00", text_color=Colors.TEXT_MUTED)
                        self.volume_ratio_label.configure(text="1.0x", text_color=Colors.TEXT_MUTED)
                        self.spread_ratio_label.configure(text="1.0x", text_color=Colors.TEXT_MUTED)
                    else:
                        self.ofi_label.configure(text="-", text_color=Colors.TEXT_MUTED)
                        self.volume_ratio_label.configure(text="-", text_color=Colors.TEXT_MUTED)
                        self.spread_ratio_label.configure(text="-", text_color=Colors.TEXT_MUTED)

                    # 風控狀態（顯示初始值）
                    self.drawdown_label.configure(text="0.0%", text_color=Colors.GREEN)

                # 計算總持倉（從 symbol_rows）
                total_pos = 0
                for row in self.symbol_rows.values():
                    long_text = row['long'].cget('text')
                    short_text = row['short'].cget('text')
                    try:
                        total_pos += float(long_text) + float(short_text)
                    except ValueError:
                        pass
                self.total_position_label.configure(text=f"{total_pos:.0f}")

            except Exception:
                pass  # 忽略更新錯誤

        # 設定下次更新
        self._update_timer = self.after(1000, self._update_ui)

    def _load_symbol_rows(self):
        """載入交易對監控行"""
        # 清空現有行
        for widget in self.symbols_scroll.winfo_children():
            widget.destroy()
        self.symbol_rows.clear()

        # 載入配置
        try:
            import sys
            from pathlib import Path
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from as_terminal_max_bitget import GlobalConfig
            config = GlobalConfig.load()
        except Exception:
            return

        # 為每個啟用的交易對創建行
        for symbol_name, symbol_cfg in config.symbols.items():
            if not symbol_cfg.enabled:
                continue

            row_frame = ctk.CTkFrame(self.symbols_scroll, fg_color=Colors.BG_TERTIARY, corner_radius=6, height=32)
            row_frame.pack(fill="x", pady=2)
            row_frame.pack_propagate(False)

            # 交易對名稱
            name_label = ctk.CTkLabel(
                row_frame, text=symbol_name[:8], width=80,
                font=ctk.CTkFont(size=10, weight="bold"), text_color=Colors.TEXT_PRIMARY
            )
            name_label.pack(side="left", padx=2, pady=6)

            # 價格
            price_label = ctk.CTkLabel(
                row_frame, text="--", width=65,
                font=ctk.CTkFont(size=10), text_color=Colors.TEXT_SECONDARY
            )
            price_label.pack(side="left", padx=2)

            # 多頭數量
            long_label = ctk.CTkLabel(
                row_frame, text="0", width=45,
                font=ctk.CTkFont(size=10), text_color=Colors.GREEN
            )
            long_label.pack(side="left", padx=2)

            # 空頭數量
            short_label = ctk.CTkLabel(
                row_frame, text="0", width=45,
                font=ctk.CTkFont(size=10), text_color=Colors.RED
            )
            short_label.pack(side="left", padx=2)

            # 浮盈
            pnl_label = ctk.CTkLabel(
                row_frame, text="+0.00", width=60,
                font=ctk.CTkFont(size=10), text_color=Colors.TEXT_MUTED
            )
            pnl_label.pack(side="left", padx=2)

            # 狀態 (裝死/加倍/正常)
            status_label = ctk.CTkLabel(
                row_frame, text="正常", width=60,
                font=ctk.CTkFont(size=9), text_color=Colors.GREEN
            )
            status_label.pack(side="left", padx=2)

            # TP/GS
            tpgs_text = f"{symbol_cfg.take_profit_spacing*100:.1f}/{symbol_cfg.grid_spacing*100:.1f}"
            tpgs_label = ctk.CTkLabel(
                row_frame, text=tpgs_text, width=70,
                font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED
            )
            tpgs_label.pack(side="left", padx=2)

            # 儲存引用和配置
            self.symbol_rows[symbol_name] = {
                'frame': row_frame,
                'price': price_label,
                'long': long_label,
                'short': short_label,
                'pnl': pnl_label,
                'status': status_label,
                'tpgs': tpgs_label,
                'config': symbol_cfg  # 保存配置以計算狀態
            }

    def add_log(self, message: str):
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.log_text.insert("end", f"{timestamp} {message}\n")
        self.log_text.see("end")

    def add_trade(self, symbol: str, side: str, price: float, pnl: float = 0):
        """添加成交記錄"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        # 創建記錄行
        row = ctk.CTkFrame(self.trades_list_frame, fg_color="transparent", height=22)
        row.pack(fill="x", pady=1)
        row.pack_propagate(False)

        # 時間
        ctk.CTkLabel(row, text=timestamp, width=60, font=ctk.CTkFont(size=9), text_color=Colors.TEXT_MUTED).pack(side="left", padx=1)
        # 交易對
        ctk.CTkLabel(row, text=symbol[:6], width=55, font=ctk.CTkFont(size=9), text_color=Colors.TEXT_SECONDARY).pack(side="left", padx=1)
        # 方向
        side_color = Colors.GREEN if side.lower() in ['buy', 'long', '多'] else Colors.RED
        side_text = "多" if side.lower() in ['buy', 'long', '多'] else "空"
        ctk.CTkLabel(row, text=side_text, width=35, font=ctk.CTkFont(size=9), text_color=side_color).pack(side="left", padx=1)
        # 價格
        ctk.CTkLabel(row, text=f"{price:.4f}", width=55, font=ctk.CTkFont(size=9), text_color=Colors.TEXT_SECONDARY).pack(side="left", padx=1)
        # 盈虧
        pnl_color = Colors.GREEN if pnl >= 0 else Colors.RED
        pnl_text = f"{'+' if pnl >= 0 else ''}{pnl:.2f}"
        ctk.CTkLabel(row, text=pnl_text, width=50, font=ctk.CTkFont(size=9), text_color=pnl_color).pack(side="left", padx=1)

        # 保持最多 50 條記錄
        self.trade_records.append(row)
        if len(self.trade_records) > 50:
            old_row = self.trade_records.pop(0)
            old_row.destroy()

    def _close_all_positions(self):
        """一鍵平倉"""
        engine = self.app.engine

        if not engine.is_connected:
            self.add_log("[錯誤] 交易所未連接")
            return

        self.add_log("執行一鍵平倉...")

        def do_close():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(engine.close_all_positions())
                self.after(0, lambda: self.add_log("一鍵平倉完成"))
            except Exception as ex:
                error_msg = f"[錯誤] 平倉失敗: {ex}"
                self.after(0, lambda err=error_msg: self.add_log(err))
            finally:
                loop.close()

        import threading
        threading.Thread(target=do_close, daemon=True).start()

    async def _close_positions_async(self):
        """異步執行平倉"""
        import ccxt.async_support as ccxt

        exchange = None
        try:
            # Bitget 版本
            exchange = ccxt.bitget({
                'apiKey': self.app.api_key,
                'secret': self.app.api_secret,
                'password': getattr(self.app, 'passphrase', ''),  # Bitget 需要 passphrase
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}  # Bitget 永續合約
            })

            positions = await exchange.fetch_positions()

            closed_count = 0
            for pos in positions:
                if pos['contracts'] > 0:
                    symbol = pos['symbol']
                    side = "sell" if pos['side'] == 'long' else "buy"
                    quantity = pos['contracts']

                    await exchange.create_market_order(
                        symbol=symbol,
                        side=side,
                        amount=quantity,
                        params={'reduceOnly': True}
                    )
                    closed_count += 1
                    self.after(0, lambda s=symbol, q=quantity: self.add_log(f"平倉: {s} {q}"))

            self.after(0, lambda c=closed_count: self.add_log(f"一鍵平倉完成，共平 {c} 個持倉"))

        except Exception as err:
            error_msg = str(err)
            self.after(0, lambda msg=error_msg: self.add_log(f"[錯誤] 平倉失敗: {msg}"))
        finally:
            if exchange:
                await exchange.close()

    def _toggle_pause(self):
        """切換暫停補倉"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_button.configure(text="恢復補倉", fg_color=Colors.STATUS_ON)
            self.add_log("已暫停補倉")
        else:
            self.pause_button.configure(text="暫停補倉", fg_color=Colors.BG_TERTIARY)
            self.add_log("已恢復補倉")
