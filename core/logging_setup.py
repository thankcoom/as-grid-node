"""
日誌系統模組

提供：
- 自動日誌輪轉 (RotatingFileHandler)
- 統一格式化
- 多層級日誌
- 顏色輸出（終端機）
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from datetime import datetime

from .constants import Constants


class ColoredFormatter(logging.Formatter):
    """帶顏色的日誌格式化器（用於終端機）"""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'

    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)


def setup_logging(
    name: str = "as_grid",
    level: str = "INFO",
    log_dir: str = "log",
    max_bytes: int = Constants.LOG_MAX_BYTES,
    backup_count: int = Constants.LOG_BACKUP_COUNT,
    console_output: bool = True,
    file_output: bool = True,
    colored: bool = True,
) -> logging.Logger:
    """
    設置日誌系統

    Args:
        name: 日誌名稱
        level: 日誌級別 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: 日誌目錄
        max_bytes: 單個日誌文件最大大小
        backup_count: 保留的備份文件數量
        console_output: 是否輸出到控制台
        file_output: 是否輸出到文件
        colored: 是否使用顏色（僅控制台）

    Returns:
        logging.Logger: 配置好的 logger
    """
    # 創建日誌目錄
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 獲取 logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 清除現有處理器
    logger.handlers.clear()

    # 基本格式
    fmt = Constants.LOG_FORMAT
    date_fmt = Constants.LOG_DATE_FORMAT

    # 控制台處理器
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        if colored and sys.stdout.isatty():
            console_handler.setFormatter(ColoredFormatter(fmt, date_fmt))
        else:
            console_handler.setFormatter(logging.Formatter(fmt, date_fmt))
        logger.addHandler(console_handler)

    # 文件處理器（帶輪轉）
    if file_output:
        log_file = log_path / f"{name}.log"
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(fmt, date_fmt))
        logger.addHandler(file_handler)

        # 錯誤專用日誌
        error_log_file = log_path / f"{name}_error.log"
        error_handler = RotatingFileHandler(
            error_log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(fmt, date_fmt))
        logger.addHandler(error_handler)

    # 防止日誌傳播到根 logger
    logger.propagate = False

    return logger


# 全域 logger 快取
_loggers: dict = {}


def get_logger(name: str = "as_grid") -> logging.Logger:
    """
    獲取或創建 logger

    Args:
        name: logger 名稱

    Returns:
        logging.Logger: 配置好的 logger
    """
    if name not in _loggers:
        _loggers[name] = setup_logging(name)
    return _loggers[name]


class LogContext:
    """日誌上下文管理器，用於追蹤操作"""

    def __init__(self, logger: logging.Logger, operation: str, **context):
        self.logger = logger
        self.operation = operation
        self.context = context
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
        self.logger.info(f"[開始] {self.operation} | {context_str}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (datetime.now() - self.start_time).total_seconds()
        if exc_type is None:
            self.logger.info(f"[完成] {self.operation} | 耗時: {elapsed:.2f}s")
        else:
            self.logger.error(
                f"[失敗] {self.operation} | 耗時: {elapsed:.2f}s | "
                f"錯誤: {exc_type.__name__}: {exc_val}"
            )
        return False  # 不抑制異常


def log_operation(logger: logging.Logger, operation: str, **context):
    """
    創建日誌上下文

    Usage:
        with log_operation(logger, "獲取市場數據", symbol="BTC/USDT"):
            data = await exchange.fetch_ticker(symbol)
    """
    return LogContext(logger, operation, **context)
