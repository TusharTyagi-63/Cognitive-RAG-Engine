import axios from 'axios';

let savedUrl = localStorage.getItem('API_URL');

// If savedUrl was accidentally set to localhost while running on a public website (Render), auto-clear it
if (
  savedUrl &&
  savedUrl.includes('localhost') &&
  typeof window !== 'undefined' &&
  window.location.hostname !== 'localhost' &&
  window.location.hostname !== '127.0.0.1'
) {
  localStorage.removeItem('API_URL');
  savedUrl = null;
}

let envUrl = import.meta.env.VITE_API_URL || '';

// Ignore internal Docker / Render service names that don't have a public TLD
if (envUrl === 'rag-backend' || (envUrl && !envUrl.includes('.') && !envUrl.includes('localhost'))) {
  envUrl = '';
}

const DEFAULT_BACKEND_URL =
  typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
    ? 'http://localhost:8000'
    : 'https://rag-backend-rxrx.onrender.com';

let activeUrl = savedUrl || envUrl || DEFAULT_BACKEND_URL;
if (activeUrl && !activeUrl.startsWith('http')) {
  activeUrl = `https://${activeUrl}`;
}

export let baseUrl = activeUrl.replace(/\/$/, '');

export const setApiUrl = (newUrl: string) => {
  let formatted = newUrl.trim();
  if (formatted && !formatted.startsWith('http')) {
    formatted = `https://${formatted}`;
  }
  formatted = formatted.replace(/\/$/, '');
  localStorage.setItem('API_URL', formatted);
  window.location.reload();
};

export const api = axios.create({
  baseURL: `${baseUrl}/api/v1`,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Interceptor to inject the token from localStorage
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor to handle 401 Unauthorized
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
      // Only redirect if we are not already on the login page
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
