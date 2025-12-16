import React, { createContext, useState, useContext, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [nodeSecret, setNodeSecret] = useState(localStorage.getItem('node_secret') || '');

  const saveNodeSecret = (secret) => {
    localStorage.setItem('node_secret', secret);
    setNodeSecret(secret);
  };

  const refreshUser = async () => {
    try {
      const res = await api.get('/users/me');
      setUser(res.data);
    } catch (e) {
      console.error('Failed to refresh user', e);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      // Fetch user profile
      api.get('/users/me')
        .then(res => setUser(res.data))
        .catch(() => {
          localStorage.removeItem('token');
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const formData = new FormData();
    formData.append('username', email);  // Use email as username
    formData.append('password', password);

    const res = await api.post('/auth/login', formData);
    const { access_token, status } = res.data;

    localStorage.setItem('token', access_token);

    // Fetch user details immediately after login
    const userRes = await api.get('/users/me');
    setUser(userRes.data);

    // Return status for caller to handle navigation
    return { status: status || userRes.data.status };
  };

  const register = async (email, password) => {
    // New flow: email + password only
    await api.post('/auth/register', { email, password });
  };

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading, nodeSecret, saveNodeSecret, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
