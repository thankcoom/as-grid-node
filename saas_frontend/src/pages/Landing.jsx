import React from 'react';
import { Link } from 'react-router-dom';
import { useI18n, LanguageToggle, Logo } from '../context/I18nContext';
import { Icons } from '../components/Icons';

const BITGET_REFERRAL_URL = 'https://partner.bitget.fit/bg/aslouis';

export default function Landing() {
    const { t } = useI18n();

    return (
        <div className="min-h-screen bg-bg-primary bg-gradient-radial bg-grid-pattern text-white overflow-x-hidden">
            {/* ═══════════════════════════════════════════════════════════════
          NAVBAR
          ═══════════════════════════════════════════════════════════════ */}
            <nav className="fixed top-0 left-0 right-0 z-50 bg-bg-primary/80 backdrop-blur-xl border-b border-white/5">
                <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
                    <Logo size="md" />

                    <div className="flex items-center gap-4">
                        <LanguageToggle />
                        <Link to="/login" className="text-[13px] text-text-muted hover:text-white transition-colors hidden sm:block">
                            {t.nav.login}
                        </Link>
                        <Link to="/register" className="px-5 py-2.5 bg-white text-black font-semibold text-[13px] rounded-xl hover:bg-white/90 transition-all flex items-center gap-2">
                            {t.nav.register}
                            <Icons.ArrowRight className="w-4 h-4" />
                        </Link>
                    </div>
                </div>
            </nav>

            {/* ═══════════════════════════════════════════════════════════════
          HERO SECTION
          ═══════════════════════════════════════════════════════════════ */}
            <section className="min-h-screen flex flex-col items-center justify-center px-6 relative">
                {/* Background orbs */}
                <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-white/[0.02] rounded-full blur-3xl animate-pulse-slow" />
                <div className="absolute bottom-1/3 left-1/4 w-96 h-96 bg-white/[0.015] rounded-full blur-3xl animate-pulse-slow" style={{ animationDelay: '1.5s' }} />

                <div className="max-w-3xl mx-auto text-center relative z-10">
                    {/* Tag */}
                    <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-full mb-8 animate-fade-in">
                        <span className="w-2 h-2 rounded-full bg-white/60 animate-pulse"></span>
                        <span className="text-[11px] font-medium text-text-muted uppercase tracking-wider">{t.landing.tag}</span>
                    </div>

                    {/* Title */}
                    <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6 animate-fade-in" style={{ animationDelay: '0.1s' }}>
                        <span className="block text-white">{t.landing.title1}</span>
                        <span className="block text-text-muted">{t.landing.title2}</span>
                    </h1>

                    {/* Subtitle */}
                    <p className="text-base md:text-lg text-text-muted max-w-xl mx-auto mb-10 animate-fade-in" style={{ animationDelay: '0.2s' }}>
                        {t.landing.subtitle}
                    </p>

                    {/* CTA Buttons */}
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-10 animate-fade-in" style={{ animationDelay: '0.3s' }}>
                        <Link
                            to="/register"
                            className="px-8 py-4 bg-white text-black font-bold text-[15px] rounded-xl hover:bg-white/90 transition-all hover:shadow-lg hover:shadow-white/10 flex items-center gap-2"
                        >
                            {t.landing.cta} <Icons.ArrowRight className="w-4 h-4" />
                        </Link>
                    </div>

                    {/* Bitget Referral */}
                    <div className="animate-fade-in" style={{ animationDelay: '0.4s' }}>
                        <div className="inline-flex items-center gap-3 px-6 py-3 bg-white/5 border border-white/10 rounded-full group hover:bg-white/10 transition-colors">
                            <span className="text-[12px] text-text-muted">{t.landing.bitgetCta}</span>
                            <a
                                href={BITGET_REFERRAL_URL}
                                target="_blank"
                                rel="noreferrer"
                                className="flex items-center gap-1 text-[13px] font-semibold text-white hover:underline underline-offset-4"
                            >
                                {t.landing.bitgetLink} <Icons.ArrowRight className="w-3 h-3 group-hover:translate-x-0.5 transition-transform" />
                            </a>
                        </div>
                    </div>

                    {/* Referral Notice - Important Warning */}
                    <div className="animate-fade-in mt-6" style={{ animationDelay: '0.5s' }}>
                        <div className="max-w-lg mx-auto px-6 py-4 bg-amber-500/10 border border-amber-500/30 rounded-xl">
                            <div className="flex items-start gap-3">
                                <div className="flex-shrink-0 w-6 h-6 rounded-full bg-amber-500/20 flex items-center justify-center mt-0.5">
                                    <span className="text-amber-400 text-sm font-bold">!</span>
                                </div>
                                <div className="text-left">
                                    <p className="text-[13px] font-medium text-amber-300">
                                        {t.landing.referralNotice}
                                    </p>
                                    <p className="text-[12px] text-amber-400/80 mt-1">
                                        {t.landing.referralNotice2}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Scroll indicator */}
                <div className="absolute bottom-10 left-1/2 -translate-x-1/2 animate-bounce">
                    <div className="w-6 h-10 border-2 border-white/20 rounded-full flex items-start justify-center pt-2">
                        <div className="w-1.5 h-3 bg-white/40 rounded-full"></div>
                    </div>
                </div>
            </section>

            {/* ═══════════════════════════════════════════════════════════════
          FEATURES SECTION
          ═══════════════════════════════════════════════════════════════ */}
            <section className="py-24 px-6 border-t border-white/5">
                <div className="max-w-5xl mx-auto">
                    <h2 className="text-2xl md:text-3xl font-bold text-center mb-16 text-white">{t.features.title}</h2>

                    <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
                        {t.features.list.map((feature, i) => (
                            <div
                                key={i}
                                className="glass-card rounded-2xl p-6 hover:border-white/20 transition-all group"
                            >
                                <div className="text-3xl font-bold text-white/10 mb-4 group-hover:text-white/20 transition-colors">
                                    0{i + 1}
                                </div>
                                <h3 className="text-[15px] font-semibold text-white mb-2">{feature.title}</h3>
                                <p className="text-[13px] text-text-muted leading-relaxed">{feature.desc}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ═══════════════════════════════════════════════════════════════
          STEPS SECTION
          ═══════════════════════════════════════════════════════════════ */}
            <section className="py-24 px-6 border-t border-white/5">
                <div className="max-w-4xl mx-auto">
                    <h2 className="text-2xl md:text-3xl font-bold text-center mb-16 text-white">{t.steps.title}</h2>

                    <div className="flex flex-col md:flex-row gap-8 md:gap-4">
                        {t.steps.list.map((step, i) => (
                            <div key={i} className="flex-1 text-center relative">
                                {i < t.steps.list.length - 1 && (
                                    <div className="hidden md:block absolute top-6 left-1/2 w-full h-px bg-white/10"></div>
                                )}
                                <div className="relative z-10">
                                    <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-[13px] font-bold text-white">
                                        0{i + 1}
                                    </div>
                                    <h3 className="text-[15px] font-semibold text-white mb-1">{step.title}</h3>
                                    <p className="text-[13px] text-text-muted">{step.desc}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* ═══════════════════════════════════════════════════════════════
          CTA SECTION
          ═══════════════════════════════════════════════════════════════ */}
            <section className="py-24 px-6 border-t border-white/5">
                <div className="max-w-2xl mx-auto text-center">
                    <h2 className="text-3xl md:text-4xl font-bold text-white mb-8">{t.cta.title}</h2>

                    <div className="flex flex-col items-center gap-6">
                        <Link
                            to="/register"
                            className="px-10 py-4 bg-white text-black font-bold text-[15px] rounded-xl hover:bg-white/90 transition-all"
                        >
                            {t.cta.button}
                        </Link>

                        {/* Bitget Referral Banner */}
                        <div className="glass-card rounded-2xl p-6 w-full max-w-md">
                            <div className="flex items-center justify-center gap-4">
                                <span className="text-[13px] text-text-muted">{t.cta.bitgetNote}</span>
                                <a
                                    href={BITGET_REFERRAL_URL}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="px-5 py-2.5 bg-white text-black font-semibold text-[13px] rounded-lg hover:bg-white/90 transition-all"
                                >
                                    {t.cta.bitgetLink} →
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* ═══════════════════════════════════════════════════════════════
          FOOTER
          ═══════════════════════════════════════════════════════════════ */}
            <footer className="border-t border-white/5 py-8 px-6">
                <div className="max-w-5xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
                    <Logo size="sm" />

                    <div className="flex items-center gap-6 text-[12px] text-text-muted">
                        <Link to="/login" className="hover:text-white transition-colors">{t.nav.login}</Link>
                        <Link to="/register" className="hover:text-white transition-colors">{t.nav.register}</Link>
                        <a href={BITGET_REFERRAL_URL} target="_blank" rel="noreferrer" className="hover:text-white transition-colors">Bitget</a>
                    </div>

                    <div className="text-[11px] text-text-disabled">
                        {t.footer.rights}
                    </div>
                </div>
            </footer>
        </div>
    );
}
