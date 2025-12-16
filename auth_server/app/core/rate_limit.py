"""
Rate Limiting Middleware
使用 slowapi 實現 API 速率限制，防止暴力攻擊
"""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# 基於 IP 地址的速率限制器
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

# 預設限制：
# - 登入/註冊: 5 次/分鐘
# - 一般 API: 60 次/分鐘

# 使用方式：
# @app.get("/some-route")
# @limiter.limit("5/minute")
# async def some_route():
#     pass
