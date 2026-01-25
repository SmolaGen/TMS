import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api/client';
import { isDevMode, getDevUser, clearDevUser } from '../components/DevAuthSelector';

interface TelegramUser {
  id: number; // Telegram ID
  driver_id?: number; // Internal database driver ID
  first_name: string;
  last_name?: string;
  username?: string;
  photo_url?: string;
  role?: string;
}

interface AuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: TelegramUser | null;
  error: string | null;
  token: string | null;
}

const TOKEN_KEY = 'tms_auth_token';
interface JwtPayload {
  sub: string; // Telegram ID
  driver_id: number; // Internal database driver ID
  role: string;
  exp: number;
}

/**
 * Проверяет, валиден ли JWT токен и не истек ли он.
 */
function isTokenValid(token: string): boolean {
  if (!token) return false;
  try {
    const base64Url = token.split('.')[1];
    if (!base64Url) return false;

    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        })
        .join(''),
    );

    const payload: JwtPayload = JSON.parse(jsonPayload);
    const now = Math.floor(Date.now() / 1000);

    // Токен валиден, если он не истек И в нем есть роль (для RBAC)
    return payload.exp > now && !!payload.role;
  } catch (e) {
    console.error('[Auth] Error decoding token:', e);
    return false;
  }
}

/**
 * Хук для авторизации через Telegram Mini App.
 *
 * Получает initData из Telegram WebApp, отправляет на бэкенд,
 * получает JWT токен и сохраняет его для последующих запросов.
 */
export function useTelegramAuth() {
  const [state, setState] = useState<AuthState>({
    isLoading: true,
    isAuthenticated: false,
    user: null,
    error: null,
    token: null,
  });

  const authenticate = useCallback(async () => {
    // 0. Проверяем dev-режим
    if (isDevMode()) {
      const devUser = getDevUser();
      if (devUser) {
        console.log('[Auth] Dev mode: using saved dev user', devUser);
        setState({
          isLoading: false,
          isAuthenticated: true,
          user: {
            id: devUser.id,
            driver_id: devUser.driver_id,
            first_name: devUser.first_name,
            last_name: devUser.last_name,
            username: devUser.username,
            role: devUser.role,
          },
          error: null,
          token: 'dev-token',
        });
        return;
      }
      // Нет dev-пользователя - показываем экран выбора
      setState({
        isLoading: false,
        isAuthenticated: false,
        user: null,
        error: null,
        token: null,
      });
      return;
    }

    // 1. Сначала проверяем сохраненный токен в localStorage
    const savedToken = localStorage.getItem(TOKEN_KEY);
    if (savedToken && isTokenValid(savedToken)) {
      // Извлекаем данные пользователя из JWT
      let userId: number | undefined;
      let driverId: number | undefined;
      let role: string | undefined;
      try {
        const base64Url = savedToken.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const payload: JwtPayload = JSON.parse(atob(base64));
        userId = parseInt(payload.sub); // Telegram ID
        driverId = payload.driver_id; // Internal DB ID
        role = payload.role;
      } catch (e) {
        console.error('[Auth] Failed to parse user data from token');
      }

      setState({
        isLoading: false,
        isAuthenticated: true,
        user: userId ? { id: userId, driver_id: driverId, first_name: 'User', role } : null,
        error: null,
        token: savedToken,
      });
      console.log('[Auth] Valid token found, restored user:', { userId, driverId, role });
      return;
    }

    if (savedToken && !isTokenValid(savedToken)) {
      console.log('[Auth] Saved token expired or invalid, removing it');
      localStorage.removeItem(TOKEN_KEY);
    }

    // 2. Проверяем наличие Telegram WebApp с initData
    const tg = (window as any).Telegram?.WebApp;

    if (!tg || !tg.initData) {
      setState({
        isLoading: false,
        isAuthenticated: false,
        user: null,
        error: 'Не удалось получить данные авторизации от Telegram.',
        token: null,
      });
      return;
    }

    const initData = tg.initData;
    const initDataUnsafe = tg.initDataUnsafe;

    try {
      // Отправляем initData на бэкенд для валидации
      const response = await apiClient.post<{
        access_token: string;
        token_type: string;
        role: string;
      }>('/auth/login', { init_data: initData });

      const token = response.data.access_token;
      const role = response.data.role;

      // Сохраняем токен
      localStorage.setItem(TOKEN_KEY, token);

      // Извлекаем информацию о пользователе
      const user: TelegramUser = {
        id: initDataUnsafe?.user?.id,
        first_name: initDataUnsafe?.user?.first_name || 'User',
        last_name: initDataUnsafe?.user?.last_name,
        username: initDataUnsafe?.user?.username,
        photo_url: initDataUnsafe?.user?.photo_url,
        role: role,
      };

      setState({
        isLoading: false,
        isAuthenticated: true,
        user,
        error: null,
        token,
      });

      console.log('[Auth] Successfully authenticated via Telegram');
    } catch (error: any) {
      console.error('[Auth] Authentication failed:', error);

      // Очищаем старый токен при ошибке
      localStorage.removeItem(TOKEN_KEY);

      setState({
        isLoading: false,
        isAuthenticated: false,
        user: null,
        error: error.response?.data?.detail || 'Ошибка авторизации',
        token: null,
      });
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    clearDevUser(); // Очищаем dev-авторизацию
    setState({
      isLoading: false,
      isAuthenticated: false,
      user: null,
      error: null,
      token: null,
    });
  }, []);

  useEffect(() => {
    authenticate();

    // Слушаем событие истечения токена из интерцептора
    const handleTokenExpired = () => {
      console.log('[Auth] Token expired event received, re-authenticating...');
      authenticate();
    };

    window.addEventListener('auth:token-expired', handleTokenExpired);
    return () => window.removeEventListener('auth:token-expired', handleTokenExpired);
  }, [authenticate]);

  return {
    ...state,
    logout,
    retry: authenticate,
  };
}

/**
 * Получить сохраненный токен (для использования в apiClient)
 */
export function getAuthToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}
