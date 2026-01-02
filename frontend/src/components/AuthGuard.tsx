import React, { useEffect, useRef } from 'react';
import { Spin, Button, Divider } from 'antd';
import { useTelegramAuth } from '../hooks/useTelegramAuth';
import { apiClient } from '../api/client';

interface AuthGuardProps {
    children: React.ReactNode;
}

declare global {
    interface Window {
        onTelegramAuth: (user: TelegramLoginUser) => void;
    }
}

interface TelegramLoginUser {
    id: number;
    first_name: string;
    last_name?: string;
    username?: string;
    photo_url?: string;
    auth_date: number;
    hash: string;
}

/**
 * Компонент-обертка для защиты приложения.
 * 
 * Показывает загрузку во время авторизации,
 * Telegram Login Widget если не в Telegram Mini App,
 * и детей если авторизован.
 */
export function AuthGuard({ children }: AuthGuardProps) {
    const { isLoading, isAuthenticated, error, retry } = useTelegramAuth();
    const widgetRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        // Callback для Telegram Login Widget
        window.onTelegramAuth = async (user: TelegramLoginUser) => {
            try {
                // Формируем строку данных для валидации (hash НЕ включается в data_check_string)
                const authData: Record<string, string | number> = {
                    id: user.id,
                    first_name: user.first_name,
                    auth_date: user.auth_date,
                };
                if (user.last_name) authData.last_name = user.last_name;
                if (user.username) authData.username = user.username;
                if (user.photo_url) authData.photo_url = user.photo_url;

                // Сортируем и формируем строку (без hash)
                const dataCheckArr: string[] = [];
                Object.keys(authData).sort().forEach(key => {
                    dataCheckArr.push(`${key}=${authData[key]}`);
                });
                
                // Hash добавляется в конец, но не участвует в data_check_string
                dataCheckArr.push(`hash=${user.hash}`);

                const initData = dataCheckArr.join('&');

                // Отправляем на бэкенд
                const response = await apiClient.post<{ access_token: string }>('/auth/login', {
                    init_data: initData
                });

                // Сохраняем токен
                localStorage.setItem('tms_auth_token', response.data.access_token);

                // Перезагружаем страницу для применения авторизации
                window.location.reload();
            } catch (err) {
                console.error('[Auth] Telegram login failed:', err);
                alert('Ошибка авторизации. Попробуйте снова.');
            }
        };
    }, []);

    useEffect(() => {
        // Добавляем Telegram Login Widget скрипт
        if (!isAuthenticated && !isLoading && widgetRef.current) {
            // Очищаем предыдущий виджет
            widgetRef.current.innerHTML = '';

            const script = document.createElement('script');
            script.src = 'https://telegram.org/js/telegram-widget.js?22';
            script.setAttribute('data-telegram-login', 'Premium_Park_Robot');
            script.setAttribute('data-size', 'large');
            script.setAttribute('data-radius', '10');
            script.setAttribute('data-onauth', 'onTelegramAuth(user)');
            script.setAttribute('data-request-access', 'write');
            script.async = true;

            widgetRef.current.appendChild(script);
        }
    }, [isAuthenticated, isLoading]);

    if (isLoading) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            }}>
                <Spin size="large" tip="Авторизация..." />
            </div>
        );
    }

    if (!isAuthenticated || error) {
        return (
            <div style={{
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                height: '100vh',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            }}>
                <div style={{
                    background: 'white',
                    borderRadius: 16,
                    padding: 32,
                    maxWidth: 400,
                    textAlign: 'center',
                    boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
                }}>
                    <div style={{ fontSize: 48, marginBottom: 16 }}>🔐</div>
                    <h2 style={{ margin: '0 0 8px 0', color: '#1a1a1a' }}>
                        Требуется авторизация
                    </h2>
                    <p style={{ color: '#666', marginBottom: 24 }}>
                        Войдите через Telegram для доступа к системе
                    </p>

                    {/* Telegram Login Widget */}
                    <div
                        ref={widgetRef}
                        style={{
                            display: 'flex',
                            justifyContent: 'center',
                            minHeight: 40,
                        }}
                    />

                    <Divider style={{ margin: '24px 0' }}>или</Divider>

                    <Button type="default" onClick={retry} block>
                        Открыть в Telegram Mini App
                    </Button>

                    {error && (
                        <p style={{ color: '#ff4d4f', marginTop: 16, fontSize: 12 }}>
                            {error}
                        </p>
                    )}
                </div>
            </div>
        );
    }

    return <>{children}</>;
}
