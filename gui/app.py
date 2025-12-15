#!/usr/bin/env python3
"""
AS 網格交易系統 - 現代化 GUI 介面 (Bitget 版本)
==============================================

設計風格：
- 黑白極簡風格（Web3 / v0.dev 風格）
- 深色主題護眼
- 清晰的數據展示
- 微動畫反饋

功能模組：
1. 交易控制台
2. 交易對管理
3. 回測/優化
4. MAX 增強設定
5. 學習模組設定
6. 風險管理
7. API 設定

Bitget 版本特點：
- 使用 Bitget 交易所 API
- 支持 passphrase 認證
- WebSocket 使用 Bitget 格式
"""

import customtkinter as ctk
from typing import Optional, Dict, Callable
import threading
from datetime import datetime
from pathlib import Path
import sys
import os
import warnings
import logging

# 抑制 asyncio 的 Task 銷毀警告 (正常關閉時可能出現)
warnings.filterwarnings("ignore", message="coroutine.*was never awaited")

# 添加專案根目錄到 path（提前處理，以便載入 core 模組）
# PyInstaller 打包環境檢測
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # PyInstaller 打包：_MEIPASS 是臨時解壓目錄
    _PROJECT_ROOT = Path(sys._MEIPASS)
    # 修正工作目錄：雙擊 .app 時工作目錄是 /，需要切換到正確位置
    os.chdir(_PROJECT_ROOT)
else:
    # 開發環境
    _PROJECT_ROOT = Path(__file__).parent.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# 使用改進的日誌系統（帶輪轉）
try:
    from core.logging_setup import setup_logging, get_logger
    from core.error_handler import CCXTErrorHandler, handle_ccxt_error
    from core.constants import Constants
    logger = setup_logging(
        name="as_grid_gui",
        level="INFO",
        log_dir="log",
        console_output=True,
        file_output=True
    )
    CORE_AVAILABLE = True
except ImportError:
    # Fallback: 使用基本日誌
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%H:%M:%S'
    )
    logger = logging.getLogger("as_grid_gui")
    CORE_AVAILABLE = False
    CCXTErrorHandler = None
    handle_ccxt_error = None
    Constants = None

# 添加 asBack 路徑（供 pages 模組使用）
sys.path.insert(0, str(_PROJECT_ROOT / "asBack"))

# ═══════════════════════════════════════════════════════════════════════════
# 導入抽離的模組
# ═══════════════════════════════════════════════════════════════════════════
from gui.styles import Colors
from gui.components import NavButton, StepIndicator, StatusIndicator
from gui.dialogs import SetupDialog, UnlockDialog, MigrationDialog
from gui.pages import (
    TradingPage,
    SymbolsPage,
    BacktestPage,
    CoinSelectionPage,
    SettingsPage
)

# ═══════════════════════════════════════════════════════════════════════════
# 應用程式狀態管理
# ═══════════════════════════════════════════════════════════════════════════

class AppState:
    """
    統一管理頁面間共享狀態

    用於解決頁面跳轉時的參數傳遞問題，取代 after(100) hack。
    """

    def __init__(self):
        # 待處理的參數（頁面跳轉時傳遞）
        self.pending_symbol_params: Optional[Dict] = None

        # 待處理的操作（如：跳轉後自動開始優化）
        self.pending_action: Optional[str] = None  # 'backtest', 'optimize', etc.

        # 當前選中的交易對
        self.current_symbol: Optional[str] = None

    def set_pending_params(self, params: Dict, action: str = None):
        """設定待處理的參數（在頁面跳轉前調用）"""
        self.pending_symbol_params = params
        self.pending_action = action

    def get_and_clear_pending_params(self) -> tuple:
        """獲取並清除待處理參數（在目標頁面顯示時調用）"""
        params = self.pending_symbol_params
        action = self.pending_action
        self.pending_symbol_params = None
        self.pending_action = None
        return params, action

    def has_pending_params(self) -> bool:
        """檢查是否有待處理參數"""
        return self.pending_symbol_params is not None


# ═══════════════════════════════════════════════════════════════════════════
# 自定義元件 - 已移至 gui/components/
# 以下類別保留為備份，加上 _Legacy 後綴避免衝突
# ═══════════════════════════════════════════════════════════════════════════



































class ASGridApp(ctk.CTk):
    """AS 網格交易系統 - 主視窗 (Bitget 版本)"""

    def __init__(self, skip_auth: bool = False):
        """
        初始化主視窗

        Args:
            skip_auth: 是否跳過授權驗證（開發模式）
        """
        super().__init__()

        # 視窗設定
        self.title("LouisLAB AS Grid Trading (Bitget)")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        self.configure(fg_color=Colors.BG_PRIMARY)

        # API 憑證 (Bitget 需要 passphrase)
        self.api_key: Optional[str] = None
        self.api_secret: Optional[str] = None
        self.passphrase: Optional[str] = None  # Bitget 專用
        self.uid: Optional[str] = None

        # 狀態
        self.is_trading = False
        self.connected = False
        self.current_page = "trading"
        self._auth_completed = False

        # 應用程式狀態管理（跨頁面共享狀態）
        self.app_state = AppState()

        # 頁面
        self.pages: Dict[str, ctk.CTkFrame] = {}
        self.nav_buttons: Dict[str, NavButton] = {}

        # 交易引擎
        from trading_engine import get_engine
        self.engine = get_engine()

        # 授權檢查
        if skip_auth:
            # 開發模式：跳過授權
            self._auth_completed = True
            self._create_ui()
        else:
            # 正常模式：先隱藏主視窗，等授權完成後再顯示
            self.withdraw()
            self.after(100, self._check_auth)

    def _create_ui(self):
        # 頂部導航欄
        self._create_header()

        # 主內容區（側邊導航 + 頁面）
        # 使用明確的背景色避免全白問題
        main_container = ctk.CTkFrame(self, fg_color=Colors.BG_PRIMARY)
        main_container.pack(fill="both", expand=True, padx=16, pady=16)

        # 側邊導航
        self._create_sidebar(main_container)

        # 右側區域（步驟指示器 + 頁面）
        right_area = ctk.CTkFrame(main_container, fg_color=Colors.BG_PRIMARY)
        right_area.pack(side="left", fill="both", expand=True)

        # 步驟指示器
        self.step_indicator = StepIndicator(right_area, current_page="trading")
        self.step_indicator.pack(fill="x", padx=0, pady=(0, 0))

        # 頁面容器
        # 使用明確的背景色避免全白問題
        self.page_container = ctk.CTkFrame(right_area, fg_color=Colors.BG_PRIMARY)
        self.page_container.pack(fill="both", expand=True)

        # 建立頁面
        self._create_pages()

        # 顯示預設頁面
        self.show_page("trading")

    def _create_header(self):
        header = ctk.CTkFrame(self, fg_color=Colors.BG_DARK, height=60, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        # Logo
        ctk.CTkLabel(header, text="LouisLAB AS Grid", font=ctk.CTkFont(size=20, weight="bold"), text_color=Colors.TEXT_PRIMARY).pack(side="left", padx=24)

        # 版本
        ctk.CTkLabel(header, text="MAX v1.0", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED, fg_color=Colors.BG_TERTIARY, corner_radius=4, padx=8, pady=2).pack(side="left", padx=(0, 20))

        # 右側狀態
        status_frame = ctk.CTkFrame(header, fg_color="transparent")
        status_frame.pack(side="right", padx=24)

        self.connection_status = StatusIndicator(status_frame, "未連接")
        self.connection_status.pack(side="left", padx=(0, 20))

        self.user_label = ctk.CTkLabel(status_frame, text="未登入", font=ctk.CTkFont(size=13), text_color=Colors.TEXT_SECONDARY)
        self.user_label.pack(side="left")

    def _create_sidebar(self, parent):
        sidebar = ctk.CTkFrame(parent, fg_color=Colors.BG_SECONDARY, width=200, corner_radius=12)
        sidebar.pack(side="left", fill="y", padx=(0, 16))
        sidebar.pack_propagate(False)

        # 導航項目
        nav_items = [
            ("trading", "交易控制台", "◉"),
            ("symbols", "交易對管理", "◎"),
            ("coinselect", "選幣評分", "◇"),
            ("backtest", "回測 / 優化", "◈"),
            ("settings", "系統設定", "⚙"),
        ]

        for page_id, text, icon in nav_items:
            btn = NavButton(
                sidebar,
                text=text,
                icon=icon,
                is_active=(page_id == "trading"),
                command=lambda p=page_id: self.show_page(p)
            )
            btn.pack(fill="x", padx=8, pady=4)
            self.nav_buttons[page_id] = btn

    def _create_pages(self):
        self.pages["trading"] = TradingPage(self.page_container, self)
        self.pages["symbols"] = SymbolsPage(self.page_container, self)
        self.pages["coinselect"] = CoinSelectionPage(self.page_container, self)
        self.pages["backtest"] = BacktestPage(self.page_container, self)
        self.pages["settings"] = SettingsPage(self.page_container, self)

    def show_page(self, page_id: str, params: Dict = None, action: str = None):
        """
        切換到指定頁面

        Args:
            page_id: 頁面 ID ('trading', 'symbols', 'backtest', etc.)
            params: 傳遞給目標頁面的參數（可選）
            action: 頁面顯示後要執行的操作（可選）
        """
        # 設定待處理參數（如果有）
        if params:
            self.app_state.set_pending_params(params, action)

        # 隱藏當前頁面
        if self.current_page in self.pages:
            self.pages[self.current_page].pack_forget()

        # 更新導航按鈕狀態
        for pid, btn in self.nav_buttons.items():
            btn.set_active(pid == page_id)

        # 更新步驟指示器
        if hasattr(self, 'step_indicator') and self.step_indicator:
            self.step_indicator.set_current_page(page_id)

        # 顯示新頁面
        if page_id in self.pages:
            page = self.pages[page_id]
            page.pack(fill="both", expand=True)
            self.current_page = page_id

            # 通知頁面已顯示（讓頁面處理 pending 參數）
            if hasattr(page, 'on_page_shown'):
                page.on_page_shown()

    def set_user(self, nickname: str):
        self.user_label.configure(text=nickname)

    def set_connected(self, connected: bool):
        self.connected = connected
        if connected:
            self.connection_status.set_active(True, "已連接")
        else:
            self.connection_status.set_active(False, "未連接")

    def _check_auth(self):
        """檢查授權狀態並顯示對應對話框"""
        if self.engine.is_credentials_configured():
            # 已設定：顯示解鎖對話框
            UnlockDialog(self, self.engine, self._on_auth_success)
        else:
            # 未設定：顯示首次設定對話框
            SetupDialog(self, self.engine, self._on_auth_success)

    def _on_auth_success(self, api_key: str, api_secret: str, passphrase: str = ""):
        """授權成功回調 (Bitget 版本)"""
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase  # Bitget 專用
        self._auth_completed = True

        # 建立 UI
        self._create_ui()

        # 顯示主視窗
        self.deiconify()

        # 自動連接交易所
        self.after(100, self._auto_connect)

    def _auto_connect(self, skip_license: bool = False):
        """自動連接交易所 (Bitget 版本)"""
        import asyncio
        import threading

        def connect():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # Bitget 需要 passphrase
                success = loop.run_until_complete(
                    self.engine.connect(
                        self.api_key,
                        self.api_secret,
                        passphrase=self.passphrase,  # Bitget 專用
                        skip_license=skip_license
                    )
                )
                # 在主線程更新 UI
                self.after(0, lambda: self._on_connect_result(success))
            except Exception as ex:
                error_msg = str(ex)
                self.after(0, lambda err=error_msg: self._on_connect_result(False, err))
            finally:
                loop.close()

        threading.Thread(target=connect, daemon=True).start()

    def _on_connect_result(self, success: bool, error: str = None):
        """連接結果回調"""
        if success:
            self.set_connected(True)
            # 更新用戶資訊
            if self.engine.user_info:
                nickname = self.engine.user_info.get("nickname", "用戶")
                self.set_user(nickname)
            else:
                self.set_user("已連接")

            # 設置 WebSocket 回調（即時更新 UI）
            if "trading" in self.pages:
                trading_page = self.pages["trading"]
                self.engine.set_callbacks(
                    on_log=lambda msg: self.after(0, lambda m=msg: trading_page.add_log(m)),
                    on_symbol_status=lambda st: self.after(0, lambda s=st: trading_page._update_symbol_rows(s)),
                    on_account=lambda acc: self.after(0, lambda a=acc: trading_page._update_accounts(a)),
                    on_indicators=lambda ind: self.after(0, lambda i=ind: trading_page._update_indicators(i)),
                )
                # 刷新帳戶顯示
                trading_page.refresh_account_display()

                # 啟動連接計時器和 UI 更新
                trading_page.start_connection_timer()

                # 啟動定期 Funding Rate 更新
                self._start_funding_rate_update()
        else:
            self.set_connected(False)
            # 顯示錯誤訊息（可選）
            if error:
                print(f"連接失敗: {error}")

    def _start_funding_rate_update(self):
        """啟動定期 Funding Rate 更新"""
        self._funding_rate_job = None

        def update_funding():
            if not self.engine or not self.engine.is_connected:
                return

            # 在背景線程執行異步操作
            def fetch():
                try:
                    import asyncio
                    # 使用 engine 的 event loop 或創建新的
                    try:
                        loop = asyncio.get_running_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    if loop.is_running():
                        # 如果 loop 已在運行，使用 run_coroutine_threadsafe
                        future = asyncio.run_coroutine_threadsafe(
                            self.engine.fetch_funding_rate(),
                            loop
                        )
                        future.result(timeout=30)
                    else:
                        loop.run_until_complete(self.engine.fetch_funding_rate())
                        loop.close()
                except Exception:
                    pass  # 靜默處理錯誤，避免干擾用戶

            threading.Thread(target=fetch, daemon=True).start()

            # 每 5 分鐘更新一次
            if self.engine and self.engine.is_connected:
                try:
                    self._funding_rate_job = self.after(300000, update_funding)
                except Exception:
                    pass

        # 首次延遲執行
        try:
            self._funding_rate_job = self.after(3000, update_funding)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
# 登入視窗（舊版，保留兼容）
# ═══════════════════════════════════════════════════════════════════════════

class LoginWindow(ctk.CTk):
    """登入視窗"""

    def __init__(self, on_success: Callable = None):
        super().__init__()

        self.on_success = on_success

        self.title("LouisLAB AS Grid - 登入")
        self.geometry("420x580")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PRIMARY)

        # 置中
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 420) // 2
        y = (self.winfo_screenheight() - 580) // 2
        self.geometry(f"420x580+{x}+{y}")

        self._create_ui()

    def _create_ui(self):
        # Logo
        logo_frame = ctk.CTkFrame(self, fg_color="transparent")
        logo_frame.pack(fill="x", pady=(60, 40))

        ctk.CTkLabel(logo_frame, text="LouisLAB", font=ctk.CTkFont(size=14), text_color=Colors.TEXT_MUTED).pack()
        ctk.CTkLabel(logo_frame, text="AS Grid", font=ctk.CTkFont(size=36, weight="bold"), text_color=Colors.TEXT_PRIMARY).pack()
        ctk.CTkLabel(logo_frame, text="Trading System", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_MUTED).pack()

        # 輸入區
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=40)

        ctk.CTkLabel(input_frame, text="解鎖密碼", font=ctk.CTkFont(size=13), text_color=Colors.TEXT_SECONDARY).pack(anchor="w", pady=(0, 8))

        self.password_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="輸入您的密碼...",
            show="●",
            height=48,
            font=ctk.CTkFont(size=14),
            fg_color=Colors.BG_SECONDARY,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY
        )
        self.password_entry.pack(fill="x", pady=(0, 24))
        self.password_entry.bind("<Return>", lambda e: self._login())

        self.login_button = ctk.CTkButton(
            input_frame,
            text="解鎖",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            height=48,
            corner_radius=8,
            command=self._login
        )
        self.login_button.pack(fill="x", pady=(0, 16))

        ctk.CTkButton(
            input_frame,
            text="首次使用？設定 API",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            text_color=Colors.TEXT_MUTED,
            hover_color=Colors.BG_SECONDARY,
            height=32,
            command=self._first_setup
        ).pack()

        self.error_label = ctk.CTkLabel(input_frame, text="", font=ctk.CTkFont(size=12), text_color=Colors.RED)
        self.error_label.pack(pady=(16, 0))

        # 底部
        ctk.CTkLabel(self, text="v1.0.0 · AES-256-GCM 加密", font=ctk.CTkFont(size=11), text_color=Colors.TEXT_MUTED).pack(side="bottom", pady=24)

    def _login(self):
        password = self.password_entry.get()

        if not password:
            self.error_label.configure(text="請輸入密碼")
            return

        self.login_button.configure(text="解密中...", state="disabled")

        def do_unlock():
            try:
                from client.secure_storage import CredentialManager, check_legacy_config

                manager = CredentialManager()

                # 檢查是否需要遷移舊版配置
                if not manager.is_configured():
                    # 檢查是否有舊版明文配置
                    config_path = Path(__file__).parent.parent / "config" / "trading_config_max.json"
                    legacy_creds = check_legacy_config(config_path)

                    if legacy_creds:
                        # 有舊版配置，顯示遷移對話框
                        api_key, api_secret = legacy_creds
                        self.login_button.configure(text="解鎖", state="normal")

                        def on_migration_success(migrated_key, migrated_secret):
                            if self.on_success:
                                self.on_success(migrated_key, migrated_secret)

                        MigrationDialog(
                            self,
                            api_key,
                            api_secret,
                            config_path,
                            on_migration_success
                        )
                        return
                    else:
                        # 沒有舊版配置，提示首次設定
                        self.error_label.configure(text="尚未設定 API，請先設定")
                        self.login_button.configure(text="解鎖", state="normal")
                        return

                try:
                    api_key, api_secret, passphrase = manager.unlock(password)
                    # 儲存到全域變數供 trading_engine 使用
                    self.api_key = api_key
                    self.api_secret = api_secret
                    self.passphrase = passphrase  # Bitget 專用

                    self.error_label.configure(text="")
                    if self.on_success:
                        self.destroy()
                        self.on_success(api_key, api_secret, passphrase)

                except ValueError:
                    self.error_label.configure(text="密碼錯誤，請重試")
                    self.login_button.configure(text="解鎖", state="normal")

            except ImportError:
                # 如果模組不存在，使用測試模式
                if password == "louislab123":
                    self.error_label.configure(text="")
                    if self.on_success:
                        self.destroy()
                        self.on_success(None, None)
                else:
                    self.error_label.configure(text="密碼錯誤，請重試")
                    self.login_button.configure(text="解鎖", state="normal")

            except Exception as e:
                self.error_label.configure(text=f"錯誤: {str(e)}")
                self.login_button.configure(text="解鎖", state="normal")

        self.after(300, do_unlock)

    def _first_setup(self):
        """首次設定"""
        SetupWindow(self)


class SetupWindow(ctk.CTkToplevel):
    """首次設定視窗 (Bitget 版本)"""

    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

        self.title("首次設定 - Bitget API 憑證")
        self.geometry("450x750")  # 增加高度以容納 passphrase 欄位
        self.configure(fg_color=Colors.BG_PRIMARY)
        self.transient(parent)
        self.grab_set()

        # 置中
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 450) // 2
        y = (self.winfo_screenheight() - 750) // 2
        self.geometry(f"450x750+{x}+{y}")

        self._create_ui()

    def _create_ui(self):
        # 標題
        ctk.CTkLabel(
            self,
            text="設定 Bitget API 憑證",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(40, 8))

        ctk.CTkLabel(
            self,
            text="您的 API 將使用 AES-256-GCM 加密儲存",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_MUTED
        ).pack(pady=(0, 32))

        # 輸入區
        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(fill="x", padx=40)

        # API Key
        ctk.CTkLabel(
            input_frame,
            text="Bitget API Key",
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 8))

        self.api_key_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="輸入 API Key...",
            height=44,
            fg_color=Colors.BG_SECONDARY,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY
        )
        self.api_key_entry.pack(fill="x", pady=(0, 16))

        # API Secret
        ctk.CTkLabel(
            input_frame,
            text="Bitget API Secret",
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 8))

        self.api_secret_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="輸入 API Secret...",
            show="●",
            height=44,
            fg_color=Colors.BG_SECONDARY,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY
        )
        self.api_secret_entry.pack(fill="x", pady=(0, 16))

        # Passphrase (Bitget 專用)
        ctk.CTkLabel(
            input_frame,
            text="Bitget Passphrase (必填)",
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 8))

        self.passphrase_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="輸入 Passphrase...",
            show="●",
            height=44,
            fg_color=Colors.BG_SECONDARY,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY
        )
        self.passphrase_entry.pack(fill="x", pady=(0, 24))

        # 分隔線
        ctk.CTkFrame(input_frame, fg_color=Colors.BORDER, height=1).pack(fill="x", pady=16)

        # 加密密碼
        ctk.CTkLabel(
            input_frame,
            text="設定加密密碼",
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 8))

        self.password_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="至少 8 個字元...",
            show="●",
            height=44,
            fg_color=Colors.BG_SECONDARY,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY
        )
        self.password_entry.pack(fill="x", pady=(0, 16))

        # 確認密碼
        ctk.CTkLabel(
            input_frame,
            text="確認密碼",
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", pady=(0, 8))

        self.confirm_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="再次輸入密碼...",
            show="●",
            height=44,
            fg_color=Colors.BG_SECONDARY,
            border_color=Colors.BORDER,
            text_color=Colors.TEXT_PRIMARY
        )
        self.confirm_entry.pack(fill="x", pady=(0, 24))

        # 儲存按鈕
        self.save_button = ctk.CTkButton(
            input_frame,
            text="加密儲存",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            height=48,
            corner_radius=8,
            command=self._save
        )
        self.save_button.pack(fill="x")

        # 錯誤訊息
        self.error_label = ctk.CTkLabel(
            input_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=Colors.RED
        )
        self.error_label.pack(pady=(16, 0))

    def _save(self):
        """儲存設定 (Bitget 版本)"""
        api_key = self.api_key_entry.get().strip()
        api_secret = self.api_secret_entry.get().strip()
        passphrase = self.passphrase_entry.get().strip()  # Bitget 專用
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()

        # 驗證
        if not api_key or not api_secret:
            self.error_label.configure(text="請輸入 API Key 和 Secret")
            return

        # Bitget 需要 passphrase
        if not passphrase:
            self.error_label.configure(text="Bitget API 需要 Passphrase")
            return

        if len(password) < 8:
            self.error_label.configure(text="密碼至少需要 8 個字元")
            return

        if password != confirm:
            self.error_label.configure(text="密碼不一致")
            return

        # 儲存中動畫
        self.save_button.configure(text="加密儲存中...", state="disabled")
        self.error_label.configure(text="", text_color=Colors.STATUS_ON)

        def do_save():
            try:
                from client.secure_storage import CredentialManager

                manager = CredentialManager()
                # 修復：傳遞 passphrase 參數 (Bitget 必須)
                manager.setup(api_key, api_secret, password, passphrase)

                self.error_label.configure(text="✓ API 憑證已加密儲存！")
                self.save_button.configure(text="✓ 已儲存")
                self.after(1500, self.destroy)

            except ImportError as e:
                self.error_label.configure(text=f"模組載入失敗: {str(e)}", text_color=Colors.RED)
                self.save_button.configure(text="加密儲存", state="normal")
            except ValueError as e:
                self.error_label.configure(text=f"設定失敗: {str(e)}", text_color=Colors.RED)
                self.save_button.configure(text="加密儲存", state="normal")
            except Exception as e:
                self.error_label.configure(text=f"儲存失敗: {str(e)}", text_color=Colors.RED)
                self.save_button.configure(text="加密儲存", state="normal")

        self.after(500, do_save)

# ═══════════════════════════════════════════════════════════════════════════
# 主入口
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """主程式入口"""
    import tkinter as tk
    import sys

    # 抑制 Tkinter 的 invalid command name 警告
    # (視窗關閉後 after 回調執行造成的無害警告)
    original_stderr = sys.stderr

    class TkWarningFilter:
        """過濾 Tkinter 警告的 stderr 包裝器"""
        def write(self, msg):
            # 過濾 after 回調相關警告
            if 'invalid command name' in msg:
                return
            if 'after' in msg and 'script' in msg:
                return
            original_stderr.write(msg)

        def flush(self):
            original_stderr.flush()

    sys.stderr = TkWarningFilter()

    def report_callback_exception(self, exc, val, tb):
        if "invalid command name" in str(val):
            pass  # 忽略此警告
        else:
            # 其他錯誤正常報告
            import traceback
            traceback.print_exception(exc, val, tb)

    tk.Tk.report_callback_exception = report_callback_exception

    def on_login_success(api_key=None, api_secret=None, passphrase=None):
        if api_key and api_secret:
            # 真實模式 - 需要驗證 UID (Bitget 需要 passphrase)
            verify_window = VerifyWindow(api_key, api_secret, passphrase or "")
            verify_window.mainloop()
        else:
            # 測試模式 - 跳過驗證
            app = ASGridApp()
            app.set_user("測試模式")
            app.set_connected(False)
            app.mainloop()

    login = LoginWindow(on_success=on_login_success)
    login.mainloop()


class VerifyWindow(ctk.CTk):
    """UID 驗證視窗 (Bitget 版本)"""

    def __init__(self, api_key: str, api_secret: str, passphrase: str = ""):
        super().__init__()

        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase  # Bitget 專用
        self.current_uid = None

        self.title("LouisLAB AS Grid (Bitget) - 驗證中")
        self.geometry("450x400")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PRIMARY)

        # 置中
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 450) // 2
        y = (self.winfo_screenheight() - 400) // 2
        self.geometry(f"450x400+{x}+{y}")

        self._create_ui()
        self.after(500, self._start_verify)

    def _create_ui(self):
        self.title_label = ctk.CTkLabel(
            self,
            text="正在驗證授權...",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        )
        self.title_label.pack(pady=(50, 20))

        self.status_label = ctk.CTkLabel(
            self,
            text="連接交易所...",
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_SECONDARY
        )
        self.status_label.pack(pady=10)

        # UID 顯示區域（初始隱藏）
        self.uid_frame = ctk.CTkFrame(self, fg_color=Colors.BG_SECONDARY, corner_radius=8)

        self.uid_label = ctk.CTkLabel(
            self.uid_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_MUTED
        )

        self.error_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=Colors.RED
        )
        self.error_label.pack(pady=10)

        # 底部按鈕區（初始隱藏）
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")

    def _start_verify(self):
        """開始驗證流程"""
        import threading

        def verify_thread():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._verify_async())
                self.after(0, lambda: self._handle_result(result))
            finally:
                loop.close()

        thread = threading.Thread(target=verify_thread, daemon=True)
        thread.start()

    async def _verify_async(self):
        """異步驗證 (Bitget 版本)"""
        import ccxt.async_support as ccxt

        exchange = None
        uid = ""

        try:
            # 1. 連接交易所 (Bitget)
            self.after(0, lambda: self.status_label.configure(text="連接 Bitget 交易所..."))

            exchange = ccxt.bitget({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'password': self.passphrase,  # Bitget 需要 passphrase
                'enableRateLimit': True,
                'options': {'defaultType': 'swap'}  # Bitget 永續合約
            })

            await exchange.load_markets()

            # 2. 獲取 UID (Bitget 版本 - 多種方法嘗試)
            self.after(0, lambda: self.status_label.configure(text="獲取 Bitget 帳戶資訊..."))

            errors = []

            # 方法 1: 使用 V2 Spot Account API (推薦)
            try:
                account_info = await exchange.privateSpotGetV2SpotAccountInfo()
                print(f"[DEBUG] V2 Spot Account Info: {account_info}")
                if account_info and account_info.get('code') == '00000':
                    data = account_info.get('data', {})
                    uid = str(data.get('userId', '') or data.get('uid', ''))
                    if uid and uid.isdigit():
                        print(f"[DEBUG] 從 V2 Spot API 獲取 UID: {uid}")
            except Exception as e1:
                errors.append(f"V2 Spot: {str(e1)[:50]}")

            # 方法 2: 使用 V2 Mix (合約) Account API
            if not uid or not uid.isdigit():
                try:
                    mix_info = await exchange.privateMixGetV2MixAccountAccounts({
                        'productType': 'USDT-FUTURES'
                    })
                    print(f"[DEBUG] V2 Mix Account Info: {mix_info}")
                    if mix_info and mix_info.get('code') == '00000':
                        data = mix_info.get('data', [])
                        if isinstance(data, list) and len(data) > 0:
                            uid = str(data[0].get('userId', '') or data[0].get('uid', ''))
                            if uid and uid.isdigit():
                                print(f"[DEBUG] 從 V2 Mix API 獲取 UID: {uid}")
                except Exception as e2:
                    errors.append(f"V2 Mix: {str(e2)[:50]}")

            # 方法 3: 嘗試 V1 Spot Account API
            if not uid or not uid.isdigit():
                try:
                    account_info_v1 = await exchange.privateSpotGetSpotV1AccountGetInfo()
                    print(f"[DEBUG] V1 Spot Account Info: {account_info_v1}")
                    if account_info_v1 and 'data' in account_info_v1:
                        data = account_info_v1.get('data', {})
                        uid = str(data.get('userId', '') or data.get('uid', ''))
                        if uid and uid.isdigit():
                            print(f"[DEBUG] 從 V1 Spot API 獲取 UID: {uid}")
                except Exception as e3:
                    errors.append(f"V1 Spot: {str(e3)[:50]}")

            # 方法 4: 通過 fetch_balance 嘗試獲取
            if not uid or not uid.isdigit():
                try:
                    balance = await exchange.fetch_balance()
                    info = balance.get('info', {})
                    print(f"[DEBUG] fetch_balance info: {info}")
                    if isinstance(info, dict):
                        uid = str(info.get('userId', '') or info.get('uid', ''))
                        if uid and uid.isdigit():
                            print(f"[DEBUG] 從 fetch_balance 獲取 UID: {uid}")
                except Exception as e4:
                    errors.append(f"Balance: {str(e4)[:50]}")

            # 方法 5: 通過 Fee Query API 獲取
            if not uid or not uid.isdigit():
                try:
                    fee_info = await exchange.privateUserGetUserV1FeeQuery()
                    print(f"[DEBUG] Fee Query Info: {fee_info}")
                    if fee_info and 'data' in fee_info:
                        data = fee_info.get('data', {})
                        uid = str(data.get('userId', '') or data.get('uid', ''))
                        if uid and uid.isdigit():
                            print(f"[DEBUG] 從 Fee Query 獲取 UID: {uid}")
                except Exception as e5:
                    errors.append(f"Fee: {str(e5)[:50]}")

            # 方法 6: 通過 V1 Mix Account 獲取
            if not uid or not uid.isdigit():
                try:
                    mix_v1 = await exchange.privateMixGetMixV1AccountAccounts({
                        'productType': 'umcbl'  # USDT-M
                    })
                    print(f"[DEBUG] V1 Mix Account: {mix_v1}")
                    if mix_v1 and 'data' in mix_v1:
                        data = mix_v1.get('data', [])
                        if isinstance(data, list) and len(data) > 0:
                            uid = str(data[0].get('userId', '') or data[0].get('uid', ''))
                            if uid and uid.isdigit():
                                print(f"[DEBUG] 從 V1 Mix 獲取 UID: {uid}")
                except Exception as e6:
                    errors.append(f"V1Mix: {str(e6)[:50]}")

            # 方法 7: 通過訂單歷史獲取 (訂單中通常包含 userId)
            if not uid or not uid.isdigit():
                try:
                    # 嘗試獲取最近的訂單
                    orders = await exchange.fetch_orders(limit=1)
                    print(f"[DEBUG] Orders: {orders}")
                    if orders and len(orders) > 0:
                        info = orders[0].get('info', {})
                        uid = str(info.get('userId', '') or info.get('uid', ''))
                        if uid and uid.isdigit():
                            print(f"[DEBUG] 從訂單獲取 UID: {uid}")
                except Exception as e7:
                    errors.append(f"Orders: {str(e7)[:50]}")

            # 檢查結果
            if not uid or not uid.isdigit():
                if errors:
                    uid = f"無法獲取 ({'; '.join(errors)[:80]})"
                else:
                    uid = "無法獲取"

            self.after(0, lambda u=uid: self.uid_label.configure(text=f"您的 UID: {u}"))

            # 3. 驗證白名單
            self.after(0, lambda: self.status_label.configure(text="驗證授權..."))

            try:
                from client.license_manager import LicenseManager

                # 驗證伺服器 URL
                SERVER_URL = os.environ.get("LICENSE_SERVER_URL", "https://as-grid-server-production.up.railway.app")

                license_mgr = LicenseManager(exchange, SERVER_URL, "1.0.0")

                # 如果我們已經獲取到有效 UID，直接設定，避免再次嘗試獲取
                if uid and uid.isdigit():
                    license_mgr.uid = uid

                result = await license_mgr.verify()

                # 停止心跳任務 (驗證階段不需要，主程式會重新啟動)
                await license_mgr.logout()

                if result["success"]:
                    return {
                        "success": True,
                        "uid": uid,
                        "user": result.get("user", {}),
                        "api_key": self.api_key,
                        "api_secret": self.api_secret
                    }
                else:
                    reason = self._clean_error_msg(result.get("reason", "未授權"))
                    return {
                        "success": False,
                        "uid": uid,
                        "reason": reason
                    }

            except ImportError:
                # 沒有 license_manager 模組 - 不允許進入
                return {
                    "success": False,
                    "uid": uid,
                    "reason": "授權模組遺失，請聯繫管理員"
                }

            except Exception as verify_error:
                # 驗證伺服器連接失敗
                reason = self._clean_error_msg(str(verify_error))
                return {
                    "success": False,
                    "uid": uid,
                    "reason": f"無法連接驗證伺服器: {reason}"
                }

        except Exception as e:
            reason = self._clean_error_msg(str(e))
            return {"success": False, "uid": uid, "reason": reason}

        finally:
            # 確保關閉 exchange 連線
            if exchange:
                try:
                    await exchange.close()
                except Exception:
                    pass

    def _clean_error_msg(self, msg: str) -> str:
        """清理錯誤訊息，移除 HTML/CSS 內容 (Bitget 版本)"""
        if not msg:
            return "未知錯誤"

        msg_lower = msg.lower()

        # 檢測 Bitget 404 錯誤（API 權限問題）
        if '404' in msg and ('bitget' in msg_lower or 'api.bitget' in msg_lower):
            return "API 無法訪問合約帳戶（請確認 API 有合約權限）"

        # 檢測 passphrase 錯誤
        if 'passphrase' in msg_lower or 'password' in msg_lower:
            return "Passphrase 錯誤，請檢查 API 設定"

        # 檢測 401/403 錯誤（認證問題）
        if '401' in msg or '403' in msg:
            return "API Key 無效或權限不足"

        # 檢測網路錯誤
        if 'timeout' in msg_lower or 'connection' in msg_lower:
            return "網路連線失敗，請檢查網路"

        # 如果包含 HTML 標籤或 CSS，則簡化訊息
        html_indicators = ['<html', '<body', '<div', '<style', '<!doctype', '<head', '<meta']
        for indicator in html_indicators:
            if indicator in msg_lower:
                # 嘗試從錯誤訊息中提取有用信息
                if '404' in msg:
                    return "請求的 API 不存在（404）"
                elif '500' in msg:
                    return "伺服器內部錯誤（500）"
                elif '502' in msg or '503' in msg:
                    return "伺服器暫時無法服務"
                return "伺服器回應格式錯誤"

        # 限制長度
        if len(msg) > 100:
            return msg[:100] + "..."

        return msg

    def _handle_result(self, result):
        """處理驗證結果"""
        if result.get("success"):
            user = result.get("user", {})
            nickname = user.get("nickname", "用戶")

            self.title_label.configure(text="✓ 驗證成功")
            self.status_label.configure(text=f"歡迎，{nickname}！", text_color=Colors.STATUS_ON)

            if result.get("offline_mode"):
                self.error_label.configure(text="（離線模式）", text_color=Colors.YELLOW)

            # 1.5 秒後進入主程式
            self.after(1500, lambda: self._enter_app(result))
        else:
            # 驗證失敗
            self.title_label.configure(text="✗ 授權驗證失敗", text_color=Colors.RED)
            self.status_label.configure(text=result.get("reason", "未知錯誤"), text_color=Colors.TEXT_MUTED)
            self.error_label.configure(text="")

            # 儲存 UID
            uid = result.get("uid", "")
            self.current_uid = uid

            # 總是顯示 UID 區域
            self.uid_frame.pack(fill="x", padx=40, pady=20)

            # 判斷 UID 是否有效（純數字才是有效的 UID）
            is_valid_uid = uid and uid.isdigit()

            if is_valid_uid:
                # 有效 UID - 顯示複製功能
                ctk.CTkLabel(
                    self.uid_frame,
                    text="請將以下 UID 發送給管理員申請授權：",
                    font=ctk.CTkFont(size=12),
                    text_color=Colors.TEXT_SECONDARY
                ).pack(anchor="w", padx=16, pady=(16, 8))

                # UID 顯示框（可選取複製）
                uid_display = ctk.CTkEntry(
                    self.uid_frame,
                    height=40,
                    font=ctk.CTkFont(size=14, weight="bold"),
                    fg_color=Colors.BG_TERTIARY,
                    border_color=Colors.BORDER,
                    text_color=Colors.TEXT_PRIMARY,
                    justify="center"
                )
                uid_display.pack(fill="x", padx=16, pady=(0, 8))
                uid_display.insert(0, uid)
                uid_display.configure(state="readonly")

                # 複製按鈕
                ctk.CTkButton(
                    self.uid_frame,
                    text="📋 複製 UID",
                    font=ctk.CTkFont(size=13),
                    fg_color=Colors.BG_TERTIARY,
                    hover_color=Colors.BORDER,
                    text_color=Colors.TEXT_PRIMARY,
                    height=36,
                    command=lambda: self._copy_uid(uid)
                ).pack(pady=(0, 16))
            else:
                # 無法獲取有效 UID - 顯示錯誤提示
                ctk.CTkLabel(
                    self.uid_frame,
                    text="無法獲取 Bitget UID",
                    font=ctk.CTkFont(size=14, weight="bold"),
                    text_color=Colors.YELLOW
                ).pack(anchor="w", padx=16, pady=(16, 8))

                # 顯示錯誤詳情
                if uid and not uid.isdigit():
                    ctk.CTkLabel(
                        self.uid_frame,
                        text=f"錯誤：{uid}",
                        font=ctk.CTkFont(size=11),
                        text_color=Colors.TEXT_MUTED,
                        wraplength=300
                    ).pack(anchor="w", padx=16, pady=(0, 8))

                # 建議步驟 (Bitget 版本)
                suggestions = [
                    "1. 確認 API Key 已開啟「合約」權限",
                    "2. 確認您已開通 Bitget 合約帳戶",
                    "3. 確認 API Key、Secret 和 Passphrase 正確"
                ]
                for suggestion in suggestions:
                    ctk.CTkLabel(
                        self.uid_frame,
                        text=suggestion,
                        font=ctk.CTkFont(size=11),
                        text_color=Colors.TEXT_SECONDARY
                    ).pack(anchor="w", padx=16, pady=1)

            # 聯繫資訊
            ctk.CTkLabel(
                self,
                text="請聯繫管理員獲取授權後重新啟動程式",
                font=ctk.CTkFont(size=11),
                text_color=Colors.TEXT_MUTED
            ).pack(pady=(10, 5))

            # 退出按鈕
            ctk.CTkButton(
                self,
                text="退出",
                font=ctk.CTkFont(size=13),
                fg_color=Colors.BG_TERTIARY,
                hover_color=Colors.BORDER,
                text_color=Colors.TEXT_PRIMARY,
                height=40,
                width=120,
                command=self.destroy
            ).pack(pady=15)

    def _copy_uid(self, uid: str):
        """複製 UID 到剪貼簿"""
        self.clipboard_clear()
        self.clipboard_append(uid)
        self.update()
        # 顯示已複製提示
        self.status_label.configure(text="✓ UID 已複製到剪貼簿", text_color=Colors.STATUS_ON)

    def _enter_app(self, result):
        """進入主程式 (Bitget 版本)"""
        self.destroy()

        # 授權已完成，跳過再次驗證
        app = ASGridApp(skip_auth=True)
        app.api_key = result.get("api_key")
        app.api_secret = result.get("api_secret")
        app.passphrase = result.get("passphrase", self.passphrase)  # Bitget 專用

        user = result.get("user", {})
        app.set_user(user.get("nickname", "用戶"))

        # 傳遞 UID 和用戶資訊到引擎
        app.uid = result.get("uid")
        app.engine.user_info = user
        app.engine.is_verified = True

        # 連接交易所並刷新帳戶顯示（授權已驗證，跳過重複驗證）
        app.after(100, lambda: app._auto_connect(skip_license=True))

        app.mainloop()


if __name__ == "__main__":
    main()
