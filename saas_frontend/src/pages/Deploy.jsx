import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle } from '../context/I18nContext';
import { Icons } from '../components/Icons';

// 官方 API 伺服器 URL
const AUTH_SERVER_URL = 'https://louisasgrid-api.zeabur.app';

// GitHub template repo (用戶 Fork 後部署)
const GITHUB_TEMPLATE_URL = 'https://github.com/thankcoom/bitget-as';

// Zeabur 一鍵部署 URL
const ZEABUR_DEPLOY_URL = 'https://zeabur.com/referral?referralCode=louis12';

export default function Deploy() {
    const { user } = useAuth();
    const { t } = useI18n();
    const navigate = useNavigate();
    const [copied, setCopied] = useState(false);

    // 用戶專屬環境變數
    const userEnvVars = [
        {
            key: 'AUTH_SERVER_URL',
            value: AUTH_SERVER_URL,
            desc: '官方 API 伺服器網址（固定值）',
            descEn: 'Official API server URL (fixed)'
        },
        {
            key: 'USER_ID',
            value: user?.id || 'your-user-id',
            desc: '您的用戶 ID（自動填入）',
            descEn: 'Your user ID (auto-filled)'
        },
        {
            key: 'NODE_SECRET',
            value: 'your-secret-' + (user?.id?.slice(0, 8) || 'xxxxx'),
            desc: '節點密鑰（可自訂，請記住）',
            descEn: 'Node secret (customizable, remember it)'
        }
    ];

    // 生成可複製的 env 格式
    const envText = userEnvVars.map(v => `${v.key}=${v.value}`).join('\n');

    const handleCopy = () => {
        navigator.clipboard.writeText(envText);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    const steps = [
        { num: 1, title: 'Fork 程式碼', titleEn: 'Fork Code', desc: '複製到您的 GitHub', icon: Icons.Play },
        { num: 2, title: '連接 Zeabur', titleEn: 'Connect Zeabur', desc: '一鍵部署', icon: Icons.Rocket },
        { num: 3, title: '設定環境變數', titleEn: 'Set Env Vars', desc: '複製下方設定', icon: Icons.Settings },
        { num: 4, title: '回填 Node URL', titleEn: 'Fill Node URL', desc: '到設定頁連接', icon: Icons.Link }
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
                            <div className="text-[11px] text-white/30 mb-1 uppercase tracking-wider">Step {step.num}</div>
                            <div className="text-[14px] font-semibold text-white mb-1">{step.title}</div>
                            <div className="text-[12px] text-white/40">{step.desc}</div>
                        </div>
                    ))}
                </div>

                {/* Step 1: Fork Code */}
                <div className="glass-card rounded-2xl p-8 mb-6 animate-fade-in" style={{ animationDelay: '0.4s' }}>
                    <h3 className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2">
                        <span className="w-6 h-6 rounded-full bg-white/10 text-white flex items-center justify-center text-[12px] font-bold">1</span>
                        Fork 程式碼到您的 GitHub
                    </h3>
                    <p className="text-[13px] text-white/50 mb-4">
                        點擊下方按鈕，將 Grid Node 程式碼複製到您的 GitHub 帳號
                    </p>
                    <a
                        href={GITHUB_TEMPLATE_URL}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-secondary inline-flex"
                    >
                        <Icons.Play className="w-4 h-4" />
                        打開 GitHub Repository
                    </a>
                </div>

                {/* Step 2: Deploy to Zeabur */}
                <div className="glass-card rounded-2xl p-8 mb-6 animate-fade-in" style={{ animationDelay: '0.5s' }}>
                    <h3 className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2">
                        <span className="w-6 h-6 rounded-full bg-white/10 text-white flex items-center justify-center text-[12px] font-bold">2</span>
                        部署到 Zeabur
                    </h3>
                    <p className="text-[13px] text-white/50 mb-4">
                        連接您的 GitHub，選擇 Fork 的 repo，部署 <code className="bg-white/10 px-1.5 py-0.5 rounded text-white/80">grid_node</code> 資料夾
                    </p>
                    <a
                        href={ZEABUR_DEPLOY_URL}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn-primary inline-flex"
                    >
                        <img src="https://zeabur.com/button.svg" alt="" className="h-5" />
                        {t.deploy.deployBtn}
                    </a>
                </div>

                {/* Step 3: Environment Variables */}
                <div className="glass-card rounded-2xl p-8 mb-6 animate-fade-in" style={{ animationDelay: '0.6s' }}>
                    <h3 className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2">
                        <span className="w-6 h-6 rounded-full bg-white/10 text-white flex items-center justify-center text-[12px] font-bold">3</span>
                        <Icons.List className="w-5 h-5 text-text-muted" />
                        設定環境變數（您的專屬設定）
                    </h3>

                    <div className="bg-black/30 rounded-xl p-4 mb-4 border border-white/10">
                        <div className="grid gap-3">
                            {userEnvVars.map((v) => (
                                <div key={v.key} className="flex items-center gap-4 py-2 border-b border-white/5 last:border-0">
                                    <code className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-[13px] font-mono text-emerald-400 min-w-[180px]">
                                        {v.key}
                                    </code>
                                    <code className="text-[13px] font-mono text-white/80 flex-1">
                                        {v.value}
                                    </code>
                                    <span className="text-[12px] text-white/40">{v.desc}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    <button
                        onClick={handleCopy}
                        className={`btn-primary ${copied ? 'bg-emerald-500' : ''}`}
                    >
                        {copied ? (
                            <>
                                <Icons.CheckCircle className="w-4 h-4" />
                                已複製！
                            </>
                        ) : (
                            <>
                                <Icons.RefreshCw className="w-4 h-4" />
                                複製全部環境變數
                            </>
                        )}
                    </button>

                    <p className="text-[11px] text-white/30 mt-4">
                        * API credentials（EXCHANGE_API_KEY 等）會在 Node 啟動時自動從官網獲取，無需手動設定
                    </p>
                </div>

                {/* Step 4: Connect Node */}
                <div className="bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border border-emerald-500/20 rounded-2xl p-8 animate-fade-in" style={{ animationDelay: '0.7s' }}>
                    <h3 className="text-[14px] font-semibold text-white mb-4 flex items-center gap-2">
                        <span className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-[12px] font-bold">4</span>
                        <Icons.CheckCircle className="w-5 h-5 text-emerald-400" />
                        部署完成後：回填 Node URL
                    </h3>
                    <ol className="space-y-3 text-[13px] text-white/60 mb-6">
                        <li className="flex items-start gap-3">
                            <span className="w-5 h-5 rounded-full bg-white/10 text-white/50 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">1</span>
                            <span>在 Zeabur Dashboard 找到您部署的服務</span>
                        </li>
                        <li className="flex items-start gap-3">
                            <span className="w-5 h-5 rounded-full bg-white/10 text-white/50 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">2</span>
                            <span>點擊 <strong className="text-white">Networking</strong> → <strong className="text-white">Generate Domain</strong></span>
                        </li>
                        <li className="flex items-start gap-3">
                            <span className="w-5 h-5 rounded-full bg-white/10 text-white/50 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">3</span>
                            <span>複製生成的網址（如 <code className="text-white/80 bg-white/5 px-1.5 py-0.5 rounded text-[12px]">https://grid-node-xxx.zeabur.app</code>）</span>
                        </li>
                        <li className="flex items-start gap-3">
                            <span className="w-5 h-5 rounded-full bg-white/10 text-white/50 text-[11px] flex items-center justify-center flex-shrink-0 font-medium">4</span>
                            <span>回到官網 <strong className="text-white">設定頁面</strong>，貼上 Node URL 並儲存</span>
                        </li>
                    </ol>
                    <Link to="/settings" className="btn-success inline-flex">
                        前往設定頁面連接節點
                        <Icons.ArrowRight className="w-4 h-4" />
                    </Link>
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
