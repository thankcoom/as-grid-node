import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle, Logo } from '../context/I18nContext';
import { createNodeApi } from '../services/nodeApi';
import { Icons } from '../components/Icons';

export default function Dashboard() {
  const { user, nodeSecret, logout } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();
  const [nodeStatus, setNodeStatus] = useState('checking');
  const [botStatus, setBotStatus] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);

  const checkNodeStatus = useCallback(async () => {
    if (!user?.zeabur_url || !nodeSecret) {
      setNodeStatus('not_configured');
      return;
    }

    try {
      const nodeApi = createNodeApi(user.zeabur_url, nodeSecret);
      await nodeApi.get('/health');
      setNodeStatus('connected');

      const statusRes = await nodeApi.get('/api/v1/grid/status');
      setBotStatus(statusRes.data);
      setLastUpdate(new Date());
    } catch (err) {
      setNodeStatus('error');
    }
  }, [user?.zeabur_url, nodeSecret]);

  useEffect(() => {
    checkNodeStatus();
    const interval = setInterval(checkNodeStatus, 30000);
    return () => clearInterval(interval);
  }, [checkNodeStatus]);

  const handleStartBot = async () => {
    if (!user?.zeabur_url || !nodeSecret) return;
    setLoading(true);
    try {
      const nodeApi = createNodeApi(user.zeabur_url, nodeSecret);
      await nodeApi.post('/api/v1/grid/start');
      await checkNodeStatus();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleStopBot = async () => {
    if (!user?.zeabur_url || !nodeSecret) return;
    setLoading(true);
    try {
      const nodeApi = createNodeApi(user.zeabur_url, nodeSecret);
      await nodeApi.post('/api/v1/grid/stop');
      await checkNodeStatus();
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const statusConfig = {
    checking: { icon: Icons.RefreshCw, spin: true, text: t.dashboard.checking, color: 'text-white/40', bg: 'bg-white/5' },
    connected: { icon: Icons.Check, text: t.dashboard.connected, color: 'text-emerald-400', bg: 'bg-emerald-500/10' },
    not_configured: { icon: Icons.AlertCircle, text: t.dashboard.notConfigured, color: 'text-amber-400', bg: 'bg-amber-500/10' },
    error: { icon: Icons.X, text: t.dashboard.error, color: 'text-red-400', bg: 'bg-red-500/10' }
  };

  const status = statusConfig[nodeStatus];

  return (
    <div className="min-h-screen bg-bg-primary bg-gradient-radial bg-grid-pattern">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-bg-primary/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Logo size="md" showText={false} />
            <nav className="hidden md:flex items-center gap-1 ml-4">
              <Link to="/dashboard" className="px-4 py-2 rounded-lg text-[13px] font-medium text-white bg-white/10">
                {t.nav.dashboard}
              </Link>
              <Link to="/deploy" className="px-4 py-2 rounded-lg text-[13px] font-medium text-white/50 hover:text-white hover:bg-white/5 transition-colors">
                {t.nav.deploy}
              </Link>
              <Link to="/settings" className="px-4 py-2 rounded-lg text-[13px] font-medium text-white/50 hover:text-white hover:bg-white/5 transition-colors">
                {t.nav.settings}
              </Link>
              {user?.is_admin && (
                <Link to="/admin" className="px-4 py-2 rounded-lg text-[13px] font-medium text-white/50 hover:text-white hover:bg-white/5 transition-colors">
                  {t.nav.admin}
                </Link>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <LanguageToggle />
            <span className="text-[13px] text-white/40 hidden sm:block">{user?.email}</span>
            <button
              onClick={() => { logout(); navigate('/login'); }}
              className="px-4 py-2 text-[13px] text-white/40 hover:text-white transition-colors flex items-center gap-2"
            >
              <Icons.LogOut className="w-4 h-4" />
              {t.nav.logout}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8">
        {/* Status Banner */}
        <div className="glass-card rounded-2xl p-6 mb-6 animate-fade-in">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className={`w-14 h-14 rounded-2xl ${status.bg} border border-white/10 flex items-center justify-center`}>
                <status.icon className={`w-6 h-6 ${status.color} ${status.spin ? 'animate-spin' : ''}`} />
              </div>
              <div>
                <h2 className="text-[18px] font-semibold text-white">{t.dashboard.tradingNode}</h2>
                <p className={`text-[13px] ${status.color}`}>{status.text}</p>
                {lastUpdate && nodeStatus === 'connected' && (
                  <p className="text-[11px] text-white/30 mt-0.5">
                    {t.dashboard.lastUpdate}: {lastUpdate.toLocaleTimeString()}
                  </p>
                )}
              </div>
            </div>

            {nodeStatus === 'not_configured' && (
              <div className="flex gap-3">
                <Link to="/deploy" className="px-5 py-2.5 bg-white text-black font-semibold rounded-xl hover:bg-white/90 transition-all text-[13px] flex items-center gap-2">
                  <Icons.Rocket className="w-4 h-4" /> {t.dashboard.deployNode}
                </Link>
                <Link to="/settings" className="px-5 py-2.5 glass-card rounded-xl hover:bg-white/10 transition-all text-[13px] text-white flex items-center gap-2">
                  <Icons.Link className="w-4 h-4" /> {t.dashboard.connectExisting}
                </Link>
              </div>
            )}

            {nodeStatus === 'error' && (
              <div className="flex gap-3">
                <button onClick={checkNodeStatus} className="px-5 py-2.5 glass-card rounded-xl hover:bg-white/10 transition-all text-[13px] text-white flex items-center gap-2">
                  <Icons.RefreshCw className="w-4 h-4" /> {t.dashboard.retry}
                </button>
                <Link to="/settings" className="px-5 py-2.5 bg-white text-black font-semibold rounded-xl text-[13px] flex items-center gap-2">
                  <Icons.Settings className="w-4 h-4" /> {t.dashboard.checkSettings}
                </Link>
              </div>
            )}

            {nodeStatus === 'connected' && (
              <div className="flex gap-3">
                {botStatus?.is_running ? (
                  <button onClick={handleStopBot} disabled={loading} className="px-5 py-2.5 glass-card rounded-xl hover:bg-red-500/20 transition-all text-[13px] text-white disabled:opacity-50 flex items-center gap-2">
                    <Icons.Square className="w-4 h-4 fill-current" /> {t.dashboard.stopTrading}
                  </button>
                ) : (
                  <button onClick={handleStartBot} disabled={loading} className="px-5 py-2.5 bg-white text-black font-semibold rounded-xl text-[13px] disabled:opacity-50 flex items-center gap-2">
                    <Icons.Play className="w-4 h-4 fill-current" /> {t.dashboard.startTrading}
                  </button>
                )}
                <button onClick={checkNodeStatus} className="px-4 py-2.5 glass-card rounded-xl text-white/60 text-[13px] hover:text-white transition-colors">
                  <Icons.RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[
            { label: t.dashboard.status, value: botStatus?.is_running ? t.dashboard.running : t.dashboard.stopped, icon: Icons.Zap, active: botStatus?.is_running },
            { label: t.dashboard.pnl, value: botStatus?.pnl ? `$${botStatus.pnl.toFixed(2)}` : '$0.00', icon: Icons.TrendingUp },
            { label: t.dashboard.buyOrders, value: botStatus?.buy_count || 0, icon: Icons.ArrowRight, iconClass: 'rotate-45 text-emerald-400' },
            { label: t.dashboard.sellOrders, value: botStatus?.sell_count || 0, icon: Icons.ArrowRight, iconClass: '-rotate-45 text-red-400' },
          ].map((stat, i) => (
            <div key={i} className="glass-card rounded-2xl p-6 transition-all hover:border-white/20 animate-fade-in" style={{ animationDelay: `${i * 0.1}s` }}>
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-[11px] font-semibold text-white/40 uppercase tracking-wider">{stat.label}</p>
                  <p className="text-3xl font-bold text-white mt-2 tracking-tight">{stat.value}</p>
                </div>
                <div className={`w-11 h-11 ${stat.active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-white/10 text-white/60'} rounded-xl flex items-center justify-center text-xl`}>
                  <stat.icon className={`w-6 h-6 ${stat.iconClass || ''}`} />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Node Details */}
        {nodeStatus === 'connected' && botStatus && (
          <div className="grid lg:grid-cols-2 gap-6 mb-6">
            <div className="glass-card rounded-2xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/5">
                <h3 className="text-[14px] font-semibold text-white">{t.dashboard.tradingConfig}</h3>
              </div>
              <div className="p-6 space-y-4">
                {[
                  { label: t.dashboard.symbol, value: botStatus.symbol || 'BTCUSDT' },
                  { label: t.dashboard.gridCount, value: botStatus.grid_count || '-' },
                  { label: t.dashboard.priceRange, value: botStatus.lower_price && botStatus.upper_price ? `$${botStatus.lower_price} - $${botStatus.upper_price}` : '-' },
                  { label: t.dashboard.qtyPerGrid, value: botStatus.quantity_per_grid || '-' },
                ].map((item, i) => (
                  <div key={i} className="flex justify-between items-center">
                    <span className="text-[13px] text-white/50">{item.label}</span>
                    <span className="text-[13px] font-mono text-white">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="glass-card rounded-2xl overflow-hidden">
              <div className="px-6 py-4 border-b border-white/5">
                <h3 className="text-[14px] font-semibold text-white">{t.dashboard.nodeInfo}</h3>
              </div>
              <div className="p-6 space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-[13px] text-white/50">{t.dashboard.nodeUrl}</span>
                  <span className="text-[12px] font-mono text-white/70 truncate max-w-[200px]">{user?.zeabur_url}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[13px] text-white/50">{t.dashboard.uid}</span>
                  <span className="text-[13px] font-mono text-white">{user?.exchange_uid || '-'}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-[13px] text-white/50">{t.dashboard.connectionStatus}</span>
                  <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/20 text-emerald-400 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> {t.dashboard.stable}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Get Started */}
        {nodeStatus !== 'connected' && (
          <div className="glass-card border-dashed rounded-2xl p-12 text-center animate-fade-in">
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-white/5 flex items-center justify-center text-white">
              <Icons.Rocket className="w-10 h-10" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">{t.dashboard.getStarted}</h3>
            <p className="text-white/40 mb-8 max-w-md mx-auto text-[14px]">{t.dashboard.getStartedDesc}</p>
            <div className="flex gap-4 justify-center">
              <Link to="/deploy" className="px-6 py-3.5 bg-white text-black font-semibold rounded-xl flex items-center gap-2 hover:bg-white/90 transition-all">
                <Icons.Rocket className="w-4 h-4" /> {t.dashboard.deployYourNode}
              </Link>
              <Link to="/settings" className="px-6 py-3.5 glass-card rounded-xl text-white flex items-center gap-2 hover:bg-white/10 transition-all">
                <Icons.Link className="w-4 h-4" /> {t.dashboard.connectExisting}
              </Link>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
