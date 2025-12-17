/**
 * 選幣系統頁面
 * 
 * 對應 GUI: CoinSelectionPage
 * 功能：掃描幣種、評分排名、加入交易
 */
import React, { useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle, Logo } from '../context/I18nContext';
import { coinApi, symbolsApi } from '../services/proxyApi';
import { Icons } from '../components/Icons';

export default function CoinSelection() {
    const { user, logout } = useAuth();
    const { t } = useI18n();

    const [rankings, setRankings] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [scanTime, setScanTime] = useState(null);
    const [selectedCoin, setSelectedCoin] = useState(null);
    const [topN, setTopN] = useState(20); // Top N filter

    const handleScan = useCallback(async (forceRefresh = false) => {
        setLoading(true);
        setError(null);
        try {
            const result = await coinApi.scan({ forceRefresh, limit: topN });
            setRankings(result.rankings || []);
            setScanTime(result.elapsed_seconds);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to scan');
        } finally {
            setLoading(false);
        }
    }, [topN]);

    const handleAddToSymbols = async (coin) => {
        try {
            await symbolsApi.add({
                symbol: coin.symbol.replace('/', '').split(':')[0],
                enabled: false,
                take_profit_spacing: 0.004,
                grid_spacing: 0.006,
                initial_quantity: 30,
                leverage: 20
            });
            alert(`Added ${coin.symbol} to symbols`);
        } catch (err) {
            alert(`Failed to add: ${err.response?.data?.detail || err.message}`);
        }
    };

    const getActionColor = (action) => {
        switch (action) {
            case 'HOLD': return 'text-emerald-400 bg-emerald-500/20';
            case 'WATCH': return 'text-amber-400 bg-amber-500/20';
            case 'AVOID': return 'text-red-400 bg-red-500/20';
            default: return 'text-white/50 bg-white/10';
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
                            <Link to="/coins" className="px-4 py-2 rounded-lg text-[13px] font-medium text-white bg-white/10">
                                選幣系統
                            </Link>
                            <Link to="/symbols" className="px-4 py-2 rounded-lg text-[13px] font-medium text-white/50 hover:text-white hover:bg-white/5 transition-colors">
                                交易對管理
                            </Link>
                            <Link to="/backtest" className="px-4 py-2 rounded-lg text-[13px] font-medium text-white/50 hover:text-white hover:bg-white/5 transition-colors">
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
                {/* Title & Controls */}
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
                    <div>
                        <h1 className="text-2xl font-bold text-white">選幣評分系統</h1>
                        <p className="text-white/50 text-sm mt-1">
                            掃描全部合約，找出最適合網格交易的幣種
                        </p>
                    </div>
                    <div className="flex gap-3 items-center">
                        {/* Top N Filter */}
                        <select
                            value={topN}
                            onChange={(e) => setTopN(parseInt(e.target.value))}
                            className="px-3 py-2.5 glass-card rounded-xl text-[13px] text-white bg-transparent border border-white/10 focus:border-white/30 outline-none"
                        >
                            <option value="10" className="bg-gray-900">Top 10</option>
                            <option value="20" className="bg-gray-900">Top 20</option>
                            <option value="30" className="bg-gray-900">Top 30</option>
                            <option value="50" className="bg-gray-900">Top 50</option>
                            <option value="100" className="bg-gray-900">全部</option>
                        </select>
                        <button
                            onClick={() => handleScan(false)}
                            disabled={loading}
                            className="px-5 py-2.5 bg-white text-black font-semibold rounded-xl text-[13px] disabled:opacity-50 flex items-center gap-2 hover:bg-white/90 transition-all"
                        >
                            {loading ? (
                                <Icons.RefreshCw className="w-4 h-4 animate-spin" />
                            ) : (
                                <Icons.Search className="w-4 h-4" />
                            )}
                            掃描全部
                        </button>
                        <button
                            onClick={() => handleScan(true)}
                            disabled={loading}
                            className="px-5 py-2.5 glass-card rounded-xl text-[13px] text-white flex items-center gap-2 hover:bg-white/10 transition-all"
                        >
                            <Icons.RefreshCw className="w-4 h-4" />
                            強制刷新
                        </button>
                    </div>
                </div>

                {/* Error */}
                {error && (
                    <div className="glass-card rounded-xl p-4 mb-6 border-red-500/30 bg-red-500/10">
                        <p className="text-red-400 text-sm">{error}</p>
                    </div>
                )}

                {/* Scan Time */}
                {scanTime && (
                    <div className="text-white/40 text-sm mb-4">
                        掃描完成，找到 {rankings.length} 個候選（{scanTime.toFixed(1)}s）
                    </div>
                )}

                {/* Rankings Table */}
                <div className="glass-card rounded-2xl overflow-hidden">
                    <table className="w-full">
                        <thead>
                            <tr className="border-b border-white/10">
                                <th className="text-left px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">排名</th>
                                <th className="text-left px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">幣種</th>
                                <th className="text-left px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">總分</th>
                                <th className="text-left px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">振幅</th>
                                <th className="text-left px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">趨勢</th>
                                <th className="text-left px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">價格</th>
                                <th className="text-left px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">建議</th>
                                <th className="text-right px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            {rankings.length === 0 ? (
                                <tr>
                                    <td colSpan={8} className="px-6 py-12 text-center text-white/40">
                                        {loading ? '掃描中...' : '點擊「掃描全部」開始評分'}
                                    </td>
                                </tr>
                            ) : (
                                rankings.map((coin, index) => (
                                    <tr
                                        key={coin.symbol}
                                        onClick={() => setSelectedCoin(coin)}
                                        className={`border-b border-white/5 hover:bg-white/5 cursor-pointer transition-colors ${selectedCoin?.symbol === coin.symbol ? 'bg-white/10' : ''
                                            }`}
                                    >
                                        <td className="px-6 py-4 text-white/60 font-mono">#{coin.rank}</td>
                                        <td className="px-6 py-4">
                                            <span className="text-white font-medium">{coin.symbol.split('/')[0]}</span>
                                            <span className="text-white/40 text-sm ml-1">/{coin.symbol.split('/')[1]?.split(':')[0]}</span>
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="flex items-center gap-2">
                                                <div className="w-16 h-2 bg-white/10 rounded-full overflow-hidden">
                                                    <div
                                                        className="h-full bg-emerald-500"
                                                        style={{ width: `${coin.total_score * 100}%` }}
                                                    />
                                                </div>
                                                <span className="text-white/60 text-sm">{(coin.total_score * 100).toFixed(0)}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-white/60">{(coin.amplitude * 100).toFixed(2)}%</td>
                                        <td className="px-6 py-4">
                                            <span className={coin.trend > 0 ? 'text-emerald-400' : coin.trend < 0 ? 'text-red-400' : 'text-white/40'}>
                                                {coin.trend > 0 ? '+' : ''}{(coin.trend * 100).toFixed(2)}%
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-white/60">${coin.price.toFixed(4)}</td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 rounded-lg text-xs font-medium ${getActionColor(coin.action)}`}>
                                                {coin.action}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleAddToSymbols(coin); }}
                                                className="px-3 py-1.5 text-xs bg-white/10 hover:bg-white/20 rounded-lg text-white transition-colors"
                                            >
                                                加入交易
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>

                {/* Selected Coin Detail */}
                {selectedCoin && (
                    <div className="glass-card rounded-2xl p-6 mt-6 animate-fade-in">
                        <h3 className="text-lg font-semibold text-white mb-4">
                            {selectedCoin.symbol.split('/')[0]} 詳細評分
                        </h3>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                            <div className="bg-white/5 rounded-xl p-4">
                                <p className="text-white/40 text-xs">網格適合度</p>
                                <p className="text-2xl font-bold text-white mt-1">
                                    {(selectedCoin.grid_suitability * 100).toFixed(0)}%
                                </p>
                            </div>
                            <div className="bg-white/5 rounded-xl p-4">
                                <p className="text-white/40 text-xs">24H 成交量</p>
                                <p className="text-2xl font-bold text-white mt-1">
                                    ${(selectedCoin.volume_24h / 1000000).toFixed(1)}M
                                </p>
                            </div>
                            <div className="bg-white/5 rounded-xl p-4">
                                <p className="text-white/40 text-xs">平均振幅</p>
                                <p className="text-2xl font-bold text-white mt-1">
                                    {(selectedCoin.amplitude * 100).toFixed(2)}%
                                </p>
                            </div>
                            <div className="bg-white/5 rounded-xl p-4">
                                <p className="text-white/40 text-xs">趨勢強度</p>
                                <p className={`text-2xl font-bold mt-1 ${Math.abs(selectedCoin.trend) < 0.02 ? 'text-emerald-400' : 'text-amber-400'
                                    }`}>
                                    {Math.abs(selectedCoin.trend * 100).toFixed(2)}%
                                </p>
                            </div>
                        </div>
                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => handleAddToSymbols(selectedCoin)}
                                className="px-5 py-2.5 bg-white text-black font-semibold rounded-xl text-[13px] flex items-center gap-2"
                            >
                                <Icons.Plus className="w-4 h-4" />
                                加入交易對
                            </button>
                            <Link
                                to={`/backtest?symbol=${selectedCoin.symbol.split('/')[0]}`}
                                className="px-5 py-2.5 glass-card rounded-xl text-[13px] text-white flex items-center gap-2 hover:bg-white/10"
                            >
                                <Icons.Play className="w-4 h-4" />
                                開始回測
                            </Link>
                        </div>
                    </div>
                )}
            </main>
        </div>
    );
}
