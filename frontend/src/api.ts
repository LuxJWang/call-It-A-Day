/// <reference types="vite/client" />

export const API_URL = import.meta.env.VITE_API_URL || '/api';
export const AUTH_TOKEN_KEY = 'callitaday_auth_token';

export const getAuthToken = () => localStorage.getItem(AUTH_TOKEN_KEY);
export const setAuthToken = (token: string | null) => {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  }
};

export const authFetch = (path: string, options: RequestInit = {}) => {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  return fetch(`${API_URL}${path}`, { ...options, headers });
};

export const authFetchJson = async (path: string, options: RequestInit = {}) => {
  const response = await authFetch(path, options);
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(data?.detail || response.statusText || '请求失败');
  }
  return data;
};
