import axios from 'axios';

const api = axios.create({
  // Use environment variable for flexibility, fallback to localhost for dev
  // VITE_AUTH_API_URL should be just the domain (e.g., https://louisasgrid.zeabur.app)
  baseURL: `${import.meta.env.VITE_AUTH_API_URL || 'http://localhost:8000'}/api/v1`,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default api;
