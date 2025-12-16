import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle } from '../context/I18nContext';
import { Icons } from '../components/Icons';

export default function Rejected() {
    const { user, logout } = useAuth();
    const { t } = useI18n();
    const navigate = useNavigate();
    const uid = user?.exchange_uid || '---';

    return (
        <div className="min-h-screen flex items-center justify-center bg-bg-primary bg-gradient-radial bg-grid-pattern relative overflow-hidden p-4">
            <div className="absolute bottom-1/3 left-1/4 w-96 h-96 bg-red-500/[0.02] rounded-full blur-3xl" />

            <div className="absolute top-6 right-6 z-20">
                <LanguageToggle />
            </div>

            <div className="w-full max-w-md glass-card rounded-2xl shadow-2xl shadow-black/50 animate-fade-in relative z-10 p-8 text-center">
                {/* Icon */}
                <div className="w-20 h-20 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-6">
                    <Icons.X className="w-10 h-10 text-red-500" />
                </div>

                {/* Title */}
                <h1 className="text-2xl font-bold text-white mb-2">{t.rejected.title}</h1>
                <p className="text-text-muted text-sm mb-8">{t.rejected.subtitle}</p>

                {/* UID Display */}
                <div className="bg-red-500/5 border border-red-500/10 rounded-xl p-5 mb-6">
                    <p className="text-[11px] font-medium text-text-muted uppercase tracking-wider mb-2">UID</p>
                    <p className="text-lg font-mono text-text-secondary">{uid}</p>
                </div>

                {/* Info */}
                <p className="text-sm text-text-secondary mb-8">
                    {t.rejected.contact}
                </p>

                {/* Contact */}
                <div className="bg-white/[0.03] border border-white/5 rounded-xl p-5 mb-6 text-left">
                    <p className="text-[11px] font-medium text-text-muted uppercase tracking-wider mb-3">{t.rejected.contactSupport}</p>
                    <div className="space-y-2 text-sm">
                        <a href="mailto:support@louislab.com" className="flex items-center gap-3 text-text-secondary hover:text-white transition-colors">
                            <Icons.Link className="w-4 h-4" /> support@louislab.com
                        </a>
                        <a href="https://t.me/louislab_support" target="_blank" rel="noopener noreferrer" className="flex items-center gap-3 text-text-secondary hover:text-white transition-colors">
                            <Icons.Link className="w-4 h-4" /> Telegram: @louislab_support
                        </a>
                    </div>
                </div>

                {/* Buttons */}
                <div className="space-y-3">
                    <button
                        onClick={() => navigate('/setup-api')}
                        className="w-full h-12 bg-white text-black font-medium rounded-xl hover:bg-white/90 transition-all flex items-center justify-center gap-2"
                    >
                        <Icons.RefreshCw className="w-4 h-4" />
                        {t.rejected.retry}
                    </button>
                    <button
                        onClick={() => { logout(); navigate('/login'); }}
                        className="w-full h-12 bg-white/5 border border-white/10 text-text-secondary rounded-xl hover:bg-white/10 hover:text-white transition-all flex items-center justify-center gap-2"
                    >
                        <Icons.LogOut className="w-4 h-4" />
                        {t.nav.logout}
                    </button>
                </div>
            </div>
        </div>
    );
}
