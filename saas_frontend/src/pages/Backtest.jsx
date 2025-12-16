/**
 * 回測頁面
 * 
 * 對應 GUI: BacktestPage
 * 功能：執行回測、參數優化
 */
import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle, Logo } from '../context/I18nContext';
import { backtestApi } from '../services/proxyApi';
import { Icons } from '../components/Icons';

export default function Backtest() {
    const { user } = useAuth();
    const { t } = useI18n();
    const [searchParams] = useSearchParams();

    const [params, setParams] = useState({
        symbol: searchParams.get('symbol') || 'XRPUSDC',
        days: 30,
        take_profit_spacing: 0.004,
        grid_spacing: 0.006,
        initial_quantity: 30,
        leverage: 20,
        initial_capital: 1000
    });

    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [optimizing, setOptimizing] = useState(false);
    const [error, setError] = useState(null);

    const handleRunBacktest = async () => {
        setLoading(true);
        setError(null);
        setResult(null);
        try {
            const res = await backtestApi.run(params);
            setResult(res);
        } catch (err) {
            setError(err.response?.data?.detail || 'Backtest failed');
        } finally {
            setLoading(false);
        }
    };

    const handleOptimize = async () => {
        setOptimizing(true);
        setError(null);
        try {
            const res = await backtestApi.optimize({
                symbol: params.symbol,
                days: params.days,
                initial_capital: params.initial_capital,
                tp_min: 0.002,
                tp_max: 0.008,
                tp_step: 0.001,
                gs_min: 0.003,
                gs_max: 0.01,
                gs_step: 0.001
            });
            // 使用優化結果更新參數
            setParams({
                ...params,
                take_profit_spacing: res.best_tp,
                grid_spacing: res.best_gs
            });
            alert(`優化完成！最佳 TP: ${(res.best_tp * 100).toFixed(2)}%, GS: ${(res.best_gs * 100).toFixed(2)}%`);
        } catch (err) {
            setError(err.response?.data?.detail || 'Optimization failed');
        } finally {
            setOptimizing(false);
        }
    };

    return (
        <div className="min-h-screen bg-bg-primary bg-gradient-radial bg-grid-pattern">
            {/* Header */}
            <header className="sticky top-0 z-50 bg-bg-primary/80 backdrop-blur-xl border-b border-white/5">
                <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Logo size="md" showText={false} />
                        <nav className="hidden md:flex items-center gap-1 ml-4">
                            <Link to="/dashboard" className="px-4 py-2 rounded-lg text-[13px] font-medium text-white/50 hover:text-white hover:bg-white/5 transition-colors">
                                {t.nav.dashboard}
                            </Link>
                            <Link to="/coins" className="px-4 py-2 rounded-lg text-[13px] font-medium text-white/50 hover:text-white hover:bg-white/5 transition-colors">
                                選幣系統
                            </Link>
                            <Link to="/symbols" className="px-4 py-2 rounded-lg text-[13px] font-medium text-white/50 hover:text-white hover:bg-white/5 transition-colors">
                                交易對管理
                            </Link>
                            <Link to="/backtest" className="px-4 py-2 rounded-lg text-[13px] font-medium text-white bg-white/10">
                                回測
                            </Link>
                        </nav>
                    </div>
                    <div className="flex items-center gap-4">
                        <LanguageToggle />
                        <span className="text-[13px] text-white/40">{user?.email}</span>
                    </div>
                </div>
            </header>

            <main className="max-w-7xl mx-auto px-6 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* Parameters Panel */}
                    <div className="lg:col-span-1">
                        <div className="glass-card rounded-2xl p-6">
                            <h2 className="text-lg font-semibold text-white mb-4">回測參數</h2>

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm text-white/60 mb-1">交易對</label>
                                    <input
                                        type="text"
                                        value={params.symbol}
                                        onChange={(e) => setParams({ ...params, symbol: e.target.value.toUpperCase() })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm text-white/60 mb-1">回測天數</label>
                                    <input
                                        type="number"
                                        value={params.days}
                                        onChange={(e) => setParams({ ...params, days: parseInt(e.target.value) })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                    />
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm text-white/60 mb-1">止盈 (%)</label>
                                        <input
                                            type="number"
                                            step="0.1"
                                            value={params.take_profit_spacing * 100}
                                            onChange={(e) => setParams({ ...params, take_profit_spacing: parseFloat(e.target.value) / 100 })}
                                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm text-white/60 mb-1">網格 (%)</label>
                                        <input
                                            type="number"
                                            step="0.1"
                                            value={params.grid_spacing * 100}
                                            onChange={(e) => setParams({ ...params, grid_spacing: parseFloat(e.target.value) / 100 })}
                                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                        />
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-4">
                                    <div>
                                        <label className="block text-sm text-white/60 mb-1">數量</label>
                                        <input
                                            type="number"
                                            value={params.initial_quantity}
                                            onChange={(e) => setParams({ ...params, initial_quantity: parseInt(e.target.value) })}
                                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-sm text-white/60 mb-1">槓桿</label>
                                        <input
                                            type="number"
                                            value={params.leverage}
                                            onChange={(e) => setParams({ ...params, leverage: parseInt(e.target.value) })}
                                            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                        />
                                    </div>
                                </div>

                                <div>
                                    <label className="block text-sm text-white/60 mb-1">初始資金</label>
                                    <input
                                        type="number"
                                        value={params.initial_capital}
                                        onChange={(e) => setParams({ ...params, initial_capital: parseFloat(e.target.value) })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                    />
                                </div>
                            </div>

                            <div className="flex flex-col gap-3 mt-6">
                                <button
                                    onClick={handleRunBacktest}
                                    disabled={loading}
                                    className="w-full px-4 py-3 bg-white text-black font-semibold rounded-xl disabled:opacity-50 flex items-center justify-center gap-2"
                                >
                                    {loading ? (
                                        <>
                                            <Icons.RefreshCw className="w-4 h-4 animate-spin" />
                                            回測中...
                                        </>
                                    ) : (
                                        <>
                                            <Icons.Play className="w-4 h-4" />
                                            開始回測
                                        </>
                                    )}
                                </button>
                                <button
                                    onClick={handleOptimize}
                                    disabled={optimizing}
                                    className="w-full px-4 py-3 glass-card rounded-xl text-white disabled:opacity-50 flex items-center justify-center gap-2 hover:bg-white/10"
                                >
                                    {optimizing ? (
                                        <>
                                            <Icons.RefreshCw className="w-4 h-4 animate-spin" />
                                            優化中...
                                        </>
                                    ) : (
                                        <>
                                            <Icons.Zap className="w-4 h-4" />
                                            參數優化
                                        </>
                                    )}
                                </button>
                            </div>
                        </div>
                    </div>

                    {/* Results Panel */}
                    <div className="lg:col-span-2">
                        {error && (
                            <div className="glass-card rounded-xl p-4 mb-6 border-red-500/30 bg-red-500/10">
                                <p className="text-red-400 text-sm">{error}</p>
                            </div>
                        )}

                        {result ? (
                            <div className="space-y-6">
                                {/* Stats Cards */}
                                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                                    <div className="glass-card rounded-xl p-4">
                                        <p className="text-white/40 text-xs">總盈虧</p>
                                        <p className={`text-2xl font-bold mt-1 ${result.total_pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                            ${result.total_pnl.toFixed(2)}
                                        </p>
                                    </div>
                                    <div className="glass-card rounded-xl p-4">
                                        <p className="text-white/40 text-xs">ROI</p>
                                        <p className={`text-2xl font-bold mt-1 ${result.roi_percent >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                                            {result.roi_percent.toFixed(2)}%
                                        </p>
                                    </div>
                                    <div className="glass-card rounded-xl p-4">
                                        <p className="text-white/40 text-xs">總交易次數</p>
                                        <p className="text-2xl font-bold text-white mt-1">{result.total_trades}</p>
                                    </div>
                                    <div className="glass-card rounded-xl p-4">
                                        <p className="text-white/40 text-xs">勝率</p>
                                        <p className="text-2xl font-bold text-white mt-1">{(result.win_rate * 100).toFixed(1)}%</p>
                                    </div>
                                </div>

                                {/* Detailed Stats */}
                                <div className="glass-card rounded-2xl p-6">
                                    <h3 className="text-lg font-semibold text-white mb-4">詳細數據</h3>
                                    <div className="grid grid-cols-2 gap-6">
                                        <div>
                                            <p className="text-white/40 text-sm">最大回撤</p>
                                            <p className="text-xl font-semibold text-red-400">{(result.max_drawdown * 100).toFixed(2)}%</p>
                                        </div>
                                        <div>
                                            <p className="text-white/40 text-sm">夏普比率</p>
                                            <p className="text-xl font-semibold text-white">{result.sharpe_ratio.toFixed(2)}</p>
                                        </div>
                                        <div>
                                            <p className="text-white/40 text-sm">最終資金</p>
                                            <p className="text-xl font-semibold text-white">${result.final_capital.toFixed(2)}</p>
                                        </div>
                                        <div>
                                            <p className="text-white/40 text-sm">回測天數</p>
                                            <p className="text-xl font-semibold text-white">{result.period_days} 天</p>
                                        </div>
                                    </div>
                                    <p className="text-white/40 text-xs mt-4">{result.message}</p>
                                </div>
                            </div>
                        ) : (
                            <div className="glass-card rounded-2xl p-12 flex flex-col items-center justify-center text-center">
                                <Icons.TrendingUp className="w-16 h-16 text-white/20 mb-4" />
                                <h3 className="text-lg font-semibold text-white mb-2">開始回測</h3>
                                <p className="text-white/50 text-sm max-w-sm">
                                    設定回測參數並點擊「開始回測」，查看策略在歷史數據上的表現
                                </p>
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    );
}
