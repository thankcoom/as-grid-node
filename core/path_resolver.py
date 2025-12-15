"""
AS Grid Trading - 路徑解析工具
==============================

提供跨平台、跨打包環境的路徑解析功能。
支援：
- 開發環境（直接運行 Python）
- Nuitka 打包（standalone / onefile）
- PyInstaller 打包
- macOS .app bundle

2025 最佳實踐：使用 Nuitka 官方推薦的 __compiled__ API
參考：https://nuitka.net/user-documentation/common-issue-solutions.html
"""

import sys
import os
import logging
from pathlib import Path
from typing import Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


def is_nuitka_compiled() -> bool:
    """檢查是否在 Nuitka 編譯環境中運行"""
    return "__compiled__" in dir()


def is_pyinstaller_compiled() -> bool:
    """檢查是否在 PyInstaller 打包環境中運行"""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def is_compiled() -> bool:
    """檢查是否在任何打包環境中運行"""
    return is_nuitka_compiled() or is_pyinstaller_compiled()


@lru_cache(maxsize=1)
def get_app_dir() -> Path:
    """
    獲取應用程式根目錄（2025 最佳實踐）

    Returns:
        Path: 應用程式根目錄的絕對路徑

    注意：
    - Nuitka 2.1.6+ 的 __compiled__.containing_dir 已修正為絕對路徑
    - 此函數會快取結果，只計算一次
    """
    # 方法 1：Nuitka 編譯環境（最可靠）
    if "__compiled__" in dir():
        try:
            # Nuitka 提供的官方 API
            # containing_dir 在 standalone 和 onefile 模式下都能正確工作
            compiled = __compiled__  # noqa: F821
            if hasattr(compiled, 'containing_dir'):
                app_dir = Path(compiled.containing_dir)
                logger.debug(f"Nuitka __compiled__.containing_dir: {app_dir}")
                return app_dir.resolve()
        except Exception as e:
            logger.warning(f"無法使用 __compiled__.containing_dir: {e}")

    # 方法 2：PyInstaller 打包環境
    if getattr(sys, 'frozen', False):
        if hasattr(sys, '_MEIPASS'):
            # PyInstaller 臨時解壓目錄
            app_dir = Path(sys._MEIPASS)
            logger.debug(f"PyInstaller _MEIPASS: {app_dir}")
            return app_dir.resolve()
        else:
            # 其他打包工具
            app_dir = Path(sys.executable).parent
            logger.debug(f"Frozen executable parent: {app_dir}")
            return app_dir.resolve()

    # 方法 3：開發環境 - 從此模組向上找到項目根目錄
    # core/path_resolver.py -> core/ -> 項目根目錄
    app_dir = Path(__file__).parent.parent
    logger.debug(f"Development mode: {app_dir}")
    return app_dir.resolve()


@lru_cache(maxsize=1)
def get_executable_dir() -> Path:
    """
    獲取執行檔所在目錄

    這與 get_app_dir() 不同：
    - get_app_dir(): 返回資源/代碼所在的目錄
    - get_executable_dir(): 返回執行檔本身所在的目錄

    在 macOS .app bundle 中，這兩者可能不同
    """
    return Path(sys.executable).parent.resolve()


def get_resource_path(relative_path: str) -> Path:
    """
    獲取資源文件的絕對路徑

    Args:
        relative_path: 相對於應用程式根目錄的路徑

    Returns:
        Path: 資源的絕對路徑

    Example:
        >>> config_path = get_resource_path("config/trading_config.json")
        >>> data_path = get_resource_path("asBack/data")
    """
    return get_app_dir() / relative_path


def get_asback_path() -> Optional[Path]:
    """
    獲取 asBack 目錄路徑（回測系統）

    Returns:
        Path: asBack 目錄的絕對路徑，如果找不到則返回 None
    """
    # 優先使用 app_dir 下的 asBack
    app_dir = get_app_dir()

    possible_paths = [
        # 標準位置
        app_dir / "asBack",
        # Nuitka standalone 輸出結構
        get_executable_dir() / "asBack",
        # macOS .app bundle 結構
        get_executable_dir().parent / "Resources" / "asBack",
        get_executable_dir().parent / "asBack",
        # 當前工作目錄
        Path.cwd() / "asBack",
    ]

    for path in possible_paths:
        if path.exists() and (path / "backtest_system").exists():
            logger.info(f"找到 asBack 路徑: {path}")
            return path.resolve()

    logger.warning(f"無法找到 asBack 路徑，嘗試過: {[str(p) for p in possible_paths]}")
    return None


def get_backtest_data_dir() -> Path:
    """
    獲取回測數據目錄

    Returns:
        Path: 數據目錄路徑
    """
    # 優先使用 asBack/data
    asback = get_asback_path()
    if asback:
        data_dir = asback / "data"
        if data_dir.exists():
            return data_dir

    # 嘗試其他可能的位置
    possible_paths = [
        get_app_dir() / "asBack" / "data",
        get_executable_dir() / "asBack" / "data",
        get_executable_dir() / "data",
    ]

    for path in possible_paths:
        if path.exists():
            return path.resolve()

    # 最後使用用戶快取目錄
    cache_dir = Path.home() / ".as_grid" / "backtest_data"
    cache_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"使用用戶快取目錄: {cache_dir}")
    return cache_dir


def get_config_dir() -> Path:
    """
    獲取配置文件目錄

    Returns:
        Path: config 目錄路徑
    """
    config_dir = get_app_dir() / "config"
    if config_dir.exists():
        return config_dir

    # 嘗試其他位置
    exe_config = get_executable_dir() / "config"
    if exe_config.exists():
        return exe_config

    # 使用用戶配置目錄
    user_config = Path.home() / ".as_grid" / "config"
    user_config.mkdir(parents=True, exist_ok=True)
    return user_config


def ensure_backtest_module_path():
    """
    確保 backtest_system 模組可以被正確導入

    這個函數會將 asBack 路徑加入 sys.path
    應該在程式啟動時調用一次
    """
    asback = get_asback_path()
    if asback and str(asback) not in sys.path:
        sys.path.insert(0, str(asback))
        logger.info(f"已將 asBack 加入 sys.path: {asback}")
        return True
    return False


def debug_paths():
    """
    輸出所有路徑資訊（用於除錯）
    """
    info = {
        "is_compiled": is_compiled(),
        "is_nuitka": is_nuitka_compiled(),
        "is_pyinstaller": is_pyinstaller_compiled(),
        "sys.executable": sys.executable,
        "sys.argv[0]": sys.argv[0] if sys.argv else "N/A",
        "__file__": __file__,
        "app_dir": str(get_app_dir()),
        "executable_dir": str(get_executable_dir()),
        "asback_path": str(get_asback_path() or "Not found"),
        "backtest_data_dir": str(get_backtest_data_dir()),
        "config_dir": str(get_config_dir()),
        "cwd": str(Path.cwd()),
    }

    logger.info("=== 路徑除錯資訊 ===")
    for key, value in info.items():
        logger.info(f"  {key}: {value}")

    return info


# ========== 模組級別的初始化 ==========

# 自動設置 backtest_system 路徑（僅在首次導入時執行）
_path_initialized = False

def _auto_init():
    """自動初始化路徑（僅執行一次）"""
    global _path_initialized
    if not _path_initialized:
        ensure_backtest_module_path()
        _path_initialized = True


# 導入時自動執行
_auto_init()
