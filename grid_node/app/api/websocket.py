"""
WebSocket 端點 - 即時數據推送

提供與 GUI 相同的即時更新體驗：
- 帳戶餘額即時更新
- 持倉變化即時通知
- 指標數據即時推送
- 交易日誌即時顯示
"""
import asyncio
import json
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """WebSocket 連線管理器"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """廣播訊息給所有連線"""
        if not self.active_connections:
            return
        
        data = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                disconnected.append(connection)
        
        # 清理斷開的連線
        for conn in disconnected:
            self.disconnect(conn)
    
    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]):
        """發送訊息給特定客戶端"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.warning(f"Failed to send personal message: {e}")


# 全局連線管理器
manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket 端點 - 即時數據推送
    
    訊息格式:
    {
        "type": "account" | "positions" | "indicators" | "log" | "status",
        "data": { ... }
    }
    """
    from app.services.bot_manager import bot_manager
    
    await manager.connect(websocket)
    
    try:
        # 連線後立即發送當前狀態
        await send_initial_state(websocket, bot_manager)
        
        # 開始定期推送更新
        update_task = asyncio.create_task(
            periodic_updates(websocket, bot_manager)
        )
        
        # 接收客戶端訊息（保持連線活躍）
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 處理客戶端命令
                if message.get("type") == "ping":
                    await manager.send_personal(websocket, {"type": "pong"})
                elif message.get("type") == "subscribe":
                    # 可以添加訂閱特定數據的邏輯
                    pass
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                pass
            except Exception as e:
                logger.error(f"WebSocket receive error: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        update_task.cancel()
        manager.disconnect(websocket)


async def send_initial_state(websocket: WebSocket, bot_manager):
    """發送初始狀態"""
    try:
        status = bot_manager._get_heartbeat_status()
        
        # 發送帳戶餘額
        await manager.send_personal(websocket, {
            "type": "account",
            "data": {
                "equity": status.get("equity", 0),
                "available_balance": status.get("available_balance", 0),
                "unrealized_pnl": status.get("unrealized_pnl", 0),
                "total_pnl": status.get("total_pnl", 0)
            }
        })
        
        # 發送持倉
        await manager.send_personal(websocket, {
            "type": "positions",
            "data": status.get("positions", [])
        })
        
        # 發送交易狀態
        await manager.send_personal(websocket, {
            "type": "status",
            "data": {
                "is_trading": status.get("is_trading", False),
                "is_paused": status.get("is_paused", False),
                "symbols": status.get("symbols", [])
            }
        })
        
        # 發送指標
        if status.get("indicators"):
            await manager.send_personal(websocket, {
                "type": "indicators",
                "data": status.get("indicators")
            })
            
    except Exception as e:
        logger.error(f"Failed to send initial state: {e}")


async def periodic_updates(websocket: WebSocket, bot_manager):
    """定期推送更新（每 2 秒）"""
    last_status = {}
    
    while True:
        try:
            await asyncio.sleep(2)  # 2 秒更新一次
            
            current_status = bot_manager._get_heartbeat_status()
            
            # 只發送變化的數據
            # 帳戶餘額
            account_data = {
                "equity": current_status.get("equity", 0),
                "available_balance": current_status.get("available_balance", 0),
                "unrealized_pnl": current_status.get("unrealized_pnl", 0),
                "total_pnl": current_status.get("total_pnl", 0)
            }
            
            if account_data != last_status.get("account"):
                await manager.send_personal(websocket, {
                    "type": "account",
                    "data": account_data
                })
                last_status["account"] = account_data
            
            # 持倉
            positions = current_status.get("positions", [])
            if positions != last_status.get("positions"):
                await manager.send_personal(websocket, {
                    "type": "positions",
                    "data": positions
                })
                last_status["positions"] = positions
            
            # 指標
            indicators = current_status.get("indicators")
            if indicators and indicators != last_status.get("indicators"):
                await manager.send_personal(websocket, {
                    "type": "indicators",
                    "data": indicators
                })
                last_status["indicators"] = indicators
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Periodic update error: {e}")
            break


# 公開的 broadcast 函數供 bot_manager 調用
async def broadcast_log(message: str):
    """廣播交易日誌"""
    await manager.broadcast({
        "type": "log",
        "data": {"message": message, "timestamp": asyncio.get_event_loop().time()}
    })


async def broadcast_trade(trade: Dict[str, Any]):
    """廣播成交通知"""
    await manager.broadcast({
        "type": "trade",
        "data": trade
    })
