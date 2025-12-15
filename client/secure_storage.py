"""
AS Grid Trading - 安全儲存模組

使用 AES-256-GCM 加密 API Key/Secret
密碼使用 Scrypt KDF 衍生加密金鑰

安全特性：
1. API Key/Secret 永遠不傳輸到任何伺服器
2. 使用用戶自己的密碼加密
3. 加密使用業界標準 AES-256-GCM
4. 密碼永不儲存，僅在記憶體中短暫存在
5. 即使開發者也無法解密用戶的 API
"""

import os
import json
import base64
import secrets
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.backends import default_backend

# 模組匯出列表
__all__ = [
    'SecureStorage',
    'CredentialManager',
    'InvalidPasswordError',
    'EncryptedData',
    'check_password_strength',
    'check_legacy_config',
    'migrate_legacy_config',
    'needs_migration',
]


class InvalidPasswordError(Exception):
    """
    密碼驗證失敗異常

    當用戶提供的密碼無法解密現有憑證時拋出此異常。
    用於區分密碼錯誤與其他類型的錯誤（如檔案不存在、格式錯誤等）。
    """
    pass


@dataclass
class EncryptedData:
    """加密資料結構"""
    salt: bytes          # 密碼鹽值（隨機生成）
    nonce: bytes         # 加密隨機數
    ciphertext: bytes    # 加密後的資料
    version: int = 1     # 加密版本（未來升級用）


class SecureStorage:
    """
    安全儲存類

    安全特性：
    1. 使用 Scrypt KDF 從密碼衍生加密金鑰
    2. 使用 AES-256-GCM 進行認證加密
    3. 每次加密使用隨機 salt 和 nonce
    4. 密碼永不儲存，僅在記憶體中短暫存在
    """

    # Scrypt 參數（提高破解難度）
    SCRYPT_N = 2**17      # CPU/記憶體成本（約需 128MB 記憶體）
    SCRYPT_R = 8          # 區塊大小
    SCRYPT_P = 1          # 並行度
    SCRYPT_LENGTH = 32    # 金鑰長度（256 bits）

    # 檔案路徑 (Bitget 版本使用獨立檔案)
    DEFAULT_FILE = ".as_credentials_bitget.enc"

    def __init__(self, storage_path: Optional[Path] = None):
        """
        初始化安全儲存

        Args:
            storage_path: 加密檔案路徑，預設為用戶目錄下的隱藏檔案
        """
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path.home() / self.DEFAULT_FILE

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """
        從密碼衍生加密金鑰

        使用 Scrypt KDF，這是目前最安全的密碼衍生函數之一
        GPU/ASIC 破解成本極高
        """
        kdf = Scrypt(
            salt=salt,
            length=self.SCRYPT_LENGTH,
            n=self.SCRYPT_N,
            r=self.SCRYPT_R,
            p=self.SCRYPT_P,
            backend=default_backend()
        )
        return kdf.derive(password.encode('utf-8'))

    def encrypt_credentials(
        self,
        api_key: str,
        api_secret: str,
        password: str,
        passphrase: str = "",
        extra_data: Optional[Dict] = None
    ) -> None:
        """
        加密並儲存 API 憑證

        Args:
            api_key: Bitget API Key
            api_secret: Bitget API Secret
            password: 用戶設定的密碼（至少 8 字元）
            passphrase: Bitget API Passphrase（Bitget 必要）
            extra_data: 額外資料（如交易所名稱等）

        Raises:
            ValueError: 密碼太短
        """
        # 密碼強度檢查
        if len(password) < 8:
            raise ValueError("密碼長度至少需要 8 個字元")

        # 準備要加密的資料
        data = {
            "api_key": api_key,
            "api_secret": api_secret,
            "passphrase": passphrase,  # Bitget 專用
            "created_at": int(time.time()),
        }
        if extra_data:
            data["extra"] = extra_data

        plaintext = json.dumps(data).encode('utf-8')

        # 生成隨機 salt 和 nonce
        salt = secrets.token_bytes(32)
        nonce = secrets.token_bytes(12)  # GCM 標準 nonce 長度

        # 衍生加密金鑰
        key = self._derive_key(password, salt)

        # AES-256-GCM 加密
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # 儲存加密資料
        encrypted = EncryptedData(
            salt=salt,
            nonce=nonce,
            ciphertext=ciphertext
        )

        self._save_to_file(encrypted)

        # 清除記憶體中的敏感資料
        del key, plaintext

    def decrypt_credentials(self, password: str) -> Tuple[str, str, str, Optional[Dict]]:
        """
        解密 API 憑證

        Args:
            password: 用戶密碼

        Returns:
            (api_key, api_secret, passphrase, extra_data)

        Raises:
            FileNotFoundError: 加密檔案不存在
            ValueError: 密碼錯誤
        """
        if not self.storage_path.exists():
            raise FileNotFoundError("尚未設定 API 憑證，請先執行首次設定")

        encrypted = self._load_from_file()

        # 衍生解密金鑰
        key = self._derive_key(password, encrypted.salt)

        # AES-256-GCM 解密
        aesgcm = AESGCM(key)

        try:
            plaintext = aesgcm.decrypt(encrypted.nonce, encrypted.ciphertext, None)
        except Exception:
            raise ValueError("密碼錯誤，無法解密")

        # 解析資料
        data = json.loads(plaintext.decode('utf-8'))

        # 清除記憶體中的敏感資料
        del key

        return (
            data["api_key"],
            data["api_secret"],
            data.get("passphrase", ""),  # Bitget 專用，向後兼容
            data.get("extra")
        )

    def _save_to_file(self, encrypted: EncryptedData) -> None:
        """儲存加密資料到檔案"""
        data = {
            "version": encrypted.version,
            "salt": base64.b64encode(encrypted.salt).decode(),
            "nonce": base64.b64encode(encrypted.nonce).decode(),
            "ciphertext": base64.b64encode(encrypted.ciphertext).decode()
        }

        # 確保目錄存在
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # 寫入檔案
        self.storage_path.write_text(json.dumps(data, indent=2))

        # 設定檔案權限（僅用戶可讀寫）- Unix 系統
        try:
            os.chmod(self.storage_path, 0o600)
        except (OSError, AttributeError):
            pass  # Windows 不支援

    def _load_from_file(self) -> EncryptedData:
        """從檔案讀取加密資料"""
        data = json.loads(self.storage_path.read_text())

        return EncryptedData(
            version=data.get("version", 1),
            salt=base64.b64decode(data["salt"]),
            nonce=base64.b64decode(data["nonce"]),
            ciphertext=base64.b64decode(data["ciphertext"])
        )

    def change_password(self, old_password: str, new_password: str) -> None:
        """
        更換密碼

        Args:
            old_password: 舊密碼
            new_password: 新密碼
        """
        # 用舊密碼解密
        api_key, api_secret, passphrase, extra = self.decrypt_credentials(old_password)

        # 用新密碼重新加密
        self.encrypt_credentials(api_key, api_secret, new_password, passphrase, extra)

        # 清除記憶體
        del api_key, api_secret, passphrase

    def exists(self) -> bool:
        """檢查是否已有加密檔案"""
        return self.storage_path.exists()

    def delete(self) -> None:
        """刪除加密檔案（安全刪除）"""
        if self.storage_path.exists():
            # 覆寫後刪除（安全刪除）
            size = self.storage_path.stat().st_size
            self.storage_path.write_bytes(secrets.token_bytes(size))
            self.storage_path.unlink()


class CredentialManager:
    """
    憑證管理器（高階 API）- Bitget 版本

    使用範例：
    ```python
    manager = CredentialManager()

    # 首次設定 (Bitget 需要 passphrase)
    if not manager.is_configured():
        manager.setup(api_key, api_secret, password, passphrase)

    # 每次啟動
    api_key, api_secret, passphrase = manager.unlock(password)

    # 使用完畢
    manager.lock()
    ```
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage = SecureStorage(storage_path)
        self._api_key: Optional[str] = None
        self._api_secret: Optional[str] = None
        self._passphrase: Optional[str] = None  # Bitget 專用
        self._unlocked = False

    def is_configured(self) -> bool:
        """是否已設定 API"""
        return self.storage.exists()

    def setup(self, api_key: str, api_secret: str, password: str, passphrase: str = "") -> None:
        """
        首次設定 API 憑證

        Args:
            api_key: Bitget API Key
            api_secret: Bitget API Secret
            password: 加密密碼（至少 8 字元，建議包含大小寫、數字、符號）
            passphrase: Bitget API Passphrase（Bitget 必要）
        """
        # 驗證 API 格式
        if not api_key or len(api_key) < 10:
            raise ValueError("API Key 格式不正確")
        if not api_secret or len(api_secret) < 10:
            raise ValueError("API Secret 格式不正確")

        self.storage.encrypt_credentials(api_key, api_secret, password, passphrase)

    def unlock(self, password: str) -> Tuple[str, str, str]:
        """
        解鎖憑證

        Args:
            password: 密碼

        Returns:
            (api_key, api_secret, passphrase)
        """
        api_key, api_secret, passphrase, _ = self.storage.decrypt_credentials(password)

        self._api_key = api_key
        self._api_secret = api_secret
        self._passphrase = passphrase
        self._unlocked = True

        return api_key, api_secret, passphrase

    def lock(self) -> None:
        """鎖定並清除記憶體中的憑證"""
        self._api_key = None
        self._api_secret = None
        self._passphrase = None
        self._unlocked = False

    def get_credentials(self) -> Tuple[str, str, str]:
        """取得憑證（需先 unlock）"""
        if not self._unlocked:
            raise RuntimeError("憑證已鎖定，請先呼叫 unlock()")
        return self._api_key, self._api_secret, self._passphrase

    @property
    def is_unlocked(self) -> bool:
        """是否已解鎖"""
        return self._unlocked

    def change_password(self, old_password: str, new_password: str) -> None:
        """更換密碼"""
        self.storage.change_password(old_password, new_password)

    def reset(self) -> None:
        """重置（刪除加密檔案）"""
        self.lock()
        self.storage.delete()

    def update_api_credentials(
        self,
        current_password: str,
        new_api_key: str,
        new_api_secret: str,
        new_passphrase: str = ""
    ) -> bool:
        """
        更換 API 憑證

        使用現有密碼驗證身份後，更換為新的 API 金鑰。
        密碼本身不會改變，只更換 API 憑證。

        Args:
            current_password: 現有密碼（用於驗證和重新加密）
            new_api_key: 新的 Bitget API Key
            new_api_secret: 新的 Bitget API Secret
            new_passphrase: 新的 Bitget Passphrase（Bitget 必要）

        Returns:
            True 表示更換成功

        Raises:
            InvalidPasswordError: 密碼錯誤，無法驗證身份
            ValueError: API Key/Secret 格式不正確（長度 < 10）
            FileNotFoundError: 尚未設定憑證

        Example:
            >>> manager = CredentialManager()
            >>> manager.update_api_credentials(
            ...     current_password="MyPassword123!",
            ...     new_api_key="new_bitget_api_key_here",
            ...     new_api_secret="new_bitget_api_secret_here",
            ...     new_passphrase="your_passphrase"
            ... )
            True
        """
        # 1. 驗證新 API 格式
        if not new_api_key or len(new_api_key) < 10:
            raise ValueError("API Key 格式不正確")
        if not new_api_secret or len(new_api_secret) < 10:
            raise ValueError("API Secret 格式不正確")

        # 2. 驗證現有密碼（嘗試解密現有憑證）
        try:
            self.storage.decrypt_credentials(current_password)
        except ValueError:
            raise InvalidPasswordError("密碼錯誤，無法更換 API")

        # 3. 使用相同密碼重新加密新的 API 憑證
        self.storage.encrypt_credentials(new_api_key, new_api_secret, current_password, new_passphrase)

        # 4. 驗證新加密的資料正確（解密後應與輸入一致）
        api_key = None
        api_secret = None
        passphrase = None
        try:
            api_key, api_secret, passphrase, _ = self.storage.decrypt_credentials(current_password)
            if api_key != new_api_key or api_secret != new_api_secret:
                raise RuntimeError("加密驗證失敗：資料不一致")
        except RuntimeError:
            raise  # 重新拋出 RuntimeError
        except Exception as e:
            raise RuntimeError(f"加密驗證失敗: {e}") from e
        finally:
            # 安全清除記憶體中的敏感資料
            del api_key, api_secret, passphrase

        # 5. 如果目前已 unlock，更新記憶體中的憑證（確保狀態一致性）
        if self._unlocked:
            self._api_key = new_api_key
            self._api_secret = new_api_secret
            self._passphrase = new_passphrase

        return True


# ========== 密碼強度檢查 ==========

def check_password_strength(password: str) -> Tuple[int, str, list]:
    """
    檢查密碼強度

    Returns:
        (score, level_name, suggestions)
        score: 0-4 分
        level_name: 強度等級名稱
        suggestions: 改進建議
    """
    score = 0
    suggestions = []

    # 長度檢查
    if len(password) >= 8:
        score += 1
    else:
        suggestions.append("長度至少 8 字元")

    if len(password) >= 12:
        score += 1
    elif len(password) >= 8:
        suggestions.append("建議長度 12 字元以上")

    # 大寫字母
    if any(c.isupper() for c in password):
        score += 0.5
    else:
        suggestions.append("建議包含大寫字母")

    # 小寫字母
    if any(c.islower() for c in password):
        score += 0.5

    # 數字
    if any(c.isdigit() for c in password):
        score += 0.5
    else:
        suggestions.append("建議包含數字")

    # 特殊符號
    special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    if any(c in special_chars for c in password):
        score += 0.5
    else:
        suggestions.append("建議包含特殊符號")

    # 等級名稱
    strength_levels = ["非常弱", "弱", "中等", "強", "非常強"]
    level = min(int(score), 4)
    level_name = strength_levels[level]

    return level, level_name, suggestions


# ========== 舊版配置遷移 ==========

def check_legacy_config(config_path: Path) -> Optional[Tuple[str, str]]:
    """
    檢查是否存在舊版明文 API 配置

    Args:
        config_path: 配置檔案路徑 (trading_config_max.json)

    Returns:
        (api_key, api_secret) 如果存在明文 API，否則 None
    """
    if not config_path.exists():
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        api_key = config.get('api_key', '').strip()
        api_secret = config.get('api_secret', '').strip()

        # 檢查是否有有效的明文 API
        if api_key and len(api_key) >= 10 and api_secret and len(api_secret) >= 10:
            return (api_key, api_secret)

        return None

    except (json.JSONDecodeError, IOError):
        return None


def migrate_legacy_config(
    config_path: Path,
    api_key: str,
    api_secret: str,
    password: str,
    backup: bool = True
) -> Tuple[bool, str]:
    """
    遷移舊版配置到加密儲存

    1. 使用提供的密碼加密 API 憑證
    2. 備份原始配置檔
    3. 從配置檔移除明文 API

    Args:
        config_path: 配置檔案路徑
        api_key: 要遷移的 API Key
        api_secret: 要遷移的 API Secret
        password: 加密密碼 (至少 8 字元)
        backup: 是否備份原始配置

    Returns:
        (成功, 訊息)
    """
    try:
        # 1. 密碼驗證
        if len(password) < 8:
            return False, "密碼長度至少需要 8 個字元"

        # 2. 加密並儲存憑證
        manager = CredentialManager()
        manager.setup(api_key, api_secret, password)

        # 3. 驗證加密成功
        try:
            decrypted_key, decrypted_secret = manager.unlock(password)
            if decrypted_key != api_key or decrypted_secret != api_secret:
                return False, "加密驗證失敗：資料不一致"
            manager.lock()
        except Exception as e:
            return False, f"加密驗證失敗: {e}"

        # 4. 備份原始配置
        if backup and config_path.exists():
            backup_path = config_path.with_suffix('.json.bak')
            import shutil
            shutil.copy2(config_path, backup_path)

        # 5. 從配置檔移除明文 API
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)

                # 移除明文 API 欄位
                removed = False
                if 'api_key' in config:
                    del config['api_key']
                    removed = True
                if 'api_secret' in config:
                    del config['api_secret']
                    removed = True

                if removed:
                    with open(config_path, 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)

            except (json.JSONDecodeError, IOError) as e:
                # 配置檔修改失敗不影響遷移成功
                return True, f"憑證已加密儲存，但配置檔清理失敗: {e}"

        return True, "遷移成功！API 憑證已加密儲存。"

    except ValueError as e:
        return False, f"加密失敗: {e}"
    except Exception as e:
        return False, f"遷移失敗: {e}"


def needs_migration(config_path: Path) -> bool:
    """
    檢查是否需要遷移

    條件：
    1. 加密憑證檔案不存在
    2. 配置檔包含明文 API

    Returns:
        True 如果需要遷移
    """
    manager = CredentialManager()

    # 如果已有加密憑證，不需要遷移
    if manager.is_configured():
        return False

    # 檢查是否有舊版明文配置
    legacy_creds = check_legacy_config(config_path)
    return legacy_creds is not None


# ========== 測試 ==========

if __name__ == "__main__":
    # 簡單測試
    print("=== 安全儲存模組測試 ===\n")

    # 測試密碼強度
    test_passwords = ["123", "password", "Password1", "MyP@ssw0rd!123"]
    for pwd in test_passwords:
        level, name, suggestions = check_password_strength(pwd)
        print(f"密碼: {pwd}")
        print(f"  強度: {name} ({level}/4)")
        if suggestions:
            print(f"  建議: {', '.join(suggestions)}")
        print()

    # 測試加密解密
    print("=== 加密解密測試 ===\n")

    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.enc', delete=False) as f:
        test_path = Path(f.name)

    try:
        manager = CredentialManager(test_path)

        # 設定
        test_key = "test_api_key_1234567890"
        test_secret = "test_api_secret_1234567890"
        test_password = "MySecurePassword123!"

        print(f"設定 API 憑證...")
        manager.setup(test_key, test_secret, test_password)
        print(f"已加密儲存到: {test_path}\n")

        # 解鎖
        print("解鎖憑證...")
        api_key, api_secret = manager.unlock(test_password)
        print(f"API Key: {api_key[:10]}...{api_key[-4:]}")
        print(f"API Secret: {api_secret[:10]}...{api_secret[-4:]}")

        # 驗證
        assert api_key == test_key
        assert api_secret == test_secret
        print("\n✅ 基本加密解密測試通過！")

        # ========== 測試 update_api_credentials ==========
        print("\n=== 測試 update_api_credentials ===\n")

        # 測試 1: 正常更換流程 (AC-1)
        print("測試 1: 正常更換 API 金鑰...")
        new_key = "new_api_key_1234567890"
        new_secret = "new_api_secret_1234567890"
        result = manager.update_api_credentials(test_password, new_key, new_secret)
        assert result == True, "更換應返回 True"

        # 驗證新金鑰已儲存 (AC-4)
        unlocked_key, unlocked_secret = manager.unlock(test_password)
        assert unlocked_key == new_key, "新 API Key 應正確儲存"
        assert unlocked_secret == new_secret, "新 API Secret 應正確儲存"
        print("✅ 正常更換流程測試通過！")

        # 測試 2: 密碼錯誤情況 (AC-2)
        print("\n測試 2: 密碼錯誤時應拋出 InvalidPasswordError...")
        try:
            manager.update_api_credentials("wrong_password", new_key, new_secret)
            assert False, "應該拋出 InvalidPasswordError"
        except InvalidPasswordError as e:
            assert "密碼錯誤" in str(e)
            print(f"✅ 密碼錯誤測試通過！拋出: {e}")

        # 測試 3: API 格式驗證 (AC-3)
        print("\n測試 3: API 格式驗證（太短應拋出 ValueError）...")

        # 測試 API Key 太短
        try:
            manager.update_api_credentials(test_password, "short", new_secret)
            assert False, "API Key 太短應該拋出 ValueError"
        except ValueError as e:
            assert "API Key 格式不正確" in str(e)
            print(f"✅ API Key 格式驗證通過！拋出: {e}")

        # 測試 API Secret 太短
        try:
            manager.update_api_credentials(test_password, new_key, "short")
            assert False, "API Secret 太短應該拋出 ValueError"
        except ValueError as e:
            assert "API Secret 格式不正確" in str(e)
            print(f"✅ API Secret 格式驗證通過！拋出: {e}")

        # 測試 4: 已 unlock 狀態下更換後記憶體更新
        print("\n測試 4: 已 unlock 狀態下記憶體更新...")
        manager.unlock(test_password)
        assert manager.is_unlocked, "應該處於 unlock 狀態"

        updated_key = "updated_api_key_12345678"
        updated_secret = "updated_api_secret_12345"
        manager.update_api_credentials(test_password, updated_key, updated_secret)

        # 檢查記憶體中的憑證已更新
        mem_key, mem_secret = manager.get_credentials()
        assert mem_key == updated_key, "記憶體中的 API Key 應已更新"
        assert mem_secret == updated_secret, "記憶體中的 API Secret 應已更新"
        print("✅ 記憶體更新測試通過！")

        # 測試 5: 未設定憑證時呼叫（重置後測試）
        print("\n測試 5: 未設定憑證時呼叫應拋出 FileNotFoundError...")
        manager.reset()

        try:
            manager.update_api_credentials(test_password, new_key, new_secret)
            assert False, "未設定憑證時應該拋出 FileNotFoundError"
        except FileNotFoundError:
            print("✅ 未設定憑證測試通過！")

        print("\n" + "=" * 50)
        print("✅ 所有 update_api_credentials 測試通過！")
        print("=" * 50)

    finally:
        # 清理
        if test_path.exists():
            test_path.unlink()
