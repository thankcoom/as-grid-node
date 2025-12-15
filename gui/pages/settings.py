"""
設定頁面 - Bitget 版本
"""

import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk

from ..styles import Colors
from ..components import Card

if TYPE_CHECKING:
    from gui.app import ASGridApp

class SettingsPage(ctk.CTkFrame):
    """設定頁面 - 綁定 GlobalConfig (Bitget 版本)"""

    def __init__(self, master, app: "ASGridApp"):
        super().__init__(master, fg_color=Colors.BG_PRIMARY)
        self.app = app
        self.config = None
        self.vars = {}  # 儲存所有變數
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
            print(f"載入配置失敗: {e}")
            self.config = None

    def _create_ui(self):
        # 可滾動區域
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        ctk.CTkLabel(scroll, text="系統設定", font=ctk.CTkFont(size=20, weight="bold"), text_color=Colors.TEXT_PRIMARY).pack(anchor="w", pady=(0, 4))

        # 全域設定說明
        ctk.CTkLabel(
            scroll,
            text="以下設定將套用於所有啟用的交易對。滑鼠懸停在 ⓘ 上可查看說明。",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED
        ).pack(anchor="w", pady=(0, 12))

        # 從配置讀取預設值
        if self.config:
            max_cfg = self.config.max_enhancement
            bandit = self.config.bandit
            leading = self.config.leading_indicator
            dgt = self.config.dgt
            risk = self.config.risk
        else:
            # 預設值
            max_cfg = type('obj', (object,), {'all_enhancements_enabled': False, 'funding_rate_enabled': False, 'glft_enabled': False, 'dynamic_grid_enabled': False})()
            bandit = type('obj', (object,), {'enabled': True, 'contextual_enabled': True, 'thompson_enabled': True})()
            leading = type('obj', (object,), {'enabled': True, 'ofi_enabled': True, 'volume_enabled': True, 'spread_enabled': True})()
            dgt = type('obj', (object,), {'enabled': False})()
            risk = type('obj', (object,), {'enabled': True, 'margin_threshold': 0.5, 'trailing_start_profit': 5.0, 'trailing_drawdown_pct': 0.1})()

        # MAX 增強設定
        max_card = Card(scroll, title="MAX 增強功能")
        max_card.pack(fill="x", pady=(0, 16))

        self.vars['max_all'] = ctk.BooleanVar(value=max_cfg.all_enhancements_enabled)
        self._create_toggle(
            max_card, "啟用所有增強功能", self.vars['max_all'], pady=(8, 12),
            tooltip="一鍵啟用以下所有增強功能。單獨關閉某項功能需先關閉此選項。"
        )

        ctk.CTkFrame(max_card, fg_color=Colors.BORDER, height=1).pack(fill="x", padx=16, pady=8)

        self.vars['funding_rate'] = ctk.BooleanVar(value=max_cfg.funding_rate_enabled)
        self._create_toggle(
            max_card, "Funding Rate 偏向調整", self.vars['funding_rate'],
            tooltip="根據永續合約資金費率自動調整交易方向偏好。正費率時偏向做空，負費率時偏向做多。"
        )

        self.vars['glft'] = ctk.BooleanVar(value=max_cfg.glft_enabled)
        self._create_toggle(
            max_card, "GLFT 庫存控制", self.vars['glft'],
            tooltip="Guéant-Lehalle-Fernandez-Tapia 模型，根據當前持倉水平動態調整報價偏移，控制庫存風險。"
        )

        self.vars['dynamic_grid'] = ctk.BooleanVar(value=max_cfg.dynamic_grid_enabled)
        self._create_toggle(
            max_card, "動態網格間距 (ATR)", self.vars['dynamic_grid'], pady=(8, 16),
            tooltip="根據 ATR (平均真實波幅) 動態調整網格間距。高波動時擴大間距，低波動時縮小間距。"
        )

        # 學習模組設定
        learning_card = Card(scroll, title="學習模組")
        learning_card.pack(fill="x", pady=(0, 16))

        self.vars['bandit'] = ctk.BooleanVar(value=bandit.enabled)
        self._create_toggle(
            learning_card, "UCB Bandit 優化器", self.vars['bandit'], pady=(8, 8),
            tooltip="使用 Upper Confidence Bound 算法自動學習最佳網格參數。會根據歷史表現動態調整止盈和補倉間距。"
        )

        self.vars['contextual'] = ctk.BooleanVar(value=bandit.contextual_enabled)
        self._create_toggle(
            learning_card, "上下文感知 (Contextual)", self.vars['contextual'],
            tooltip="將市場狀態（波動率、趨勢強度）納入參數選擇決策，不同市場環境使用不同參數組合。"
        )

        self.vars['thompson'] = ctk.BooleanVar(value=bandit.thompson_enabled)
        self._create_toggle(
            learning_card, "Thompson Sampling", self.vars['thompson'],
            tooltip="使用貝葉斯方法進行參數探索與利用的平衡。更適合非穩定環境，收斂更快。"
        )

        ctk.CTkFrame(learning_card, fg_color=Colors.BORDER, height=1).pack(fill="x", padx=16, pady=8)

        self.vars['leading'] = ctk.BooleanVar(value=leading.enabled)
        self._create_toggle(
            learning_card, "領先指標系統", self.vars['leading'],
            tooltip="使用多種領先指標預測短期價格方向，提前調整交易策略。"
        )

        self.vars['ofi'] = ctk.BooleanVar(value=leading.ofi_enabled)
        self._create_toggle(
            learning_card, "訂單流失衡 (OFI)", self.vars['ofi'],
            tooltip="分析買賣訂單流的不平衡程度，預測短期價格壓力方向。"
        )

        self.vars['volume'] = ctk.BooleanVar(value=leading.volume_enabled)
        self._create_toggle(
            learning_card, "成交量分析", self.vars['volume'],
            tooltip="分析成交量變化和異常，識別潛在的趨勢延續或反轉信號。"
        )

        self.vars['spread'] = ctk.BooleanVar(value=leading.spread_enabled)
        self._create_toggle(
            learning_card, "價差分析", self.vars['spread'],
            tooltip="監控買賣價差變化，識別流動性變化和市場情緒轉變。"
        )

        ctk.CTkFrame(learning_card, fg_color=Colors.BORDER, height=1).pack(fill="x", padx=16, pady=8)

        self.vars['dgt'] = ctk.BooleanVar(value=dgt.enabled)
        self._create_toggle(
            learning_card, "DGT 動態邊界重置", self.vars['dgt'], pady=(8, 16),
            tooltip="動態網格觸發器。當價格脫離網格範圍時，自動重置網格邊界，適應趨勢行情。"
        )

        # 風險管理
        risk_card = Card(scroll, title="風險管理")
        risk_card.pack(fill="x", pady=(0, 16))

        self.vars['risk_enabled'] = ctk.BooleanVar(value=risk.enabled)
        self._create_toggle(
            risk_card, "追蹤止盈", self.vars['risk_enabled'], pady=(8, 8),
            tooltip="當總盈利達到設定值後，啟用動態追蹤止盈。盈利回撤超過比例時自動平倉保護利潤。"
        )

        self.vars['margin_threshold'] = ctk.StringVar(value=f"{risk.margin_threshold * 100:.0f}")
        self._create_input(
            risk_card, "保證金警戒線 (%)", self.vars['margin_threshold'],
            tooltip="當保證金使用率超過此值時發出警告。建議設定在 50-70% 之間。"
        )

        self.vars['trailing_start'] = ctk.StringVar(value=f"{risk.trailing_start_profit:.1f}")
        self._create_input(
            risk_card, "追蹤起始盈利 (U)", self.vars['trailing_start'],
            tooltip="當總未實現盈利達到此金額 (USDT) 後，開始啟用追蹤止盈功能。"
        )

        self.vars['trailing_drawdown'] = ctk.StringVar(value=f"{risk.trailing_drawdown_pct * 100:.0f}")
        self._create_input(
            risk_card, "追蹤回撤比例 (%)", self.vars['trailing_drawdown'], pady=(8, 16),
            tooltip="最高盈利回撤超過此比例時觸發止盈。例如設定 10%，則從最高盈利回撤 10% 時平倉。"
        )

        # API 狀態顯示 (Bitget 版本 - 包含 passphrase)
        api_card = Card(scroll, title="API 狀態 (Bitget)")
        api_card.pack(fill="x", pady=(0, 16))

        # API Key 狀態
        if self.app.api_key:
            api_text = f"API Key: {self.app.api_key[:8]}...{self.app.api_key[-4:]}"
            api_color = Colors.STATUS_ON
        else:
            api_text = "API Key: 未設定"
            api_color = Colors.TEXT_MUTED

        ctk.CTkLabel(api_card, text=api_text, font=ctk.CTkFont(size=13), text_color=api_color).pack(anchor="w", padx=16, pady=(16, 4))

        # Passphrase 狀態 (Bitget 專用)
        passphrase = getattr(self.app, 'passphrase', None)
        if passphrase:
            pass_text = f"Passphrase: {'*' * 8}"
            pass_color = Colors.STATUS_ON
        else:
            pass_text = "Passphrase: 未設定 (Bitget 必需)"
            pass_color = Colors.STATUS_OFF

        ctk.CTkLabel(api_card, text=pass_text, font=ctk.CTkFont(size=13), text_color=pass_color).pack(anchor="w", padx=16, pady=(0, 8))

        # 提示文字
        ctk.CTkLabel(
            api_card,
            text="💡 Bitget API 需要 API Key + Secret + Passphrase",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED
        ).pack(anchor="w", padx=16, pady=(0, 8))

        # 更換 API 按鈕
        if self.app.api_key:
            self.change_api_button = ctk.CTkButton(
                api_card,
                text="🔄 更換 API 憑證",
                font=ctk.CTkFont(size=13),
                fg_color=Colors.BG_TERTIARY,
                text_color=Colors.TEXT_PRIMARY,
                hover_color=Colors.BORDER,
                height=36,
                corner_radius=6,
                command=self._show_change_api_dialog
            )
            self.change_api_button.pack(anchor="w", padx=16, pady=(0, 16))

        # 儲存按鈕
        self.save_button = ctk.CTkButton(
            scroll,
            text="儲存設定",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            height=44,
            corner_radius=8,
            command=self._save_settings
        )
        self.save_button.pack(fill="x", pady=(0, 16))

    def _create_toggle(self, parent, text: str, var: ctk.BooleanVar, pady=(8, 8), tooltip: str = None):
        """建立開關，支援 tooltip 說明"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=16, pady=pady)

        # 左側：標籤 + tooltip 圖示
        left = ctk.CTkFrame(frame, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        label = ctk.CTkLabel(left, text=text, font=ctk.CTkFont(size=13), text_color=Colors.TEXT_PRIMARY)
        label.pack(side="left")

        if tooltip:
            # 添加說明圖示
            info_label = ctk.CTkLabel(
                left,
                text="ⓘ",
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED,
                cursor="hand2"
            )
            info_label.pack(side="left", padx=(4, 0))

            # Tooltip 浮動視窗
            tooltip_window = None

            def show_tooltip(event):
                nonlocal tooltip_window
                if tooltip_window:
                    return
                x = event.x_root + 10
                y = event.y_root + 10

                tooltip_window = ctk.CTkToplevel(self)
                tooltip_window.wm_overrideredirect(True)
                tooltip_window.wm_geometry(f"+{x}+{y}")
                tooltip_window.configure(fg_color=Colors.BG_TERTIARY)

                tooltip_label = ctk.CTkLabel(
                    tooltip_window,
                    text=tooltip,
                    font=ctk.CTkFont(size=11),
                    text_color=Colors.TEXT_SECONDARY,
                    wraplength=250,
                    justify="left"
                )
                tooltip_label.pack(padx=10, pady=8)

            def hide_tooltip(_event):
                nonlocal tooltip_window
                if tooltip_window:
                    tooltip_window.destroy()
                    tooltip_window = None

            info_label.bind("<Enter>", show_tooltip)
            info_label.bind("<Leave>", hide_tooltip)

        switch = ctk.CTkSwitch(
            frame,
            text="",
            variable=var,
            width=44,
            height=22,
            fg_color=Colors.STATUS_OFF,
            progress_color=Colors.STATUS_ON,
            button_color=Colors.TEXT_PRIMARY
        )
        switch.pack(side="right")

    def _create_input(self, parent, label: str, var: ctk.StringVar, pady=(8, 8), tooltip: str = None):
        """建立輸入框，支援 tooltip 說明"""
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=16, pady=pady)

        # 左側：標籤 + tooltip 圖示
        left = ctk.CTkFrame(frame, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        label_widget = ctk.CTkLabel(left, text=label, font=ctk.CTkFont(size=13), text_color=Colors.TEXT_PRIMARY)
        label_widget.pack(side="left")

        if tooltip:
            info_label = ctk.CTkLabel(
                left,
                text="ⓘ",
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED,
                cursor="hand2"
            )
            info_label.pack(side="left", padx=(4, 0))

            tooltip_window = None

            def show_tooltip(event):
                nonlocal tooltip_window
                if tooltip_window:
                    return
                x = event.x_root + 10
                y = event.y_root + 10

                tooltip_window = ctk.CTkToplevel(self)
                tooltip_window.wm_overrideredirect(True)
                tooltip_window.wm_geometry(f"+{x}+{y}")
                tooltip_window.configure(fg_color=Colors.BG_TERTIARY)

                tooltip_label = ctk.CTkLabel(
                    tooltip_window,
                    text=tooltip,
                    font=ctk.CTkFont(size=11),
                    text_color=Colors.TEXT_SECONDARY,
                    wraplength=250,
                    justify="left"
                )
                tooltip_label.pack(padx=10, pady=8)

            def hide_tooltip(_event):
                nonlocal tooltip_window
                if tooltip_window:
                    tooltip_window.destroy()
                    tooltip_window = None

            info_label.bind("<Enter>", show_tooltip)
            info_label.bind("<Leave>", hide_tooltip)

        entry = ctk.CTkEntry(
            frame,
            textvariable=var,
            width=80,
            height=32,
            fg_color=Colors.BG_TERTIARY,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY
        )
        entry.pack(side="right")

    def _save_settings(self):
        """儲存設定到配置檔"""
        self.save_button.configure(text="儲存中...", state="disabled")

        def do_save():
            try:
                if self.config:
                    # MAX 增強
                    self.config.max_enhancement.all_enhancements_enabled = self.vars['max_all'].get()
                    self.config.max_enhancement.funding_rate_enabled = self.vars['funding_rate'].get()
                    self.config.max_enhancement.glft_enabled = self.vars['glft'].get()
                    self.config.max_enhancement.dynamic_grid_enabled = self.vars['dynamic_grid'].get()

                    # Bandit
                    self.config.bandit.enabled = self.vars['bandit'].get()
                    self.config.bandit.contextual_enabled = self.vars['contextual'].get()
                    self.config.bandit.thompson_enabled = self.vars['thompson'].get()

                    # 領先指標
                    self.config.leading_indicator.enabled = self.vars['leading'].get()
                    self.config.leading_indicator.ofi_enabled = self.vars['ofi'].get()
                    self.config.leading_indicator.volume_enabled = self.vars['volume'].get()
                    self.config.leading_indicator.spread_enabled = self.vars['spread'].get()

                    # DGT
                    self.config.dgt.enabled = self.vars['dgt'].get()

                    # 風控
                    self.config.risk.enabled = self.vars['risk_enabled'].get()
                    try:
                        self.config.risk.margin_threshold = float(self.vars['margin_threshold'].get()) / 100
                        self.config.risk.trailing_start_profit = float(self.vars['trailing_start'].get())
                        self.config.risk.trailing_drawdown_pct = float(self.vars['trailing_drawdown'].get()) / 100
                    except ValueError:
                        pass

                    # 儲存
                    self.config.save()

                self.save_button.configure(text="✓ 已儲存", state="normal")
                self.after(1500, lambda: self.save_button.configure(text="儲存設定"))

            except Exception as e:
                self.save_button.configure(text=f"錯誤: {e}", state="normal")
                self.after(2000, lambda: self.save_button.configure(text="儲存設定"))

        self.after(300, do_save)

    def _show_change_api_dialog(self):
        """開啟更換 API 憑證對話框"""
        # master=self.app (主視窗作為父級), app=self.app (應用程式參考)
        ChangeAPIDialog(self.app, self.app)

    def _reset_api(self):
        """重設 API 憑證 (破壞性重置 - 保留供未來使用)"""
        from tkinter import messagebox

        # 確認對話框
        if not messagebox.askyesno(
            "確認更換 API",
            "確定要更換 API 憑證嗎？\n\n"
            "這將會：\n"
            "• 停止所有交易\n"
            "• 斷開交易所連接\n"
            "• 清除已儲存的 API 憑證\n"
            "• 需要重新輸入新的 API\n\n"
            "確定要繼續嗎？"
        ):
            return

        # 停止交易並斷開連接
        engine = self.app.engine
        if engine:
            if engine.is_trading:
                engine.stop_trading()
            if engine.is_connected:
                import asyncio
                try:
                    asyncio.get_event_loop().run_until_complete(engine.disconnect())
                except Exception:
                    pass

            # 重設憑證管理器
            if engine.credential_manager:
                engine.credential_manager.reset()

        # 清除 app 的 API 資訊
        self.app.api_key = None
        self.app.api_secret = None
        self.app.uid = None
        self.app.connected = False

        # 提示用戶
        messagebox.showinfo(
            "API 已清除",
            "API 憑證已成功清除。\n\n"
            "請重新啟動應用程式以設定新的 API 憑證。"
        )

        # 關閉應用程式
        self.app.destroy()


# ═══════════════════════════════════════════════════════════════════════════
# 主應用程式
# ═══════════════════════════════════════════════════════════════════════════
