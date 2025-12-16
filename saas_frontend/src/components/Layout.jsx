import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const location = useLocation();

  const NavItem = ({ to, label, icon }) => {
    const isActive = location.pathname === to;
    return (
      <Link 
        to={to} 
        className={`flex items-center px-4 py-3 text-sm tracking-wide transition-colors ${
          isActive 
            ? 'bg-bg-elevated text-text-primary border-l-2 border-accent' 
            : 'text-text-muted hover:text-text-secondary hover:bg-bg-secondary'
        }`}
      >
        <span className="mr-3 text-xs">{icon}</span>
        {label}
      </Link>
    );
  };

  return (
    <div className="flex min-h-screen bg-bg-primary font-sans text-text-primary">
      {/* Sidebar */}
      <aside className="w-64 bg-bg-secondary border-r border-border flex flex-col">
        <div className="p-6 border-b border-border">
          <h1 className="text-xl font-bold tracking-widest text-text-primary">AS GRID</h1>
          <div className="mt-2 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-status-on animate-pulse"></div>
            <span className="text-[10px] font-mono text-text-muted uppercase">System Active</span>
          </div>
        </div>

        <nav className="flex-1 py-6 space-y-1">
          <NavItem to="/dashboard" label="DASHBOARD" icon="◉" />
          <NavItem to="/settings" label="SETTINGS" icon="⚙" />
        </nav>

        <div className="p-6 border-t border-border">
          <div className="text-xs text-text-muted mb-4 font-mono">
            LOGGED IN AS<br/>
            <span className="text-text-secondary">{user?.username}</span>
          </div>
          <button 
            onClick={logout} 
            className="w-full py-2 text-xs border border-border rounded text-text-muted hover:text-text-primary hover:border-text-primary transition-colors"
          >
            LOGOUT
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 p-8 overflow-auto">
        {children}
      </main>
    </div>
  );
}
