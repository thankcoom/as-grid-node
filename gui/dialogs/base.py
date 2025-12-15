"""
基礎對話框

包含:
- ConfirmDialog: 通用確認對話框
"""

import customtkinter as ctk
from ..styles import Colors


class ConfirmDialog(ctk.CTkToplevel):
    """通用確認對話框"""

    def __init__(
        self,
        parent,
        title: str = "確認操作",
        message: str = "確定要執行此操作？",
        details: str = None,
        confirm_text: str = "確定",
        cancel_text: str = "取消",
        danger: bool = False,
        on_confirm: callable = None
    ):
        """
        初始化確認對話框

        Args:
            parent: 父視窗
            title: 對話框標題
            message: 主要訊息
            details: 詳細說明（可選，會以較淡顏色顯示）
            confirm_text: 確認按鈕文字
            cancel_text: 取消按鈕文字
            danger: 是否為危險操作（影響按鈕顏色）
            on_confirm: 確認後的回調函數
        """
        super().__init__(parent)
        self.on_confirm = on_confirm
        self.result = False

        self.title(title)
        self.geometry("400x220" if details else "400x180")
        self.configure(fg_color=Colors.BG_PRIMARY)
        self.transient(parent.winfo_toplevel())
        self.grab_set()

        # 置中
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        width = 400
        height = 220 if details else 180
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.geometry(f"{width}x{height}+{x}+{y}")

        # 圖示和標題
        icon = "⚠️" if danger else "❓"
        ctk.CTkLabel(
            self,
            text=icon,
            font=ctk.CTkFont(size=32)
        ).pack(pady=(20, 8))

        # 主訊息
        ctk.CTkLabel(
            self,
            text=message,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(0, 4))

        # 詳細說明
        if details:
            ctk.CTkLabel(
                self,
                text=details,
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED,
                wraplength=350
            ).pack(pady=(0, 8))

        # 按鈕區
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=40, pady=(16, 20))

        ctk.CTkButton(
            btn_frame,
            text=cancel_text,
            font=ctk.CTkFont(size=13),
            fg_color=Colors.BG_TERTIARY,
            hover_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY,
            width=120,
            height=36,
            corner_radius=6,
            command=self._cancel
        ).pack(side="left")

        confirm_bg = Colors.RED if danger else Colors.ACCENT
        confirm_hover = Colors.RED_DARK if danger else Colors.GREEN_DARK
        ctk.CTkButton(
            btn_frame,
            text=confirm_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=confirm_bg,
            hover_color=confirm_hover,
            text_color=Colors.TEXT_PRIMARY if danger else Colors.BG_PRIMARY,
            width=120,
            height=36,
            corner_radius=6,
            command=self._confirm
        ).pack(side="right")

    def _confirm(self):
        """確認操作"""
        self.result = True
        if self.on_confirm:
            self.on_confirm()
        self.destroy()

    def _cancel(self):
        """取消操作"""
        self.result = False
        self.destroy()
