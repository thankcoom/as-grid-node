import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle } from '../context/I18nContext';
import { Icons } from '../components/Icons';

export default function PendingApproval() {
    const { user, logout } = useAuth();
    const { t } = useI18n();
    const location = useLocation();
    const navigate = useNavigate();
    const uid = location.state?.uid || user?.exchange_uid || '---';

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-bg-primary bg-gradient-radial bg-grid-pattern relative overflow-hidden p-4">
            {/* Background effects */}
            <div className="absolute top-1/4 right-1/3 w-80 h-80 bg-white/[0.02] rounded-full blur-3xl animate-pulse-slow" />

            <div className="absolute top-6 right-6 z-20">
                <LanguageToggle />
            </div>

            <div className="w-full max-w-md glass-card rounded-2xl shadow-2xl shadow-black/50 animate-fade-in relative z-10 p-8 text-center">
                {/* Icon */}
                <div className="w-20 h-20 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex items-center justify-center mx-auto mb-6">
                    <Icons.Clock className="w-10 h-10 text-amber-500 animate-pulse" />
                </div>

                {/* Title */}
                <h1 className="text-2xl font-bold text-white mb-2">{t.status.pending_approval}</h1>
                <p className="text-text-muted text-sm mb-8">{t.admin.pendingApprovalStatus}...</p>

                {/* UID Display */}
                <div className="bg-white/5 border border-white/10 rounded-xl p-5 mb-6">
                    <p className="text-[11px] font-medium text-text-muted uppercase tracking-wider mb-2">Your UID</p>
                    <p className="text-xl font-mono text-white tracking-wide">{uid}</p>
                </div>

                {/* Status Indicator */}
                <div className="flex items-center justify-center gap-2 mb-8">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-500 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
                    </span>
                    <span className="text-sm text-text-muted">{t.admin.waiting}</span>
                </div>

                {/* Info */}
                <div className="text-sm text-text-secondary space-y-2 mb-8">
                    <p>Review within <span className="text-white font-medium">24 hours</span>.</p>
                </div>

                {/* Contact */}
                <div className="bg-white/[0.03] border border-white/5 rounded-xl p-5 mb-6 text-left">
                    <p className="text-[11px] font-medium text-text-muted uppercase tracking-wider mb-3">需要協助？</p>
                    <div className="space-y-3 text-sm">
                        <a href="https://louis12.pse.is/8geqph" target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 text-text-secondary hover:text-emerald-400 transition-colors">
                            <Icons.Users className="w-4 h-4" />
                            加入 LINE 社群
                        </a>
                        <a href="https://www.instagram.com/mr.__.l" target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 text-text-secondary hover:text-pink-400 transition-colors">
                            <Icons.Globe className="w-4 h-4" />
                            Instagram: @mr.__.l
                        </a>
                    </div>
                </div>

                {/* Logout */}
                <button
                    onClick={handleLogout}
                    className="w-full h-12 bg-white/5 border border-white/10 text-text-secondary rounded-xl hover:bg-white/10 hover:text-white transition-all flex items-center justify-center gap-2"
                >
                    <Icons.LogOut className="w-4 h-4" />
                    {t.nav.logout}
                </button>
            </div>
        </div>
    );
}
