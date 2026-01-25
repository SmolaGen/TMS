import axios from 'axios';
import type { ApiError } from '../types/api';

const TOKEN_KEY = 'tms_auth_token';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Интерцептор для добавления токена авторизации
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

// Интерцептор для логирования ошибок и обработки 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const apiError: ApiError = {
      message: error.response?.data?.detail || error.message || 'Unknown API Error',
      status: error.response?.status,
      data: error.response?.data,
      originalError: error,
    };

    if (error.response?.status === 401) {
      const detail = error.response.data?.detail;
      // Если токен истек или невалиден - очищаем его
      if (detail === 'Token expired' || detail === 'Invalid token') {
        console.warn('[Auth] Token expired, clearing storage');
        localStorage.removeItem(TOKEN_KEY);
        window.dispatchEvent(new CustomEvent('auth:token-expired'));
      }
    }

    console.error('[API Error]', apiError.status, apiError.message);
    return Promise.reject(apiError);
  },
);
