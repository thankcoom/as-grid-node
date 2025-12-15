"""
選幣頁面
"""

import asyncio
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional, TYPE_CHECKING

import customtkinter as ctk

from ..styles import Colors
from ..components import Card, MiniChart
from ..dialogs import (
    ConfirmDialog, AddFromCoinSelectDialog, OptimizeDialog,
    RotationExecuteConfirmDialog, RotationConfirmDialog, RotationHistoryDialog
)

if TYPE_CHECKING:
    from gui.app import ASGridApp

class CoinSelectionPage(ctk.CTkFrame):
    """
    選幣評分儀表板

    功能:
    - 顯示所有候選幣種的評分和排名
    - 即時更新評分數據
    - 顯示評分詳情和趨勢
    """

    # 預設候選幣種 (MATIC 已改名為 POL)
    DEFAULT_SYMBOLS = [
        "XRP/USDC:USDC", "DOGE/USDC:USDC", "ETH/USDC:USDC", "BTC/USDC:USDC",
        "SOL/USDC:USDC", "ADA/USDC:USDC", "POL/USDC:USDC", "LINK/USDC:USDC"
    ]

    def __init__(self, master, app: "ASGridApp"):
        super().__init__(master, fg_color=Colors.BG_PRIMARY)
        self.app = app
        self.rankings = []
        self.is_loading = False
        self.selected_symbol = None

        # 輪動相關
        self.rotator = None
        self.tracker = None
        self._init_rotation_system()

        self._create_ui()

    def _init_rotation_system(self):
        """初始化輪動系統"""
        try:
            from coin_selection import CoinScorer, CoinRanker, CoinRotator, RotationTracker
            scorer = CoinScorer()
            ranker = CoinRanker(scorer)
            self.rotator = CoinRotator(ranker, on_rotation_signal=self._on_rotation_signal)
            self.tracker = RotationTracker()
        except Exception as e:
            print(f"初始化輪動系統失敗: {e}")

    def _on_rotation_signal(self, signal):
        """輪動信號回調"""
        # 在主執行緒中顯示對話框
        self.after(0, lambda: self._show_rotation_dialog(signal))

    def _create_ui(self):
        # 可滾動區域
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        # 標題
        header_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            header_frame,
            text="選幣評分系統",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(side="left")

        # 掃描全部按鈕 (動態獲取交易對)
        self.scan_button = ctk.CTkButton(
            header_frame,
            text="🔍 掃描全部",
            width=100,
            height=32,
            fg_color=Colors.ACCENT,
            hover_color=Colors.GREEN_DARK,
            text_color=Colors.BG_PRIMARY,
            command=self._scan_all_symbols
        )
        self.scan_button.pack(side="right")

        # 刷新按鈕
        self.refresh_button = ctk.CTkButton(
            header_frame,
            text="刷新排名",
            width=100,
            height=32,
            fg_color=Colors.BG_TERTIARY,
            hover_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY,
            command=self._refresh_rankings
        )
        self.refresh_button.pack(side="right", padx=(0, 8))

        # 輪動歷史按鈕
        ctk.CTkButton(
            header_frame,
            text="輪動歷史",
            width=80,
            height=32,
            fg_color="transparent",
            hover_color=Colors.BORDER,
            text_color=Colors.TEXT_MUTED,
            border_width=1,
            border_color=Colors.BORDER,
            command=self._show_rotation_history
        ).pack(side="right", padx=(0, 8))

        # 檢查輪動按鈕
        self.check_rotation_button = ctk.CTkButton(
            header_frame,
            text="檢查輪動",
            width=80,
            height=32,
            fg_color=Colors.GREEN,
            hover_color=Colors.GREEN_DARK,
            text_color=Colors.BG_PRIMARY,
            command=self._check_rotation
        )
        self.check_rotation_button.pack(side="right", padx=(0, 8))

        # 強制刷新 (忽略快取)
        self.force_refresh_button = ctk.CTkButton(
            header_frame,
            text="強制刷新",
            width=80,
            height=32,
            fg_color="transparent",
            hover_color=Colors.BORDER,
            text_color=Colors.TEXT_MUTED,
            border_width=1,
            border_color=Colors.BORDER,
            command=lambda: self._refresh_rankings(force=True)
        )
        self.force_refresh_button.pack(side="right", padx=(0, 8))

        # 快取間隔選擇
        self.cache_var = ctk.StringVar(value="15")
        cache_menu = ctk.CTkOptionMenu(
            header_frame,
            values=["1", "5", "15", "30"],
            variable=self.cache_var,
            width=70,
            height=32,
            fg_color=Colors.BG_TERTIARY,
            button_color=Colors.BG_TERTIARY,
            button_hover_color=Colors.BORDER,
            dropdown_fg_color=Colors.BG_SECONDARY,
            command=self._on_cache_interval_change
        )
        cache_menu.pack(side="right", padx=(0, 4))

        ctk.CTkLabel(
            header_frame,
            text="快取(分):",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED
        ).pack(side="right", padx=(0, 4))

        # 狀態標籤
        self.status_label = ctk.CTkLabel(
            header_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_MUTED
        )
        self.status_label.pack(side="right", padx=16)

        # 評分說明卡片
        info_card = Card(scroll, title="評分說明")
        info_card.pack(fill="x", pady=(0, 16))

        info_text = (
            "評分權重: 波動率(15%) + 流動性(20%) + 均值回歸(40%) + 動量(15%) + 穩定性(10%)\n"
            "最佳幣種: 高均值回歸 (H<0.5, ADF p<0.05)、波動率 2-5%、流動性穩定 (CV<0.5)、低趨勢 (ADX<25)"
        )
        ctk.CTkLabel(
            info_card,
            text=info_text,
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_SECONDARY,
            justify="left"
        ).pack(padx=16, pady=8, anchor="w")

        # 排名表格卡片
        ranking_card = Card(scroll, title="幣種評分排名")
        ranking_card.pack(fill="x", pady=(0, 16))

        # 排序選擇器
        sort_frame = ctk.CTkFrame(ranking_card, fg_color="transparent")
        sort_frame.pack(fill="x", padx=16, pady=(8, 4))

        ctk.CTkLabel(
            sort_frame,
            text="排序方式:",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED
        ).pack(side="left")

        self.sort_var = ctk.StringVar(value="適合度")
        self.sort_menu = ctk.CTkOptionMenu(
            sort_frame,
            values=["適合度", "總分", "振幅", "成交量", "幣價", "趨勢"],
            variable=self.sort_var,
            width=90,
            height=28,
            fg_color=Colors.BG_TERTIARY,
            button_color=Colors.BG_TERTIARY,
            button_hover_color=Colors.BORDER,
            dropdown_fg_color=Colors.BG_SECONDARY,
            command=self._on_sort_change
        )
        self.sort_menu.pack(side="left", padx=(8, 16))

        # 排序方向
        self.sort_desc_var = ctk.BooleanVar(value=True)
        self.sort_order_btn = ctk.CTkButton(
            sort_frame,
            text="↓ 降序",
            width=70,
            height=28,
            fg_color=Colors.BG_TERTIARY,
            hover_color=Colors.BORDER,
            text_color=Colors.TEXT_SECONDARY,
            command=self._toggle_sort_order
        )
        self.sort_order_btn.pack(side="left")

        # 結果數量
        self.result_count_label = ctk.CTkLabel(
            sort_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED
        )
        self.result_count_label.pack(side="right")

        # 表格標題
        header_row = ctk.CTkFrame(ranking_card, fg_color=Colors.BG_TERTIARY, corner_radius=4)
        header_row.pack(fill="x", padx=16, pady=(8, 4))

        columns = [
            ("排名", 60), ("幣種", 80), ("總分", 60),
            ("振幅", 70), ("趨勢", 70), ("成交量", 90), ("幣價", 90), ("建議", 70)
        ]
        for col_name, width in columns:
            ctk.CTkLabel(
                header_row,
                text=col_name,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=Colors.TEXT_SECONDARY,
                width=width
            ).pack(side="left", padx=4, pady=6)

        # 表格內容區域
        self.table_frame = ctk.CTkFrame(ranking_card, fg_color="transparent")
        self.table_frame.pack(fill="x", padx=16, pady=(0, 8))

        # 初始提示
        self.empty_label = ctk.CTkLabel(
            self.table_frame,
            text="點擊「刷新排名」獲取最新評分",
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_MUTED
        )
        self.empty_label.pack(pady=20)

        # 評分詳情卡片
        self.detail_card = Card(scroll, title="評分詳情")
        self.detail_card.pack(fill="x", pady=(0, 16))

        self.detail_content = ctk.CTkFrame(self.detail_card, fg_color="transparent")
        self.detail_content.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(
            self.detail_content,
            text="選擇幣種查看詳細評分指標",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_MUTED
        ).pack(pady=10)

    def _on_sort_change(self, _value: str):
        """排序方式變更"""
        if self.rankings:
            self._sort_and_render_rankings()

    def _toggle_sort_order(self):
        """切換排序方向"""
        self.sort_desc_var.set(not self.sort_desc_var.get())
        if self.sort_desc_var.get():
            self.sort_order_btn.configure(text="↓ 降序")
        else:
            self.sort_order_btn.configure(text="↑ 升序")

        if self.rankings:
            self._sort_and_render_rankings()

    def _sort_and_render_rankings(self):
        """根據選擇的排序方式重新排序並渲染"""
        if not self.rankings:
            return

        sort_key = self.sort_var.get()
        reverse = self.sort_desc_var.get()

        # 定義排序鍵
        def get_sort_value(rank):
            amp_stats = getattr(rank, '_amplitude_stats', None)
            if sort_key == "適合度":
                return amp_stats.grid_suitability if amp_stats else 0
            elif sort_key == "總分":
                return rank.score.final_score
            elif sort_key == "振幅":
                return amp_stats.avg_amplitude if amp_stats else 0
            elif sort_key == "成交量":
                return amp_stats.volume_24h if amp_stats else rank.score.volume_24h
            elif sort_key == "幣價":
                return amp_stats.last_price if amp_stats else 0
            elif sort_key == "趨勢":
                # 趨勢用絕對值，值越小越適合網格
                # 升序: 小→大 (最適合的在前)
                # 降序: 大→小 (最不適合的在前)
                return abs(amp_stats.total_change) if amp_stats else 100
            return 0

        # 排序
        sorted_rankings = sorted(self.rankings, key=get_sort_value, reverse=reverse)

        # 重新編號
        for i, rank in enumerate(sorted_rankings, 1):
            rank.rank = i

        # 渲染
        self._render_rankings_table(sorted_rankings)

    def _on_cache_interval_change(self, value: str):
        """快取間隔變更"""
        try:
            from coin_selection import set_cache_ttl
            minutes = int(value)
            set_cache_ttl(minutes)
            self.status_label.configure(text=f"快取時間已設為 {minutes} 分鐘")
        except Exception as e:
            print(f"設置快取間隔失敗: {e}")

    def _scan_all_symbols(self):
        """
        掃描交易所全部合約交易對，進行振幅篩選

        參考 FMZ 策略:
        - 振幅 = (最高價 - 最低價) / 開盤價 × 100%
        - 篩選高振幅、低趨勢的幣種
        """
        if self.is_loading:
            return

        self.is_loading = True
        self.scan_button.configure(text="掃描中...", state="disabled")
        self.refresh_button.configure(state="disabled")
        self.status_label.configure(text="正在掃描全部交易對...")

        import time
        start_time = time.time()

        def do_scan():
            import asyncio
            import ccxt.async_support as ccxt_async

            async def scan():
                # 創建新的交易所連接 (避免與主連接衝突)
                exchange = None
                try:
                    # 檢查交易引擎配置
                    if not hasattr(self.app, 'engine') or not self.app.engine:
                        return None, "交易引擎未初始化", 0

                    engine = self.app.engine
                    if not getattr(engine, 'is_connected', False):
                        return None, "交易所未連接，請先在交易控制台連接", 0

                    # 從引擎獲取 API 配置
                    api_key = getattr(engine, 'api_key', None)
                    api_secret = getattr(engine, 'api_secret', None)

                    if not api_key or not api_secret:
                        # 嘗試從配置獲取
                        if hasattr(engine, 'config'):
                            api_key = getattr(engine.config, 'api_key', None)
                            api_secret = getattr(engine.config, 'api_secret', None)

                    # 創建獨立的交易所連接用於掃描 (Bitget 版本)
                    # 從引擎獲取 passphrase (Bitget 需要)
                    passphrase = getattr(engine, 'passphrase', None) or getattr(engine, '_passphrase', None)
                    if not passphrase and hasattr(engine, 'config'):
                        passphrase = getattr(engine.config, 'passphrase', None)

                    exchange = ccxt_async.bitget({
                        'apiKey': api_key,
                        'secret': api_secret,
                        'password': passphrase,  # Bitget 需要 passphrase
                        'enableRateLimit': True,
                        'options': {'defaultType': 'swap'}
                    })

                    # 導入掃描模組
                    from coin_selection import SymbolScanner, CoinScorer, CoinRanker

                    # Step 1: 掃描並振幅篩選 (USDC + USDT)
                    scanner = SymbolScanner({
                        'min_amplitude': 3.0,      # 最低振幅 3%
                        'max_amplitude': 15.0,     # 最高振幅 15%
                        'max_total_change': 50.0,  # 累計漲跌幅 < 50%
                        'min_volume_24h': 5_000_000,  # 最低交易量 $5M
                    })

                    # 更新狀態
                    self.after(0, lambda: self.status_label.configure(
                        text="掃描 USDC 交易對中..."
                    ))

                    # 掃描 USDC
                    usdc_results = await scanner.scan_with_amplitude(
                        exchange,
                        quote_currency='USDC',
                        top_n=15
                    )

                    # 更新狀態
                    self.after(0, lambda: self.status_label.configure(
                        text="掃描 USDT 交易對中..."
                    ))

                    # 掃描 USDT
                    usdt_results = await scanner.scan_with_amplitude(
                        exchange,
                        quote_currency='USDT',
                        top_n=15
                    )

                    # 合併結果 (去重，優先 USDC)
                    seen_bases = set()
                    scan_results = []

                    # 先加入 USDC (優先)
                    for sym, stats in usdc_results:
                        if sym.base not in seen_bases:
                            seen_bases.add(sym.base)
                            scan_results.append((sym, stats))

                    # 再加入 USDT (補充)
                    for sym, stats in usdt_results:
                        if sym.base not in seen_bases:
                            seen_bases.add(sym.base)
                            scan_results.append((sym, stats))

                    # 按適合度重新排序，取 top 20
                    scan_results.sort(key=lambda x: x[1].grid_suitability, reverse=True)
                    scan_results = scan_results[:20]

                    logging.info(f"合併結果: USDC {len(usdc_results)} + USDT {len(usdt_results)} = {len(scan_results)} 個候選")

                    if not scan_results:
                        return None, "未找到符合條件的交易對", 0

                    # Step 2: 對候選進行評分
                    self.after(0, lambda: self.status_label.configure(
                        text=f"找到 {len(scan_results)} 個候選，正在評分..."
                    ))

                    symbols = [sym.ccxt_symbol for sym, _ in scan_results]
                    scorer = CoinScorer()
                    ranker = CoinRanker(scorer)

                    rankings = await ranker.get_rankings(
                        symbols,
                        exchange,
                        force_refresh=True
                    )

                    # 附加振幅數據到結果
                    amp_data = {sym.ccxt_symbol: stats for sym, stats in scan_results}
                    for rank in rankings:
                        if rank.symbol in amp_data:
                            stats = amp_data[rank.symbol]
                            # 將振幅數據附加到 rank
                            rank._amplitude_stats = stats

                    elapsed = time.time() - start_time
                    return rankings, None, elapsed

                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    elapsed = time.time() - start_time
                    return None, str(e), elapsed
                finally:
                    # 確保關閉交易所連接
                    if exchange:
                        try:
                            await exchange.close()
                        except Exception:
                            pass

            # 創建新的事件循環
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(scan())
            finally:
                try:
                    loop.close()
                except Exception:
                    pass

        def on_complete():
            try:
                rankings, error, elapsed = do_scan()
                self.after(0, lambda: self._update_scan_ui(rankings, error, elapsed))
            except Exception as ex:
                error_msg = str(ex)
                self.after(0, lambda err=error_msg: self._update_scan_ui(None, err, 0))

        import threading
        thread = threading.Thread(target=on_complete, daemon=True)
        thread.start()

    def _update_scan_ui(self, rankings, error, elapsed: float = 0):
        """更新掃描結果 UI"""
        self.is_loading = False
        self.scan_button.configure(text="🔍 掃描全部", state="normal")
        self.refresh_button.configure(state="normal")

        if error:
            self.status_label.configure(text=f"掃描失敗: {error}", text_color=Colors.RED)
            return

        if not rankings:
            self.status_label.configure(text="未找到符合條件的交易對", text_color=Colors.YELLOW)
            return

        # 更新狀態
        self.status_label.configure(
            text=f"掃描完成！找到 {len(rankings)} 個候選 ({elapsed:.1f}s)",
            text_color=Colors.GREEN
        )

        # 更新 DEFAULT_SYMBOLS
        self.DEFAULT_SYMBOLS = [r.symbol for r in rankings]

        # 儲存 rankings
        self.rankings = rankings

        # 更新表格 (帶振幅數據)
        self._render_rankings_table(rankings)

    def _render_rankings_table(self, rankings):
        """
        渲染掃描結果表格 (含振幅數據)

        顯示欄位: 排名、幣種、總分、振幅、趨勢、成交量、幣價、建議
        """
        # 清空表格
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        if not rankings:
            ctk.CTkLabel(
                self.table_frame,
                text="無掃描結果",
                font=ctk.CTkFont(size=14),
                text_color=Colors.TEXT_MUTED
            ).pack(pady=20)
            self.result_count_label.configure(text="")
            return

        # 更新結果數量
        self.result_count_label.configure(text=f"共 {len(rankings)} 個候選")

        # 填充排名數據 (含振幅)
        for rank in rankings:
            is_best = (rank.rank == 1)

            if is_best:
                row_bg = Colors.FILL_SELECTED  # 選中行背景（黑白風格）
            elif rank.rank % 2 == 0:
                row_bg = Colors.BG_TERTIARY
            else:
                row_bg = "transparent"

            row = ctk.CTkFrame(
                self.table_frame,
                fg_color=row_bg,
                corner_radius=4,
                cursor="hand2"
            )
            row.pack(fill="x", pady=1)
            row.bind("<Button-1>", lambda e, r=rank: self._show_scan_detail(r))

            # 排名
            rank_color = Colors.GREEN if is_best else Colors.TEXT_PRIMARY
            ctk.CTkLabel(
                row, text=f"#{rank.rank}", width=60,
                font=ctk.CTkFont(size=12, weight="bold" if is_best else "normal"),
                text_color=rank_color
            ).pack(side="left", padx=4, pady=6)

            # 幣種
            symbol_short = rank.symbol.split('/')[0]
            ctk.CTkLabel(
                row, text=symbol_short, width=80,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=Colors.GREEN if is_best else Colors.TEXT_PRIMARY
            ).pack(side="left", padx=4)

            # 總分
            score_color = Colors.GREEN if rank.score.final_score >= 70 else Colors.TEXT_SECONDARY
            ctk.CTkLabel(
                row, text=f"{rank.score.final_score:.1f}", width=60,
                font=ctk.CTkFont(size=12, weight="bold" if is_best else "normal"),
                text_color=score_color
            ).pack(side="left", padx=4)

            # 振幅 (從 _amplitude_stats 取得)
            amp_stats = getattr(rank, '_amplitude_stats', None)
            if amp_stats:
                amp_text = f"{amp_stats.avg_amplitude:.1f}%"
                # 振幅越高越適合網格
                if amp_stats.avg_amplitude >= 5:
                    amp_color = Colors.GREEN
                elif amp_stats.avg_amplitude >= 3:
                    amp_color = Colors.YELLOW
                else:
                    amp_color = Colors.TEXT_MUTED
            else:
                amp_text = "—"
                amp_color = Colors.TEXT_MUTED

            ctk.CTkLabel(
                row, text=amp_text, width=70,
                font=ctk.CTkFont(size=12),
                text_color=amp_color
            ).pack(side="left", padx=4)

            # 趨勢 (累計漲跌幅)
            if amp_stats:
                change = amp_stats.total_change
                trend_text = f"{change:+.1f}%"
                # 趨勢越接近 0 越適合網格
                if abs(change) < 20:
                    trend_color = Colors.GREEN
                elif abs(change) < 40:
                    trend_color = Colors.YELLOW
                else:
                    trend_color = Colors.RED
            else:
                trend_text = "—"
                trend_color = Colors.TEXT_MUTED

            ctk.CTkLabel(
                row, text=trend_text, width=70,
                font=ctk.CTkFont(size=12),
                text_color=trend_color
            ).pack(side="left", padx=4)

            # 交易量
            if amp_stats:
                vol = amp_stats.volume_24h
                if vol >= 1e9:
                    vol_text = f"${vol/1e9:.1f}B"
                elif vol >= 1e6:
                    vol_text = f"${vol/1e6:.1f}M"
                else:
                    vol_text = f"${vol/1e3:.0f}K"
            else:
                vol_text = f"${rank.score.volume_24h/1e6:.1f}M"

            ctk.CTkLabel(
                row, text=vol_text, width=90,
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_SECONDARY
            ).pack(side="left", padx=4)

            # 幣價
            if amp_stats and amp_stats.last_price:
                price = amp_stats.last_price
                if price >= 1000:
                    price_text = f"${price:,.0f}"
                elif price >= 1:
                    price_text = f"${price:.2f}"
                else:
                    price_text = f"${price:.4f}"
            else:
                price_text = "—"

            ctk.CTkLabel(
                row, text=price_text, width=90,
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_SECONDARY
            ).pack(side="left", padx=4)

            # 建議
            action_colors = {
                "HOLD": Colors.GREEN,
                "WATCH": Colors.YELLOW,
                "MONITOR": Colors.TEXT_SECONDARY,
                "AVOID": Colors.RED
            }
            action_color = action_colors.get(rank.action.value, Colors.TEXT_MUTED)
            ctk.CTkLabel(
                row, text=rank.action.value, width=70,
                font=ctk.CTkFont(size=11),
                text_color=action_color
            ).pack(side="left", padx=4)

            # 綁定所有子元件的點擊事件
            for child in row.winfo_children():
                child.bind("<Button-1>", lambda e, r=rank: self._show_scan_detail(r))

    def _show_scan_detail(self, rank):
        """顯示掃描結果詳情 (含振幅數據)"""
        self.selected_symbol = rank.symbol

        # 清空詳情區域
        for widget in self.detail_content.winfo_children():
            widget.destroy()

        # 幣種標題
        header = ctk.CTkFrame(self.detail_content, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        symbol_short = rank.symbol.split('/')[0]
        ctk.CTkLabel(
            header,
            text=f"{symbol_short} 掃描詳情",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text=f"總分: {rank.score.final_score:.1f}",
            font=ctk.CTkFont(size=14),
            text_color=Colors.GREEN if rank.score.final_score >= 70 else Colors.TEXT_SECONDARY
        ).pack(side="right")

        # 振幅數據
        amp_stats = getattr(rank, '_amplitude_stats', None)
        if amp_stats:
            amp_frame = ctk.CTkFrame(self.detail_content, fg_color=Colors.BG_TERTIARY, corner_radius=4)
            amp_frame.pack(fill="x", pady=(0, 8))

            ctk.CTkLabel(
                amp_frame,
                text="振幅分析",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=Colors.TEXT_PRIMARY
            ).pack(side="left", padx=8, pady=6)

            amp_details = f"平均: {amp_stats.avg_amplitude:.1f}% | 最大: {amp_stats.max_amplitude:.1f}% | 累計漲跌: {amp_stats.total_change:+.1f}%"
            ctk.CTkLabel(
                amp_frame,
                text=amp_details,
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_SECONDARY
            ).pack(side="right", padx=8)

            # 網格適合度
            suitability_frame = ctk.CTkFrame(self.detail_content, fg_color=Colors.BG_TERTIARY, corner_radius=4)
            suitability_frame.pack(fill="x", pady=(0, 8))

            suitability = amp_stats.grid_suitability
            if suitability >= 70:
                suit_color = Colors.GREEN
                suit_text = "非常適合"
            elif suitability >= 50:
                suit_color = Colors.YELLOW
                suit_text = "適合"
            else:
                suit_color = Colors.RED
                suit_text = "不太適合"

            ctk.CTkLabel(
                suitability_frame,
                text=f"網格適合度: {suitability:.0f} ({suit_text})",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=suit_color
            ).pack(side="left", padx=8, pady=6)

        # 詳細指標
        details = [
            ("波動率評分", f"{rank.score.volatility_score:.1f}", f"ATR: {rank.score.atr_pct*100:.2f}%"),
            ("流動性評分", f"{rank.score.liquidity_score:.1f}", f"24h量: ${rank.score.volume_24h/1e6:.1f}M"),
            ("均值回歸評分", f"{rank.score.mean_revert_score:.1f}", f"Hurst: {rank.score.hurst_exponent:.3f}"),
            ("動量評分", f"{rank.score.momentum_score:.1f}", f"ADX: {rank.score.adx:.1f}"),
        ]

        for label, score, detail in details:
            row = ctk.CTkFrame(self.detail_content, fg_color=Colors.BG_TERTIARY, corner_radius=4)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row, text=label, width=120,
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_SECONDARY
            ).pack(side="left", padx=8, pady=6)

            ctk.CTkLabel(
                row, text=score, width=60,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=Colors.TEXT_PRIMARY
            ).pack(side="left", padx=8)

            ctk.CTkLabel(
                row, text=detail,
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED
            ).pack(side="right", padx=8)

        # 操作按鈕區域
        btn_frame = ctk.CTkFrame(self.detail_content, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(16, 0))

        # 捕獲當前 rank（避免閉包問題）
        current_symbol = rank.symbol
        current_rank = rank

        ctk.CTkButton(
            btn_frame,
            text="+ 加入交易對",
            width=130,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=Colors.ACCENT,
            hover_color=Colors.GREEN_DARK,
            text_color=Colors.BG_PRIMARY,
            command=lambda s=current_symbol, r=current_rank: self._add_symbol_from_scan(s, r)
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            btn_frame,
            text="回測 / 優化",
            width=120,
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=Colors.FILL_HIGHLIGHT,
            hover_color=Colors.BORDER_LIGHT,
            text_color=Colors.TEXT_PRIMARY,
            command=lambda s=current_symbol: self._goto_backtest(s)
        ).pack(side="left", padx=4)

    def _add_to_watchlist(self, symbol: str):
        """加入監控列表"""
        if symbol not in self.DEFAULT_SYMBOLS:
            self.DEFAULT_SYMBOLS.append(symbol)
            self.status_label.configure(
                text=f"已加入監控: {symbol.split('/')[0]}",
                text_color=Colors.GREEN
            )

    def _add_symbol_from_scan(self, symbol: str, rank):
        """從掃描結果加入交易對"""
        # 轉換格式: "XRP/USDC:USDC" -> "XRPUSDC"
        raw_symbol = symbol.split('/')[0] + symbol.split('/')[1].split(':')[0]

        # 根據評分建議預設參數
        atr_pct = rank.score.atr_pct

        # 動態計算建議參數
        if atr_pct > 0.04:
            suggested_gs = "0.8%"
            suggested_tp = "0.5%"
        elif atr_pct > 0.025:
            suggested_gs = "0.6%"
            suggested_tp = "0.4%"
        else:
            suggested_gs = "0.4%"
            suggested_tp = "0.3%"

        data = {
            "symbol": raw_symbol,
            "enabled": False,
            "tp": suggested_tp,
            "gs": suggested_gs,
            "qty": 30,
            "leverage": 20
        }

        # 顯示確認對話框
        AddFromCoinSelectDialog(self, data, rank.score)

    def _goto_backtest(self, symbol: str):
        """跳轉到回測/優化頁面並預填參數"""
        # 轉換格式: "XRP/USDC:USDC" -> "XRPUSDC"
        raw_symbol = symbol.split('/')[0] + symbol.split('/')[1].split(':')[0]

        # 準備參數
        params = {
            'symbol': raw_symbol,
            'tp': '0.4',
            'gs': '0.6',
            'qty': '30',
            'leverage': '20'
        }

        # 使用 AppState 系統跳轉並帶入參數
        self.app.show_page("backtest", params=params, action='backtest')

    def _refresh_rankings(self, force: bool = False):
        """
        刷新排名數據

        Args:
            force: 是否強制刷新 (忽略快取)
        """
        if self.is_loading:
            return

        self.is_loading = True
        self.refresh_button.configure(text="載入中...", state="disabled")
        self.force_refresh_button.configure(state="disabled")

        if force:
            self.status_label.configure(text="強制刷新中 (忽略快取)...")
            # 清除快取
            try:
                from coin_selection import clear_cache
                clear_cache()
            except Exception:
                pass
        else:
            self.status_label.configure(text="正在獲取評分數據...")

        # 記錄開始時間
        import time
        start_time = time.time()

        # 在背景執行
        def fetch_rankings():
            import asyncio

            async def do_fetch():
                try:
                    # 檢查是否有交易引擎和交易所連接
                    if not hasattr(self.app, 'engine') or not self.app.engine:
                        return None, "交易引擎未初始化", 0

                    engine = self.app.engine

                    # 檢查是否已連接 (is_connected 標誌)
                    if not getattr(engine, 'is_connected', False):
                        return None, "交易所未連接，請先在交易控制台連接", 0

                    if not hasattr(engine, 'exchange') or not engine.exchange:
                        return None, "交易所連接異常", 0

                    # 導入評分模組
                    from coin_selection import CoinScorer, CoinRanker

                    scorer = CoinScorer()
                    ranker = CoinRanker(scorer)

                    # 獲取排名 (使用快取)
                    rankings = await ranker.get_rankings(
                        self.DEFAULT_SYMBOLS,
                        engine.exchange,
                        force_refresh=force
                    )

                    elapsed = time.time() - start_time
                    return rankings, None, elapsed

                except Exception as e:
                    elapsed = time.time() - start_time
                    return None, str(e), elapsed

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(do_fetch())
            finally:
                loop.close()

        def on_complete():
            rankings, error, elapsed = fetch_rankings()
            self.after(0, lambda: self._update_rankings_ui(rankings, error, elapsed))

        import threading
        thread = threading.Thread(target=on_complete, daemon=True)
        thread.start()

    def _update_rankings_ui(self, rankings, error, elapsed: float = 0):
        """更新排名 UI"""
        self.is_loading = False
        self.refresh_button.configure(text="刷新排名", state="normal")
        self.force_refresh_button.configure(state="normal")

        if error:
            # 清空表格並顯示錯誤
            for widget in self.table_frame.winfo_children():
                widget.destroy()

            # 根據錯誤類型顯示不同提示
            if "未初始化" in error or "未連接" in error:
                error_msg = "請先在「設定」頁面配置 API 並連接交易所"
                hint_msg = "設定 → API 設定 → 儲存 → 連接交易所"
            else:
                error_msg = f"錯誤: {error}"
                hint_msg = "請檢查網路連線或 API 設定"

            ctk.CTkLabel(
                self.table_frame,
                text=error_msg,
                font=ctk.CTkFont(size=14),
                text_color=Colors.RED
            ).pack(pady=(20, 5))

            ctk.CTkLabel(
                self.table_frame,
                text=hint_msg,
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_MUTED
            ).pack(pady=(0, 20))

            self.status_label.configure(text="")
            return

        if not rankings:
            self.status_label.configure(text="無排名數據")
            return

        self.rankings = rankings
        elapsed_text = f" ({elapsed:.1f}s)" if elapsed > 0 else ""
        self.status_label.configure(
            text=f"更新: {rankings[0].score.timestamp.strftime('%H:%M:%S')}{elapsed_text}"
        )

        # 清空表格
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        # 填充排名數據
        for rank in rankings:
            is_best = (rank.rank == 1)  # 第一名為最優

            # 第一名用特殊背景色突出
            if is_best:
                row_bg = Colors.FILL_SELECTED  # 選中行背景（黑白風格）
            elif rank.rank % 2 == 0:
                row_bg = Colors.BG_TERTIARY
            else:
                row_bg = "transparent"

            row = ctk.CTkFrame(
                self.table_frame,
                fg_color=row_bg,
                corner_radius=4,
                cursor="hand2"
            )
            row.pack(fill="x", pady=1)
            row.bind("<Button-1>", lambda e, r=rank: self._show_detail(r))

            # 排名 + 趨勢 (第一名顯示「最優」)
            if is_best:
                rank_text = f"#1 {rank.trend.value} 最優"
                rank_color = Colors.GREEN
            else:
                rank_text = f"{rank.rank:2d} {rank.trend.value}"
                rank_color = Colors.TEXT_PRIMARY

            ctk.CTkLabel(
                row, text=rank_text, width=80,
                font=ctk.CTkFont(size=12, weight="bold" if is_best else "normal"),
                text_color=rank_color
            ).pack(side="left", padx=4, pady=6)

            # 幣種
            symbol_short = rank.symbol.split('/')[0]
            ctk.CTkLabel(
                row, text=symbol_short, width=80,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=Colors.GREEN if is_best else Colors.TEXT_PRIMARY
            ).pack(side="left", padx=4)

            # 總分
            score_color = Colors.GREEN if rank.score.final_score >= 70 else Colors.TEXT_SECONDARY
            ctk.CTkLabel(
                row, text=f"{rank.score.final_score:.1f}", width=70,
                font=ctk.CTkFont(size=12, weight="bold" if is_best else "normal"),
                text_color=score_color
            ).pack(side="left", padx=4)

            # 波動率
            ctk.CTkLabel(
                row, text=f"{rank.score.volatility_score:.0f}", width=70,
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_SECONDARY
            ).pack(side="left", padx=4)

            # 流動性
            ctk.CTkLabel(
                row, text=f"{rank.score.liquidity_score:.0f}", width=70,
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_SECONDARY
            ).pack(side="left", padx=4)

            # 均值回歸
            ctk.CTkLabel(
                row, text=f"{rank.score.mean_revert_score:.0f}", width=80,
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_SECONDARY
            ).pack(side="left", padx=4)

            # 動作
            action_colors = {
                "HOLD": Colors.GREEN,
                "WATCH": Colors.YELLOW,
                "MONITOR": Colors.TEXT_SECONDARY,
                "AVOID": Colors.RED
            }
            action_color = action_colors.get(rank.action.value, Colors.TEXT_MUTED)
            ctk.CTkLabel(
                row, text=rank.action.value, width=80,
                font=ctk.CTkFont(size=11),
                text_color=action_color
            ).pack(side="left", padx=4)

    def _show_detail(self, rank):
        """顯示評分詳情"""
        self.selected_symbol = rank.symbol

        # 清空詳情區域
        for widget in self.detail_content.winfo_children():
            widget.destroy()

        # 幣種標題
        header = ctk.CTkFrame(self.detail_content, fg_color="transparent")
        header.pack(fill="x", pady=(0, 8))

        symbol_short = rank.symbol.split('/')[0]
        ctk.CTkLabel(
            header,
            text=f"{symbol_short} 評分詳情",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(side="left")

        ctk.CTkLabel(
            header,
            text=f"總分: {rank.score.final_score:.1f}",
            font=ctk.CTkFont(size=14),
            text_color=Colors.GREEN if rank.score.final_score >= 70 else Colors.TEXT_SECONDARY
        ).pack(side="right")

        # 詳細指標
        # 安全取得新欄位 (兼容舊版)
        volume_cv = getattr(rank.score, 'volume_cv', 1.0)
        adf_pvalue = getattr(rank.score, 'adf_pvalue', 1.0)

        details = [
            ("波動率評分", f"{rank.score.volatility_score:.1f}", f"ATR: {rank.score.atr_pct*100:.2f}%"),
            ("流動性評分", f"{rank.score.liquidity_score:.1f}", f"24h量: ${rank.score.volume_24h/1e6:.1f}M"),
            ("均值回歸評分", f"{rank.score.mean_revert_score:.1f}", f"Hurst: {rank.score.hurst_exponent:.3f} | ADF p: {adf_pvalue:.3f}"),
            ("動量評分", f"{rank.score.momentum_score:.1f}", f"ADX: {rank.score.adx:.1f}"),
            ("穩定性", "—", f"Volume CV: {volume_cv:.3f}"),
        ]

        for label, score, detail in details:
            row = ctk.CTkFrame(self.detail_content, fg_color=Colors.BG_TERTIARY, corner_radius=4)
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(
                row, text=label, width=120,
                font=ctk.CTkFont(size=12),
                text_color=Colors.TEXT_SECONDARY
            ).pack(side="left", padx=8, pady=6)

            ctk.CTkLabel(
                row, text=score, width=60,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=Colors.TEXT_PRIMARY
            ).pack(side="left", padx=8)

            ctk.CTkLabel(
                row, text=detail,
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED
            ).pack(side="right", padx=8)

        # 建議說明
        action_desc = {
            "HOLD": "適合網格交易，建議持有",
            "WATCH": "表現良好，值得關注",
            "MONITOR": "一般，持續監控",
            "AVOID": "不適合網格策略，建議避免"
        }
        desc = action_desc.get(rank.action.value, "")

        ctk.CTkLabel(
            self.detail_content,
            text=f"建議: {rank.action.value} - {desc}",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_MUTED
        ).pack(pady=(12, 4), anchor="w")

        # 操作按鈕區域
        button_frame = ctk.CTkFrame(self.detail_content, fg_color="transparent")
        button_frame.pack(fill="x", pady=(16, 8))

        # 加入交易對按鈕
        ctk.CTkButton(
            button_frame,
            text="+ 加入交易對",
            font=ctk.CTkFont(size=13),
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            height=36,
            corner_radius=8,
            command=lambda: self._add_to_symbols(rank)
        ).pack(side="left", padx=(0, 8))

        # 開始回測按鈕
        ctk.CTkButton(
            button_frame,
            text="開始回測",
            font=ctk.CTkFont(size=13),
            fg_color=Colors.BG_TERTIARY,
            text_color=Colors.TEXT_PRIMARY,
            hover_color=Colors.BORDER,
            height=36,
            corner_radius=8,
            command=lambda: self._start_backtest(rank)
        ).pack(side="left")

    def _add_to_symbols(self, rank):
        """將選中的幣種加入交易對管理"""
        symbol = rank.symbol

        # 轉換格式: "XRP/USDC:USDC" -> "XRPUSDC"
        raw_symbol = symbol.split('/')[0] + symbol.split('/')[1].split(':')[0]

        # 根據評分建議預設參數
        # 高波動 -> 較大 grid spacing
        # 高均值回歸 -> 較小 take profit
        atr_pct = rank.score.atr_pct

        # 動態計算建議參數
        if atr_pct > 0.04:
            suggested_gs = "0.8%"
            suggested_tp = "0.5%"
        elif atr_pct > 0.025:
            suggested_gs = "0.6%"
            suggested_tp = "0.4%"
        else:
            suggested_gs = "0.4%"
            suggested_tp = "0.3%"

        data = {
            "symbol": raw_symbol,
            "enabled": False,  # 預設停用，需要回測後再啟用
            "tp": suggested_tp,
            "gs": suggested_gs,
            "qty": 30,
            "leverage": 20
        }

        # 顯示確認對話框
        AddFromCoinSelectDialog(self, data, rank.score)

    def _start_backtest(self, rank):
        """跳轉到回測頁面並預填幣種"""
        symbol = rank.symbol

        # 切換到回測頁面
        self.app.show_page("backtest")

        # 嘗試預填交易對
        backtest_page = self.app.pages.get("backtest")
        if backtest_page and hasattr(backtest_page, 'symbol_entry'):
            # 轉換格式
            raw_symbol = symbol.split('/')[0] + symbol.split('/')[1].split(':')[0]
            backtest_page.symbol_entry.delete(0, "end")
            backtest_page.symbol_entry.insert(0, raw_symbol)

    # ========== 輪動功能 (Story 4.2) ==========

    def _check_rotation(self):
        """檢查是否需要輪動"""
        if not self.rotator:
            self.status_label.configure(text="輪動系統未初始化")
            return

        # 獲取當前交易對 (從配置中已啟用的交易對)
        current_symbol = self._get_current_trading_symbol()
        if not current_symbol:
            self.status_label.configure(text="請先在交易對管理頁面啟用至少一個交易對")
            return

        self.check_rotation_button.configure(text="檢查中...", state="disabled")
        self.status_label.configure(text="正在檢查輪動條件...")

        def do_check():
            import asyncio

            async def check():
                try:
                    if not hasattr(self.app, 'engine') or not self.app.engine:
                        return None, "交易引擎未初始化"

                    engine = self.app.engine

                    # 檢查是否已連接
                    if not getattr(engine, 'is_connected', False):
                        return None, "交易所未連接，請先在交易控制台連接"

                    if not hasattr(engine, 'exchange') or not engine.exchange:
                        return None, "交易所連接異常"

                    signal = await self.rotator.check_rotation(
                        current_symbol,
                        engine.exchange,
                        self.DEFAULT_SYMBOLS,
                        force_check=True
                    )
                    return signal, None

                except Exception as e:
                    return None, str(e)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(check())
            finally:
                loop.close()

        def on_complete():
            signal, error = do_check()
            self.after(0, lambda: self._update_rotation_result(signal, error))

        import threading
        thread = threading.Thread(target=on_complete, daemon=True)
        thread.start()

    def _update_rotation_result(self, signal, error):
        """更新輪動檢查結果"""
        self.check_rotation_button.configure(text="檢查輪動", state="normal")

        if error:
            self.status_label.configure(text=f"檢查失敗: {error}")
            return

        if signal:
            self.status_label.configure(text="發現更優幣種，顯示輪動建議...")
            self._show_rotation_dialog(signal)
        else:
            # 檢查輪動狀態
            if self.rotator:
                status = self.rotator.get_status()
                if not status['cooldown_passed']:
                    remaining = status['cooldown_remaining_hours']
                    self.status_label.configure(text=f"冷卻期內，剩餘 {remaining:.1f} 小時")
                elif status['rotations_this_week'] >= status['max_rotations_per_week']:
                    self.status_label.configure(text="本週輪動次數已達上限")
                else:
                    self.status_label.configure(text="當前幣種已是最佳選擇")
            else:
                self.status_label.configure(text="當前幣種已是最佳選擇")

    def _get_current_trading_symbol(self) -> str:
        """獲取當前正在交易的幣種 (從配置中已啟用的交易對)"""
        try:
            from as_terminal_max_bitget import GlobalConfig
            config = GlobalConfig.load()

            # 獲取所有已啟用的交易對
            enabled_symbols = [
                sym_cfg.symbol for sym_cfg in config.symbols.values()
                if sym_cfg.enabled
            ]

            if enabled_symbols:
                # 返回第一個啟用的交易對 (通常只有一個)
                return enabled_symbols[0]

        except Exception:
            pass

        # 備用：嘗試從交易引擎獲取
        if hasattr(self.app, 'engine') and self.app.engine:
            engine = self.app.engine
            if hasattr(engine, 'config') and engine.config:
                for sym_cfg in engine.config.symbols.values():
                    if sym_cfg.enabled:
                        return sym_cfg.symbol

        return None

    def _show_rotation_dialog(self, signal):
        """顯示輪動確認對話框"""
        RotationConfirmDialog(
            self,
            signal,
            on_confirm=self._on_rotation_confirm,
            on_cancel=self._on_rotation_cancel
        )

    def _on_rotation_confirm(self, signal):
        """確認輪動 - 顯示最終確認對話框"""
        # 顯示最終確認對話框（因為這是高風險操作）
        RotationExecuteConfirmDialog(
            self,
            signal=signal,
            on_execute=lambda: self._execute_rotation(signal)
        )

    def _execute_rotation(self, signal):
        """實際執行輪動操作"""
        self.status_label.configure(text=f"執行輪動中: {signal.from_symbol} → {signal.to_symbol}...")

        # 記錄輪動
        if self.rotator:
            self.rotator.record_rotation(signal)

        # 記錄到歷史
        if self.tracker:
            self.tracker.record_from_signal(signal)

        # 在背景執行緒執行實際操作
        def do_rotation():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._execute_rotation_async(signal))
            except Exception as ex:
                self.after(0, lambda e=str(ex): self.status_label.configure(
                    text=f"輪動失敗: {e}"
                ))
            finally:
                loop.close()

        import threading
        threading.Thread(target=do_rotation, daemon=True).start()

    async def _execute_rotation_async(self, signal):
        """異步執行輪動的完整流程"""
        import ccxt.async_support as ccxt
        from as_terminal_max_bitget import GlobalConfig, SymbolConfig, normalize_symbol

        from_symbol = signal.from_symbol  # e.g. "XRPUSDC"
        to_symbol = signal.to_symbol      # e.g. "DOGEUSDC"

        exchange = None
        try:
            # 1. 連接交易所 (Bitget 版本)
            self.after(0, lambda: self.status_label.configure(text="連接 Bitget 交易所..."))

            exchange = ccxt.bitget({
                'apiKey': self.app.api_key,
                'secret': self.app.api_secret,
                'password': getattr(self.app, 'passphrase', ''),  # Bitget 需要 passphrase
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}  # Bitget 永續合約
            })

            # 2. 平倉 from_symbol 的所有持倉
            self.after(0, lambda: self.status_label.configure(
                text=f"平倉 {from_symbol} 持倉..."
            ))

            positions = await exchange.fetch_positions()
            closed_count = 0

            for pos in positions:
                # 檢查是否是要平倉的幣種
                pos_symbol = pos.get('symbol', '').replace('/', '').replace(':USDC', '').replace(':USDT', '')
                if pos_symbol == from_symbol and pos['contracts'] > 0:
                    side = "sell" if pos['side'] == 'long' else "buy"
                    quantity = pos['contracts']

                    await exchange.create_market_order(
                        symbol=pos['symbol'],
                        side=side,
                        amount=quantity,
                        params={'reduceOnly': True}
                    )
                    closed_count += 1
                    self.after(0, lambda q=quantity: self.status_label.configure(
                        text=f"已平倉 {from_symbol}: {q}"
                    ))

            # 3. 取消 from_symbol 的所有掛單
            self.after(0, lambda: self.status_label.configure(
                text=f"取消 {from_symbol} 掛單..."
            ))

            try:
                # 轉換為 CCXT 格式
                ccxt_from = from_symbol.replace('USDC', '/USDC:USDC').replace('USDT', '/USDT:USDT')
                open_orders = await exchange.fetch_open_orders(ccxt_from)
                for order in open_orders:
                    await exchange.cancel_order(order['id'], ccxt_from)
                    self.after(0, lambda: self.status_label.configure(
                        text=f"已取消掛單: {order['id'][:8]}..."
                    ))
            except Exception as cancel_err:
                # 取消掛單失敗不阻止流程
                print(f"取消掛單時出錯 (可忽略): {cancel_err}")

            # 4. 更新配置：停用舊幣，啟用新幣
            self.after(0, lambda: self.status_label.configure(text="更新配置..."))

            config = GlobalConfig.load(force_reload=True)

            # 停用 from_symbol
            if from_symbol in config.symbols:
                config.symbols[from_symbol].enabled = False

            # 確保 to_symbol 存在並啟用
            if to_symbol in config.symbols:
                config.symbols[to_symbol].enabled = True
            else:
                # 新增 to_symbol，使用 from_symbol 的參數作為模板
                template = config.symbols.get(from_symbol)
                if template:
                    raw, ccxt_sym, _, _ = normalize_symbol(to_symbol)
                    config.symbols[to_symbol] = SymbolConfig(
                        symbol=raw or to_symbol,
                        ccxt_symbol=ccxt_sym or f"{to_symbol[:len(to_symbol)-4]}/USDC:USDC",
                        enabled=True,
                        take_profit_spacing=template.take_profit_spacing,
                        grid_spacing=template.grid_spacing,
                        initial_quantity=template.initial_quantity,
                        leverage=template.leverage,
                        limit_multiplier=template.limit_multiplier,
                        threshold_multiplier=template.threshold_multiplier
                    )

            config.save()

            # 5. 完成
            self.after(0, lambda: self.status_label.configure(
                text=f"輪動完成: {from_symbol} → {to_symbol} (平倉 {closed_count} 筆)"
            ))

            # 通知用戶需要重啟交易引擎
            self.after(100, lambda: self._show_rotation_complete_dialog(from_symbol, to_symbol))

        except Exception as err:
            error_msg = str(err)
            self.after(0, lambda msg=error_msg: self.status_label.configure(
                text=f"輪動失敗: {msg}"
            ))
            raise
        finally:
            if exchange:
                await exchange.close()

    def _show_rotation_complete_dialog(self, from_symbol: str, to_symbol: str):
        """顯示輪動完成對話框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("輪動完成")
        dialog.geometry("400x200")
        dialog.resizable(False, False)
        dialog.configure(fg_color=Colors.BG_PRIMARY)
        dialog.transient(self)
        dialog.grab_set()

        # 內容
        ctk.CTkLabel(
            dialog,
            text="✓ 輪動執行完成",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(24, 12))

        ctk.CTkLabel(
            dialog,
            text=f"{from_symbol} → {to_symbol}",
            font=ctk.CTkFont(size=14),
            text_color=Colors.TEXT_SECONDARY
        ).pack(pady=4)

        ctk.CTkLabel(
            dialog,
            text="配置已更新。如果交易引擎正在運行，\n建議重啟以載入新配置。",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_MUTED
        ).pack(pady=12)

        # 按鈕
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=24, pady=16)

        ctk.CTkButton(
            btn_frame,
            text="確定",
            width=120,
            fg_color=Colors.STATUS_ON,
            hover_color=Colors.TEXT_PRIMARY,
            text_color=Colors.BG_PRIMARY,
            command=dialog.destroy
        ).pack(side="right")

    def _on_rotation_cancel(self, signal):
        """取消輪動"""
        self.status_label.configure(text="輪動已取消")

        # 記錄拒絕
        if self.rotator:
            self.rotator.record_rejection(signal)

    def _show_rotation_history(self):
        """顯示輪動歷史對話框"""
        RotationHistoryDialog(self, tracker=self.tracker)
