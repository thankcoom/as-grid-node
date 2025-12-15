"""
導航元件

包含:
- NavButton: 導航按鈕
- StepIndicator: 步驟指示器
"""

import customtkinter as ctk
from ..styles import Colors


class NavButton(ctk.CTkButton):
    """導航按鈕"""
    def __init__(self, master, text: str, icon: str = "", is_active: bool = False, **kwargs):
        super().__init__(
            master,
            text=f"{icon}  {text}" if icon else text,
            font=ctk.CTkFont(size=13),
            fg_color=Colors.NAV_ACTIVE if is_active else "transparent",
            text_color=Colors.TEXT_PRIMARY if is_active else Colors.TEXT_SECONDARY,
            hover_color=Colors.NAV_HOVER,
            anchor="w",
            height=40,
            corner_radius=8,
            **kwargs
        )
        self.is_active = is_active

    def set_active(self, active: bool):
        self.is_active = active
        self.configure(
            fg_color=Colors.NAV_ACTIVE if active else "transparent",
            text_color=Colors.TEXT_PRIMARY if active else Colors.TEXT_SECONDARY
        )


class StepIndicator(ctk.CTkFrame):
    """
    步驟指示器 - 顯示用戶當前所在的操作流程

    顯示格式: ① 選幣 → ② 配置 → ③ 啟用 → ④ 監控
    """

    # 預設步驟（可在實例化時覆蓋）
    DEFAULT_STEPS = [
        ("選幣", "coinselect"),
        ("配置", "symbols"),
        ("回測", "backtest"),
        ("監控", "trading"),
        ("設定", "settings")
    ]

    def __init__(self, master, steps: list = None, current_page: str = None, **kwargs):
        """
        初始化步驟指示器

        Args:
            master: 父元件
            steps: 步驟列表，格式為 [(label, page_id), ...]
            current_page: 當前頁面 ID
        """
        super().__init__(master, fg_color="transparent", **kwargs)

        self.steps = steps or self.DEFAULT_STEPS
        self.current_page = current_page
        self.step_labels = []

        self._create_ui()

    def _create_ui(self):
        """建立 UI"""
        # 容器
        container = ctk.CTkFrame(self, fg_color=Colors.BG_SECONDARY, corner_radius=8)
        container.pack(fill="x", pady=(0, 12))

        inner = ctk.CTkFrame(container, fg_color="transparent")
        inner.pack(padx=16, pady=10)

        for i, (label, page_id) in enumerate(self.steps):
            # 步驟編號圓圈
            is_current = (page_id == self.current_page)
            is_completed = self._is_step_completed(i)

            # 數字圓圈
            circle_text = f"{'✓' if is_completed and not is_current else i + 1}"
            circle_color = Colors.ACCENT if is_current else (Colors.STATUS_ON if is_completed else Colors.BG_TERTIARY)
            text_color = Colors.BG_PRIMARY if is_current else (Colors.BG_PRIMARY if is_completed else Colors.TEXT_MUTED)

            circle = ctk.CTkLabel(
                inner,
                text=circle_text,
                width=24,
                height=24,
                fg_color=circle_color,
                corner_radius=12,
                text_color=text_color,
                font=ctk.CTkFont(size=11, weight="bold")
            )
            circle.pack(side="left")

            # 步驟名稱
            label_color = Colors.TEXT_PRIMARY if is_current else (Colors.TEXT_SECONDARY if is_completed else Colors.TEXT_MUTED)
            step_label = ctk.CTkLabel(
                inner,
                text=label,
                font=ctk.CTkFont(size=12, weight="bold" if is_current else "normal"),
                text_color=label_color
            )
            step_label.pack(side="left", padx=(4, 0))

            self.step_labels.append((circle, step_label, page_id))

            # 箭頭（非最後一個步驟）
            if i < len(self.steps) - 1:
                arrow = ctk.CTkLabel(
                    inner,
                    text="→",
                    font=ctk.CTkFont(size=12),
                    text_color=Colors.TEXT_MUTED
                )
                arrow.pack(side="left", padx=8)

    def _is_step_completed(self, step_index: int) -> bool:
        """判斷步驟是否已完成（簡化邏輯：當前步驟之前的都視為完成）"""
        current_index = self._get_current_index()
        return step_index < current_index if current_index >= 0 else False

    def _get_current_index(self) -> int:
        """獲取當前步驟索引"""
        for i, (_, page_id) in enumerate(self.steps):
            if page_id == self.current_page:
                return i
        return -1

    def set_current_page(self, page_id: str):
        """更新當前頁面並刷新顯示"""
        self.current_page = page_id
        # 重建 UI（簡單實現）
        for widget in self.winfo_children():
            widget.destroy()
        self.step_labels = []
        self._create_ui()
