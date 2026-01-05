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
        if (savedToken) {
            setState({
                isLoading: false,
                isAuthenticated: true,
                user: null,
                error: null,
                token: savedToken,
            });
            console.log('[Auth] Found saved token, using it');
            return;
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
