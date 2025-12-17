import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle, Logo } from '../context/I18nContext';
import api from '../services/api';
import { Icons } from '../components/Icons';

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

  useEffect(() => {
    checkNodeStatus();
    const interval = setInterval(checkNodeStatus, 30000);
    return () => clearInterval(interval);
  }, [checkNodeStatus]);

  const statusConfig = {
    checking: { icon: Icons.RefreshCw, spin: true, text: t.dashboard.checking, color: 'text-white/40', bg: 'bg-white/5' },
    connected: { icon: Icons.Check, text: t.dashboard.connected, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    offline: { icon: Icons.Clock, text: '節點離線', color: 'text-amber-400', bg: 'bg-amber-500/10' },
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
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-black/20 rounded-xl p-4">
                <p className="text-[11px] text-white/40 mb-1">{t.dashboard.totalPnl}</p>
                <p className={`text-xl font-bold ${(nodeData.total_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  ${(nodeData.total_pnl || 0).toFixed(2)}
                </p>
              </div>
              <div className="bg-black/20 rounded-xl p-4">
                <p className="text-[11px] text-white/40 mb-1">{t.dashboard.equity}</p>
                <p className="text-xl font-bold text-white">
                  ${(nodeData.equity || 0).toFixed(2)}
                </p>
              </div>
              <div className="bg-black/20 rounded-xl p-4">
                <p className="text-[11px] text-white/40 mb-1">{t.dashboard.tradingStatus}</p>
                <p className={`text-lg font-bold ${nodeData.is_trading ? 'text-emerald-400' : 'text-white/60'}`}>
                  {nodeData.is_trading ? t.dashboard.running : t.dashboard.stopped}
                </p>
              </div>
              <div className="bg-black/20 rounded-xl p-4">
                <p className="text-[11px] text-white/40 mb-1">{t.dashboard.lastUpdate}</p>
                <p className="text-[13px] text-white/60">
                  {nodeData.last_heartbeat ? new Date(nodeData.last_heartbeat).toLocaleTimeString() : '-'}
                </p>
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
            <h3 className="text-[16px] font-semibold text-white mb-6 flex items-center gap-2">
              <Icons.Zap className="w-5 h-5" />
              {t.dashboard.controlPanel}
            </h3>
            <div className="flex gap-4">
              <button
                onClick={handleStartBot}
                disabled={actionLoading || nodeData.is_trading}
                className="btn-primary flex-1"
              >
                {actionLoading ? (
                  <><Icons.RefreshCw className="w-4 h-4 animate-spin" /> 處理中...</>
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
            <p className="text-[13px] text-white/60 group-hover:text-white">{t.nav.coins || '選幣'}</p>
          </Link>
          <Link to="/backtest" className="glass-card rounded-xl p-4 text-center hover:bg-white/5 transition-colors group">
            <Icons.BarChart2 className="w-6 h-6 mx-auto mb-2 text-white/40 group-hover:text-white transition-colors" />
            <p className="text-[13px] text-white/60 group-hover:text-white">{t.nav.backtest || '回測'}</p>
          </Link>
        </div>
      </main>
    </div>
  );
}
