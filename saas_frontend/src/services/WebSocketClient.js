/**
 * WebSocket 客戶端 - 即時數據連線
 * 
 * 提供與 Grid Node 的即時連線，實現類似 GUI 的即時更新體驗
 */

class WebSocketClient {
    constructor() {
        this.ws = null;
        this.nodeUrl = null;
        this.callbacks = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.isConnected = false;
        this.pingInterval = null;
    }

    /**
     * 連接到 Grid Node WebSocket
     * @param {string} nodeUrl - Grid Node URL (不含 /ws)
     */
    connect(nodeUrl) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.disconnect();
        }

        this.nodeUrl = nodeUrl;
        const wsUrl = nodeUrl.replace('https://', 'wss://').replace('http://', 'ws://');

        try {
            this.ws = new WebSocket(`${wsUrl}/api/v1/ws`);

            this.ws.onopen = () => {
                console.log('[WebSocket] Connected to Grid Node');
                this.isConnected = true;
                this.reconnectAttempts = 0;
                this.startPing();

                if (this.callbacks.onConnect) {
                    this.callbacks.onConnect();
                }
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (e) {
                    console.error('[WebSocket] Parse error:', e);
                }
            };

            this.ws.onerror = (error) => {
                console.error('[WebSocket] Error:', error);
                if (this.callbacks.onError) {
                    this.callbacks.onError(error);
                }
            };

            this.ws.onclose = (event) => {
                console.log('[WebSocket] Disconnected:', event.code, event.reason);
                this.isConnected = false;
                this.stopPing();

                if (this.callbacks.onDisconnect) {
                    this.callbacks.onDisconnect();
                }

                // 自動重連
                if (this.reconnectAttempts < this.maxReconnectAttempts) {
                    this.reconnectAttempts++;
                    console.log(`[WebSocket] Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
                    setTimeout(() => this.connect(this.nodeUrl), this.reconnectDelay);
                }
            };
        } catch (e) {
            console.error('[WebSocket] Connection failed:', e);
        }
    }

    /**
     * 斷開連線
     */
    disconnect() {
        this.stopPing();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.isConnected = false;
    }

    /**
     * 處理收到的訊息
     */
    handleMessage(message) {
        const { type, data } = message;

        switch (type) {
            case 'account':
                if (this.callbacks.onAccount) {
                    this.callbacks.onAccount(data);
                }
                break;

            case 'positions':
                if (this.callbacks.onPositions) {
                    this.callbacks.onPositions(data);
                }
                break;

            case 'indicators':
                if (this.callbacks.onIndicators) {
                    this.callbacks.onIndicators(data);
                }
                break;

            case 'status':
                if (this.callbacks.onStatus) {
                    this.callbacks.onStatus(data);
                }
                break;

            case 'log':
                if (this.callbacks.onLog) {
                    this.callbacks.onLog(data);
                }
                break;

            case 'trade':
                if (this.callbacks.onTrade) {
                    this.callbacks.onTrade(data);
                }
                break;

            case 'pong':
                // Ping-pong 心跳回應
                break;

            default:
                console.log('[WebSocket] Unknown message type:', type);
        }
    }

    /**
     * 註冊回調函數
     * @param {string} event - 事件名稱
     * @param {function} callback - 回調函數
     */
    on(event, callback) {
        this.callbacks[event] = callback;
    }

    /**
     * 移除回調函數
     * @param {string} event - 事件名稱
     */
    off(event) {
        delete this.callbacks[event];
    }

    /**
     * 發送訊息到伺服器
     */
    send(type, data = {}) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type, data }));
        }
    }

    /**
     * 開始 ping 心跳
     */
    startPing() {
        this.pingInterval = setInterval(() => {
            this.send('ping');
        }, 30000); // 每 30 秒 ping 一次
    }

    /**
     * 停止 ping 心跳
     */
    stopPing() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }
}

// 單例模式
let wsClient = null;

export function getWebSocketClient() {
    if (!wsClient) {
        wsClient = new WebSocketClient();
    }
    return wsClient;
}

export default WebSocketClient;
