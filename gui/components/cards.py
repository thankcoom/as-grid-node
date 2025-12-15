"""
卡片元件

包含:
- Card: 基礎卡片
- StatCard: 數據統計卡片
- RiskBadge: 風險評分徽章
"""

import customtkinter as ctk
from ..styles import Colors


class Card(ctk.CTkFrame):
    """卡片元件"""
    def __init__(self, master, title: str = None, **kwargs):
        super().__init__(
            master,
            fg_color=Colors.BG_SECONDARY,
            corner_radius=12,
            border_width=1,
            border_color=Colors.BORDER,
            **kwargs
        )

        if title:
            self.title_label = ctk.CTkLabel(
                self,
                text=title,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=Colors.TEXT_PRIMARY
            )
            self.title_label.pack(anchor="w", padx=16, pady=(16, 8))


class StatCard(ctk.CTkFrame):
    """數據統計卡片"""
    def __init__(
        self,
        master,
        title: str,
        value: str,
        subtitle: str = "",
        value_color: str = None,
        **kwargs
    ):
        if value_color is None:
            value_color = Colors.TEXT_PRIMARY

        super().__init__(
            master,
            fg_color=Colors.BG_SECONDARY,
            corner_radius=12,
            border_width=1,
            border_color=Colors.BORDER,
            **kwargs
        )

        # 標題
        self.title_label = ctk.CTkLabel(
            self,
            text=title,
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_MUTED
        )
        self.title_label.pack(anchor="w", padx=16, pady=(16, 4))

        # 數值
        self.value_label = ctk.CTkLabel(
            self,
            text=value,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=value_color
        )
        self.value_label.pack(anchor="w", padx=16, pady=(0, 4))

        # 副標題
        if subtitle:
            self.subtitle_label = ctk.CTkLabel(
                self,
                text=subtitle,
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_SECONDARY
            )
            self.subtitle_label.pack(anchor="w", padx=16, pady=(0, 16))

    def update_value(self, value: str, color: str = None):
        """更新數值"""
        self.value_label.configure(text=value)
        if color:
            self.value_label.configure(text_color=color)


class RiskBadge(ctk.CTkFrame):
    """風險評分徽章 - 顯示選幣評分"""

    def __init__(self, master, score: float = 0, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.score = score

        # 評分標籤
        self.score_label = ctk.CTkLabel(
            self,
            text="--",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=Colors.TEXT_MUTED,
            width=32,
            height=18,
            fg_color=Colors.BG_TERTIARY,
            corner_radius=3
        )
        self.score_label.pack()

        self.set_score(score)

    def set_score(self, score: float):
        """設置評分 (0-100) - 黑白風格"""
        self.score = score

        if score <= 0:
            text = "--"
            color = Colors.TEXT_MUTED
            bg = Colors.BG_TERTIARY
        elif score >= 70:
            text = f"{score:.0f}"
            color = Colors.TEXT_PRIMARY   # 優秀 - 白色
            bg = Colors.FILL_HIGHLIGHT
        elif score >= 55:
            text = f"{score:.0f}"
            color = Colors.TEXT_SECONDARY # 良好 - 淺灰
            bg = Colors.FILL_POSITIVE
        elif score >= 40:
            text = f"{score:.0f}"
            color = Colors.TEXT_SECONDARY # 一般 - 淺灰
            bg = Colors.BG_TERTIARY
        else:
            text = f"{score:.0f}"
            color = Colors.TEXT_MUTED     # 差 - 暗灰
            bg = Colors.BG_TERTIARY

        self.score_label.configure(text=text, text_color=color, fg_color=bg)
