import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle } from '../context/I18nContext';
import { Icons } from '../components/Icons';

// Zeabur Template ID - 已創建: https://zeabur.com/templates/RBBWT1
const ZEABUR_TEMPLATE_ID = 'RBBWT1';

// Referral code
const REFERRAL_CODE = 'louis12';

export default function Deploy() {
    const { user } = useAuth();
    const { t } = useI18n();
    const navigate = useNavigate();
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [copied, setCopied] = useState(false);

    // 使用 Bitget UID (exchange_uid) 而非 System UUID
    // Bitget UID 是 10 位數字，更容易記住
    const bitgetUid = user?.exchange_uid;
    const hasValidBitgetUid = bitgetUid && bitgetUid.length >= 8;

    // 動態生成一鍵部署 URL（包含 BITGET_UID）
    const oneClickDeployUrl = hasValidBitgetUid
        ? `https://zeabur.com/templates/${ZEABUR_TEMPLATE_ID}?referralCode=${REFERRAL_CODE}&BITGET_UID=${bitgetUid}`
        : null;

    // Bitget UID 複製功能
    const handleCopyBitgetUid = () => {
        navigator.clipboard.writeText(bitgetUid || '');
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const steps = [
        { num: 1, title: t.deploy.step1Title || '一鍵部署', titleEn: 'One-Click Deploy', desc: t.deploy.step1Desc || '點擊按鈕開始', icon: Icons.Rocket },
        { num: 2, title: t.deploy.step2Title || '確認部署', titleEn: 'Confirm Deploy', desc: t.deploy.step2Desc || '在 Zeabur 確認', icon: Icons.CheckCircle },
        { num: 3, title: t.deploy.step3Title || '連接節點', titleEn: 'Connect Node', desc: t.deploy.step3Desc || '貼上網域到設定', icon: Icons.Link }
    ];

    return (
        <div className="min-h-screen bg-bg-primary bg-gradient-radial bg-grid-pattern">
            {/* Header */}
            <header className="sticky top-0 z-50 bg-bg-primary/80 backdrop-blur-xl border-b border-white/5">
                <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
                    <button onClick={() => navigate('/dashboard')} className="text-[13px] text-white/40 hover:text-white transition-colors flex items-center gap-1">
                        <Icons.ArrowLeft className="w-4 h-4" />
                        {t.nav.back}
                    </button>
                    <span className="text-[14px] font-semibold text-white">{t.deploy.title}</span>
                    <LanguageToggle />
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
                        {t.deploy.heroSubtitle || '只需點擊一個按鈕，即可部署您的專屬交易節點'}
                    </p>
                </div>

                {/* Simple Steps */}
                <div className="grid grid-cols-3 gap-4 mb-12">
                    {steps.map((step, i) => (
                        <div
                            key={step.num}
                            className="glass-card rounded-2xl p-6 text-center animate-fade-in hover:border-white/10 transition-all group"
                            style={{ animationDelay: `${i * 0.1}s` }}
                        >
                            <span className="mb-3 block flex justify-center text-white/60 group-hover:text-white transition-colors">
                                <step.icon className="w-8 h-8" />
                            </span>
                            <div className="text-[11px] text-white/30 mb-1 uppercase tracking-wider">Step {step.num}</div>
                            <div className="text-[14px] font-semibold text-white mb-1">{step.title}</div>
                            <div className="text-[12px] text-white/40">{step.desc}</div>
                        </div>
                    ))}
                </div>

                {/* Main Deploy Card */}
                <div className="bg-gradient-to-br from-white/10 to-white/5 border border-white/20 rounded-3xl p-10 mb-8 animate-fade-in text-center" style={{ animationDelay: '0.3s' }}>
                    <div className="mb-6">
                        <h3 className="text-2xl font-bold text-white mb-2">
                            {t.deploy.oneClickTitle || '一鍵部署您的交易節點'}
                        </h3>
                        <p className="text-white/50 text-[14px]">
                            {t.deploy.oneClickDesc || '無需任何技術背景，點擊按鈕即可完成部署'}
                        </p>
                    </div>

                    {/* Bitget UID Display */}
                    <div className="bg-black/30 rounded-xl p-4 mb-6 inline-block">
                        <p className="text-[11px] text-white/40 mb-2 uppercase tracking-wider">
                            {t.deploy.yourBitgetUid || '您的 Bitget UID'}
                        </p>
                        <div className="flex items-center gap-3">
                            {hasValidBitgetUid ? (
                                <>
                                    <code className="text-[20px] font-mono text-emerald-400 font-bold">
                                        {bitgetUid}
                                    </code>
                                    <button
                                        onClick={handleCopyBitgetUid}
                                        className="text-white/40 hover:text-white transition-colors"
                                        title="Copy"
                                    >
                                        {copied ? <Icons.CheckCircle className="w-4 h-4 text-emerald-400" /> : <Icons.RefreshCw className="w-4 h-4" />}
                                    </button>
                                </>
                            ) : (
                                <span className="text-[14px] text-amber-400">
                                    {user ? '請先驗證 Bitget API 以獲取您的 UID' : '請先登入'}
                                </span>
                            )}
                        </div>
                        {hasValidBitgetUid && (
                            <p className="text-[11px] text-white/30 mt-2">
                                這是您的 Bitget 帳戶 ID，部署時會自動填入
                            </p>
                        )}
                    </div>

                    {/* One-Click Deploy Button */}
                    <div className="mb-6">
                        {hasValidBitgetUid ? (
                            <a
                                href={oneClickDeployUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-3 px-10 py-5 bg-white text-black font-bold text-lg rounded-2xl hover:bg-white/90 transition-all shadow-lg shadow-white/20 hover:shadow-white/30 active:scale-[0.98]"
                            >
                                <Icons.Rocket className="w-6 h-6" />
                                {t.deploy.oneClickBtn || '一鍵部署到 Zeabur'}
                            </a>
                        ) : user ? (
                            <button
                                onClick={() => navigate('/setup-api')}
                                className="inline-flex items-center gap-3 px-10 py-5 bg-amber-500 text-black font-bold text-lg rounded-2xl hover:bg-amber-400 transition-all"
                            >
                                <Icons.Settings className="w-6 h-6" />
                                前往驗證 Bitget API
                            </button>
                        ) : (
                            <button
                                onClick={() => navigate('/login')}
                                className="inline-flex items-center gap-3 px-10 py-5 bg-amber-500 text-black font-bold text-lg rounded-2xl hover:bg-amber-400 transition-all"
                            >
                                <Icons.LogOut className="w-6 h-6" />
                                請先登入
                            </button>
                        )}
                    </div>

                    <p className="text-[12px] text-white/30 flex items-center justify-center gap-2">
                        <Icons.Shield className="w-4 h-4" />
                        {t.deploy.securityNote || '安全加密・無需提供 API 密鑰'}
                    </p>
                </div>

                {/* After Deploy Instructions */}
                <div className="bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border border-emerald-500/20 rounded-2xl p-8 mb-8 animate-fade-in" style={{ animationDelay: '0.4s' }}>
                    <h3 className="text-[16px] font-semibold text-white mb-4 flex items-center gap-2">
                        <Icons.CheckCircle className="w-5 h-5 text-emerald-400" />
                        {t.deploy.afterDeployTitle || '部署完成後'}
                    </h3>
                    <ol className="space-y-3 text-[13px] text-white/60 mb-6">
                        <li className="flex items-start gap-3">
                            <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">1</span>
                            <span>{t.deploy.afterStep1 || '等待 Zeabur 部署完成（約 1-2 分鐘）'}</span>
                        </li>
                        <li className="flex items-start gap-3">
                            <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">2</span>
                            <span>
                                {t.deploy.afterStep2 || '在 Zeabur 頁面複製生成的網域'}
                                <code className="text-white/80 bg-white/5 px-1.5 py-0.5 rounded text-[12px] ml-1">xxx.zeabur.app</code>
                            </span>
                        </li>
                        <li className="flex items-start gap-3">
                            <span className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">3</span>
                            <span>{t.deploy.afterStep3 || '返回本站設定頁面，貼上網域並儲存'}</span>
                        </li>
                    </ol>
                    <Link to="/settings" className="btn-success inline-flex">
                        {t.deploy.goToSettings || '前往設定頁面'}
                        <Icons.ArrowRight className="w-4 h-4" />
                    </Link>
                </div>

                {/* Advanced Options Toggle */}
                <div className="text-center">
                    <button
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="text-[13px] text-white/30 hover:text-white/60 transition-colors flex items-center gap-2 mx-auto"
                    >
                        {showAdvanced ? <Icons.X className="w-4 h-4" /> : <Icons.Settings className="w-4 h-4" />}
                        {showAdvanced ? (t.deploy.hideAdvanced || '隱藏進階選項') : (t.deploy.showAdvanced || '進階用戶：手動部署')}
                    </button>
                </div>

                {/* Advanced Options */}
                {showAdvanced && (
                    <div className="mt-8 glass-card rounded-2xl p-8 animate-fade-in">
                        <h4 className="text-[14px] font-semibold text-white/60 mb-4 flex items-center gap-2">
                            <Icons.Settings className="w-4 h-4" />
                            {t.deploy.advancedTitle || '手動部署（進階用戶）'}
                        </h4>
                        <p className="text-[13px] text-white/40 mb-6">
                            {t.deploy.advancedDesc || '如果您想自行管理程式碼，可以使用以下方式：'}
                        </p>

                        <div className="space-y-4">
                            <div className="bg-black/20 rounded-xl p-4">
                                <p className="text-[12px] text-white/40 mb-2">1. Fork Repository</p>
                                <a
                                    href="https://github.com/thankcoom/bitget-as"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-[13px] text-white hover:underline flex items-center gap-2"
                                >
                                    <Icons.Play className="w-4 h-4" />
                                    github.com/thankcoom/bitget-as
                                </a>
                            </div>

                            <div className="bg-black/20 rounded-xl p-4">
                                <p className="text-[12px] text-white/40 mb-2">2. {t.deploy.envVars || '環境變數'}</p>
                                <div className="space-y-2 font-mono text-[12px]">
                                    <div className="flex gap-2">
                                        <code className="text-emerald-400">AUTH_SERVER_URL</code>
                                        <code className="text-white/60">=</code>
                                        <code className="text-white/80">https://louisasgrid-api.zeabur.app</code>
                                    </div>
                                    <div className="flex gap-2">
                                        <code className="text-emerald-400">USER_ID</code>
                                        <code className="text-white/60">=</code>
                                        <code className="text-white/80">{user?.id || 'your-user-id'}</code>
                                    </div>
                                    <div className="flex gap-2">
                                        <code className="text-emerald-400">NODE_SECRET</code>
                                        <code className="text-white/60">=</code>
                                        <code className="text-white/80">{t.deploy.autoGenerated || '（自動生成）'}</code>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )}

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
