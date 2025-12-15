"""
設定相關對話框

包含:
- SetupDialog: 首次設定 API 對話框
- UnlockDialog: 解鎖密碼對話框
- ChangeAPIDialog: 更換 API 憑證對話框
- MigrationDialog: 舊版配置遷移對話框
"""

import asyncio
import concurrent.futures
from pathlib import Path
from typing import TYPE_CHECKING

import customtkinter as ctk
from ..styles import Colors

if TYPE_CHECKING:
    from gui.app import ASGridApp


# 導入安全相關異常
try:
    from client.secure_storage import InvalidPasswordError
except ImportError:
    class InvalidPasswordError(Exception):
        pass


class SetupDialog(ctk.CTkToplevel):
    """首次設定 API 對話框 (Bitget 版本)"""

    def __init__(self, parent, engine, on_success: callable):
        super().__init__(parent)
        self.engine = engine
        self.on_success = on_success

        self.title("首次設定 (Bitget)")
        self.geometry("450x650")  # 增加高度容納 passphrase
        self.configure(fg_color=Colors.BG_PRIMARY)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # 置中
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 450) // 2
        y = (screen_height - 650) // 2
        self.geometry(f"450x650+{x}+{y}")

        self._create_ui()

    def _create_ui(self):
        # 標題
        ctk.CTkLabel(
            self,
            text="AS 網格交易系統",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(30, 8))

        ctk.CTkLabel(
            self,
            text="首次使用，請設定您的 API 憑證",
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_SECONDARY
        ).pack(pady=(0, 24))

        # 說明卡片
        info_card = ctk.CTkFrame(self, fg_color=Colors.BG_TERTIARY, corner_radius=8)
        info_card.pack(fill="x", padx=32, pady=(0, 20))
        ctk.CTkLabel(
            info_card,
            text="您的 API 將使用 AES-256-GCM 加密儲存\n密碼僅用於本地解密，不會傳輸至伺服器",
            font=ctk.CTkFont(size=11),
            text_color=Colors.TEXT_MUTED,
            justify="center"
        ).pack(padx=16, pady=12)

        # API Key
        ctk.CTkLabel(self, text="Bitget API Key", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY).pack(anchor="w", padx=32)
        self.api_key_entry = ctk.CTkEntry(self, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=40, width=386)
        self.api_key_entry.pack(padx=32, pady=(4, 12))

        # API Secret
        ctk.CTkLabel(self, text="Bitget API Secret", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY).pack(anchor="w", padx=32)
        self.api_secret_entry = ctk.CTkEntry(self, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=40, width=386, show="*")
        self.api_secret_entry.pack(padx=32, pady=(4, 12))

        # Passphrase (Bitget 專用)
        ctk.CTkLabel(self, text="Bitget Passphrase", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY).pack(anchor="w", padx=32)
        self.passphrase_entry = ctk.CTkEntry(self, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=40, width=386, show="*")
        self.passphrase_entry.pack(padx=32, pady=(4, 20))

        # 密碼設定
        ctk.CTkLabel(self, text="設定加密密碼", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY).pack(anchor="w", padx=32)
        self.password_entry = ctk.CTkEntry(self, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=40, width=386, show="*")
        self.password_entry.pack(padx=32, pady=(4, 4))
        self.password_entry.bind("<KeyRelease>", self._check_strength)

        # 密碼強度
        self.strength_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=10), text_color=Colors.TEXT_MUTED)
        self.strength_label.pack(anchor="w", padx=32, pady=(0, 12))

        # 確認密碼
        ctk.CTkLabel(self, text="確認密碼", font=ctk.CTkFont(size=12), text_color=Colors.TEXT_SECONDARY).pack(anchor="w", padx=32)
        self.confirm_entry = ctk.CTkEntry(self, fg_color=Colors.BG_TERTIARY, border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY, height=40, width=386, show="*")
        self.confirm_entry.pack(padx=32, pady=(4, 20))

        # 錯誤訊息
        self.error_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11), text_color=Colors.RED)
        self.error_label.pack(pady=(0, 8))

        # 按鈕
        ctk.CTkButton(
            self,
            text="開始使用",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            height=44,
            width=200,
            corner_radius=8,
            command=self._save
        ).pack(pady=(0, 20))

    def _check_strength(self, _event=None):
        password = self.password_entry.get()
        if not password:
            self.strength_label.configure(text="")
            return

        level, name, _suggestions = self.engine.check_password_strength(password)
        # 灰階顏色用於密碼強度 (從弱到強)
        colors = [Colors.RED, Colors.RED_DARK, Colors.YELLOW, Colors.GREEN_DARK, Colors.GREEN]
        self.strength_label.configure(text=f"密碼強度: {name}", text_color=colors[min(level, 4)])

    def _save(self):
        api_key = self.api_key_entry.get().strip()
        api_secret = self.api_secret_entry.get().strip()
        passphrase = self.passphrase_entry.get().strip()  # Bitget 專用
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()

        # 驗證
        if not api_key or len(api_key) < 10:
            self.error_label.configure(text="請輸入有效的 API Key")
            return
        if not api_secret or len(api_secret) < 10:
            self.error_label.configure(text="請輸入有效的 API Secret")
            return
        if not passphrase:
            self.error_label.configure(text="請輸入 Bitget Passphrase")
            return
        if len(password) < 8:
            self.error_label.configure(text="密碼長度至少需要 8 個字元")
            return
        if password != confirm:
            self.error_label.configure(text="兩次輸入的密碼不一致")
            return

        # 儲存 (包含 passphrase)
        success, error = self.engine.setup_credentials(api_key, api_secret, password, passphrase)
        if success:
            self.on_success(api_key, api_secret, passphrase)
            self.destroy()
        else:
            self.error_label.configure(text=error)

    def _on_close(self):
        # 如果關閉視窗，退出程式
        self.destroy()
        self.master.destroy()


class UnlockDialog(ctk.CTkToplevel):
    """解鎖密碼對話框"""

    def __init__(self, parent, engine, on_success: callable):
        super().__init__(parent)
        self.engine = engine
        self.on_success = on_success
        self.attempts = 0
        self.max_attempts = 3

        self.title("解鎖")
        self.geometry("400x320")
        self.configure(fg_color=Colors.BG_PRIMARY)
        self.transient(parent)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # 置中
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 320) // 2
        self.geometry(f"400x320+{x}+{y}")

        self._create_ui()

    def _create_ui(self):
        # 標題
        ctk.CTkLabel(
            self,
            text="AS 網格交易系統",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(40, 8))

        ctk.CTkLabel(
            self,
            text="請輸入密碼解鎖",
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_SECONDARY
        ).pack(pady=(0, 30))

        # 密碼輸入
        self.password_entry = ctk.CTkEntry(
            self,
            fg_color=Colors.BG_TERTIARY,
            border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY,
            height=44,
            width=300,
            show="*",
            placeholder_text="輸入密碼"
        )
        self.password_entry.pack(pady=(0, 12))
        self.password_entry.bind("<Return>", lambda e: self._unlock())
        self.password_entry.focus()

        # 錯誤訊息
        self.error_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=11), text_color=Colors.RED)
        self.error_label.pack(pady=(0, 16))

        # 按鈕
        ctk.CTkButton(
            self,
            text="解鎖",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            height=44,
            width=150,
            corner_radius=8,
            command=self._unlock
        ).pack()

        # 重置連結
        ctk.CTkButton(
            self,
            text="忘記密碼？重新設定",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            text_color=Colors.TEXT_MUTED,
            hover_color=Colors.BG_TERTIARY,
            command=self._reset
        ).pack(pady=(16, 0))

    def _unlock(self):
        password = self.password_entry.get()
        if not password:
            self.error_label.configure(text="請輸入密碼")
            return

        success, _error, api_key, api_secret, passphrase = self.engine.unlock_credentials(password)

        if success:
            self.on_success(api_key, api_secret, passphrase)
            self.destroy()
        else:
            self.attempts += 1
            remaining = self.max_attempts - self.attempts
            if remaining > 0:
                self.error_label.configure(text=f"密碼錯誤，還剩 {remaining} 次機會")
                self.password_entry.delete(0, "end")
            else:
                self.error_label.configure(text="密碼錯誤次數過多")
                self.after(1500, self._on_close)

    def _reset(self):
        # 確認重置
        confirm = ctk.CTkInputDialog(
            text="輸入 RESET 確認重置所有設定",
            title="確認重置"
        )
        if confirm.get_input() == "RESET":
            self.engine.reset_credentials()
            self.destroy()
            # 重新顯示設定對話框
            SetupDialog(self.master, self.engine, self.on_success)

    def _on_close(self):
        self.destroy()
        self.master.destroy()


class ChangeAPIDialog(ctk.CTkToplevel):
    """更換 API 憑證對話框

    Story 1.2: 建立骨架框架
    Story 1.3: 實作完整的更換功能
    """

    def __init__(self, master, app: "ASGridApp"):
        super().__init__(master)
        self.app = app

        self.title("更換 API 憑證")
        self.geometry("450x400")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PRIMARY)

        # 模態設定
        self.transient(master)
        self.grab_set()

        # 視窗關閉處理
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda e: self.destroy())

        # 置中顯示
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 450) // 2
        y = (screen_height - 400) // 2
        self.geometry(f"450x400+{x}+{y}")

        self._create_ui()

    def _create_ui(self):
        """建立更換 API 表單 UI"""
        # 標題
        ctk.CTkLabel(
            self,
            text="🔄 更換 API 金鑰",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(30, 8))

        ctk.CTkLabel(
            self,
            text="請輸入現有密碼和新的 API 憑證",
            font=ctk.CTkFont(size=13),
            text_color=Colors.TEXT_SECONDARY
        ).pack(pady=(0, 24))

        # 現有密碼
        ctk.CTkLabel(
            self, text="現有密碼",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", padx=32)
        self.password_entry = ctk.CTkEntry(
            self,
            fg_color=Colors.BG_TERTIARY,
            border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY,
            height=40,
            width=386,
            show="*"
        )
        self.password_entry.pack(padx=32, pady=(4, 12))

        # 新 API Key
        ctk.CTkLabel(
            self, text="新 API Key",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", padx=32)
        self.api_key_entry = ctk.CTkEntry(
            self,
            fg_color=Colors.BG_TERTIARY,
            border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY,
            height=40,
            width=386
        )
        self.api_key_entry.pack(padx=32, pady=(4, 12))

        # 新 API Secret
        ctk.CTkLabel(
            self, text="新 API Secret",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", padx=32)
        self.api_secret_entry = ctk.CTkEntry(
            self,
            fg_color=Colors.BG_TERTIARY,
            border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY,
            height=40,
            width=386,
            show="*"
        )
        self.api_secret_entry.pack(padx=32, pady=(4, 16))

        # 錯誤訊息標籤
        self.error_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=Colors.RED
        )
        self.error_label.pack(pady=(0, 8))

        # 按鈕容器
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=(8, 20))

        # 取消按鈕
        ctk.CTkButton(
            button_frame,
            text="取消",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=Colors.BG_TERTIARY,
            text_color=Colors.TEXT_PRIMARY,
            hover_color=Colors.BORDER,
            height=44,
            width=150,
            corner_radius=8,
            command=self.destroy
        ).pack(side="left", padx=(0, 8))

        # 確認更換按鈕
        self.submit_button = ctk.CTkButton(
            button_frame,
            text="確認更換",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            height=44,
            width=150,
            corner_radius=8,
            command=self._on_submit
        )
        self.submit_button.pack(side="left")

    def _on_submit(self):
        """處理確認更換按鈕點擊"""
        # 清除之前的錯誤訊息
        self.error_label.configure(text="")

        # 取得輸入值（密碼不 strip，可能包含前後空格作為有效字元）
        current_password = self.password_entry.get()
        new_api_key = self.api_key_entry.get().strip()
        new_api_secret = self.api_secret_entry.get().strip()

        # 驗證必填欄位
        if not current_password:
            self.error_label.configure(text="請輸入現有密碼")
            return

        # 驗證 API 格式 (長度 10-128 字元)
        if not new_api_key or len(new_api_key) < 10:
            self.error_label.configure(text="API Key 格式不正確（長度至少 10 字元）")
            return
        if len(new_api_key) > 128:
            self.error_label.configure(text="API Key 格式不正確（長度超過上限）")
            return
        if not new_api_secret or len(new_api_secret) < 10:
            self.error_label.configure(text="API Secret 格式不正確（長度至少 10 字元）")
            return
        if len(new_api_secret) > 128:
            self.error_label.configure(text="API Secret 格式不正確（長度超過上限）")
            return

        # 禁用按鈕，防止重複提交
        self.submit_button.configure(state="disabled", text="處理中...")

        # 保存原有 API（用於連接失敗時回滾）
        old_api_key = self.app.api_key
        old_api_secret = self.app.api_secret

        try:
            # 呼叫 CredentialManager 更新憑證
            self.app.engine.credential_manager.update_api_credentials(
                current_password,
                new_api_key,
                new_api_secret
            )
        except InvalidPasswordError:
            self.error_label.configure(text="密碼錯誤")
            self.submit_button.configure(state="normal", text="確認更換")
            return
        except ValueError as e:
            self.error_label.configure(text=str(e))
            self.submit_button.configure(state="normal", text="確認更換")
            return

        # 憑證更新成功，測試新 API 連接
        self._test_new_connection(
            new_api_key, new_api_secret,
            old_api_key, old_api_secret,
            current_password
        )

    def _test_new_connection(self, new_api_key, new_api_secret,
                              old_api_key, old_api_secret, current_password):
        """測試新 API 連接（在背景執行）"""
        # 保存 executor 引用以便後續清理
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        def _async_test():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # 斷開現有連接
                if self.app.engine.is_connected:
                    loop.run_until_complete(self.app.engine.disconnect())

                # 測試新連接
                success = loop.run_until_complete(
                    self.app.engine.connect(new_api_key, new_api_secret)
                )
                return success
            finally:
                loop.close()

        def _on_test_complete():
            try:
                success = future.result()
            except (concurrent.futures.CancelledError, RuntimeError, ConnectionError):
                # 連接被取消、執行時錯誤或連接錯誤
                success = False

            # 清理 executor 資源
            self._executor.shutdown(wait=False)

            if success:
                # 連接成功
                self._show_success()
            else:
                # 連接失敗，回滾憑證
                self._rollback_credentials(
                    old_api_key, old_api_secret, current_password
                )

        future = self._executor.submit(_async_test)

        # 定時檢查結果
        def check_result():
            if future.done():
                _on_test_complete()
            else:
                self.after(100, check_result)

        self.after(100, check_result)

    def _rollback_credentials(self, old_api_key, old_api_secret, current_password):
        """回滾到原有憑證"""
        try:
            self.app.engine.credential_manager.update_api_credentials(
                current_password,
                old_api_key,
                old_api_secret
            )
            # 嘗試重新連接原有 API
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    self.app.engine.connect(old_api_key, old_api_secret)
                )
            finally:
                loop.close()
        except Exception:
            pass  # 回滾失敗，保持當前狀態

        self.error_label.configure(text="API 金鑰無效，請檢查")
        self.submit_button.configure(state="normal", text="確認更換")

    def _show_success(self):
        """顯示成功訊息並關閉對話框"""
        # 更新應用程式中的 API 金鑰
        self.app.api_key = self.api_key_entry.get().strip()
        self.app.api_secret = self.api_secret_entry.get().strip()

        # 顯示成功訊息
        self.error_label.configure(text="✓ API 更換成功", text_color=Colors.GREEN)
        self.submit_button.configure(state="disabled")

        # 1.5 秒後關閉對話框
        self.after(1500, self.destroy)


class MigrationDialog(ctk.CTkToplevel):
    """舊版配置遷移對話框

    Story 1.5: 配置遷移工具與舊版相容
    偵測到舊版明文 API 配置時顯示，引導用戶設定加密密碼並遷移。
    """

    def __init__(self, parent, api_key: str, api_secret: str, config_path: Path, on_success: callable):
        super().__init__(parent)
        self.parent = parent
        self.api_key = api_key
        self.api_secret = api_secret
        self.config_path = config_path
        self.on_success = on_success

        self.title("配置遷移")
        self.geometry("480x550")
        self.resizable(False, False)
        self.configure(fg_color=Colors.BG_PRIMARY)

        # 模態設定
        self.transient(parent)
        self.grab_set()

        # 視窗關閉處理
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self._on_close())

        # 置中顯示
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 480) // 2
        y = (screen_height - 550) // 2
        self.geometry(f"480x550+{x}+{y}")

        self._create_ui()

    def _create_ui(self):
        """建立遷移表單 UI"""
        # 標題
        ctk.CTkLabel(
            self,
            text="🔐 配置安全升級",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=Colors.TEXT_PRIMARY
        ).pack(pady=(30, 8))

        ctk.CTkLabel(
            self,
            text="偵測到舊版明文 API 配置",
            font=ctk.CTkFont(size=14),
            text_color=Colors.TEXT_SECONDARY
        ).pack(pady=(0, 16))

        # 說明卡片
        info_card = ctk.CTkFrame(self, fg_color=Colors.BG_TERTIARY, corner_radius=8)
        info_card.pack(fill="x", padx=32, pady=(0, 20))
        ctk.CTkLabel(
            info_card,
            text="為了保護您的 API 安全，系統將：\n\n"
                 "1. 使用 AES-256-GCM 加密您的 API 憑證\n"
                 "2. 備份原始配置檔\n"
                 "3. 從配置檔移除明文 API\n\n"
                 "請設定一個密碼用於解鎖憑證。",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_SECONDARY,
            justify="left"
        ).pack(padx=16, pady=16, anchor="w")

        # API 預覽 (隱藏部分)
        api_preview = f"API Key: {self.api_key[:8]}...{self.api_key[-4:]}"
        ctk.CTkLabel(
            self,
            text=api_preview,
            font=ctk.CTkFont(size=11, family="Courier"),
            text_color=Colors.TEXT_MUTED
        ).pack(pady=(0, 16))

        # 密碼設定
        ctk.CTkLabel(
            self, text="設定加密密碼",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", padx=32)
        self.password_entry = ctk.CTkEntry(
            self,
            fg_color=Colors.BG_TERTIARY,
            border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY,
            height=40,
            width=416,
            show="*",
            placeholder_text="至少 8 個字元"
        )
        self.password_entry.pack(padx=32, pady=(4, 4))
        self.password_entry.bind("<KeyRelease>", self._check_strength)

        # 密碼強度
        self.strength_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(size=10),
            text_color=Colors.TEXT_MUTED
        )
        self.strength_label.pack(anchor="w", padx=32, pady=(0, 12))

        # 確認密碼
        ctk.CTkLabel(
            self, text="確認密碼",
            font=ctk.CTkFont(size=12),
            text_color=Colors.TEXT_SECONDARY
        ).pack(anchor="w", padx=32)
        self.confirm_entry = ctk.CTkEntry(
            self,
            fg_color=Colors.BG_TERTIARY,
            border_color=Colors.BORDER, text_color=Colors.TEXT_PRIMARY,
            height=40,
            width=416,
            show="*"
        )
        self.confirm_entry.pack(padx=32, pady=(4, 16))

        # 錯誤訊息標籤
        self.error_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=Colors.RED
        )
        self.error_label.pack(pady=(0, 8))

        # 按鈕容器
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(pady=(8, 20))

        # 跳過按鈕 (手動設定)
        ctk.CTkButton(
            button_frame,
            text="跳過 (手動設定)",
            font=ctk.CTkFont(size=13),
            fg_color=Colors.BG_TERTIARY,
            text_color=Colors.TEXT_MUTED,
            hover_color=Colors.BORDER,
            height=40,
            width=150,
            corner_radius=8,
            command=self._skip_migration
        ).pack(side="left", padx=(0, 8))

        # 開始遷移按鈕
        self.submit_button = ctk.CTkButton(
            button_frame,
            text="開始遷移",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=Colors.ACCENT,
            text_color=Colors.BG_PRIMARY,
            hover_color=Colors.GREEN_DARK,
            height=44,
            width=150,
            corner_radius=8,
            command=self._do_migration
        )
        self.submit_button.pack(side="left")

    def _check_strength(self, _event=None):
        """檢查密碼強度"""
        password = self.password_entry.get()
        if not password:
            self.strength_label.configure(text="")
            return

        from client.secure_storage import check_password_strength
        level, name, _suggestions = check_password_strength(password)
        # 灰階顏色用於密碼強度 (從弱到強)
        colors = [Colors.RED, Colors.RED_DARK, Colors.YELLOW, Colors.GREEN_DARK, Colors.GREEN]
        self.strength_label.configure(text=f"密碼強度: {name}", text_color=colors[min(level, 4)])

    def _do_migration(self):
        """執行遷移"""
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()

        # 驗證密碼
        if len(password) < 8:
            self.error_label.configure(text="密碼長度至少需要 8 個字元")
            return
        if password != confirm:
            self.error_label.configure(text="兩次輸入的密碼不一致")
            return

        # 禁用按鈕
        self.submit_button.configure(state="disabled", text="遷移中...")

        # 執行遷移
        from client.secure_storage import migrate_legacy_config
        success, message = migrate_legacy_config(
            self.config_path,
            self.api_key,
            self.api_secret,
            password
        )

        if success:
            self.error_label.configure(text="✓ " + message, text_color=Colors.GREEN)
            # 1.5 秒後繼續
            self.after(1500, lambda: self._finish_migration(password))
        else:
            self.error_label.configure(text=message)
            self.submit_button.configure(state="normal", text="開始遷移")

    def _finish_migration(self, password: str):
        """遷移完成，進入解鎖流程"""
        from client.secure_storage import CredentialManager
        manager = CredentialManager()
        try:
            api_key, api_secret = manager.unlock(password)
            self.destroy()
            if self.on_success:
                self.on_success(api_key, api_secret)
        except Exception as e:
            self.error_label.configure(text=f"解鎖失敗: {e}")
            self.submit_button.configure(state="normal", text="開始遷移")

    def _skip_migration(self):
        """跳過遷移，使用手動設定"""
        self.destroy()
        # 開啟首次設定視窗
        # 注意：這裡需要導入 SetupWindow（如果有的話）或使用 SetupDialog
        # 由於 SetupWindow 可能未定義，先使用 SetupDialog
        from gui.app import ASGridApp
        # 這裡假設 parent 有 engine 屬性
        if hasattr(self.parent, 'engine'):
            SetupDialog(self.parent, self.parent.engine, self.on_success)

    def _on_close(self):
        """視窗關閉處理"""
        self.destroy()
        self.parent.destroy()
