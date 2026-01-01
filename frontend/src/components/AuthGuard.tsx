import React from 'react';
import { Spin, Result, Button } from 'antd';
import { useTelegramAuth } from '../hooks/useTelegramAuth';

interface AuthGuardProps {
    children: React.ReactNode;
}

/**
 * Компонент-обертка для защиты приложения.
 * 
 * Показывает загрузку во время авторизации,
 * ошибку если не в Telegram, и детей если авторизован.
 */
export function AuthGuard({ children }: AuthGuardProps) {
    const { isLoading, isAuthenticated, error, retry } = useTelegramAuth();

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
                <Result
                    status="warning"
                    title="Требуется авторизация"
                    subTitle={error || 'Откройте приложение через Telegram'}
                    extra={[
                        <Button type="primary" key="retry" onClick={retry}>
                            Попробовать снова
                        </Button>,
                    ]}
                    style={{
                        background: 'white',
                        borderRadius: 16,
                        padding: 24,
                        maxWidth: 400,
                    }}
                />
            </div>
        );
    }

    return <>{children}</>;
}
