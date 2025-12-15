"""
交易對管理對話框

包含:
- AddSymbolDialog: 新增交易對
- EditSymbolDialog: 編輯交易對
- AddFromCoinSelectDialog: 從選幣頁面新增
"""

import customtkinter as ctk
from typing import Dict
from ..styles import Colors


class AddSymbolDialog(ctk.CTkToplevel):
    """新增交易對對話框"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title("新增交易對")
        self.geometry("400x500")
        self.configure(fg_color=Colors.BG_PRIMARY)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        # 置中
        self.update_idletasks()
        x = self.winfo_toplevel().winfo_x() + 100
        y = self.winfo_toplevel().winfo_y() + 100
        self.geometry(f"400x500+{x}+{y}")

        self._create_ui()

    def _create_ui(self):
        ctk.CTkLabel(self, text="新增交易對", font=ctk.CTkFont(size=18, weight="bold"), text_color=Colors.TEXT_PRIMARY).pack(pady=(20, 16))

        # 交易對選擇
        ctk.CTkLabel(self, text="交易對", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY).pack(anchor="w", padx=24)
        self.symbol_menu = ctk.CTkOptionMenu(self, values=["XRPUSDC", "BTCUSDC", "ETHUSDC", "SOLUSDC", "DOGEUSDC", "XRPUSDT", "BTCUSDT", "ETHUSDT"], fg_color=Colors.BG_TERTIARY, button_color=Colors.BG_TERTIARY, width=352)
        self.symbol_menu.pack(padx=24, pady=(4, 12))

        # 止盈間距
        ctk.CTkLabel(self, text="止盈間距 (%)", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY).pack(anchor="w", padx=24)
        self.tp_entry = ctk.CTkEntry(self, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=36)
        self.tp_entry.insert(0, "0.4")
        self.tp_entry.pack(fill="x", padx=24, pady=(4, 12))

        # 補倉間距
        ctk.CTkLabel(self, text="補倉間距 (%)", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY).pack(anchor="w", padx=24)
        self.gs_entry = ctk.CTkEntry(self, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=36)
        self.gs_entry.insert(0, "0.6")
        self.gs_entry.pack(fill="x", padx=24, pady=(4, 12))

        # 每單數量
        ctk.CTkLabel(self, text="每單數量", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY).pack(anchor="w", padx=24)
        self.qty_entry = ctk.CTkEntry(self, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=36)
        self.qty_entry.insert(0, "30")
        self.qty_entry.pack(fill="x", padx=24, pady=(4, 12))

        # 槓桿
        ctk.CTkLabel(self, text="槓桿倍數", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY).pack(anchor="w", padx=24)
        self.leverage_entry = ctk.CTkEntry(self, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=36)
        self.leverage_entry.insert(0, "20")
        self.leverage_entry.pack(fill="x", padx=24, pady=(4, 24))

        # 按鈕
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24)

        ctk.CTkButton(btn_frame, text="取消", fg_color=Colors.BG_TERTIARY, hover_color=Colors.BORDER, width=100, command=self.destroy).pack(side="left")
        ctk.CTkButton(btn_frame, text="新增", fg_color=Colors.ACCENT, text_color=Colors.BG_PRIMARY, hover_color=Colors.GREEN_DARK, width=100, command=self._save).pack(side="right")

    def _save(self):
        # 獲取數據
        data = {
            "symbol": self.symbol_menu.get(),
            "enabled": True,
            "tp": f"{self.tp_entry.get()}%",
            "gs": f"{self.gs_entry.get()}%",
            "qty": float(self.qty_entry.get()),
            "leverage": int(self.leverage_entry.get())
        }
        # 添加到列表和 GlobalConfig
        self.parent._create_symbol_row(data)
        self.parent.add_symbol_to_config(data)
        self.destroy()


class EditSymbolDialog(ctk.CTkToplevel):
    """編輯交易對對話框 - 帶 Tab 切換的完整版"""

    def __init__(self, parent, data: Dict):
        super().__init__(parent)
        self.parent = parent
        self.data = data
        self.use_global_advanced = ctk.BooleanVar(value=data.get('use_global_advanced', True))

        self.title(f"編輯 {data['symbol']}")
        self.geometry("450x550")
        self.configure(fg_color=Colors.BG_PRIMARY)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        self._create_ui()

    def _create_ui(self):
        # 標題
        ctk.CTkLabel(
            self,
            text=f"編輯 {self.data['symbol']}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(16, 8))

        # Tab 按鈕區
        tab_frame = ctk.CTkFrame(self, fg_color="transparent")
        tab_frame.pack(fill="x", padx=20, pady=(0, 8))

        self.current_tab = "basic"
        self.tab_buttons = {}

        self.tab_buttons["basic"] = ctk.CTkButton(
            tab_frame,
            text="基本",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            width=100, height=32,
            corner_radius=6,
            command=lambda: self._switch_tab("basic")
        )
        self.tab_buttons["basic"].pack(side="left", padx=(0, 4))

        self.tab_buttons["advanced"] = ctk.CTkButton(
            tab_frame,
            text="進階",
            font=ctk.CTkFont(size=12),
            fg_color=Colors.BG_TERTIARY,
            text_color=Colors.TEXT_SECONDARY,
            hover_color=Colors.BORDER,
            width=100, height=32,
            corner_radius=6,
            command=lambda: self._switch_tab("advanced")
        )
        self.tab_buttons["advanced"].pack(side="left")

        # Tab 內容區
        self.tab_container = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_container.pack(fill="both", expand=True, padx=20, pady=(0, 8))

        self.tabs = {}
        self._create_basic_tab()
        self._create_advanced_tab()

        # 預設顯示基本 Tab
        self.tabs["basic"].pack(fill="both", expand=True)

        # 按鈕區
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 16))

        ctk.CTkButton(
            btn_frame,
            text="取消",
            fg_color=Colors.BG_TERTIARY,
            hover_color=Colors.BORDER,
            width=100,
            command=self.destroy
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="儲存",
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            width=100,
            command=self._save
        ).pack(side="right")

    def _create_basic_tab(self):
        """創建基本 Tab"""
        frame = ctk.CTkScrollableFrame(self.tab_container, fg_color="transparent")
        self.tabs["basic"] = frame

        # 止盈間距
        ctk.CTkLabel(frame, text="止盈間距 (%)", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_SECONDARY).pack(anchor="w", pady=(8, 0))
        self.tp_entry = ctk.CTkEntry(frame, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=36)
        self.tp_entry.insert(0, self.data.get('tp', '0.4%').replace('%', ''))
        self.tp_entry.pack(fill="x", pady=(4, 8))

        # 補倉間距
        ctk.CTkLabel(frame, text="補倉間距 (%)", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.gs_entry = ctk.CTkEntry(frame, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=36)
        self.gs_entry.insert(0, self.data.get('gs', '0.6%').replace('%', ''))
        self.gs_entry.pack(fill="x", pady=(4, 8))

        # 每單數量
        ctk.CTkLabel(frame, text="每單數量", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.qty_entry = ctk.CTkEntry(frame, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=36)
        self.qty_entry.insert(0, str(self.data.get('qty', 3)))
        self.qty_entry.pack(fill="x", pady=(4, 8))

        # 槓桿
        ctk.CTkLabel(frame, text="槓桿倍數", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.leverage_entry = ctk.CTkEntry(frame, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=36)
        self.leverage_entry.insert(0, str(self.data.get('leverage', 20)))
        self.leverage_entry.pack(fill="x", pady=(4, 12))

        # 說明
        info_frame = ctk.CTkFrame(frame, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        info_frame.pack(fill="x", pady=(8, 0))
        ctk.CTkLabel(
            info_frame,
            text="提示：進階參數在「進階」Tab 中設定",
            font=ctk.CTkFont(size=10),
            text_color=Colors.TEXT_MUTED
        ).pack(padx=12, pady=10)

    def _create_advanced_tab(self):
        """創建進階 Tab"""
        frame = ctk.CTkScrollableFrame(self.tab_container, fg_color="transparent")
        self.tabs["advanced"] = frame

        # 使用全域設定開關
        global_frame = ctk.CTkFrame(frame, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        global_frame.pack(fill="x", pady=(8, 12))

        ctk.CTkCheckBox(
            global_frame,
            text="使用全域設定",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_PRIMARY,
            fg_color=Colors.ACCENT,
            hover_color=Colors.GREEN_DARK,
            variable=self.use_global_advanced,
            command=self._toggle_advanced_fields
        ).pack(anchor="w", padx=12, pady=(10, 4))

        ctk.CTkLabel(
            global_frame,
            text="勾選後將使用全域預設值，取消勾選可獨立配置",
            font=ctk.CTkFont(size=10),
            text_color=Colors.TEXT_MUTED
        ).pack(anchor="w", padx=12, pady=(0, 10))

        # 進階參數區
        self.advanced_fields_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self.advanced_fields_frame.pack(fill="x")

        # 止盈加倍倍數
        ctk.CTkLabel(
            self.advanced_fields_frame,
            text="止盈加倍倍數",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 0))
        ctk.CTkLabel(
            self.advanced_fields_frame,
            text="持倉達「每單數量 × 此倍數」後，止盈自動加倍",
            font=ctk.CTkFont(size=9),
            text_color=Colors.TEXT_MUTED
        ).pack(anchor="w")
        self.limit_entry = ctk.CTkEntry(
            self.advanced_fields_frame,
            fg_color=Colors.BG_TERTIARY,
            border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY,
            height=36
        )
        self.limit_entry.insert(0, str(self.data.get('limit_mult', 5.0)))
        self.limit_entry.pack(fill="x", pady=(4, 8))

        # 裝死模式倍數
        ctk.CTkLabel(
            self.advanced_fields_frame,
            text="裝死模式倍數",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w")
        ctk.CTkLabel(
            self.advanced_fields_frame,
            text="持倉達「每單數量 × 此倍數」後，停止補倉",
            font=ctk.CTkFont(size=9),
            text_color=Colors.TEXT_MUTED
        ).pack(anchor="w")
        self.threshold_entry = ctk.CTkEntry(
            self.advanced_fields_frame,
            fg_color=Colors.BG_TERTIARY,
            border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY,
            height=36
        )
        self.threshold_entry.insert(0, str(self.data.get('threshold_mult', 20.0)))
        self.threshold_entry.pack(fill="x", pady=(4, 12))

        # 計算預覽
        preview_frame = ctk.CTkFrame(frame, fg_color=Colors.BG_TERTIARY, corner_radius=8)
        preview_frame.pack(fill="x", pady=(8, 0))

        ctk.CTkLabel(
            preview_frame,
            text="實際閾值預覽",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self.preview_label = ctk.CTkLabel(
            preview_frame,
            text="",
            font=ctk.CTkFont(size=10),
            text_color=Colors.TEXT_MUTED,
            justify="left"
        )
        self.preview_label.pack(anchor="w", padx=12, pady=(0, 10))

        # 綁定更新預覽
        self.qty_entry.bind("<KeyRelease>", lambda e: self._update_preview())
        self.limit_entry.bind("<KeyRelease>", lambda e: self._update_preview())
        self.threshold_entry.bind("<KeyRelease>", lambda e: self._update_preview())

        self._update_preview()
        self._toggle_advanced_fields()

    def _switch_tab(self, tab_name: str):
        """切換 Tab"""
        if tab_name == self.current_tab:
            return

        # 隱藏當前 Tab
        self.tabs[self.current_tab].pack_forget()

        # 更新按鈕樣式
        self.tab_buttons[self.current_tab].configure(
            fg_color=Colors.BG_TERTIARY,
            text_color=Colors.TEXT_SECONDARY,
            font=ctk.CTkFont(size=12)
        )
        self.tab_buttons[tab_name].configure(
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            font=ctk.CTkFont(size=12, weight="bold")
        )

        # 顯示新 Tab
        self.tabs[tab_name].pack(fill="both", expand=True)
        self.current_tab = tab_name

    def _toggle_advanced_fields(self):
        """切換進階欄位的啟用狀態"""
        use_global = self.use_global_advanced.get()
        state = "disabled" if use_global else "normal"
        text_color = Colors.TEXT_DISABLED if use_global else Colors.TEXT_PRIMARY

        self.limit_entry.configure(state=state, text_color=text_color)
        self.threshold_entry.configure(state=state, text_color=text_color)

        if use_global:
            # 顯示全域預設值
            self.limit_entry.configure(placeholder_text="使用全域: 5.0")
            self.threshold_entry.configure(placeholder_text="使用全域: 20.0")
        else:
            self.limit_entry.configure(placeholder_text="")
            self.threshold_entry.configure(placeholder_text="")

        self._update_preview()

    def _update_preview(self):
        """更新持倉閾值預覽"""
        try:
            qty = float(self.qty_entry.get() or 3)

            if self.use_global_advanced.get():
                limit = 5.0  # 全域預設
                threshold = 20.0  # 全域預設
                source = "全域"
            else:
                limit = float(self.limit_entry.get() or 5)
                threshold = float(self.threshold_entry.get() or 20)
                source = "獨立"

            pos_limit = qty * limit
            pos_threshold = qty * threshold

            self.preview_label.configure(
                text=f"止盈加倍閾值: {pos_limit:.1f} (= {qty:.0f} × {limit:.0f}) [{source}]\n"
                     f"裝死模式閾值: {pos_threshold:.1f} (= {qty:.0f} × {threshold:.0f}) [{source}]"
            )
        except ValueError:
            self.preview_label.configure(text="請輸入有效數值")

    def _save(self):
        try:
            # 更新數據
            self.data['tp'] = f"{self.tp_entry.get()}%"
            self.data['gs'] = f"{self.gs_entry.get()}%"
            self.data['qty'] = float(self.qty_entry.get())
            self.data['leverage'] = int(self.leverage_entry.get())
            self.data['use_global_advanced'] = self.use_global_advanced.get()

            if not self.use_global_advanced.get():
                # 使用獨立設定
                self.data['limit_mult'] = float(self.limit_entry.get())
                self.data['threshold_mult'] = float(self.threshold_entry.get())
            else:
                # 使用全域設定，移除獨立值
                self.data.pop('limit_mult', None)
                self.data.pop('threshold_mult', None)

            # 持久化到 GlobalConfig
            self.parent.update_symbol_in_config(self.data['symbol'], self.data)
            self.parent.refresh()
            self.destroy()
        except ValueError:
            from tkinter import messagebox
            messagebox.showerror("輸入錯誤", "請輸入有效的數值")


class AddFromCoinSelectDialog(ctk.CTkToplevel):
    """從選幣頁面加入交易對的對話框 - 精簡版"""

    def __init__(self, parent, data: Dict, score):
        super().__init__(parent)
        self.parent = parent
        self.data = data
        self.score = score

        self.title("加入交易對")
        self.geometry("400x420")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PRIMARY)

        # 置中
        self.transient(parent)
        self.grab_set()

        self._create_ui()

    def _create_ui(self):
        # 標題 + 評分
        header = ctk.CTkFrame(self, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        header.pack(fill="x", padx=16, pady=(16, 12))

        ctk.CTkLabel(
            header,
            text=self.data.get('symbol', 'N/A'),
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(side="left", padx=12, pady=12)

        if self.score:
            score_text = f"{self.score.final_score:.0f} 分"
            ctk.CTkLabel(
                header,
                text=score_text,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=Colors.TEXT_SECONDARY
            ).pack(side="right", padx=12, pady=12)

        # 參數設定
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.pack(fill="x", padx=16, pady=8)

        # 止盈間距
        ctk.CTkLabel(form, text="止盈間距 (%)", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.tp_entry = ctk.CTkEntry(form, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=36)
        self.tp_entry.insert(0, "0.4")
        self.tp_entry.pack(fill="x", pady=(4, 10))

        # 補倉間距
        ctk.CTkLabel(form, text="補倉間距 (%)", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.gs_entry = ctk.CTkEntry(form, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=36)
        self.gs_entry.insert(0, "0.6")
        self.gs_entry.pack(fill="x", pady=(4, 10))

        # 每單數量
        ctk.CTkLabel(form, text="每單數量", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.qty_entry = ctk.CTkEntry(form, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=36)
        self.qty_entry.insert(0, "30")
        self.qty_entry.pack(fill="x", pady=(4, 10))

        # 槓桿
        ctk.CTkLabel(form, text="槓桿倍數", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_SECONDARY).pack(anchor="w")
        self.leverage_entry = ctk.CTkEntry(form, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=36)
        self.leverage_entry.insert(0, "20")
        self.leverage_entry.pack(fill="x", pady=(4, 10))

        # 按鈕區
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=16)

        ctk.CTkButton(
            btn_frame,
            text="取消",
            fg_color=Colors.BG_TERTIARY,
            hover_color=Colors.BORDER,
            width=100,
            command=self.destroy
        ).pack(side="left")

        ctk.CTkButton(
            btn_frame,
            text="加入並回測",
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            width=130,
            command=lambda: self._do_action("backtest")
        ).pack(side="right")

        ctk.CTkButton(
            btn_frame,
            text="直接加入",
            fg_color=Colors.BG_SECONDARY,
            hover_color=Colors.BORDER,
            width=100,
            command=lambda: self._do_action("add")
        ).pack(side="right", padx=8)

    def _do_action(self, action: str):
        """執行加入操作"""
        data = {
            'symbol': self.data.get('symbol'),
            'enabled': True,
            'tp': f"{self.tp_entry.get()}%",
            'gs': f"{self.gs_entry.get()}%",
            'qty': float(self.qty_entry.get()),
            'leverage': int(self.leverage_entry.get())
        }

        self.destroy()

        if action == "backtest":
            # 跳轉到回測頁面並填入參數
            self.parent.app.app_state.set_pending_params(data, action='backtest')
            self.parent.app.show_page('backtest')
        else:
            # 直接加入
            self._do_add(data)

    def _do_add(self, data: Dict):
        """執行加入操作"""
        # 加入到 SymbolsPage
        symbols_page = self.parent.app.pages.get("symbols")
        if symbols_page:
            symbols_page.add_symbol_to_config(data)
            symbols_page._create_symbol_row(data)
