import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle } from '../context/I18nContext';
import { createNodeApi } from '../services/nodeApi';
import { Icons } from '../components/Icons';

export default function Settings() {
  const { user, nodeSecret, setNodeSecret, updateZeaburUrl } = useAuth();
  const { t } = useI18n();
  const navigate = useNavigate();

  const [url, setUrl] = useState(user?.zeabur_url || '');
  const [secret, setSecret] = useState(nodeSecret || '');
  const [status, setStatus] = useState({ type: 'idle', msg: '' });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (user?.zeabur_url) setUrl(user.zeabur_url);
    if (nodeSecret) setSecret(nodeSecret);
  }, [user, nodeSecret]);

  const testConnection = async () => {
    if (!url || !secret) {
      setStatus({ type: 'error', msg: t.settings.fieldsRequired });
      return;
    }

    setLoading(true);
    setStatus({ type: 'idle', msg: '' });

    try {
      const nodeApi = createNodeApi(url, secret);
      await nodeApi.get('/health');
      setStatus({ type: 'success', msg: t.settings.testSuccess });
    } catch (err) {
      console.error(err);
      setStatus({ type: 'error', msg: t.settings.testFailed });
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (status.type !== 'success') {
      await testConnection();
      if (status.type === 'error') return;
    }

    try {
      await updateZeaburUrl(url);
      setNodeSecret(secret);
      navigate('/dashboard');
    } catch (err) {
      setStatus({ type: 'error', msg: t.settings.saveFailed });
    }
  };

  return (
    <div className="min-h-screen bg-bg-primary bg-gradient-radial bg-grid-pattern">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-bg-primary/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-2xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={() => navigate('/dashboard')} className="text-[13px] text-white/40 hover:text-white transition-colors flex items-center gap-1">
              <Icons.ArrowLeft className="w-4 h-4" />
              {t.nav.back}
            </button>
          </div>
          <span className="text-[14px] font-semibold text-white">{t.settings.title}</span>
          <div className="flex items-center gap-4">
            <LanguageToggle />
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-12">
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
              <label className="block text-[12px] font-medium text-white/50 mb-2 ml-1">{t.settings.nodeUrl}</label>
              <input
                type="text"
                placeholder="https://your-node.zeabur.app"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="w-full h-12 bg-black/20 border border-white/10 rounded-xl px-4 text-[14px] text-white focus:outline-none focus:border-white/20 transition-all font-mono placeholder:text-white/10"
              />
              <p className="text-[11px] text-white/20 mt-1.5 ml-1">{t.settings.nodeUrlDesc}</p>
            </div>

            <div>
              <label className="block text-[12px] font-medium text-white/50 mb-2 ml-1">{t.settings.nodeSecret}</label>
              <input
                type="password"
                placeholder={t.settings.nodeSecretPlaceholder}
                value={secret}
                onChange={(e) => setSecret(e.target.value)}
                className="w-full h-12 bg-black/20 border border-white/10 rounded-xl px-4 text-[14px] text-white focus:outline-none focus:border-white/20 transition-all font-mono placeholder:text-white/10"
              />
              <p className="text-[11px] text-white/20 mt-1.5 ml-1">{t.settings.nodeSecretHint}</p>
            </div>

            {/* Status Message */}
            {status.msg && (
              <div className={`p-4 rounded-xl text-[13px] flex items-center gap-2 ${status.type === 'success' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                  'bg-red-500/10 text-red-400 border border-red-500/20'
                }`}>
                {status.type === 'success' ? <Icons.CheckCircle className="w-4 h-4" /> : <Icons.AlertCircle className="w-4 h-4" />}
                {status.msg}
              </div>
            )}

            <div className="flex gap-4 pt-4 border-t border-white/5">
              <button
                onClick={testConnection}
                disabled={loading}
                className="flex-1 h-12 glass-card rounded-xl text-[14px] font-medium text-white hover:bg-white/5 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Icons.RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                {t.settings.testConn}
              </button>
              <button
                onClick={handleSave}
                disabled={loading}
                className="flex-[2] h-12 bg-white text-black rounded-xl text-[14px] font-bold hover:bg-white/90 transition-all disabled:opacity-50 shadow-lg shadow-white/5"
              >
                {t.settings.save}
              </button>
            </div>
          </div>
        </div>

        {/* Tips */}
        <div className="glass-card rounded-2xl p-6 border-l-2 border-l-white/20">
          <h4 className="text-[14px] font-semibold text-white mb-3 flex items-center gap-2">
            <Icons.List className="w-4 h-4" /> {t.settings.howToGetUrl}
          </h4>
          <ol className="space-y-2 text-[13px] text-white/50 ml-1">
            <li className="flex items-start gap-2">
              <span className="mt-1 w-1 h-1 rounded-full bg-white/40 flex-shrink-0"></span>
              {t.deploy.afterStep1}
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-1 w-1 h-1 rounded-full bg-white/40 flex-shrink-0"></span>
              {t.deploy.afterStep2}
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-1 w-1 h-1 rounded-full bg-white/40 flex-shrink-0"></span>
              {t.deploy.afterStep3}
            </li>
          </ol>
        </div>
      </main>
    </div>
  );
}
