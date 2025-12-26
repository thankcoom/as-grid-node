/**
 * SSE (Server-Sent Events) 客戶端 - 即時數據連線
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * 【P2: SSE 前端通訊】
 *
 * 架構：
 * 前端 ← (JWT) → auth_server ← (NODE_SECRET) → Grid Node
 *
 * 優點 (相比 WebSocket):
 * - 更簡單的協議，瀏覽器原生支援
 * - 自動重連機制
 * - 更好的防火牆穿透性 (標準 HTTP)
 * - 通過 auth_server 代理，前端不需要知道 NODE_SECRET
 *
 * 事件類型:
 * - connected         - 連線成功
 * - status_update     - 狀態更新 (5 秒)
 * - account_update    - 帳戶餘額更新 (10 秒)
 * - position_update   - 持倉更新
 * - connection_status - 連線狀態變更
 * - heartbeat         - 心跳
 * - error             - 錯誤
 * ═══════════════════════════════════════════════════════════════════════════
 */

class SSEClient {
    constructor() {
        this.abortController = null;
        this.callbacks = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
        this.isConnected = false;
        this.reconnectTimer = null;
        this.authToken = null;
    }

    /**
     * 連接到 SSE 代理端點
     * @param {string} authToken - JWT token for authentication
     */
    connect(authToken) {
        if (this.abortController) {
            this.disconnect();
        }

        this.authToken = authToken;
        this.abortController = new AbortController();

        // 連接到 auth_server 的 SSE 代理端點
        this.connectToProxy();
    }

    /**
     * 連接到 auth_server SSE 代理
     */
    async connectToProxy() {
        // 使用與 api.js 相同的環境變數
        const authApiUrl = import.meta.env.VITE_AUTH_API_URL || '';
        const url = `${authApiUrl}/api/v1/proxy/sse/events`;

        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${this.authToken}`,
                    'Accept': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                },
                signal: this.abortController?.signal,
            });

            if (!response.ok) {
                throw new Error(`SSE connection failed: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            this.isConnected = true;
            this.reconnectAttempts = 0;
            console.log('[SSE] Connected via auth_server proxy');

            if (this.callbacks.onConnect) {
                this.callbacks.onConnect();
            }

            // 讀取 SSE 事件流
            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    console.log('[SSE] Stream ended');
                    break;
                }

                buffer += decoder.decode(value, { stream: true });

                // 解析 SSE 事件
                const events = this.parseSSEEvents(buffer);
                buffer = events.remaining;

                for (const event of events.parsed) {
                    this.handleEvent(event);
                }
            }

            // 連線結束，嘗試重連
            this.handleDisconnect();

        } catch (error) {
            // 忽略中止錯誤
            if (error.name === 'AbortError') {
                console.log('[SSE] Connection aborted');
                return;
            }

            console.error('[SSE] Connection error:', error);

            if (this.callbacks.onError) {
                this.callbacks.onError(error);
            }

            this.handleDisconnect();
        }
    }

    /**
     * 解析 SSE 事件
     */
    parseSSEEvents(buffer) {
        const parsed = [];
        const lines = buffer.split('\n');
        let remaining = '';
        let currentEvent = { type: null, data: null };

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i];

            // 事件邊界 (空行)
            if (line === '') {
                if (currentEvent.type && currentEvent.data) {
                    try {
                        parsed.push({
                            type: currentEvent.type,
                            data: JSON.parse(currentEvent.data)
                        });
                    } catch (e) {
                        console.error('[SSE] JSON parse error:', e);
                    }
                }
                currentEvent = { type: null, data: null };
                continue;
            }

            // 解析 event: 和 data: 欄位
            if (line.startsWith('event: ')) {
                currentEvent.type = line.substring(7);
            } else if (line.startsWith('data: ')) {
                currentEvent.data = line.substring(6);
            }
        }

        // 保留未完成的部分
        if (currentEvent.type || currentEvent.data) {
            remaining = lines.slice(-2).join('\n');
        }

        return { parsed, remaining };
    }

    /**
     * 處理 SSE 事件
     */
    handleEvent(event) {
        const { type, data } = event;

        switch (type) {
            case 'connected':
                console.log('[SSE] Server confirmed connection');
                break;

            case 'status_update':
                if (this.callbacks.onStatus) {
                    this.callbacks.onStatus(data);
                }
                // 也觸發 account 更新 (狀態中包含帳戶資訊)
                if (this.callbacks.onAccount) {
                    this.callbacks.onAccount({
                        equity: data.equity,
                        available_balance: data.available_balance,
                        unrealized_pnl: data.unrealized_pnl,
                        total_pnl: data.total_pnl,
                        usdt_equity: data.usdt_equity,
                        usdt_available: data.usdt_available,
                        usdc_equity: data.usdc_equity,
                        usdc_available: data.usdc_available,
                    });
                }
                break;

            case 'account_update':
                if (this.callbacks.onAccount) {
                    this.callbacks.onAccount(data);
                }
                break;

            case 'position_update':
                if (this.callbacks.onPositions) {
                    this.callbacks.onPositions(data.positions);
                }
                break;

            case 'connection_status':
                if (this.callbacks.onConnectionStatus) {
                    this.callbacks.onConnectionStatus(data);
                }
                break;

            case 'heartbeat':
                // 心跳 - 保持連線
                break;

            case 'error':
                console.error('[SSE] Server error:', data.message);
                if (this.callbacks.onError) {
                    this.callbacks.onError(new Error(data.message));
                }
                break;

            default:
                console.log('[SSE] Unknown event type:', type, data);
        }
    }

    /**
     * 處理斷線
     */
    handleDisconnect() {
        this.isConnected = false;

        if (this.callbacks.onDisconnect) {
            this.callbacks.onDisconnect();
        }

        // 自動重連
        if (this.reconnectAttempts < this.maxReconnectAttempts && this.authToken) {
            this.reconnectAttempts++;
            console.log(`[SSE] Reconnecting... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

            this.reconnectTimer = setTimeout(() => {
                this.abortController = new AbortController();
                this.connectToProxy();
            }, this.reconnectDelay * this.reconnectAttempts);
        }
    }

    /**
     * 斷開連線
     */
    disconnect() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }

        // 使用 AbortController 中止 fetch 請求
        if (this.abortController) {
            this.abortController.abort();
            this.abortController = null;
        }

        this.isConnected = false;
        this.reconnectAttempts = this.maxReconnectAttempts; // 防止自動重連

        console.log('[SSE] Disconnected');
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
}

// 單例模式
let sseClient = null;

export function getSSEClient() {
    if (!sseClient) {
        sseClient = new SSEClient();
    }
    return sseClient;
}

export default SSEClient;
