import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle } from '../context/I18nContext';
import { Icons } from '../components/Icons';

export default function Deploy() {
    const { user } = useAuth();
    const { t } = useI18n();
    const navigate = useNavigate();

    const ZEABUR_TEMPLATE_URL = 'https://zeabur.com/referral?referralCode=louis12';

    const steps = [
        { num: 1, title: t.deploy.step1, desc: t.deploy.step1Desc, icon: Icons.Rocket },
        { num: 2, title: t.deploy.step2, desc: t.deploy.step2Desc, icon: Icons.Settings },
        { num: 3, title: t.deploy.step3, desc: t.deploy.step3Desc, icon: Icons.Clock },
        { num: 4, title: t.deploy.step4, desc: t.deploy.step4Desc, icon: Icons.Link }
    ];

    const envVars = [
        { key: 'NODE_SECRET', desc: t.settings.nodeSecretHint },
        { key: 'EXCHANGE_API_KEY', desc: 'Bitget API Key' },
        { key: 'EXCHANGE_SECRET', desc: 'Bitget API Secret' },
        { key: 'EXCHANGE_PASSPHRASE', desc: 'Bitget Passphrase' }
    ];

    return (
        <div className="min-h-screen bg-bg-primary bg-gradient-radial bg-grid-pattern">
            {/* Header */}
            <header className="sticky top-0 z-50 bg-bg-primary/80 backdrop-blur-xl border-b border-white/5">
                <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <button onClick={() => navigate('/dashboard')} className="text-[13px] text-white/40 hover:text-white transition-colors flex items-center gap-1">
                            <Icons.ArrowLeft className="w-4 h-4" />
                            {t.nav.back}
                        </button>
                    </div>
                    <span className="text-[14px] font-semibold text-white">{t.deploy.title}</span>
                    <div className="flex items-center gap-4">
                        <LanguageToggle />
                    </div>
                </div>
            </header>

            <main className="max-w-5xl mx-auto px-6 py-12">
                {/* Hero */}
                <div className="text-center mb-12 animate-fade-in">
                    <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-white/10 to-white/5 border border-white/10 mb-6 text-white">
                        <Icons.Rocket className="w-10 h-10" />
                    </div>
                    <h2 className="text-3xl font-bold text-white mb-3">{t.deploy.heroTitle}</h2>
                    <p className="text-white/40 max-w-lg mx-auto text-[15px]">
                        {t.deploy.heroSubtitle}
                    </p>
                </div>

                {/* Steps */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
                    {steps.map((step, i) => (
                        <div
                            key={step.num}
                            className="glass-card rounded-2xl p-6 text-center animate-fade-in hover:border-white/10 transition-all group"
                            style={{ animationDelay: `${i * 0.1}s` }}
                        >
                            <span className="mb-3 block flex justify-center text-white/60 group-hover:text-white transition-colors">
                                <step.icon className="w-8 h-8" />
                            </span>
                            <div className="text-[11px] text-white/30 mb-1 uppercase tracking-wider">{t.deploy.step} {step.num}</div>
                            <div className="text-[14px] font-semibold text-white mb-1">{step.title}</div>
                            <div className="text-[12px] text-white/40">{step.desc}</div>
                        </div>
                    ))}
                </div>

                {/* Deploy Button */}
                <div className="text-center mb-12 animate-fade-in" style={{ animationDelay: '0.4s' }}>
                    <a
                        href={ZEABUR_TEMPLATE_URL}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-3 px-10 py-5 bg-white text-black font-bold rounded-2xl text-lg transition-all duration-300 hover:bg-white/90 shadow-lg shadow-white/20 hover:shadow-xl hover:shadow-white/30 hover:scale-105 active:scale-[0.98]"
                    >
                        <img src="https://zeabur.com/button.svg" alt="" className="h-6" />
                        {t.deploy.deployBtn}
                    </a>
                    <p className="text-[12px] text-white/30 mt-4 flex items-center justify-center gap-1">
                        <Icons.ArrowRight className="w-3 h-3" />
                        {t.deploy.clickToOpen}
                    </p>
                </div>

                {/* Environment Variables */}
                <div className="glass-card rounded-2xl p-8 mb-8 animate-fade-in" style={{ animationDelay: '0.5s' }}>
                    <h3 className="text-[14px] font-semibold text-white mb-6 flex items-center gap-2">
                        <Icons.List className="w-5 h-5 text-text-muted" /> {t.deploy.envVars}
                    </h3>
                    <div className="grid gap-3">
                        {envVars.map((v, i) => (
                            <div key={v.key} className="flex items-center gap-4 py-3 border-b border-white/5 last:border-0">
                                <code className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-[13px] font-mono text-white min-w-[200px]">
                                    {v.key}
                                </code>
                                <span className="text-[13px] text-white/50">{v.desc}</span>
                            </div>
                        ))}
                    </div>
                </div>

                {/* After Deploy */}
                <div className="bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border border-emerald-500/20 rounded-2xl p-8 animate-fade-in" style={{ animationDelay: '0.6s' }}>
                    <h3 className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2">
                        <Icons.CheckCircle className="w-5 h-5 text-emerald-400" /> {t.deploy.afterDeploy}
                    </h3>
                    <ol className="space-y-3 text-[13px] text-white/60">
                        <li className="flex items-start gap-3">
                            <span className="w-5 h-5 rounded-full bg-white/10 text-white/50 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">1</span>
                            <span>{t.deploy.afterStep1}</span>
                        </li>
                        <li className="flex items-start gap-3">
                            <span className="w-5 h-5 rounded-full bg-white/10 text-white/50 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">2</span>
                            <span>{t.deploy.afterStep2} (<code className="text-white/80 bg-white/5 px-1.5 py-0.5 rounded text-[12px]">https://xxx.zeabur.app</code>)</span>
                        </li>
                        <li className="flex items-start gap-3">
                            <span className="w-5 h-5 rounded-full bg-white/10 text-white/50 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">3</span>
                            <span>{t.deploy.afterStep3}</span>
                        </li>
                    </ol>
                </div>

                {/* Bottom Link */}
                <div className="text-center mt-8">
                    <p className="text-[13px] text-white/30 mb-2">{t.deploy.alreadyDeployed}</p>
                    <Link to="/settings" className="text-white font-medium hover:underline underline-offset-4 text-[14px] flex items-center justify-center gap-1">
                        {t.deploy.connectNode} <Icons.ArrowRight className="w-3 h-3" />
                    </Link>
                </div>
            </main>
        </div>
    );
}
