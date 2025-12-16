"""
Logging Middleware
記錄每個請求的詳細資訊，便於調試和審計
"""
import time
import logging
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# 設置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("api")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    請求日誌中間件
    記錄：IP、路徑、方法、狀態碼、處理時間
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 獲取客戶端 IP
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            client_ip = forwarded_for.split(",")[0].strip()
        
        # 處理請求
        response = await call_next(request)
        
        # 計算處理時間
        process_time = (time.time() - start_time) * 1000  # 毫秒
        
        # 記錄日誌（跳過健康檢查）
        if request.url.path not in ["/", "/health"]:
            log_message = (
                f"{client_ip} | "
                f"{request.method} {request.url.path} | "
                f"{response.status_code} | "
                f"{process_time:.2f}ms"
            )
            
            if response.status_code >= 400:
                logger.warning(log_message)
            else:
                logger.info(log_message)
        
        # 添加處理時間到響應頭
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        
        return response
