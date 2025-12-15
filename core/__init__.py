"""
AS Grid Trading - 核心模組
==========================

提供統一的基礎設施：
- 配置管理 (AppConfig)
- 日誌系統 (setup_logging)
- 錯誤處理 (CCXTErrorHandler)
- 常量定義 (Constants)
- 路徑解析 (path_resolver) - 支援打包環境
"""

from .config import AppConfig, get_config
from .logging_setup import setup_logging, get_logger
from .error_handler import CCXTErrorHandler, handle_ccxt_error
from .constants import Constants
from .path_resolver import (
    get_app_dir,
    get_resource_path,
    get_asback_path,
    get_backtest_data_dir,
    get_config_dir,
    ensure_backtest_module_path,
    is_compiled,
    debug_paths,
)

__all__ = [
    'AppConfig',
    'get_config',
    'setup_logging',
    'get_logger',
    'CCXTErrorHandler',
    'handle_ccxt_error',
    'Constants',
    # 路徑解析
    'get_app_dir',
    'get_resource_path',
    'get_asback_path',
    'get_backtest_data_dir',
    'get_config_dir',
    'ensure_backtest_module_path',
    'is_compiled',
    'debug_paths',
]

__version__ = '1.0.0'
