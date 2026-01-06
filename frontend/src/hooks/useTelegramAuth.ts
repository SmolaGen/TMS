import { useState, useEffect, useCallback } from 'react';
import { apiClient } from '../api/client';

interface TelegramUser {
    id: number;
    first_name: string;
    last_name?: string;
    username?: string;
    photo_url?: string;
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
    sub: string;
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
        const jsonPayload = decodeURIComponent(atob(base64).split('').map((c) => {
            return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        }).join(''));

        const payload: JwtPayload = JSON.parse(jsonPayload);
        const now = Math.floor(Date.now() / 1000);

        return payload.exp > now;
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
        // 1. Сначала проверяем сохраненный токен в localStorage
        const savedToken = localStorage.getItem(TOKEN_KEY);
        if (savedToken && isTokenValid(savedToken)) {
            setState({
                isLoading: false,
                isAuthenticated: true,
                user: null,
                error: null,
                token: savedToken,
            });
            console.log('[Auth] Found valid saved token, using it');
            return;
        }

        if (savedToken && !isTokenValid(savedToken)) {
            console.log('[Auth] Saved token expired or invalid, removing it');
            localStorage.removeItem(TOKEN_KEY);
        }

        // 2. Проверяем наличие Telegram WebApp с initData
        const tg = (window as any).Telegram?.WebApp;

        if (!tg || !tg.initData) {
            // Нет ни токена, ни initData — показываем страницу авторизации
            setState({
                isLoading: false,
                isAuthenticated: false,
                user: null,
                error: 'Не удалось получить данные авторизации от Telegram.',
                token: null,
            });
            return;
        }

        // 3. Есть initData — авторизуемся через Mini App
        tg.ready();
        tg.expand();

        const initData = tg.initData;
        const initDataUnsafe = tg.initDataUnsafe;

        try {
            // Отправляем initData на бэкенд для валидации
            const response = await apiClient.post<{ access_token: string; token_type: string }>(
                '/auth/login',
                { init_data: initData }
            );

            const token = response.data.access_token;

            // Сохраняем токен
            localStorage.setItem(TOKEN_KEY, token);

            // Извлекаем информацию о пользователе
            const user: TelegramUser = {
                id: initDataUnsafe?.user?.id,
                first_name: initDataUnsafe?.user?.first_name || 'User',
                last_name: initDataUnsafe?.user?.last_name,
                username: initDataUnsafe?.user?.username,
                photo_url: initDataUnsafe?.user?.photo_url,
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
