import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { useI18n, LanguageToggle, Logo } from '../context/I18nContext';
import { Icons } from '../components/Icons';

export default function Register() {
  const { t } = useI18n();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!email || !password) {
      setError(t.settings.fieldsRequired || 'Please fill in all fields');
      return;
    }

    if (password.length < 8) {
      setError(t.auth.passwordMin || 'Password must be at least 8 characters');
      return;
    }

    if (password !== confirmPassword) {
      setError(t.auth.passwordsDoNotMatch || 'Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      await api.post('/auth/register', { email, password });
      const formData = new FormData();
      formData.append('username', email);
      formData.append('password', password);
      // Assuming api.post works with { api } import
      const loginRes = await api.post('/auth/login', formData);
      localStorage.setItem('token', loginRes.data.access_token);
      navigate('/setup-api');
    } catch (err) {
      setError(err.response?.data?.detail || t.common.error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-bg-primary bg-gradient-radial bg-grid-pattern relative overflow-hidden">
      {/* Animated background orbs */}
      <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-white/[0.02] rounded-full blur-3xl animate-pulse-slow" />
      <div className="absolute bottom-1/3 left-1/4 w-96 h-96 bg-white/[0.015] rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1.5s' }} />

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
            {t.auth.createAccount}
          </h1>
          <p className="text-text-muted text-sm">
            {t.auth.joinMessage}
          </p>
        </div>

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-white/5 border border-red-500/30 rounded-xl text-center animate-fade-in">
            <div className="flex items-center justify-center gap-2">
              <Icons.AlertCircle className="w-4 h-4 text-red-400" />
              <p className="text-[13px] text-red-400">{error}</p>
            </div>
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
              placeholder={t.auth.passwordMin}
              autoComplete="new-password"
            />
          </div>

          <div>
            <label className="block text-[11px] font-medium text-text-muted mb-2 uppercase tracking-wider ml-1">
              {t.auth.confirmPassword}
            </label>
            <input
              type="password"
              className="w-full h-12 rounded-xl bg-white/5 border border-white/10 px-4 text-white placeholder-text-disabled/50 focus:bg-white/[0.07] focus:border-white/20 focus:outline-none transition-all"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder={t.auth.confirmPassword}
              autoComplete="new-password"
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
            ) : t.auth.registerBtn}
          </button>
        </form>

        {/* Divider */}
        <div className="flex items-center gap-4 my-8">
          <div className="flex-1 h-px bg-white/10" />
          <span className="text-[10px] text-white/20 uppercase tracking-widest">OR</span>
          <div className="flex-1 h-px bg-white/10" />
        </div>

        {/* Link to login */}
        <div className="text-center">
          <p className="text-[13px] text-text-muted">
            {t.auth.hasAccount}{' '}
            <Link
              to="/login"
              className="text-white font-medium hover:underline underline-offset-4"
            >
              {t.auth.signIn}
            </Link>
          </p>
        </div>
      </div>

      {/* Version */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 text-[10px] text-text-disabled/50">
        © 2025 Louis AS Grid • {t.brand.tagline}
      </div>
    </div>
  );
}