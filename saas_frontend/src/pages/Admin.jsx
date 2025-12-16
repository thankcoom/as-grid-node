import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useI18n, LanguageToggle, Logo } from '../context/I18nContext';
import { Icons } from '../components/Icons';

export default function Admin() {
    const { user, logout } = useAuth();
    const { t } = useI18n();
    const navigate = useNavigate();
    const [stats, setStats] = useState({ total_users: 0, active_users: 0, pending_users: 0, groups_count: 0 });
    const [pendingUsers, setPendingUsers] = useState([]);
    const [groups, setGroups] = useState([]);
    const [whitelist, setWhitelist] = useState([]);
    const [refresh, setRefresh] = useState(false);

    // Modal states
    const [showAddUid, setShowAddUid] = useState(false);
    const [showAddGroup, setShowAddGroup] = useState(false);
    const [newUid, setNewUid] = useState('');
    const [newUidEmail, setNewUidEmail] = useState('');
    const [newGroupName, setNewGroupName] = useState('');
    const [newGroupDesc, setNewGroupDesc] = useState('');
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        fetchData();
    }, [refresh]);

    const fetchData = async () => {
        try {
            const [statsRes, usersRes, groupsRes, whitelistRes] = await Promise.all([
                api.get('/admin/stats'),
                api.get('/admin/users?status=pending_approval'),
                api.get('/admin/groups'),
                api.get('/admin/whitelist')
            ]);
            setStats(statsRes.data);
            setPendingUsers(usersRes.data);
            setGroups(groupsRes.data);
            setWhitelist(whitelistRes.data);
        } catch (err) {
            console.error(err);
            if (err.response?.status === 401) navigate('/login');
        }
    };

    const handleApprove = async (userId) => {
        try {
            await api.put(`/admin/users/${userId}/approve`);
            setRefresh(!refresh);
        } catch (err) {
            console.error(err);
        }
    };

    const handleReject = async (userId) => {
        if (!window.confirm(t.common.confirm + ' ' + t.common.delete + '?')) return;
        try {
            await api.delete(`/admin/users/${userId}/reject`);
            setRefresh(!refresh);
        } catch (err) {
            console.error(err);
        }
    };

    const handleAddUid = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await api.post('/admin/whitelist', { uid: newUid, email: newUidEmail || null });
            setShowAddUid(false);
            setNewUid('');
            setNewUidEmail('');
            setRefresh(!refresh);
        } catch (err) {
            alert(t.common.error + ': ' + (err.response?.data?.detail || err.message));
        } finally {
            setLoading(false);
        }
    };

    const handleCreateGroup = async (e) => {
        e.preventDefault();
        setLoading(true);
        try {
            await api.post('/admin/groups', { name: newGroupName, description: newGroupDesc });
            setShowAddGroup(false);
            setNewGroupName('');
            setNewGroupDesc('');
            setRefresh(!refresh);
        } catch (err) {
            alert(t.common.error + ': ' + (err.response?.data?.detail || err.message));
        } finally {
            setLoading(false);
        }
    };

    const navItems = [
        { id: 'overview', label: t.admin.overview, icon: Icons.BarChart2 },
        { id: 'pending', label: t.admin.pending, icon: Icons.Clock, badge: pendingUsers.length },
        { id: 'users', label: t.admin.users, icon: Icons.Users },
        { id: 'whitelist', label: t.admin.whitelist, icon: Icons.List },
        { id: 'groups', label: t.admin.groups, icon: Icons.Tag },
    ];

    const [activeTab, setActiveTab] = useState('overview');

    return (
        <div className="min-h-screen bg-bg-primary bg-gradient-radial bg-grid-pattern flex">
            {/* Sidebar */}
            <aside className="w-64 border-r border-white/5 bg-bg-primary/50 backdrop-blur-xl fixed h-full z-20">
                <div className="p-6 border-b border-white/5">
                    <Logo size="sm" />
                </div>

                <nav className="p-4 space-y-1">
                    {navItems.map(item => (
                        <button
                            key={item.id}
                            onClick={() => setActiveTab(item.id)}
                            className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-[13px] font-medium transition-all ${activeTab === item.id
                                ? 'bg-white text-black shadow-lg shadow-white/10 connection'
                                : 'text-white/50 hover:text-white hover:bg-white/5'
                                }`}
                        >
                            <div className="flex items-center gap-3">
                                <item.icon className="w-4 h-4" />
                                <span>{item.label}</span>
                            </div>
                            {item.badge > 0 && (
                                <span className="px-2 py-0.5 rounded-full bg-amber-500 text-black text-[10px] font-bold">
                                    {item.badge}
                                </span>
                            )}
                        </button>
                    ))}
                </nav>

                <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-white/5">
                    <div className="flex items-center gap-3 px-4 py-3 mb-2">
                        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 flex items-center justify-center text-xs font-bold text-white">
                            A
                        </div>
                        <div className="overflow-hidden">
                            <p className="text-[12px] font-medium text-white truncate">Admin</p>
                            <p className="text-[10px] text-white/40 truncate">{t.admin.sysAdmin}</p>
                        </div>
                    </div>

                    <div className="flex items-center justify-between px-2">
                        <LanguageToggle className="scale-90 origin-left" />
                        <button onClick={logout} className="text-[11px] text-white/40 hover:text-white transition-colors flex items-center gap-1">
                            <Icons.LogOut className="w-3 h-3" />
                            {t.nav.logout}
                        </button>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="flex-1 ml-64 p-8">
                <header className="flex items-center justify-between mb-8 animate-fade-in">
                    <div>
                        <h1 className="text-2xl font-bold text-white mb-1">{t.admin.title}</h1>
                        <p className="text-sm text-white/40">{t.admin.subtitle}</p>
                    </div>
                    <Link to="/dashboard" className="px-4 py-2 glass-card rounded-lg text-[13px] text-white hover:bg-white/10 transition-colors flex items-center gap-2">
                        <Icons.ArrowLeft className="w-3 h-3" /> {t.admin.backToDashboard}
                    </Link>
                </header>

                {/* Content based on active tab */}
                <div className="animate-fade-in">
                    {activeTab === 'overview' && (
                        <div className="space-y-6">
                            {/* Stats Cards */}
                            <div className="grid grid-cols-4 gap-4">
                                {[
                                    { label: t.admin.totalUsers, value: stats.total_users, sub: t.admin.cumulative, icon: Icons.Users },
                                    { label: t.admin.pendingUsers, value: stats.pending_users, sub: t.admin.needsAction, icon: Icons.Clock, highlight: stats.pending_users > 0 },
                                    { label: t.admin.activeUsers, value: stats.active_users, sub: t.admin.running, icon: Icons.CheckCircle },
                                    { label: t.admin.totalGroups, value: stats.groups_count, sub: t.admin.total, icon: Icons.Tag }
                                ].map((stat, i) => (
                                    <div key={i} className={`glass-card rounded-2xl p-6 ${stat.highlight ? 'border-amber-500/30 bg-amber-500/5' : ''}`}>
                                        <div className="flex justify-between items-start mb-4">
                                            <div className={`p-2 rounded-lg ${stat.highlight ? 'bg-amber-500/20 text-amber-500' : 'bg-white/5 text-white/60'}`}>
                                                <stat.icon className="w-5 h-5" />
                                            </div>
                                            {stat.highlight && <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />}
                                        </div>
                                        <div className="text-3xl font-bold text-white mb-1">{stat.value}</div>
                                        <div className="flex justify-between items-end">
                                            <p className="text-[11px] font-medium text-white/40 uppercase tracking-wider">{stat.label}</p>
                                            <p className="text-[10px] text-white/30">{stat.sub}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>

                            {/* Recent Pending Users */}
                            <div className="glass-card rounded-2xl p-6">
                                <div className="flex items-center justify-between mb-6">
                                    <h3 className="text-lg font-semibold text-white">{t.admin.pendingApproval}</h3>
                                    <button onClick={() => setActiveTab('pending')} className="text-xs text-white/40 hover:text-white transition-colors flex items-center gap-1">
                                        {t.admin.viewAll} <Icons.ArrowRight className="w-3 h-3" />
                                    </button>
                                </div>

                                {pendingUsers.length === 0 ? (
                                    <div className="text-center py-12 text-white/20">
                                        <p>{t.admin.noPending}</p>
                                    </div>
                                ) : (
                                    <div className="space-y-3">
                                        {pendingUsers.slice(0, 5).map(user => (
                                            <div key={user.id} className="flex items-center justify-between p-4 bg-white/5 rounded-xl border border-white/5">
                                                <div className="flex items-center gap-4">
                                                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-gray-700 to-gray-800 flex items-center justify-center text-white/60 font-mono text-xs">
                                                        {user.email.substring(0, 2).toUpperCase()}
                                                    </div>
                                                    <div>
                                                        <p className="text-sm font-medium text-white">{user.email}</p>
                                                        <p className="text-xs text-white/40">UID: {user.exchange_uid || '-'}</p>
                                                    </div>
                                                </div>
                                                <div className="flex gap-2">
                                                    <button
                                                        onClick={() => handleApprove(user.id)}
                                                        className="px-3 py-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-lg text-xs font-medium hover:bg-emerald-500/20 transition-colors"
                                                    >
                                                        {t.admin.approve}
                                                    </button>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    )}

                    {activeTab === 'whitelist' && (
                        <div className="space-y-6">
                            <div className="flex justify-between items-center">
                                <div>
                                    <h2 className="text-xl font-bold text-white mb-2">{t.admin.uidWhitelist}</h2>
                                    <p className="text-sm text-white/40">{t.admin.uidWhitelistDesc}</p>
                                </div>
                                <button
                                    onClick={() => setShowAddUid(true)}
                                    className="px-4 py-2 bg-white text-black rounded-xl text-sm font-bold hover:bg-white/90 transition-all flex items-center gap-2"
                                >
                                    <span>+</span> {t.admin.addUid}
                                </button>
                            </div>

                            <div className="glass-card rounded-2xl overflow-hidden">
                                <table className="w-full text-left">
                                    <thead className="bg-white/5 text-white/40 text-xs uppercase">
                                        <tr>
                                            <th className="px-6 py-4 font-medium">UID</th>
                                            <th className="px-6 py-4 font-medium">{t.auth.email}</th>
                                            <th className="px-6 py-4 font-medium">{t.common.create}</th>
                                            <th className="px-6 py-4 font-medium">{t.admin.statusLabel}</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-white/5">
                                        {whitelist.length === 0 ? (
                                            <tr>
                                                <td colSpan="4" className="px-6 py-12 text-center text-white/20">
                                                    {t.admin.noPreApproved}
                                                </td>
                                            </tr>
                                        ) : (
                                            whitelist.map((item) => (
                                                <tr key={item.id} className="text-sm text-white hover:bg-white/5 transition-colors">
                                                    <td className="px-6 py-4 font-mono">{item.uid}</td>
                                                    <td className="px-6 py-4 text-white/60">{item.email || '-'}</td>
                                                    <td className="px-6 py-4 text-white/40">{new Date(item.created_at).toLocaleDateString()}</td>
                                                    <td className="px-6 py-4">
                                                        <span className="px-2 py-1 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                                                            {t.admin.enabled}
                                                        </span>
                                                    </td>
                                                </tr>
                                            ))
                                        )}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}

                    {/* Add other tabs implementation here if needed, keeping them simplified for this update */}
                    {(activeTab === 'pending' || activeTab === 'users' || activeTab === 'groups') && (
                        <div className="flex items-center justify-center py-20 text-white/20">
                            Tab content placeholder for {activeTab}
                        </div>
                    )}
                </div>
            </main>

            {/* Modals */}
            {showAddUid && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in">
                    <div className="bg-[#111] border border-white/10 rounded-2xl p-6 w-full max-w-sm shadow-2xl">
                        <h3 className="text-lg font-bold text-white mb-4">{t.admin.addUidTitle}</h3>
                        <form onSubmit={handleAddUid} className="space-y-4">
                            <div>
                                <label className="block text-xs font-medium text-white/40 mb-2 uppercase">{t.admin.bitgetUid}</label>
                                <input
                                    type="text"
                                    required
                                    value={newUid}
                                    onChange={e => setNewUid(e.target.value)}
                                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:border-white/20"
                                    placeholder="e.g. 12345678"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium text-white/40 mb-2 uppercase">{t.admin.emailOptional}</label>
                                <input
                                    type="email"
                                    value={newUidEmail}
                                    onChange={e => setNewUidEmail(e.target.value)}
                                    className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white focus:outline-none focus:border-white/20"
                                    placeholder="user@example.com"
                                />
                            </div>
                            <div className="flex gap-3 pt-2">
                                <button
                                    type="button"
                                    onClick={() => setShowAddUid(false)}
                                    className="flex-1 py-3 bg-white/5 text-white rounded-xl text-xs font-bold hover:bg-white/10"
                                >
                                    {t.common.cancel}
                                </button>
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="flex-1 py-3 bg-white text-black rounded-xl text-xs font-bold hover:bg-white/90"
                                >
                                    {loading ? t.admin.adding : t.admin.addUid}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}
