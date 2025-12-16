import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { I18nProvider } from './context/I18nContext';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import SetupAPI from './pages/SetupAPI';
import PendingApproval from './pages/PendingApproval';
import Rejected from './pages/Rejected';
import Dashboard from './pages/Dashboard';
import Settings from './pages/Settings';
import Admin from './pages/Admin';
import Deploy from './pages/Deploy';

// Protected Route - requires login and active status
const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary bg-gradient-radial bg-grid-pattern">
        <div className="text-text-muted">Loading...</div>
      </div>
    );
  }

  if (!user) return <Navigate to="/login" />;

  // Redirect based on status
  if (user.status === 'pending_api') return <Navigate to="/setup-api" />;
  if (user.status === 'pending_approval') return <Navigate to="/pending" />;
  if (user.status === 'rejected') return <Navigate to="/rejected" />;

  return children;
};

// Admin Route - requires is_admin
const AdminRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary bg-gradient-radial bg-grid-pattern">
        <div className="text-text-muted">Loading...</div>
      </div>
    );
  }

  if (!user) return <Navigate to="/login" />;
  if (!user.is_admin) return <Navigate to="/dashboard" />;

  return children;
};

// Auth Route - requires login but allows any status
const AuthRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary bg-gradient-radial bg-grid-pattern">
        <div className="text-text-muted">Loading...</div>
      </div>
    );
  }

  if (!user) return <Navigate to="/login" />;

  return children;
};

function App() {
  return (
    <I18nProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            {/* Auth Required Routes (any status) */}
            <Route path="/setup-api" element={
              <AuthRoute>
                <SetupAPI />
              </AuthRoute>
            } />
            <Route path="/pending" element={<PendingApproval />} />
            <Route path="/rejected" element={<Rejected />} />

            {/* Protected Routes (active status only) */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            } />
            <Route path="/settings" element={
              <ProtectedRoute>
                <Settings />
              </ProtectedRoute>
            } />
            <Route path="/deploy" element={
              <ProtectedRoute>
                <Deploy />
              </ProtectedRoute>
            } />

            {/* Admin Routes */}
            <Route path="/admin" element={
              <AdminRoute>
                <Admin />
              </AdminRoute>
            } />

            {/* Landing page */}
            <Route path="/" element={<Landing />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </I18nProvider>
  );
}

export default App;
