import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle } from '../context/I18nContext';
import { Icons } from '../components/Icons';

export default function SetupAPI() {
    const { refreshUser } = useAuth();
    const { t } = useI18n();
    const navigate = useNavigate();

    const [apiKey, setApiKey] = useState('');
    const [apiSecret, setApiSecret] = useState('');
    const [passphrase, setPassphrase] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [step, setStep] = useState(1);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (!apiKey || !apiSecret || !passphrase) {
            setError(t.settings.fieldsRequired || 'All fields are required');
            return;
        }

        setLoading(true);
        try {
            const res = await api.post('/auth/verify_api', {
                api_key: apiKey,
                api_secret: apiSecret,
                passphrase: passphrase
            });

            await refreshUser();
            navigate('/pending', { state: { uid: res.data.uid } });
        } catch (err) {
            const detail = err.response?.data?.detail;
            setError(typeof detail === 'string' ? detail : detail?.message || t.common.error);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-bg-primary bg-gradient-radial bg-grid-pattern relative overflow-hidden p-4">
            {/* Background effects */}
            <div className="absolute top-1/4 left-1/3 w-96 h-96 bg-white/[0.02] rounded-full blur-3xl animate-pulse-slow" />

            <div className="absolute top-6 right-6 z-20">
                <LanguageToggle />
            </div>

            <div className="w-full max-w-xl glass-card rounded-2xl shadow-2xl shadow-black/50 animate-fade-in relative z-10 overflow-hidden">
                {/* Header */}
                <div className="p-8 border-b border-white/5">
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center">
                            <Icons.Shield className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h1 className="text-xl font-bold text-white">{t.setup.title}</h1>
                            <p className="text-sm text-text-muted">{t.setup.subtitle}</p>
                        </div>
                    </div>
                </div>

                {/* Progress Steps */}
                <div className="px-8 py-6 bg-white/[0.02] border-b border-white/5">
                    <div className="flex items-center justify-center gap-4">
                        <div className="flex items-center gap-2">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${step >= 1 ? 'bg-white text-black' : 'bg-white/10 text-text-muted'}`}>
                                1
                            </div>
                            <span className={`text-sm ${step >= 1 ? 'text-white' : 'text-text-muted'}`}>{t.setup.step1}</span>
                        </div>
                        <div className={`w-12 h-px ${step >= 2 ? 'bg-white' : 'bg-white/20'}`} />
                        <div className="flex items-center gap-2">
                            <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold transition-all ${step >= 2 ? 'bg-white text-black' : 'bg-white/10 text-text-muted'}`}>
                                2
                            </div>
                            <span className={`text-sm ${step >= 2 ? 'text-white' : 'text-text-muted'}`}>{t.setup.step2}</span>
                        </div>
                    </div>
                </div>

                <div className="p-8">
                    {/* Step 1: Instructions */}
                    {step === 1 && (
                        <div className="space-y-6 animate-fade-in">
                            <div className="bg-white/[0.03] border border-white/5 rounded-xl p-6">
                                <h3 className="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                                    <Icons.List className="w-4 h-4" /> {t.setup.howTo}
                                </h3>
                                <ol className="space-y-3">
                                    {[
                                        t.setup.instruction1,
                                        t.setup.instruction2,
                                        t.setup.instruction3,
                                        t.setup.instruction4,
                                        t.setup.instruction5
                                    ].map((text, i) => (
                                        <li key={i} className="flex items-start gap-3">
                                            <span className="w-5 h-5 rounded-full bg-white/10 text-text-muted text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                                                {i + 1}
                                            </span>
                                            <span className="text-sm text-text-secondary">{text}</span>
                                        </li>
                                    ))}
                                </ol>
                            </div>

                            <a
                                href="https://www.bitget.com/zh-CN/account/newapi"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center justify-center gap-2 w-full py-3 bg-white/5 border border-white/10 text-text-secondary text-sm rounded-xl hover:bg-white/[0.07] hover:border-white/20 transition-all"
                            >
                                <Icons.Link className="w-4 h-4" /> {t.setup.openBitget}
                            </a>

                            <button
                                onClick={() => setStep(2)}
                                className="w-full h-12 bg-white text-black font-semibold rounded-xl transition-all duration-300 hover:bg-white/90 hover:shadow-lg hover:shadow-white/10 active:scale-[0.98] flex items-center justify-center gap-2"
                            >
                                {t.setup.readyBtn} <Icons.ArrowRight className="w-4 h-4" />
                            </button>
                        </div>
                    )}

                    {/* Step 2: Input API */}
                    {step === 2 && (
                        <form onSubmit={handleSubmit} className="space-y-5 animate-fade-in">
                            {error && (
                                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-center flex items-center justify-center gap-2">
                                    <Icons.AlertCircle className="w-4 h-4 text-red-400" />
                                    <p className="text-[13px] text-red-400">{error}</p>
                                </div>
                            )}

                            <div>
                                <label className="block text-[11px] font-medium text-text-muted mb-2 uppercase tracking-wider ml-1">
                                    {t.setup.apiKey}
                                </label>
                                <input
                                    type="text"
                                    className="w-full h-12 rounded-xl bg-white/5 border border-white/10 px-4 text-white font-mono text-sm placeholder-text-disabled/50 focus:bg-white/[0.07] focus:border-white/20 focus:outline-none transition-all"
                                    value={apiKey}
                                    onChange={(e) => setApiKey(e.target.value)}
                                    placeholder="bg_xxxxxxxxxxxxxxxx"
                                />
                            </div>

                            <div>
                                <label className="block text-[11px] font-medium text-text-muted mb-2 uppercase tracking-wider ml-1">
                                    {t.setup.apiSecret}
                                </label>
                                <input
                                    type="password"
                                    className="w-full h-12 rounded-xl bg-white/5 border border-white/10 px-4 text-white font-mono text-sm placeholder-text-disabled/50 focus:bg-white/[0.07] focus:border-white/20 focus:outline-none transition-all"
                                    value={apiSecret}
                                    onChange={(e) => setApiSecret(e.target.value)}
                                    placeholder="••••••••••••••••"
                                />
                            </div>

                            <div>
                                <label className="block text-[11px] font-medium text-text-muted mb-2 uppercase tracking-wider ml-1">
                                    {t.setup.passphrase} <span className="text-red-400">{t.setup.required}</span>
                                </label>
                                <input
                                    type="password"
                                    className="w-full h-12 rounded-xl bg-white/5 border border-white/10 px-4 text-white font-mono text-sm placeholder-text-disabled/50 focus:bg-white/[0.07] focus:border-white/20 focus:outline-none transition-all"
                                    value={passphrase}
                                    onChange={(e) => setPassphrase(e.target.value)}
                                    placeholder="••••••••"
                                />
                            </div>

                            <div className="flex gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setStep(1)}
                                    className="flex-1 h-12 bg-white/5 border border-white/10 text-text-secondary rounded-xl hover:bg-white/[0.07] transition-all flex items-center justify-center gap-2"
                                >
                                    <Icons.ArrowLeft className="w-4 h-4" /> {t.setup.back}
                                </button>
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="flex-1 h-12 bg-white text-black font-semibold rounded-xl transition-all hover:bg-white/90 disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    {loading ? (
                                        <>
                                            <Icons.RefreshCw className="w-4 h-4 animate-spin" />
                                            <span>{t.setup.verifying}</span>
                                        </>
                                    ) : t.setup.verify}
                                </button>
                            </div>

                            <p className="text-xs text-text-muted text-center pt-4 flex items-center justify-center gap-1">
                                <Icons.Shield className="w-3 h-3" /> {t.setup.securityNote}
                            </p>
                        </form>
                    )}
                </div>
            </div>
        </div>
    );
}
