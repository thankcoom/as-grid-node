import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle, Logo } from '../context/I18nContext';
import api from '../services/api';
import { Icons } from '../components/Icons';
import { getSSEClient } from '../services/SSEClient';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [nodeStatus, setNodeStatus] = useState('checking');
  const [nodeData, setNodeData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [actionLoading, setActionLoading] = useState(false);

  const checkNodeStatus = useCallback(async () => {
    try {
      // 使用 auth_server API 獲取 Node 狀態
      const res = await api.get('/node/my-status');

      if (res.data.status === 'not_registered') {
        setNodeStatus('not_configured');
        setNodeData(null);
      } else if (res.data.is_online) {
        setNodeStatus('connected');
        setNodeData(res.data);
        setLastUpdate(new Date());
      } else {
        setNodeStatus('offline');
        setNodeData(res.data);
      }
    } catch (err) {
      console.error('Failed to fetch node status:', err);
      setNodeStatus('error');
    }
  }, []);

  // 通過 proxy 控制 Node
  const handleStartBot = async () => {
    setActionLoading(true);
    try {
      await api.post('/proxy/grid/start', { symbol: 'BTCUSDT', quantity: 0.001 });
      await checkNodeStatus();
    } catch (err) {
      console.error('Start failed:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStopBot = async () => {
    setActionLoading(true);
    try {
      await api.post('/proxy/grid/stop');
      await checkNodeStatus();
    } catch (err) {
      console.error('Stop failed:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCloseAll = async () => {
    if (!confirm('確定要平倉所有持倉？此操作無法撤回。')) return;
    setActionLoading(true);
    try {
      await api.post('/proxy/grid/close_all');
      await checkNodeStatus();
    } catch (err) {
      console.error('Close all failed:', err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleTogglePause = async () => {
    setActionLoading(true);
    try {
      await api.post('/proxy/grid/pause');
      await checkNodeStatus();
    } catch (err) {
      console.error('Toggle pause failed:', err);
    } finally {
      setActionLoading(false);
    }
  };

  // SSE 連線 ref
  const sseConnectedRef = useRef(false);
  const [sseConnected, setSseConnected] = useState(false);
  const [logs, setLogs] = useState([]);
  const [runtime, setRuntime] = useState(0);
  const runtimeRef = useRef(null);

  // 格式化運行時間
  const formatRuntime = (seconds) => {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // 運行時間計時器
  useEffect(() => {
    if (nodeData?.is_trading) {
      runtimeRef.current = setInterval(() => {
        setRuntime(prev => prev + 1);
      }, 1000);
    } else {
      if (runtimeRef.current) {
        clearInterval(runtimeRef.current);
        runtimeRef.current = null;
      }
      setRuntime(0);
    }
    return () => {
      if (runtimeRef.current) {
        clearInterval(runtimeRef.current);
      }
    };
  }, [nodeData?.is_trading]);

  // 初始化輪詢
  useEffect(() => {
    // 首次獲取狀態
    checkNodeStatus();

    // 保留輪詢作為備用（15秒間隔，SSE 連線成功後會更快更新）
    const interval = setInterval(checkNodeStatus, 15000);
    return () => clearInterval(interval);
  }, [checkNodeStatus]);

  // SSE 連線（當 Node 已連接時）
  useEffect(() => {
    if (nodeStatus !== 'connected') return;

    // 從 localStorage 獲取 JWT token
    const token = localStorage.getItem('token');
    if (!token) {
      console.warn('[Dashboard] No auth token found');
      return;
    }

    const sseClient = getSSEClient();

    // 註冊回調
    sseClient.on('onConnect', () => {
      console.log('[Dashboard] SSE connected');
      setSseConnected(true);
      sseConnectedRef.current = true;
    });

    sseClient.on('onDisconnect', () => {
      console.log('[Dashboard] SSE disconnected');
      setSseConnected(false);
      sseConnectedRef.current = false;
    });

    sseClient.on('onAccount', (data) => {
      setNodeData(prev => ({
        ...prev,
        equity: data.equity,
        available_balance: data.available_balance,
        unrealized_pnl: data.unrealized_pnl,
        total_pnl: data.total_pnl || prev?.total_pnl || 0,
        usdt_equity: data.usdt_equity || prev?.usdt_equity || 0,
        usdt_available: data.usdt_available || prev?.usdt_available || 0,
        usdc_equity: data.usdc_equity || prev?.usdc_equity || 0,
        usdc_available: data.usdc_available || prev?.usdc_available || 0,
      }));
      setLastUpdate(new Date());
    });

    sseClient.on('onPositions', (positions) => {
      setNodeData(prev => ({
        ...prev,
        positions: positions
      }));
    });

    sseClient.on('onStatus', (status) => {
      setNodeData(prev => ({
        ...prev,
        is_trading: status.is_trading,
        is_paused: status.is_paused,
        symbols: status.symbols
      }));
    });

    sseClient.on('onConnectionStatus', (status) => {
      console.log('[Dashboard] Node connection status:', status);
      // 可用於顯示 Node 與交易所的連線狀態
    });

    sseClient.on('onError', (error) => {
      console.error('[Dashboard] SSE error:', error);
    });

    // 連線到 SSE 代理
    sseClient.connect(token);

    return () => {
      sseClient.disconnect();
    };
  }, [nodeStatus]);

  const statusConfig = {
    checking: { icon: Icons.RefreshCw, spin: true, text: t.dashboard.checking, color: 'text-white/40', bg: 'bg-white/5' },
    connected: { icon: Icons.Check, text: t.dashboard.connected, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    offline: { icon: Icons.Clock, text: t.dashboard.nodeOffline, color: 'text-amber-400', bg: 'bg-amber-500/10' },
    not_configured: { icon: Icons.AlertCircle, text: t.dashboard.notConfigured, color: 'text-amber-400', bg: 'bg-amber-500/10' },
    error: { icon: Icons.X, text: t.dashboard.error, color: 'text-red-400', bg: 'bg-red-500/10' }
  };

  const status = statusConfig[nodeStatus];

  return (
    <div className="min-h-screen bg-bg-primary bg-gradient-radial bg-grid-pattern">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-bg-primary/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Logo size="sm" showText={false} />
            <span className="text-[14px] font-semibold text-white">{t.nav.dashboard}</span>
          </div>
          <div className="flex items-center gap-3">
            <LanguageToggle />
            {user?.is_admin && (
              <Link to="/admin" className="btn-secondary text-[12px] px-3 py-1.5">
                <Icons.Settings className="w-3.5 h-3.5" />
                Admin
              </Link>
            )}
            <button onClick={logout} className="text-white/40 hover:text-white transition-colors">
              <Icons.LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-12 space-y-8">
        {/* Node Status Card */}
        <div className="glass-card rounded-2xl p-8 animate-fade-in">
          <div className="flex items-center justify-between mb-8">
            <div className="flex items-center gap-4">
              <div className={`w-12 h-12 rounded-xl ${status.bg} flex items-center justify-center ${status.color}`}>
                <status.icon className={`w-6 h-6 ${status.spin ? 'animate-spin' : ''}`} />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">{t.dashboard.nodeStatus}</h2>
                <p className={`text-[13px] ${status.color}`}>{status.text}</p>
              </div>
            </div>
            <Link to="/settings" className="btn-secondary">
              <Icons.Settings className="w-4 h-4" />
              {t.nav.settings}
            </Link>
          </div>

          {nodeStatus === 'connected' && nodeData && (
            <div className="space-y-4">
              {/* USDC/USDT Split Display - Like GUI */}
              <div className="grid grid-cols-2 gap-4">
                {/* USDC Account */}
                <div className="bg-black/20 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[13px] font-semibold text-white">USDC</span>
                    <span className="text-[11px] text-white/40">{t.dashboard.futuresAccount}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-[12px]">
                    <div>
                      <p className="text-white/40 mb-0.5">{t.dashboard.equity}</p>
                      <p className="font-medium text-white">${(nodeData.usdc_equity || nodeData.equity || 0).toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-white/40 mb-0.5">{t.dashboard.available}</p>
                      <p className="font-medium text-emerald-400">${(nodeData.usdc_available || nodeData.available_balance || 0).toFixed(2)}</p>
                    </div>
                  </div>
                </div>
                {/* USDT Account */}
                <div className="bg-black/20 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-[13px] font-semibold text-white">USDT</span>
                    <span className="text-[11px] text-white/40">{t.dashboard.futuresAccount}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-[12px]">
                    <div>
                      <p className="text-white/40 mb-0.5">權益</p>
                      <p className="font-medium text-white">${(nodeData.usdt_equity || 0).toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-white/40 mb-0.5">可用</p>
                      <p className="font-medium text-emerald-400">${(nodeData.usdt_available || 0).toFixed(2)}</p>
                    </div>
                  </div>
                </div>
              </div>
              {/* Summary Row */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-black/20 rounded-xl p-4">
                  <p className="text-[11px] text-white/40 mb-1">總權益</p>
                  <p className="text-xl font-bold text-white">
                    ${(nodeData.equity || 0).toFixed(2)}
                  </p>
                </div>
                <div className="bg-black/20 rounded-xl p-4">
                  <p className="text-[11px] text-white/40 mb-1">總可用</p>
                  <p className="text-xl font-bold text-emerald-400">
                    ${(nodeData.available_balance || 0).toFixed(2)}
                  </p>
                </div>
                <div className="bg-black/20 rounded-xl p-4">
                  <p className="text-[11px] text-white/40 mb-1">{t.dashboard.totalPnl}</p>
                  <p className={`text-xl font-bold ${(nodeData.total_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    ${(nodeData.total_pnl || 0).toFixed(2)}
                  </p>
                </div>
                <div className="bg-black/20 rounded-xl p-4">
                  <p className="text-[11px] text-white/40 mb-1">浮動盈虧</p>
                  <p className={`text-xl font-bold ${(nodeData.unrealized_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    ${(nodeData.unrealized_pnl || 0).toFixed(2)}
                  </p>
                </div>
              </div>
            </div>
          )}

          {nodeStatus === 'not_configured' && (
            <div className="text-center py-8">
              <Icons.Rocket className="w-12 h-12 text-white/20 mx-auto mb-4" />
              <p className="text-white/40 mb-4">{t.dashboard.noNodeDeployed}</p>
              <Link to="/deploy" className="btn-primary inline-flex">
                <Icons.Rocket className="w-4 h-4" />
                {t.dashboard.deployNow}
              </Link>
            </div>
          )}

          {nodeStatus === 'offline' && (
            <div className="text-center py-8">
              <Icons.Clock className="w-12 h-12 text-amber-400/40 mx-auto mb-4" />
              <p className="text-white/40 mb-2">節點最後心跳超過 10 分鐘</p>
              <p className="text-[13px] text-white/30">請檢查 Zeabur 上的節點服務是否正常運行</p>
            </div>
          )}
        </div>

        {/* Control Panel - Only show when connected */}
        {nodeStatus === 'connected' && nodeData && (
          <div className="glass-card rounded-2xl p-8 animate-fade-in">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-[16px] font-semibold text-white flex items-center gap-2">
                <Icons.Zap className="w-5 h-5" />
                {t.dashboard.controlPanel}
              </h3>
              {nodeData.is_trading && (
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2 bg-black/20 rounded-lg px-3 py-1.5">
                    <Icons.Clock className="w-4 h-4 text-white/40" />
                    <span className="text-[13px] font-mono text-white">{formatRuntime(runtime)}</span>
                  </div>
                  <span className={`px-2.5 py-1 rounded-full text-[11px] font-medium ${nodeData.is_paused
                    ? 'bg-amber-500/20 text-amber-400'
                    : 'bg-emerald-500/20 text-emerald-400'
                    }`}>
                    {nodeData.is_paused ? t.dashboard.paused : t.dashboard.running}
                  </span>
                </div>
              )}
            </div>
            {/* Main Controls */}
            <div className="flex gap-4 mb-4">
              <button
                onClick={handleStartBot}
                disabled={actionLoading || nodeData.is_trading}
                className="btn-primary flex-1"
              >
                {actionLoading ? (
                  <><Icons.RefreshCw className="w-4 h-4 animate-spin" /> {t.dashboard.processing}</>
                ) : (
                  <><Icons.Play className="w-4 h-4" /> {t.dashboard.startTrading}</>
                )}
              </button>
              <button
                onClick={handleStopBot}
                disabled={actionLoading || !nodeData.is_trading}
                className="btn-secondary flex-1"
              >
                <Icons.Square className="w-4 h-4" />
                {t.dashboard.stopTrading}
              </button>
            </div>
            {/* Additional Controls - Only when trading */}
            {nodeData.is_trading && (
              <div className="flex gap-4 pt-4 border-t border-white/10">
                <button
                  onClick={handleTogglePause}
                  disabled={actionLoading}
                  className={`flex-1 px-4 py-2.5 rounded-lg font-medium text-[13px] transition-all flex items-center justify-center gap-2 ${nodeData.is_paused
                    ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
                    : 'bg-white/5 text-white/60 hover:bg-white/10'
                    }`}
                >
                  {nodeData.is_paused ? (
                    <><Icons.Play className="w-4 h-4" /> {t.dashboard.resumeRefill}</>
                  ) : (
                    <><Icons.Pause className="w-4 h-4" /> {t.dashboard.pauseRefill}</>
                  )}
                </button>
                <button
                  onClick={handleCloseAll}
                  disabled={actionLoading}
                  className="flex-1 px-4 py-2.5 rounded-lg font-medium text-[13px] bg-red-500/10 text-red-400 hover:bg-red-500/20 transition-all flex items-center justify-center gap-2"
                >
                  <Icons.X className="w-4 h-4" />
                  {t.dashboard.closeAll}
                </button>
              </div>
            )}
          </div>
        )}

        {/* Positions Table - Only when trading */}
        {nodeStatus === 'connected' && nodeData && nodeData.positions && nodeData.positions.length > 0 && (
          <div className="glass-card rounded-2xl p-8 animate-fade-in">
            <h3 className="text-[16px] font-semibold text-white mb-6 flex items-center gap-2">
              <Icons.TrendingUp className="w-5 h-5" />
              {t.dashboard.positions}
            </h3>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-[11px] text-white/40 border-b border-white/10">
                    <th className="text-left py-2 px-2">{t.dashboard.pair}</th>
                    <th className="text-right py-2 px-2">{t.dashboard.long}</th>
                    <th className="text-right py-2 px-2">{t.dashboard.short}</th>
                    <th className="text-right py-2 px-2">{t.dashboard.unrealizedPnl}</th>
                  </tr>
                </thead>
                <tbody>
                  {nodeData.positions.map((pos, idx) => (
                    <tr key={idx} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                      <td className="py-3 px-2 text-[13px] text-white font-medium">{pos.symbol}</td>
                      <td className="py-3 px-2 text-right">
                        <span className={`text-[13px] ${pos.long > 0 ? 'text-emerald-400' : 'text-white/40'}`}>
                          {pos.long > 0 ? pos.long.toFixed(4) : '-'}
                        </span>
                      </td>
                      <td className="py-3 px-2 text-right">
                        <span className={`text-[13px] ${pos.short > 0 ? 'text-red-400' : 'text-white/40'}`}>
                          {pos.short > 0 ? pos.short.toFixed(4) : '-'}
                        </span>
                      </td>
                      <td className="py-3 px-2 text-right">
                        <span className={`text-[13px] font-medium ${(pos.unrealized_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                          ${(pos.unrealized_pnl || 0).toFixed(2)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Indicators Panel - Only when trading */}
        {nodeStatus === 'connected' && nodeData && nodeData.is_trading && nodeData.indicators && (
          <div className="glass-card rounded-2xl p-8 animate-fade-in">
            <h3 className="text-[16px] font-semibold text-white mb-6 flex items-center gap-2">
              <Icons.BarChart2 className="w-5 h-5" />
              {t.dashboard.indicators}
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {/* Funding Rate */}
              <div className="bg-black/20 rounded-xl p-4">
                <p className="text-[11px] text-white/40 mb-1">Funding Rate</p>
                <p className={`text-lg font-bold ${(nodeData.indicators.funding_rate || 0) > 0 ? 'text-emerald-400' :
                  (nodeData.indicators.funding_rate || 0) < 0 ? 'text-red-400' : 'text-white/60'
                  }`}>
                  {((nodeData.indicators.funding_rate || 0) * 100).toFixed(4)}%
                </p>
              </div>
              {/* OFI */}
              <div className="bg-black/20 rounded-xl p-4">
                <p className="text-[11px] text-white/40 mb-1">OFI</p>
                <p className={`text-lg font-bold ${(nodeData.indicators.ofi_value || 0) > 0.3 ? 'text-emerald-400' :
                  (nodeData.indicators.ofi_value || 0) < -0.3 ? 'text-red-400' : 'text-white/60'
                  }`}>
                  {(nodeData.indicators.ofi_value || 0).toFixed(2)}
                </p>
              </div>
              {/* Volume Ratio */}
              <div className="bg-black/20 rounded-xl p-4">
                <p className="text-[11px] text-white/40 mb-1">Volume Ratio</p>
                <p className={`text-lg font-bold ${(nodeData.indicators.volume_ratio || 1) > 2 ? 'text-amber-400' : 'text-white/60'
                  }`}>
                  {(nodeData.indicators.volume_ratio || 1).toFixed(1)}x
                </p>
              </div>
              {/* Total Positions */}
              <div className="bg-black/20 rounded-xl p-4">
                <p className="text-[11px] text-white/40 mb-1">{t.dashboard.totalPositions}</p>
                <p className="text-lg font-bold text-white">
                  {nodeData.indicators.total_positions || 0}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Trading Log Panel - Real-time via WebSocket */}
        {nodeStatus === 'connected' && nodeData && nodeData.is_trading && (
          <div className="glass-card rounded-2xl p-8 animate-fade-in">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-[16px] font-semibold text-white flex items-center gap-2">
                <Icons.Terminal className="w-5 h-5" />
                {t.dashboard.tradingLog}
              </h3>
              <div className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${sseConnected ? 'bg-emerald-400' : 'bg-amber-400'}`} />
                <span className="text-[11px] text-white/40">
                  {sseConnected ? t.dashboard.realtime : t.dashboard.connecting}
                </span>
              </div>
            </div>
            <div className="bg-black/30 rounded-lg p-4 h-48 overflow-y-auto font-mono text-[12px]">
              {logs.length === 0 ? (
                <p className="text-white/30">{t.dashboard.waitingForLogs}</p>
              ) : (
                logs.map((log, idx) => (
                  <p key={idx} className="text-white/60 leading-relaxed">
                    {log}
                  </p>
                ))
              )}
            </div>
          </div>
        )}

        {/* Quick Links */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Link to="/deploy" className="glass-card rounded-xl p-4 text-center hover:bg-white/5 transition-colors group">
            <Icons.Rocket className="w-6 h-6 mx-auto mb-2 text-white/40 group-hover:text-white transition-colors" />
            <p className="text-[13px] text-white/60 group-hover:text-white">{t.nav.deploy}</p>
          </Link>
          <Link to="/settings" className="glass-card rounded-xl p-4 text-center hover:bg-white/5 transition-colors group">
            <Icons.Settings className="w-6 h-6 mx-auto mb-2 text-white/40 group-hover:text-white transition-colors" />
            <p className="text-[13px] text-white/60 group-hover:text-white">{t.nav.settings}</p>
          </Link>
          <Link to="/coins" className="glass-card rounded-xl p-4 text-center hover:bg-white/5 transition-colors group">
            <Icons.TrendingUp className="w-6 h-6 mx-auto mb-2 text-white/40 group-hover:text-white transition-colors" />
            <p className="text-[13px] text-white/60 group-hover:text-white">{t.dashboard.coins}</p>
          </Link>
          <Link to="/backtest" className="glass-card rounded-xl p-4 text-center hover:bg-white/5 transition-colors group">
            <Icons.BarChart2 className="w-6 h-6 mx-auto mb-2 text-white/40 group-hover:text-white transition-colors" />
            <p className="text-[13px] text-white/60 group-hover:text-white">{t.dashboard.backtest}</p>
          </Link>
        </div>
      </main>
    </div>
  );
}
