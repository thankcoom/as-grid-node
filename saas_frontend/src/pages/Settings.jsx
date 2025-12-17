import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle } from '../context/I18nContext';
import api from '../services/api';
import { Icons } from '../components/Icons';

export default function Settings() {
  const { user } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();

  const [nodeUrl, setNodeUrl] = useState('');
  const [status, setStatus] = useState({ type: 'idle', msg: '' });
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [nodeStatus, setNodeStatus] = useState(null);

  // 取得目前 Node 狀態
  useEffect(() => {
    fetchNodeStatus();
  }, []);

  const fetchNodeStatus = async () => {
    try {
      const res = await api.get('/node/my-status');
      setNodeStatus(res.data);
      // 如果有已設定的 URL，顯示部分
      if (res.data.node_url) {
        setNodeUrl(res.data.node_url);
      }
    } catch (err) {
      console.log('Node status not available');
    }
  };

  // 測試 Node 連接
  const testConnection = async () => {
    if (!nodeUrl) {
      setStatus({ type: 'error', msg: '請輸入 Node URL' });
      return;
    }

    setTesting(true);
    setStatus({ type: 'idle', msg: '' });

    try {
      // 先儲存 URL
      await api.post('/proxy/node/url', null, { params: { node_url: nodeUrl } });

      // 測試連接
      const res = await api.get('/proxy/node/test');

      if (res.data.status === 'connected') {
        setStatus({ type: 'success', msg: `連線成功！延遲 ${res.data.latency || 'N/A'}` });
        fetchNodeStatus();
      } else {
        setStatus({ type: 'error', msg: res.data.error || '連線失敗' });
      }
    } catch (err) {
      setStatus({ type: 'error', msg: err.response?.data?.detail || '無法連接到 Node' });
    } finally {
      setTesting(false);
    }
  };

  // 儲存設定
  const handleSave = async () => {
    setLoading(true);
    try {
      await api.post('/proxy/node/url', null, { params: { node_url: nodeUrl } });
      setStatus({ type: 'success', msg: '已儲存！' });
      setTimeout(() => navigate('/dashboard'), 1000);
    } catch (err) {
      setStatus({ type: 'error', msg: err.response?.data?.detail || '儲存失敗' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg-primary bg-gradient-radial bg-grid-pattern">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-bg-primary/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-2xl mx-auto px-6 py-4 flex items-center justify-between">
          <button onClick={() => navigate('/dashboard')} className="text-[13px] text-white/40 hover:text-white transition-colors flex items-center gap-1">
            <Icons.ArrowLeft className="w-4 h-4" />
            {t.nav.back}
          </button>
          <span className="text-[14px] font-semibold text-white">{t.settings.title}</span>
          <LanguageToggle />
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-12">
        {/* Node 狀態卡片 */}
        <div className="glass-card rounded-2xl p-6 mb-6 animate-fade-in">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-[14px] font-semibold text-white flex items-center gap-2">
              <Icons.RefreshCw className="w-4 h-4" />
              節點狀態
            </h3>
            <span className={`px-3 py-1 rounded-full text-[12px] font-medium ${nodeStatus?.is_online
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-white/10 text-white/40'
              }`}>
              {nodeStatus?.is_online ? '在線' : nodeStatus?.status === 'not_registered' ? '未部署' : '離線'}
            </span>
          </div>

          {nodeStatus?.is_online && (
            <div className="grid grid-cols-3 gap-4">
              <div className="bg-black/20 rounded-xl p-4">
                <p className="text-[10px] text-white/40 mb-1">總盈虧</p>
                <p className={`text-lg font-bold ${nodeStatus.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  ${nodeStatus.total_pnl?.toFixed(2) || '0.00'}
                </p>
              </div>
              <div className="bg-black/20 rounded-xl p-4">
                <p className="text-[10px] text-white/40 mb-1">交易狀態</p>
                <p className="text-lg font-bold text-white">
                  {nodeStatus.is_trading ? '運行中' : '已停止'}
                </p>
              </div>
              <div className="bg-black/20 rounded-xl p-4">
                <p className="text-[10px] text-white/40 mb-1">最後心跳</p>
                <p className="text-[13px] text-white/60">
                  {nodeStatus.last_heartbeat ? new Date(nodeStatus.last_heartbeat).toLocaleTimeString() : '-'}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Node URL 設定 */}
        <div className="glass-card rounded-2xl p-8 mb-8 animate-fade-in">
          <div className="flex items-center gap-4 mb-6">
            <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center text-white">
              <Icons.Link className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">{t.settings.bindNode}</h2>
              <p className="text-[13px] text-white/40">{t.settings.bindDesc}</p>
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <label className="block text-[12px] font-medium text-white/50 mb-2 ml-1">
                Node URL
              </label>
              <input
                type="text"
                placeholder="https://your-grid-node.zeabur.app"
                value={nodeUrl}
                onChange={(e) => setNodeUrl(e.target.value)}
                className="w-full h-12 bg-black/20 border border-white/10 rounded-xl px-4 text-[14px] text-white focus:outline-none focus:border-white/20 transition-all font-mono placeholder:text-white/20"
              />
              <p className="text-[11px] text-white/30 mt-1.5 ml-1">
                從 Zeabur Dashboard 的 Networking → Domains 取得
              </p>
            </div>

            {/* Status Message */}
            {status.msg && (
              <div className={`p-4 rounded-xl text-[13px] flex items-center gap-2 ${status.type === 'success'
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                  : 'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                {status.type === 'success' ? <Icons.CheckCircle className="w-4 h-4" /> : <Icons.AlertCircle className="w-4 h-4" />}
                {status.msg}
              </div>
            )}

            <div className="flex gap-3 pt-4 border-t border-white/5">
              <button
                onClick={testConnection}
                disabled={testing || !nodeUrl}
                className="btn-secondary flex-1"
              >
                {testing ? (
                  <>
                    <Icons.RefreshCw className="w-4 h-4 animate-spin" />
                    測試中...
                  </>
                ) : (
                  <>
                    <Icons.Zap className="w-4 h-4" />
                    測試連接
                  </>
                )}
              </button>
              <button
                onClick={handleSave}
                disabled={loading || !nodeUrl}
                className="btn-primary flex-[2]"
              >
                {loading ? '儲存中...' : '儲存設定'}
              </button>
            </div>
          </div>
        </div>

        {/* 尚未部署提示 */}
        {(!nodeStatus || nodeStatus.status === 'not_registered') && (
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-2xl p-6 animate-fade-in">
            <div className="flex items-start gap-4">
              <div className="w-10 h-10 rounded-xl bg-amber-500/20 flex items-center justify-center text-amber-400 flex-shrink-0">
                <Icons.Rocket className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-[14px] font-semibold text-amber-300 mb-1">尚未部署節點？</h4>
                <p className="text-[13px] text-amber-400/60 mb-4">
                  前往部署頁面，一鍵部署您的專屬交易節點
                </p>
                <Link to="/deploy" className="btn-warning inline-flex">
                  <Icons.Rocket className="w-4 h-4" />
                  前往部署
                </Link>
              </div>
            </div>
          </div>
        )}

        {/* Tips */}
        <div className="glass-card rounded-2xl p-6 mt-6 border-l-2 border-l-white/20">
          <h4 className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
            <Icons.List className="w-4 h-4" />
            如何取得 Node URL？
          </h4>
          <ol className="space-y-2 text-[13px] text-white/50 ml-1">
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-white/10 text-white/50 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">1</span>
              登入 Zeabur Dashboard
            </li>
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-white/10 text-white/50 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">2</span>
              找到您部署的 grid-node 服務
            </li>
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-white/10 text-white/50 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">3</span>
              點擊 <strong className="text-white">Networking</strong> → <strong className="text-white">Generate Domain</strong>
            </li>
            <li className="flex items-start gap-2">
              <span className="w-5 h-5 rounded-full bg-white/10 text-white/50 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">4</span>
              複製生成的 URL 並貼到上方
            </li>
          </ol>
        </div>
      </main>
    </div>
  );
}
