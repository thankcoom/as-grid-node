"""
常量定義模組
"""


class Constants:
    """應用程式常量"""

    # 應用程式資訊
    APP_NAME = "AS Grid Trading"
    APP_VERSION = "2.0.0"

    # 支援的交易所
    SUPPORTED_EXCHANGES = ["bitget"]

    # 支援的計價貨幣
    QUOTE_CURRENCIES = ["USDC", "USDT"]

    # 預設值
    DEFAULT_LEVERAGE = 20
    DEFAULT_ORDER_VALUE = 10.0
    DEFAULT_INITIAL_BALANCE = 1000.0
    DEFAULT_TP_SPACING = 0.004  # 0.4%
    DEFAULT_GRID_SPACING = 0.006  # 0.6%
    DEFAULT_MAX_POSITIONS = 50
    DEFAULT_FEE_PCT = 0.0004  # 0.04%

    # WebSocket 設定
    WS_PING_INTERVAL = 20  # 秒
    WS_PONG_TIMEOUT = 10   # 秒
    WS_RECONNECT_DELAY = 5  # 秒
    WS_MAX_RECONNECT_ATTEMPTS = 5

    # API 速率限制
    API_RATE_LIMIT_DELAY = 0.1  # 秒
    API_BATCH_SIZE = 15

    # 快取設定
    CACHE_TTL_TICKER = 5       # 秒
    CACHE_TTL_OHLCV = 60       # 秒
    CACHE_TTL_MARKETS = 3600   # 秒
    CACHE_MAX_SIZE = 1000      # 最大快取項目數

    # 日誌設定
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5
    LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

    # 回測設定
    BACKTEST_DEFAULT_DAYS = 30
    BACKTEST_TIMEFRAMES = ["1m", "5m", "15m", "1h", "4h", "1d"]

    # GUI 設定
    GUI_REFRESH_INTERVAL = 1000  # 毫秒
    GUI_CHART_UPDATE_INTERVAL = 5000  # 毫秒

    # 風控設定
    DEFAULT_MAX_DRAWDOWN = 0.5  # 50%
    POSITION_THRESHOLD = 500.0  # 裝死模式閾值
    POSITION_LIMIT = 100.0      # 止盈加倍閾值


class ErrorCodes:
    """錯誤代碼"""

    # 網路錯誤 (1xxx)
    NETWORK_ERROR = 1001
    TIMEOUT_ERROR = 1002
    CONNECTION_REFUSED = 1003

    # 認證錯誤 (2xxx)
    AUTH_ERROR = 2001
    INVALID_API_KEY = 2002
    PERMISSION_DENIED = 2003

    # 交易錯誤 (3xxx)
    INSUFFICIENT_BALANCE = 3001
    INVALID_ORDER = 3002
    ORDER_NOT_FOUND = 3003
    MIN_NOTIONAL_ERROR = 3004

    # 速率限制 (4xxx)
    RATE_LIMIT = 4001
    DDOS_PROTECTION = 4002

    # 系統錯誤 (5xxx)
    EXCHANGE_NOT_AVAILABLE = 5001
    MAINTENANCE = 5002
    INTERNAL_ERROR = 5003
