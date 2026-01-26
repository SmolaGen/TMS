import React from 'react';
import { Typography, Button, Popconfirm, message, Space, Divider } from 'antd';
import { useOnboarding } from '../hooks/useOnboarding';

export const SettingsPage: React.FC = () => {
    const { restartOnboarding, isLoading } = useOnboarding();

    const triggerError = () => {
        throw new Error('Test error for GlobalErrorBoundary');
    };

    const handleRestartOnboarding = async () => {
        try {
            await restartOnboarding();
            message.success('Онбординг успешно сброшен. Перезагрузите страницу для начала.');
        } catch (error: any) {
            message.error(error.response?.data?.detail || 'Ошибка при сбросе онбординга');
        }
    };

    return (
        <div style={{ padding: 24 }}>
            <Typography.Title level={2}>Настройки</Typography.Title>
            <Typography.Text type="secondary">
                Страница в разработке.
            </Typography.Text>

            <Divider />

            <div>
                <Typography.Title level={4}>Онбординг</Typography.Title>
                <Typography.Paragraph type="secondary">
                    Пройдите интерактивное обучение основным функциям системы
                </Typography.Paragraph>
                <Popconfirm
                    title="Пройти онбординг заново?"
                    description="Это сбросит ваш прогресс онбординга и запустит его с начала"
                    onConfirm={handleRestartOnboarding}
                    okText="Да, начать заново"
                    cancelText="Отмена"
                    disabled={isLoading}
                >
                    <Button loading={isLoading}>
                        Пройти онбординг заново
                    </Button>
                </Popconfirm>
            </div>

            <Divider />

            <div>
                <Typography.Title level={4}>Разработка</Typography.Title>
                <Space direction="vertical">
                    <Button danger onClick={triggerError}>
                        Триггернуть тестовую ошибку
                    </Button>
                </Space>
            </div>
        </div>
    );
};
