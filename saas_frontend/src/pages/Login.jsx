import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { useI18n, LanguageToggle, Logo } from '../context/I18nContext';
import { Icons } from '../components/Icons';

export default function Login() {
  const { t } = useI18n();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError(t.settings.fieldsRequired || 'Please fill in all fields'); // strict t check
      return;
    }

    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);

      // We need to resolve import. I'll maintain existing import style for now to avoid breakage, 
      // but if Admin.jsx worked, maybe both work?
      // I'll stick to what the file had: `import api` (default).
      const res = await api.post('/auth/login', formData);
      localStorage.setItem('token', res.data.access_token);

      if (res.data.status === 'pending_api') {
        navigate('/setup-api');
      } else {
        navigate('/dashboard');
      }
    } catch (err) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'object') {
        if (detail.code === 'PENDING_APPROVAL') {
          navigate('/pending', { state: { uid: detail.uid } });
        } else if (detail.code === 'REJECTED') {
          navigate('/rejected');
        } else {
          setError(detail.message || t.common.error);
        }
      } else {
        setError(detail || t.common.error);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary bg-gradient-radial bg-grid-pattern relative overflow-hidden">
      {/* Animated background orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-white/[0.02] rounded-full blur-3xl animate-pulse-slow" />
      <div className="absolute bottom-1/4 right-1/4 w-80 h-80 bg-white/[0.015] rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1s' }} />

      <div className="absolute top-6 right-6 z-20">
        <LanguageToggle />
      </div>

      <div className="w-full max-w-md p-8 glass-card rounded-2xl shadow-2xl shadow-black/50 animate-fade-in relative z-10">
        {/* Logo & Title */}
        <div className="text-center mb-10 stagger-children flex flex-col items-center">
          <div className="mb-6 animate-glow transform hover:scale-105 transition-transform duration-500">
            <Logo size="lg" showText={false} />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white mb-2">
            {t.auth.signIn}
          </h1>
          <p className="text-text-muted text-sm">
            {t.auth.joinMessage}
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-center animate-fade-in flex items-center justify-center gap-2">
            <Icons.AlertCircle className="w-4 h-4 text-red-400" />
            <p className="text-[13px] text-red-400">{error}</p>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5 stagger-children">
          <div>
            <label className="block text-[11px] font-medium text-text-muted mb-2 uppercase tracking-wider ml-1">
              {t.auth.email}
            </label>
            <input
              type="email"
              className="w-full h-12 rounded-xl bg-white/5 border border-white/10 px-4 text-white placeholder-text-disabled/50 focus:bg-white/[0.07] focus:border-white/20 focus:outline-none transition-all"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
            />
          </div>

          <div>
            <label className="block text-[11px] font-medium text-text-muted mb-2 uppercase tracking-wider ml-1">
              {t.auth.password}
            </label>
            <input
              type="password"
              className="w-full h-12 rounded-xl bg-white/5 border border-white/10 px-4 text-white placeholder-text-disabled/50 focus:bg-white/[0.07] focus:border-white/20 focus:outline-none transition-all"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••"
              autoComplete="current-password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full h-12 bg-white text-black font-semibold rounded-xl transition-all duration-300 hover:bg-white/90 hover:shadow-lg hover:shadow-white/10 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed mt-4 flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Icons.RefreshCw className="w-4 h-4 animate-spin" />
                <span>{t.common.loading}</span>
              </>
            ) : t.auth.signIn}
          </button>
        </form>

        {/* Divider */}
        <div className="flex items-center gap-4 my-8">
          <div className="flex-1 h-px bg-white/10" />
          <span className="text-[10px] text-white/20 uppercase tracking-widest">OR</span>
          <div className="flex-1 h-px bg-white/10" />
        </div>

        {/* Link to register */}
        <div className="text-center">
          <p className="text-[13px] text-text-muted">
            {t.auth.noAccount}{' '}
            <Link
              to="/register"
              className="text-white font-medium hover:underline underline-offset-4"
            >
              {t.auth.createAccount}
            </Link>
          </p>
        </div>
      </div>

      {/* Version */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 text-[10px] text-text-disabled/50">
        © 2024 Louis AS Grid • {t.brand.tagline}
      </div>
    </div>
  );
}