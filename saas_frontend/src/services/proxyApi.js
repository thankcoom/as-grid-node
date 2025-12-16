/**
 * Proxy API Service
 * 
 * 通過官方伺服器的代理層訪問用戶的 Grid Node
 * 所有 /proxy/* 請求會被轉發到用戶的 Node
 */
import api from './api';

/**
 * 獲取 Node 狀態（直接從官方伺服器）
 */
export const getNodeStatus = async () => {
    const response = await api.get('/node/my-status');
    return response.data;
};

/**
 * 測試 Node 連接
 */
export const testNodeConnection = async () => {
    const response = await api.get('/proxy/node/test');
    return response.data;
};

/**
 * 設定 Node URL
 */
export const setNodeUrl = async (nodeUrl) => {
    const response = await api.post('/proxy/node/url', null, {
        params: { node_url: nodeUrl }
    });
    return response.data;
};

// ═══════════════════════════════════════════════════════════════════════════
// Grid 交易控制（通過代理）
// ═══════════════════════════════════════════════════════════════════════════

export const gridApi = {
    /** 獲取交易狀態 */
    getStatus: async () => {
        const response = await api.get('/proxy/grid/status');
        return response.data;
    },

    /** 啟動交易 */
    start: async (symbol, quantity) => {
        const response = await api.post('/proxy/grid/start', { symbol, quantity });
        return response.data;
    },

    /** 停止交易 */
    stop: async () => {
        const response = await api.post('/proxy/grid/stop');
        return response.data;
    },
};

// ═══════════════════════════════════════════════════════════════════════════
// 選幣系統（通過代理）
// ═══════════════════════════════════════════════════════════════════════════

export const coinApi = {
    /** 掃描全部幣種 */
    scan: async (options = {}) => {
        const response = await api.post('/proxy/coin/scan', {
            force_refresh: options.forceRefresh || false,
            limit: options.limit || 20
        });
        return response.data;
    },

    /** 獲取緩存的排名 */
    getRankings: async () => {
        const response = await api.get('/proxy/coin/rankings');
        return response.data;
    },

    /** 檢查輪動 */
    checkRotation: async (currentSymbol) => {
        const response = await api.post('/proxy/coin/rotation/check', {
            current_symbol: currentSymbol
        });
        return response.data;
    },
};

// ═══════════════════════════════════════════════════════════════════════════
// 交易對管理（通過代理）
// ═══════════════════════════════════════════════════════════════════════════

export const symbolsApi = {
    /** 獲取交易對列表 */
    list: async () => {
        const response = await api.get('/proxy/symbols');
        return response.data;
    },

    /** 新增交易對 */
    add: async (symbolConfig) => {
        const response = await api.post('/proxy/symbols', symbolConfig);
        return response.data;
    },

    /** 更新交易對 */
    update: async (symbol, config) => {
        const response = await api.put(`/proxy/symbols/${symbol}`, config);
        return response.data;
    },

    /** 刪除交易對 */
    delete: async (symbol) => {
        const response = await api.delete(`/proxy/symbols/${symbol}`);
        return response.data;
    },

    /** 切換啟用狀態 */
    toggle: async (symbol) => {
        const response = await api.post(`/proxy/symbols/${symbol}/toggle`);
        return response.data;
    },
};

// ═══════════════════════════════════════════════════════════════════════════
// 回測系統（通過代理）
// ═══════════════════════════════════════════════════════════════════════════

export const backtestApi = {
    /** 執行回測 */
    run: async (params) => {
        const response = await api.post('/proxy/backtest/run', params);
        return response.data;
    },

    /** 獲取回測結果 */
    getResult: async (symbol) => {
        const response = await api.get(`/proxy/backtest/result/${symbol}`);
        return response.data;
    },

    /** 參數優化 */
    optimize: async (params) => {
        const response = await api.post('/proxy/backtest/optimize', params);
        return response.data;
    },
};

// 統一導出
export default {
    getNodeStatus,
    testNodeConnection,
    setNodeUrl,
    grid: gridApi,
    coin: coinApi,
    symbols: symbolsApi,
    backtest: backtestApi,
};
