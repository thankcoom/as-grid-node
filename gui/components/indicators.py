"""
指示器元件

包含:
- StatusIndicator: 狀態指示器
"""

import customtkinter as ctk
from ..styles import Colors


class StatusIndicator(ctk.CTkFrame):
    """狀態指示器"""
    def __init__(self, master, text: str, is_active: bool = False, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        # 圓點
        self.dot = ctk.CTkLabel(
            self,
            text="●",
            font=ctk.CTkFont(size=10),
            text_color=Colors.STATUS_ON if is_active else Colors.STATUS_OFF
        )
        self.dot.pack(side="left", padx=(0, 6))

        # 文字
        self.text_label = ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_SECONDARY
        )
        self.text_label.pack(side="left")

    def set_active(self, is_active: bool, text: str = None):
        self.dot.configure(text_color=Colors.STATUS_ON if is_active else Colors.STATUS_OFF)
        if text:
            self.text_label.configure(text=text)
