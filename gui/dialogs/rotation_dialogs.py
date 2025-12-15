"""
輪動相關對話框

包含:
- RotationExecuteConfirmDialog: 輪動執行最終確認對話框
- RotationConfirmDialog: 輪動確認對話框
- RotationHistoryDialog: 輪動歷史對話框
"""

from typing import Dict

import customtkinter as ctk
from ..styles import Colors


class RotationExecuteConfirmDialog(ctk.CTkToplevel):
    """
    輪動執行最終確認對話框

    這是高風險操作（會平倉並修改配置），需要用戶明確確認。
    """

    def __init__(self, parent, signal, on_execute=None):
        super().__init__(parent)
        self.signal = signal
        self.on_execute = on_execute

        self.title("確認執行輪動")
        self.geometry("450x320")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PRIMARY)

        # 模態設定
        self.transient(parent)
        self.grab_set()

        # 置中
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 450) // 2
        y = (self.winfo_screenheight() - 320) // 2
        self.geometry(f"450x320+{x}+{y}")

        self._create_ui()

    def _create_ui(self):
        """建立 UI"""
        # 警告圖示 + 標題
        ctk.CTkLabel(
            self,
            text="⚠️ 確認執行輪動",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(28, 16))

        # 操作說明
        info_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        info_frame.pack(fill="x", padx=28, pady=(0, 16))

        ctk.CTkLabel(
            info_frame,
            text=f"{self.signal.from_symbol}  →  {self.signal.to_symbol}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(16, 8))

        ctk.CTkLabel(
            info_frame,
            text="此操作將執行以下動作：",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_SECONDARY
        ).pack(pady=(0, 8))

        actions = [
            f"1. 平倉 {self.signal.from_symbol} 所有持倉",
            f"2. 取消 {self.signal.from_symbol} 所有掛單",
            f"3. 停用 {self.signal.from_symbol}",
            f"4. 啟用 {self.signal.to_symbol}",
        ]

        for action in actions:
            ctk.CTkLabel(
                info_frame,
                text=action,
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED,
                anchor="w"
            ).pack(fill="x", padx=20, pady=2)

        ctk.CTkLabel(
            info_frame,
            text="",
            height=8
        ).pack()  # 間距

        # 警告
        ctk.CTkLabel(
            self,
            text="此操作不可撤銷，請確認後再執行",
            font=ctk.CTkFont(size=11),
            text_color="#ff6b6b"
        ).pack(pady=(0, 16))

        # 按鈕
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=28, pady=(0, 24))

        ctk.CTkButton(
            btn_frame,
            text="取消",
            width=100,
            fg_color=Colors.BG_TERTIARY,
            hover_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
            command=self.destroy
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="確認執行",
            width=120,
            fg_color="#c0392b",
            hover_color="#e74c3c",
            text_color="#ffffff",
            command=self._on_execute
        ).pack(side="right")

    def _on_execute(self):
        """執行輪動"""
        self.destroy()
        if self.on_execute:
            self.on_execute()


class RotationConfirmDialog(ctk.CTkToplevel):
    """
    輪動確認對話框

    當系統偵測到更優幣種時顯示，讓用戶確認是否執行輪動。

    Story 4.2: 輪動確認對話框
    """

    def __init__(
        self,
        parent,
        signal,  # RotationSignal
        on_confirm=None,
        on_cancel=None
    ):
        super().__init__(parent)
        self.signal = signal
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel

        self.title("輪動建議")
        self.geometry("500x580")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PRIMARY)

        # 模態設定
        self.transient(parent)
        self.grab_set()

        # 視窗關閉處理
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda e: self._on_cancel())

        # 置中顯示
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 500) // 2
        y = (screen_height - 580) // 2
        self.geometry(f"500x580+{x}+{y}")

        self._create_ui()

    def _create_ui(self):
        """建立 UI"""
        # 標題區
        ctk.CTkLabel(
            self,
            text="輪動建議",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(30, 8))

        ctk.CTkLabel(
            self,
            text="系統偵測到更優質的交易對",
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_SECONDARY
        ).pack(pady=(0, 24))

        # 當前幣種卡片
        from_card = ctk.CTkFrame(self, fg_color=Colors.BG_SECONDARY, corner_radius=10)
        from_card.pack(fill="x", padx=30, pady=(0, 8))

        ctk.CTkLabel(
            from_card,
            text="當前幣種",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED
        ).pack(anchor="w", padx=16, pady=(12, 4))

        from_row = ctk.CTkFrame(from_card, fg_color="transparent")
        from_row.pack(fill="x", padx=16, pady=(0, 12))

        # 原幣種名稱和評分
        from_symbol = self.signal.from_symbol.split('/')[0] if '/' in self.signal.from_symbol else self.signal.from_symbol
        from_score = self.signal.from_score.final_score if self.signal.from_score else 0

        ctk.CTkLabel(
            from_row,
            text=from_symbol,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            from_row,
            text=f"評分: {from_score:.1f}",
            font=ctk.CTkFont(size=14),
            text_color=Colors.RED
        ).pack(side="right")

        # 原因說明 (如果有 from_score 詳細資料)
        if self.signal.from_score:
            from_detail = f"H={self.signal.from_score.hurst_exponent:.2f} | ATR={self.signal.from_score.atr_pct*100:.1f}%"
            ctk.CTkLabel(
                from_card,
                text=from_detail,
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED
            ).pack(anchor="w", padx=16, pady=(0, 12))

        # 箭頭
        ctk.CTkLabel(
            self,
            text="▼",
            font=ctk.CTkFont(size=24),
            text_color=Colors.TEXT_MUTED
        ).pack(pady=8)

        # 建議幣種卡片
        to_card = ctk.CTkFrame(self, fg_color=Colors.FILL_SELECTED, corner_radius=10)  # 推薦項目背景（黑白風格）
        to_card.pack(fill="x", padx=30, pady=(0, 16))

        ctk.CTkLabel(
            to_card,
            text="建議幣種",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED
        ).pack(anchor="w", padx=16, pady=(12, 4))

        to_row = ctk.CTkFrame(to_card, fg_color="transparent")
        to_row.pack(fill="x", padx=16, pady=(0, 12))

        # 目標幣種名稱和評分
        to_symbol = self.signal.to_symbol.split('/')[0] if '/' in self.signal.to_symbol else self.signal.to_symbol
        to_score = self.signal.to_score.final_score if self.signal.to_score else 0

        ctk.CTkLabel(
            to_row,
            text=to_symbol,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=Colors.GREEN
        ).pack(side="left")

        ctk.CTkLabel(
            to_row,
            text=f"評分: {to_score:.1f}",
            font=ctk.CTkFont(size=14),
            text_color=Colors.GREEN
        ).pack(side="right")

        # 優勢說明
        if self.signal.to_score:
            to_detail = f"H={self.signal.to_score.hurst_exponent:.2f} | ATR={self.signal.to_score.atr_pct*100:.1f}%"
            ctk.CTkLabel(
                to_card,
                text=to_detail,
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_SECONDARY
            ).pack(anchor="w", padx=16, pady=(0, 12))

        # 評分差異
        diff_frame = ctk.CTkFrame(self, fg_color=Colors.BG_TERTIARY, corner_radius=8)
        diff_frame.pack(fill="x", padx=30, pady=(0, 16))

        ctk.CTkLabel(
            diff_frame,
            text=f"評分差異: +{self.signal.score_diff:.1f} 分",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=Colors.GREEN
        ).pack(pady=12)

        # 輪動原因
        reason_frame = ctk.CTkFrame(self, fg_color="transparent")
        reason_frame.pack(fill="x", padx=30, pady=(0, 16))

        ctk.CTkLabel(
            reason_frame,
            text="輪動原因:",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w")

        # 分行顯示原因
        reasons = self.signal.reason.split("；") if "；" in self.signal.reason else [self.signal.reason]
        for reason in reasons[:3]:  # 最多顯示 3 條
            ctk.CTkLabel(
                reason_frame,
                text=f"  • {reason}",
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED
            ).pack(anchor="w", pady=2)

        # 警告提示
        warning_frame = ctk.CTkFrame(self, fg_color=Colors.BG_TERTIARY, corner_radius=8)
        warning_frame.pack(fill="x", padx=30, pady=(0, 24))

        slippage_text = f"預估滑點: {self.signal.estimated_slippage*100:.2f}%"
        ctk.CTkLabel(
            warning_frame,
            text=f"輪動將平倉現有倉位 | {slippage_text}",
            font=ctk.CTkFont(size=11),
            text_color=Colors.YELLOW
        ).pack(pady=10)

        # 按鈕區
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=30, pady=(0, 30))

        # 取消按鈕
        ctk.CTkButton(
            button_frame,
            text="取消",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=Colors.BG_TERTIARY,
            text_color=Colors.TEXT_PRIMARY,
            hover_color=Colors.BORDER,
            height=48,
            corner_radius=8,
            command=self._on_cancel
        ).pack(side="left", expand=True, fill="x", padx=(0, 8))

        # 確認輪動按鈕
        ctk.CTkButton(
            button_frame,
            text="確認輪動",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=Colors.GREEN,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            height=48,
            corner_radius=8,
            command=self._on_confirm
        ).pack(side="left", expand=True, fill="x")

    def _on_confirm(self):
        """確認輪動"""
        if self.on_confirm:
            self.on_confirm(self.signal)
        self.destroy()

    def _on_cancel(self):
        """取消輪動"""
        if self.on_cancel:
            self.on_cancel(self.signal)
        self.destroy()


class RotationHistoryDialog(ctk.CTkToplevel):
    """
    輪動歷史對話框

    顯示輪動歷史記錄和統計數據。

    Story 4.3: 輪動歷史與統計
    """

    def __init__(self, parent, tracker=None):
        super().__init__(parent)
        self.tracker = tracker

        self.title("輪動歷史")
        self.geometry("600x500")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PRIMARY)

        # 模態設定
        self.transient(parent)
        self.grab_set()

        # 置中顯示
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 600) // 2
        y = (screen_height - 500) // 2
        self.geometry(f"600x500+{x}+{y}")

        self._create_ui()

    def _create_ui(self):
        """建立 UI"""
        # 標題
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 16))

        ctk.CTkLabel(
            header,
            text="輪動歷史",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(side="left")

        # 關閉按鈕
        ctk.CTkButton(
            header,
            text="關閉",
            font=ctk.CTkFont(size=12),
            fg_color=Colors.BG_TERTIARY,
            text_color=Colors.TEXT_PRIMARY,
            hover_color=Colors.BORDER,
            width=60,
            height=30,
            corner_radius=6,
            command=self.destroy
        ).pack(side="right")

        # 統計摘要
        stats_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SECONDARY, corner_radius=10)
        stats_frame.pack(fill="x", padx=20, pady=(0, 16))

        stats = self._get_stats()

        stats_row = ctk.CTkFrame(stats_frame, fg_color="transparent")
        stats_row.pack(fill="x", padx=16, pady=12)

        # 統計項目
        stat_items = [
            ("總輪動次數", str(stats.get('total_rotations', 0))),
            ("成功率", f"{stats.get('success_rate', 0):.1f}%"),
            ("平均損益", f"{stats.get('avg_pnl_impact', 0):+.4f}"),
            ("評分改善", f"{stats.get('avg_score_improvement', 0):+.1f}"),
        ]

        for label, value in stat_items:
            item = ctk.CTkFrame(stats_row, fg_color="transparent")
            item.pack(side="left", expand=True)

            ctk.CTkLabel(
                item,
                text=label,
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED
            ).pack()

            ctk.CTkLabel(
                item,
                text=value,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=Colors.TEXT_PRIMARY
            ).pack()

        # 歷史列表
        list_frame = ctk.CTkScrollableFrame(self, fg_color="transparent", height=300)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # 表頭
        header_row = ctk.CTkFrame(list_frame, fg_color=Colors.BG_TERTIARY, corner_radius=4)
        header_row.pack(fill="x", pady=(0, 8))

        headers = [("時間", 100), ("原幣種", 80), ("目標幣種", 80), ("評分變化", 80), ("損益", 80)]
        for text, width in headers:
            ctk.CTkLabel(
                header_row,
                text=text,
                width=width,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=Colors.TEXT_SECONDARY
            ).pack(side="left", padx=4, pady=8)

        # 歷史記錄
        logs = self._get_logs()

        if not logs:
            ctk.CTkLabel(
                list_frame,
                text="暫無輪動記錄",
                font=ctk.CTkFont(size=13),
                text_color=Colors.TEXT_MUTED
            ).pack(pady=40)
        else:
            for log in logs[-20:]:  # 最多顯示 20 筆
                row = ctk.CTkFrame(list_frame, fg_color="transparent")
                row.pack(fill="x", pady=1)

                # 時間
                time_str = log.timestamp.strftime("%m-%d %H:%M") if hasattr(log, 'timestamp') else "N/A"
                ctk.CTkLabel(
                    row, text=time_str, width=100,
                    font=ctk.CTkFont(size=11),
                    text_color=Colors.TEXT_SECONDARY
                ).pack(side="left", padx=4)

                # 原幣種
                from_sym = log.from_symbol.split('/')[0] if '/' in log.from_symbol else log.from_symbol
                ctk.CTkLabel(
                    row, text=from_sym, width=80,
                    font=ctk.CTkFont(size=11),
                    text_color=Colors.TEXT_PRIMARY
                ).pack(side="left", padx=4)

                # 目標幣種
                to_sym = log.to_symbol.split('/')[0] if '/' in log.to_symbol else log.to_symbol
                ctk.CTkLabel(
                    row, text=to_sym, width=80,
                    font=ctk.CTkFont(size=11),
                    text_color=Colors.GREEN
                ).pack(side="left", padx=4)

                # 評分變化
                score_change = log.score_after - log.score_before
                change_color = Colors.GREEN if score_change > 0 else Colors.RED
                ctk.CTkLabel(
                    row, text=f"{score_change:+.1f}", width=80,
                    font=ctk.CTkFont(size=11),
                    text_color=change_color
                ).pack(side="left", padx=4)

                # 損益
                pnl_color = Colors.GREEN if log.pnl_impact >= 0 else Colors.RED
                ctk.CTkLabel(
                    row, text=f"{log.pnl_impact:+.4f}", width=80,
                    font=ctk.CTkFont(size=11),
                    text_color=pnl_color
                ).pack(side="left", padx=4)

    def _get_stats(self) -> Dict:
        """獲取統計數據"""
        if self.tracker:
            return self.tracker.get_stats(days=30)
        return {
            'total_rotations': 0,
            'success_rate': 0.0,
            'avg_pnl_impact': 0.0,
            'avg_score_improvement': 0.0
        }

    def _get_logs(self):
        """獲取歷史記錄"""
        if self.tracker:
            return self.tracker.get_recent(days=30)
        return []
