"""
統一配置管理模組

使用 pydantic 進行配置驗證，支援環境變數和 .env 文件
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from functools import lru_cache
import json

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field, validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseSettings = object

from .constants import Constants


if PYDANTIC_AVAILABLE:
    class AppConfig(BaseSettings):
        """應用程式統一配置"""

        # === 應用程式基本設定 ===
        app_name: str = Constants.APP_NAME
        app_version: str = Constants.APP_VERSION
        debug: bool = False
        log_level: str = "INFO"

        # === 交易所設定 ===
        exchange: str = "bitget"
        api_key: Optional[str] = Field(default=None, env="BITGET_API_KEY")
        api_secret: Optional[str] = Field(default=None, env="BITGET_API_SECRET")
        testnet: bool = False

        # === 交易設定 ===
        leverage: int = Constants.DEFAULT_LEVERAGE
        order_value: float = Constants.DEFAULT_ORDER_VALUE
        initial_balance: float = Constants.DEFAULT_INITIAL_BALANCE
        tp_spacing: float = Constants.DEFAULT_TP_SPACING
        grid_spacing: float = Constants.DEFAULT_GRID_SPACING
        max_positions: int = Constants.DEFAULT_MAX_POSITIONS
        fee_pct: float = Constants.DEFAULT_FEE_PCT

        # === 風控設定 ===
        max_drawdown: float = Constants.DEFAULT_MAX_DRAWDOWN
        position_threshold: float = Constants.POSITION_THRESHOLD
        position_limit: float = Constants.POSITION_LIMIT

        # === WebSocket 設定 ===
        ws_ping_interval: int = Constants.WS_PING_INTERVAL
        ws_pong_timeout: int = Constants.WS_PONG_TIMEOUT
        ws_reconnect_delay: int = Constants.WS_RECONNECT_DELAY
        ws_max_reconnect: int = Constants.WS_MAX_RECONNECT_ATTEMPTS

        # === 快取設定 ===
        cache_ttl_ticker: int = Constants.CACHE_TTL_TICKER
        cache_ttl_ohlcv: int = Constants.CACHE_TTL_OHLCV
        cache_max_size: int = Constants.CACHE_MAX_SIZE

        # === 日誌設定 ===
        log_max_bytes: int = Constants.LOG_MAX_BYTES
        log_backup_count: int = Constants.LOG_BACKUP_COUNT
        log_dir: str = "log"

        # === 資料庫設定 ===
        database_url: str = "sqlite+aiosqlite:///./as_grid.db"

        # === GUI 設定 ===
        gui_refresh_interval: int = Constants.GUI_REFRESH_INTERVAL
        gui_theme: str = "dark"  # dark, light, system

        @property
        def async_database_url(self) -> str:
            """轉換為 async 格式"""
            url = self.database_url
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url

        @property
        def log_path(self) -> Path:
            """日誌目錄路徑"""
            path = Path(self.log_dir)
            path.mkdir(parents=True, exist_ok=True)
            return path

        def has_api_credentials(self) -> bool:
            """檢查是否有 API 憑證"""
            return bool(self.api_key and self.api_secret)

        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = "ignore"

else:
    # Fallback: 不依賴 pydantic
    @dataclass
    class AppConfig:
        """應用程式統一配置 (Fallback 版本)"""

        app_name: str = Constants.APP_NAME
        app_version: str = Constants.APP_VERSION
        debug: bool = False
        log_level: str = "INFO"

        exchange: str = "bitget"
        api_key: Optional[str] = None
        api_secret: Optional[str] = None
        api_passphrase: Optional[str] = None
        testnet: bool = False

        leverage: int = Constants.DEFAULT_LEVERAGE
        order_value: float = Constants.DEFAULT_ORDER_VALUE
        initial_balance: float = Constants.DEFAULT_INITIAL_BALANCE
        tp_spacing: float = Constants.DEFAULT_TP_SPACING
        grid_spacing: float = Constants.DEFAULT_GRID_SPACING
        max_positions: int = Constants.DEFAULT_MAX_POSITIONS
        fee_pct: float = Constants.DEFAULT_FEE_PCT

        max_drawdown: float = Constants.DEFAULT_MAX_DRAWDOWN
        position_threshold: float = Constants.POSITION_THRESHOLD
        position_limit: float = Constants.POSITION_LIMIT

        ws_ping_interval: int = Constants.WS_PING_INTERVAL
        ws_pong_timeout: int = Constants.WS_PONG_TIMEOUT
        ws_reconnect_delay: int = Constants.WS_RECONNECT_DELAY
        ws_max_reconnect: int = Constants.WS_MAX_RECONNECT_ATTEMPTS

        cache_ttl_ticker: int = Constants.CACHE_TTL_TICKER
        cache_ttl_ohlcv: int = Constants.CACHE_TTL_OHLCV
        cache_max_size: int = Constants.CACHE_MAX_SIZE

        log_max_bytes: int = Constants.LOG_MAX_BYTES
        log_backup_count: int = Constants.LOG_BACKUP_COUNT
        log_dir: str = "log"

        database_url: str = "sqlite+aiosqlite:///./as_grid.db"
        gui_refresh_interval: int = Constants.GUI_REFRESH_INTERVAL
        gui_theme: str = "dark"

        def __post_init__(self):
            # 從環境變數讀取
            self.api_key = os.getenv("BITGET_API_KEY", self.api_key)
            self.api_secret = os.getenv("BITGET_API_SECRET", self.api_secret)
            self.api_passphrase = os.getenv("BITGET_API_PASSPHRASE", self.api_passphrase)
            self.debug = os.getenv("DEBUG", "false").lower() == "true"
            self.log_level = os.getenv("LOG_LEVEL", self.log_level)

        @property
        def async_database_url(self) -> str:
            url = self.database_url
            if url.startswith("postgresql://"):
                return url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url

        @property
        def log_path(self) -> Path:
            path = Path(self.log_dir)
            path.mkdir(parents=True, exist_ok=True)
            return path

        def has_api_credentials(self) -> bool:
            return bool(self.api_key and self.api_secret)


# 全域配置實例
_config_instance: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """獲取配置單例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig()
    return _config_instance


def reload_config() -> AppConfig:
    """重新載入配置"""
    global _config_instance
    _config_instance = AppConfig()
    return _config_instance


@dataclass
class TradingConfig:
    """交易配置（用於策略）"""

    symbol: str = "XRPUSDC"
    initial_balance: float = Constants.DEFAULT_INITIAL_BALANCE
    order_value: float = Constants.DEFAULT_ORDER_VALUE
    leverage: int = Constants.DEFAULT_LEVERAGE

    take_profit_spacing: float = Constants.DEFAULT_TP_SPACING
    grid_spacing: float = Constants.DEFAULT_GRID_SPACING

    max_drawdown: float = Constants.DEFAULT_MAX_DRAWDOWN
    max_positions: int = Constants.DEFAULT_MAX_POSITIONS
    fee_pct: float = Constants.DEFAULT_FEE_PCT

    position_threshold: float = Constants.POSITION_THRESHOLD
    position_limit: float = Constants.POSITION_LIMIT

    direction: str = "both"  # long, short, both
    grid_refresh_interval: int = 5

    dead_mode_enabled: bool = True
    dead_mode_fallback_long: float = 1.05
    dead_mode_fallback_short: float = 0.95

    @property
    def long_settings(self) -> Dict[str, float]:
        return {
            "up_spacing": self.take_profit_spacing,
            "down_spacing": self.grid_spacing
        }

    @property
    def short_settings(self) -> Dict[str, float]:
        return {
            "up_spacing": self.grid_spacing,
            "down_spacing": self.take_profit_spacing
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "initial_balance": self.initial_balance,
            "order_value": self.order_value,
            "leverage": self.leverage,
            "take_profit_spacing": self.take_profit_spacing,
            "grid_spacing": self.grid_spacing,
            "max_drawdown": self.max_drawdown,
            "max_positions": self.max_positions,
            "fee_pct": self.fee_pct,
            "direction": self.direction,
            "grid_refresh_interval": self.grid_refresh_interval,
            "position_threshold": self.position_threshold,
            "position_limit": self.position_limit,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingConfig':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def save(self, filepath: str):
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'TradingConfig':
        with open(filepath, 'r') as f:
            return cls.from_dict(json.load(f))
