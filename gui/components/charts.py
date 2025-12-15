"""
圖表元件

包含:
- MiniChart: 迷你曲線圖
"""

import customtkinter as ctk
from typing import List
from ..styles import Colors


class MiniChart(ctk.CTkCanvas):
    """迷你曲線圖 - 用於顯示回測權益曲線（可點擊）"""

    def __init__(
        self,
        master,
        width: int = 120,
        height: int = 40,
        bg_color: str = None,  # 預設使用 Colors.BG_TERTIARY
        clickable: bool = False,
        on_click: callable = None,
        **kwargs
    ):
        if bg_color is None:
            bg_color = Colors.BG_TERTIARY
        super().__init__(
            master,
            width=width,
            height=height,
            bg=bg_color,
            highlightthickness=0,
            cursor="hand2" if clickable else "",
            **kwargs
        )
        self.width = width
        self.height = height
        self.bg_color = bg_color
        self.data = []
        self.clickable = clickable
        self.on_click = on_click

        # 綁定點擊事件
        if clickable and on_click:
            self.bind("<Button-1>", lambda e: on_click())

    def set_data(self, data: List[float]):
        """設置數據並繪製曲線"""
        self.data = data
        self._draw()

    def _draw(self):
        """繪製曲線"""
        self.delete("all")

        if not self.data or len(self.data) < 2:
            # 無數據時顯示占位線
            self.create_line(
                0, self.height // 2,
                self.width, self.height // 2,
                fill=Colors.TEXT_MUTED,
                dash=(2, 2)
            )
            return

        # 判斷趨勢顏色（黑白風格）
        is_positive = self.data[-1] >= self.data[0]
        if is_positive:
            line_color = Colors.GREEN
            fill_color = Colors.FILL_POSITIVE
        else:
            line_color = Colors.RED
            fill_color = Colors.FILL_NEGATIVE

        # 正規化數據
        min_val = min(self.data)
        max_val = max(self.data)
        val_range = max_val - min_val if max_val != min_val else 1

        padding = 4
        chart_height = self.height - padding * 2
        chart_width = self.width - padding * 2

        # 計算點座標
        points = []
        for i, val in enumerate(self.data):
            x = padding + (i / (len(self.data) - 1)) * chart_width
            y = padding + (1 - (val - min_val) / val_range) * chart_height
            points.append((x, y))

        # 繪製填充區域
        fill_points = [(padding, self.height - padding)]
        fill_points.extend(points)
        fill_points.append((self.width - padding, self.height - padding))

        self.create_polygon(
            *[coord for point in fill_points for coord in point],
            fill=fill_color,
            outline=""
        )

        # 繪製曲線
        if len(points) >= 2:
            flat_points = [coord for point in points for coord in point]
            self.create_line(
                *flat_points,
                fill=line_color,
                width=2,
                smooth=True
            )

        # 繪製終點標記
        end_x, end_y = points[-1]
        self.create_oval(
            end_x - 3, end_y - 3,
            end_x + 3, end_y + 3,
            fill=line_color,
            outline=""
        )
