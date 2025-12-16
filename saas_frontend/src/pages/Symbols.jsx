/**
 * 交易對管理頁面
 * 
 * 對應 GUI: SymbolsPage
 * 功能：管理交易對、設定參數
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle, Logo } from '../context/I18nContext';
import { symbolsApi } from '../services/proxyApi';
import { Icons } from '../components/Icons';

export default function Symbols() {
    const { user } = useAuth();
    const { t } = useI18n();

    const [symbols, setSymbols] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [editingSymbol, setEditingSymbol] = useState(null);
    const [showAddModal, setShowAddModal] = useState(false);

    // 新增交易對表單
    const [newSymbol, setNewSymbol] = useState({
        symbol: '',
        take_profit_spacing: 0.004,
        grid_spacing: 0.006,
        initial_quantity: 30,
        leverage: 20,
        enabled: false
    });

    const loadSymbols = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const result = await symbolsApi.list();
            setSymbols(result.symbols || []);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to load symbols');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadSymbols();
    }, [loadSymbols]);

    const handleToggle = async (symbol) => {
        try {
            await symbolsApi.toggle(symbol);
            loadSymbols();
        } catch (err) {
            alert(`Failed to toggle: ${err.response?.data?.detail || err.message}`);
        }
    };

    const handleDelete = async (symbol) => {
        if (!window.confirm(`確定要刪除 ${symbol}？`)) return;
        try {
            await symbolsApi.delete(symbol);
            loadSymbols();
        } catch (err) {
            alert(`Failed to delete: ${err.response?.data?.detail || err.message}`);
        }
    };

    const handleAdd = async () => {
        try {
            await symbolsApi.add(newSymbol);
            setShowAddModal(false);
            setNewSymbol({
                symbol: '',
                take_profit_spacing: 0.004,
                grid_spacing: 0.006,
                initial_quantity: 30,
                leverage: 20,
                enabled: false
            });
            loadSymbols();
        } catch (err) {
            alert(`Failed to add: ${err.response?.data?.detail || err.message}`);
        }
    };

    const handleUpdate = async () => {
        if (!editingSymbol) return;
        try {
            await symbolsApi.update(editingSymbol.symbol, editingSymbol);
            setEditingSymbol(null);
            loadSymbols();
        } catch (err) {
            alert(`Failed to update: ${err.response?.data?.detail || err.message}`);
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
                            <Link to="/symbols" className="px-4 py-2 rounded-lg text-[13px] font-medium text-white bg-white/10">
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
                        <h1 className="text-2xl font-bold text-white">交易對管理</h1>
                        <p className="text-white/50 text-sm mt-1">
                            管理網格交易的幣種和參數
                        </p>
                    </div>
                    <div className="flex gap-3">
                        <button
                            onClick={() => setShowAddModal(true)}
                            className="px-5 py-2.5 bg-white text-black font-semibold rounded-xl text-[13px] flex items-center gap-2 hover:bg-white/90 transition-all"
                        >
                            <Icons.Plus className="w-4 h-4" />
                            新增交易對
                        </button>
                        <button
                            onClick={loadSymbols}
                            disabled={loading}
                            className="px-4 py-2.5 glass-card rounded-xl text-white/60 text-[13px] hover:text-white transition-colors"
                        >
                            <Icons.RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                        </button>
                    </div>
                </div>

                {/* Error */}
                {error && (
                    <div className="glass-card rounded-xl p-4 mb-6 border-red-500/30 bg-red-500/10">
                        <p className="text-red-400 text-sm">{error}</p>
                    </div>
                )}

                {/* Symbols Table */}
                <div className="glass-card rounded-2xl overflow-hidden">
                    <table className="w-full">
                        <thead>
                            <tr className="border-b border-white/10">
                                <th className="text-left px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">交易對</th>
                                <th className="text-left px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">止盈 (TP)</th>
                                <th className="text-left px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">網格 (GS)</th>
                                <th className="text-left px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">數量</th>
                                <th className="text-left px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">槓桿</th>
                                <th className="text-left px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">狀態</th>
                                <th className="text-right px-6 py-4 text-[11px] font-semibold text-white/40 uppercase">操作</th>
                            </tr>
                        </thead>
                        <tbody>
                            {symbols.length === 0 ? (
                                <tr>
                                    <td colSpan={7} className="px-6 py-12 text-center text-white/40">
                                        {loading ? '載入中...' : '尚無交易對，點擊「新增交易對」開始'}
                                    </td>
                                </tr>
                            ) : (
                                symbols.map((sym) => (
                                    <tr key={sym.symbol} className="border-b border-white/5 hover:bg-white/5 transition-colors">
                                        <td className="px-6 py-4">
                                            <span className="text-white font-medium">{sym.symbol}</span>
                                            <span className="text-white/40 text-xs ml-2">{sym.ccxt_symbol}</span>
                                        </td>
                                        <td className="px-6 py-4 text-white/60">{(sym.take_profit_spacing * 100).toFixed(2)}%</td>
                                        <td className="px-6 py-4 text-white/60">{(sym.grid_spacing * 100).toFixed(2)}%</td>
                                        <td className="px-6 py-4 text-white/60">{sym.initial_quantity}</td>
                                        <td className="px-6 py-4 text-white/60">{sym.leverage}x</td>
                                        <td className="px-6 py-4">
                                            <button
                                                onClick={() => handleToggle(sym.symbol)}
                                                className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors ${sym.enabled
                                                        ? 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
                                                        : 'bg-white/10 text-white/40 hover:bg-white/20'
                                                    }`}
                                            >
                                                {sym.enabled ? '啟用中' : '已停用'}
                                            </button>
                                        </td>
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex gap-2 justify-end">
                                                <button
                                                    onClick={() => setEditingSymbol(sym)}
                                                    className="p-2 text-white/40 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                                                >
                                                    <Icons.Edit className="w-4 h-4" />
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(sym.symbol)}
                                                    className="p-2 text-white/40 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                                                >
                                                    <Icons.Trash className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </main>

            {/* Add Modal */}
            {showAddModal && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="glass-card rounded-2xl p-6 w-full max-w-md animate-fade-in">
                        <h3 className="text-lg font-semibold text-white mb-4">新增交易對</h3>
                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm text-white/60 mb-1">交易對符號</label>
                                <input
                                    type="text"
                                    value={newSymbol.symbol}
                                    onChange={(e) => setNewSymbol({ ...newSymbol, symbol: e.target.value.toUpperCase() })}
                                    placeholder="例如: XRPUSDC"
                                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-white/30 focus:border-white/30 outline-none"
                                />
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-white/60 mb-1">止盈間距 (%)</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        value={newSymbol.take_profit_spacing * 100}
                                        onChange={(e) => setNewSymbol({ ...newSymbol, take_profit_spacing: parseFloat(e.target.value) / 100 })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-white/60 mb-1">網格間距 (%)</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        value={newSymbol.grid_spacing * 100}
                                        onChange={(e) => setNewSymbol({ ...newSymbol, grid_spacing: parseFloat(e.target.value) / 100 })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-white/60 mb-1">初始數量</label>
                                    <input
                                        type="number"
                                        value={newSymbol.initial_quantity}
                                        onChange={(e) => setNewSymbol({ ...newSymbol, initial_quantity: parseInt(e.target.value) })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-white/60 mb-1">槓桿倍數</label>
                                    <input
                                        type="number"
                                        value={newSymbol.leverage}
                                        onChange={(e) => setNewSymbol({ ...newSymbol, leverage: parseInt(e.target.value) })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                    />
                                </div>
                            </div>
                        </div>
                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => setShowAddModal(false)}
                                className="flex-1 px-4 py-3 glass-card rounded-xl text-white/60 hover:text-white transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleAdd}
                                className="flex-1 px-4 py-3 bg-white text-black font-semibold rounded-xl hover:bg-white/90 transition-all"
                            >
                                新增
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Edit Modal */}
            {editingSymbol && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50">
                    <div className="glass-card rounded-2xl p-6 w-full max-w-md animate-fade-in">
                        <h3 className="text-lg font-semibold text-white mb-4">編輯 {editingSymbol.symbol}</h3>
                        <div className="space-y-4">
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-white/60 mb-1">止盈間距 (%)</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        value={editingSymbol.take_profit_spacing * 100}
                                        onChange={(e) => setEditingSymbol({ ...editingSymbol, take_profit_spacing: parseFloat(e.target.value) / 100 })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-white/60 mb-1">網格間距 (%)</label>
                                    <input
                                        type="number"
                                        step="0.1"
                                        value={editingSymbol.grid_spacing * 100}
                                        onChange={(e) => setEditingSymbol({ ...editingSymbol, grid_spacing: parseFloat(e.target.value) / 100 })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                    />
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm text-white/60 mb-1">初始數量</label>
                                    <input
                                        type="number"
                                        value={editingSymbol.initial_quantity}
                                        onChange={(e) => setEditingSymbol({ ...editingSymbol, initial_quantity: parseInt(e.target.value) })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm text-white/60 mb-1">槓桿倍數</label>
                                    <input
                                        type="number"
                                        value={editingSymbol.leverage}
                                        onChange={(e) => setEditingSymbol({ ...editingSymbol, leverage: parseInt(e.target.value) })}
                                        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:border-white/30 outline-none"
                                    />
                                </div>
                            </div>
                        </div>
                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => setEditingSymbol(null)}
                                className="flex-1 px-4 py-3 glass-card rounded-xl text-white/60 hover:text-white transition-colors"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleUpdate}
                                className="flex-1 px-4 py-3 bg-white text-black font-semibold rounded-xl hover:bg-white/90 transition-all"
                            >
                                儲存
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
