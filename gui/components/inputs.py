"""
輸入元件

包含:
- InputField: 輸入欄位
- ToggleSwitch: 開關元件
"""

import customtkinter as ctk
from typing import Callable
from ..styles import Colors


class ToggleSwitch(ctk.CTkFrame):
    """開關元件"""
    def __init__(self, master, text: str, initial: bool = False, command: Callable = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.command = command

        ctk.CTkLabel(
            self,
            text=text,
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_SECONDARY
        ).pack(side="left")

        self.switch = ctk.CTkSwitch(
            self,
            text="",
            width=40,
            height=20,
            switch_width=36,
            switch_height=18,
            fg_color=Colors.BG_TERTIARY,
            progress_color=Colors.STATUS_ON,
            button_color=Colors.TEXT_PRIMARY,
            button_hover_color=Colors.TEXT_SECONDARY,
            command=self._on_change
        )
        self.switch.pack(side="right")

        if initial:
            self.switch.select()

    def _on_change(self):
        if self.command:
            self.command(self.switch.get())

    def get(self) -> bool:
        return bool(self.switch.get())

    def set(self, value: bool):
        if value:
            self.switch.select()
        else:
            self.switch.deselect()


class InputField(ctk.CTkFrame):
    """輸入欄位元件"""
    def __init__(
        self,
        master,
        label: str,
        default: str = "",
        placeholder: str = "",
        width: int = 100,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        ctk.CTkLabel(
            self,
            text=label,
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_SECONDARY
        ).pack(side="left")

        self.entry = ctk.CTkEntry(
            self,
            width=width,
            height=32,
            fg_color=Colors.BG_TERTIARY,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY,
            placeholder_text=placeholder
        )
        self.entry.pack(side="right")
        if default:
            self.entry.insert(0, default)

    def get(self) -> str:
        return self.entry.get()

    def set(self, value: str):
        self.entry.delete(0, "end")
        self.entry.insert(0, value)
