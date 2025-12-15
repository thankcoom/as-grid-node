"""
CCXT 錯誤處理模組

基於 Context7 獲取的 CCXT 最佳實踐，提供：
- 分類錯誤處理
- 自動重試機制
- 錯誤恢復策略
"""

import asyncio
import logging
from typing import Optional, Callable, Any, TypeVar, Awaitable
from functools import wraps
from dataclasses import dataclass
from enum import Enum
import time

try:
    import ccxt
    import ccxt.async_support as ccxt_async
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    ccxt = None
    ccxt_async = None

from .constants import ErrorCodes


class ErrorSeverity(Enum):
    """錯誤嚴重程度"""
    LOW = "low"           # 可忽略，自動重試
    MEDIUM = "medium"     # 需要處理，可恢復
    HIGH = "high"         # 嚴重錯誤，需要人工介入
    CRITICAL = "critical" # 致命錯誤，停止交易


@dataclass
class ErrorInfo:
    """錯誤資訊"""
    code: int
    message: str
    severity: ErrorSeverity
    retryable: bool
    retry_delay: float = 1.0
    original_exception: Optional[Exception] = None


class CCXTErrorHandler:
    """
    CCXT 錯誤處理器

    基於 CCXT 官方錯誤層級：
    - BaseError
      ├── ExchangeError
      │   ├── AuthenticationError
      │   ├── PermissionDenied
      │   ├── AccountSuspended
      │   ├── ArgumentsRequired
      │   ├── BadRequest
      │   ├── BadSymbol
      │   ├── MarginModeAlreadySet
      │   ├── BadResponse
      │   ├── NullResponse
      │   ├── InsufficientFunds
      │   ├── InvalidAddress
      │   ├── AddressPending
      │   ├── InvalidOrder
      │   │   ├── OrderNotFound
      │   │   ├── OrderNotCached
      │   │   ├── CancelPending
      │   │   ├── OrderImmediatelyFillable
      │   │   ├── OrderNotFillable
      │   │   ├── DuplicateOrderId
      │   │   └── ContractUnavailable
      │   ├── NotSupported
      │   ├── ProxyError
      │   ├── ExchangeClosedByUser
      │   └── OperationRejected
      │       ├── OnMaintenance
      │       └── AccountNotEnabled
      ├── NetworkError
      │   ├── DDoSProtection
      │   │   └── RateLimitExceeded
      │   ├── ExchangeNotAvailable
      │   │   └── OnMaintenance
      │   ├── InvalidNonce
      │   └── RequestTimeout
      └── OperationFailed (async-specific)
          ├── CancelPending
          ├── OrderNotCached
          └── NetworkError
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger("ccxt_error_handler")
        self._error_counts: dict = {}  # 追蹤錯誤次數

    def classify_error(self, exception: Exception) -> ErrorInfo:
        """
        分類錯誤並返回錯誤資訊

        Args:
            exception: 捕獲的異常

        Returns:
            ErrorInfo: 錯誤資訊
        """
        if not CCXT_AVAILABLE:
            return ErrorInfo(
                code=ErrorCodes.INTERNAL_ERROR,
                message=str(exception),
                severity=ErrorSeverity.HIGH,
                retryable=False,
                original_exception=exception
            )

        # === 網路錯誤（通常可重試）===
        if isinstance(exception, ccxt.RateLimitExceeded):
            return ErrorInfo(
                code=ErrorCodes.RATE_LIMIT,
                message="API 速率限制，請稍後重試",
                severity=ErrorSeverity.LOW,
                retryable=True,
                retry_delay=60.0,  # 等待較長時間
                original_exception=exception
            )

        if isinstance(exception, ccxt.DDoSProtection):
            return ErrorInfo(
                code=ErrorCodes.DDOS_PROTECTION,
                message="觸發 DDoS 保護，暫停請求",
                severity=ErrorSeverity.MEDIUM,
                retryable=True,
                retry_delay=120.0,
                original_exception=exception
            )

        if isinstance(exception, ccxt.RequestTimeout):
            return ErrorInfo(
                code=ErrorCodes.TIMEOUT_ERROR,
                message="請求超時",
                severity=ErrorSeverity.LOW,
                retryable=True,
                retry_delay=5.0,
                original_exception=exception
            )

        if isinstance(exception, ccxt.ExchangeNotAvailable):
            return ErrorInfo(
                code=ErrorCodes.EXCHANGE_NOT_AVAILABLE,
                message="交易所暫時不可用",
                severity=ErrorSeverity.MEDIUM,
                retryable=True,
                retry_delay=30.0,
                original_exception=exception
            )

        if isinstance(exception, ccxt.NetworkError):
            return ErrorInfo(
                code=ErrorCodes.NETWORK_ERROR,
                message=f"網路錯誤: {str(exception)}",
                severity=ErrorSeverity.LOW,
                retryable=True,
                retry_delay=10.0,
                original_exception=exception
            )

        # === 認證錯誤（不可重試）===
        if isinstance(exception, ccxt.AuthenticationError):
            return ErrorInfo(
                code=ErrorCodes.AUTH_ERROR,
                message="API 認證失敗，請檢查 API Key",
                severity=ErrorSeverity.CRITICAL,
                retryable=False,
                original_exception=exception
            )

        if isinstance(exception, ccxt.PermissionDenied):
            return ErrorInfo(
                code=ErrorCodes.PERMISSION_DENIED,
                message="權限不足，請檢查 API 權限設定",
                severity=ErrorSeverity.HIGH,
                retryable=False,
                original_exception=exception
            )

        # === 交易錯誤 ===
        if isinstance(exception, ccxt.InsufficientFunds):
            return ErrorInfo(
                code=ErrorCodes.INSUFFICIENT_BALANCE,
                message="餘額不足",
                severity=ErrorSeverity.HIGH,
                retryable=False,
                original_exception=exception
            )

        if isinstance(exception, ccxt.OrderNotFound):
            return ErrorInfo(
                code=ErrorCodes.ORDER_NOT_FOUND,
                message="訂單不存在",
                severity=ErrorSeverity.LOW,
                retryable=False,
                original_exception=exception
            )

        if isinstance(exception, ccxt.InvalidOrder):
            return ErrorInfo(
                code=ErrorCodes.INVALID_ORDER,
                message=f"無效訂單: {str(exception)}",
                severity=ErrorSeverity.MEDIUM,
                retryable=False,
                original_exception=exception
            )

        # === 其他交易所錯誤 ===
        if isinstance(exception, ccxt.ExchangeError):
            # 檢查是否是最小名義價值錯誤
            if "MIN_NOTIONAL" in str(exception):
                return ErrorInfo(
                    code=ErrorCodes.MIN_NOTIONAL_ERROR,
                    message="訂單金額低於最小限制",
                    severity=ErrorSeverity.MEDIUM,
                    retryable=False,
                    original_exception=exception
                )

            return ErrorInfo(
                code=ErrorCodes.INTERNAL_ERROR,
                message=f"交易所錯誤: {str(exception)}",
                severity=ErrorSeverity.MEDIUM,
                retryable=False,
                original_exception=exception
            )

        # === 未知錯誤 ===
        return ErrorInfo(
            code=ErrorCodes.INTERNAL_ERROR,
            message=f"未知錯誤: {str(exception)}",
            severity=ErrorSeverity.HIGH,
            retryable=False,
            original_exception=exception
        )

    def handle_error(self, exception: Exception, context: str = "") -> ErrorInfo:
        """
        處理錯誤並記錄日誌

        Args:
            exception: 捕獲的異常
            context: 錯誤上下文

        Returns:
            ErrorInfo: 錯誤資訊
        """
        error_info = self.classify_error(exception)

        # 追蹤錯誤次數
        error_key = f"{error_info.code}:{context}"
        self._error_counts[error_key] = self._error_counts.get(error_key, 0) + 1

        # 記錄日誌
        log_msg = f"[{context}] {error_info.message} (代碼: {error_info.code})"

        if error_info.severity == ErrorSeverity.LOW:
            self.logger.warning(log_msg)
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.error(log_msg)
        else:
            self.logger.critical(log_msg)

        return error_info

    def get_error_stats(self) -> dict:
        """獲取錯誤統計"""
        return dict(self._error_counts)

    def clear_error_stats(self):
        """清除錯誤統計"""
        self._error_counts.clear()


# === 裝飾器 ===

T = TypeVar('T')


def handle_ccxt_error(
    max_retries: int = 3,
    logger: Optional[logging.Logger] = None,
    context: str = ""
) -> Callable:
    """
    CCXT 錯誤處理裝飾器

    Args:
        max_retries: 最大重試次數
        logger: 日誌記錄器
        context: 錯誤上下文

    Usage:
        @handle_ccxt_error(max_retries=3, context="獲取餘額")
        async def get_balance(exchange):
            return await exchange.fetch_balance()
    """
    handler = CCXTErrorHandler(logger)

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None
            ctx = context or func.__name__

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_info = handler.handle_error(e, ctx)

                    if not error_info.retryable or attempt >= max_retries:
                        raise

                    if handler.logger:
                        handler.logger.info(
                            f"[{ctx}] 重試 {attempt + 1}/{max_retries}，"
                            f"等待 {error_info.retry_delay:.1f}s"
                        )
                    await asyncio.sleep(error_info.retry_delay)

            raise last_exception

        return wrapper
    return decorator


def retry_on_network_error(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential: bool = True
) -> Callable:
    """
    網路錯誤重試裝飾器（指數退避）

    Args:
        max_retries: 最大重試次數
        base_delay: 基礎延遲（秒）
        max_delay: 最大延遲（秒）
        exponential: 是否使用指數退避
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    # 只重試網路相關錯誤
                    if CCXT_AVAILABLE and isinstance(e, (
                        ccxt.NetworkError,
                        ccxt.RequestTimeout,
                        ccxt.ExchangeNotAvailable
                    )):
                        last_exception = e
                        if attempt >= max_retries:
                            raise

                        if exponential:
                            delay = min(base_delay * (2 ** attempt), max_delay)
                        else:
                            delay = base_delay

                        await asyncio.sleep(delay)
                    else:
                        raise

            raise last_exception

        return wrapper
    return decorator


class ErrorRecovery:
    """錯誤恢復策略"""

    @staticmethod
    async def reconnect_exchange(exchange, logger: Optional[logging.Logger] = None):
        """重新連接交易所"""
        if logger:
            logger.info("嘗試重新連接交易所...")

        try:
            await exchange.close()
        except Exception:
            pass

        await asyncio.sleep(5)

        try:
            await exchange.load_markets()
            if logger:
                logger.info("交易所重新連接成功")
            return True
        except Exception as e:
            if logger:
                logger.error(f"交易所重新連接失敗: {e}")
            return False

    @staticmethod
    async def safe_cancel_order(
        exchange,
        order_id: str,
        symbol: str,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """安全取消訂單"""
        try:
            await exchange.cancel_order(order_id, symbol)
            return True
        except Exception as e:
            if CCXT_AVAILABLE and isinstance(e, ccxt.OrderNotFound):
                # 訂單已經不存在，視為成功
                return True
            if logger:
                logger.error(f"取消訂單失敗: {e}")
            return False
