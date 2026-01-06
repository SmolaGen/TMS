import React from 'react';
import { Card, Button, Space, Typography, Avatar, Tag } from 'antd';
import { UserOutlined, CarOutlined, DesktopOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

// Проверяем, включен ли dev-режим
export const isDevMode = (): boolean => {
    return import.meta.env.DEV || import.meta.env.VITE_DEV_AUTH === 'true';
};

// Ключ для хранения dev-данных
const DEV_AUTH_KEY = 'tms_dev_auth';

export interface DevUser {
    id: number;
    driver_id?: number;
    first_name: string;
    last_name?: string;
    username?: string;
    role: 'staff' | 'driver';
}

// Предустановленные тестовые пользователи
const DEV_USERS: DevUser[] = [
    {
        id: 1,
        first_name: 'Диспетчер',
        last_name: 'Тестовый',
        username: 'dispatcher_test',
        role: 'staff',
    },
    {
        id: 2,
        driver_id: 1,
        first_name: 'Водитель',
        last_name: 'Иванов',
        username: 'driver_test',
        role: 'driver',
    },
    {
        id: 3,
        driver_id: 2,
        first_name: 'Водитель',
        last_name: 'Петров',
        username: 'driver2_test',
        role: 'driver',
    },
];

/**
 * Получить сохраненного dev-пользователя
 */
export function getDevUser(): DevUser | null {
    if (!isDevMode()) return null;

    const saved = localStorage.getItem(DEV_AUTH_KEY);
    if (saved) {
        try {
            return JSON.parse(saved);
        } catch {
            return null;
        }
    }
    return null;
}

/**
 * Установить dev-пользователя
 */
export function setDevUser(user: DevUser): void {
    localStorage.setItem(DEV_AUTH_KEY, JSON.stringify(user));
}

/**
 * Очистить dev-авторизацию
 */
export function clearDevUser(): void {
    localStorage.removeItem(DEV_AUTH_KEY);
}

interface DevAuthSelectorProps {
    onSelect: (user: DevUser) => void;
}

/**
 * Компонент выбора роли для dev-режима.
 * Позволяет войти как диспетчер или водитель без Telegram авторизации.
 */
export const DevAuthSelector: React.FC<DevAuthSelectorProps> = ({ onSelect }) => {
    const handleSelect = (user: DevUser) => {
        setDevUser(user);
        onSelect(user);
    };

    return (
        <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '100vh',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            padding: 16,
        }}>
            <Card
                style={{
                    maxWidth: 500,
                    width: '100%',
                    borderRadius: 16,
                    boxShadow: '0 10px 40px rgba(0,0,0,0.2)',
                }}
            >
                <div style={{ textAlign: 'center', marginBottom: 24 }}>
                    <Tag color="orange" style={{ marginBottom: 16 }}>DEV MODE</Tag>
                    <Title level={3} style={{ margin: 0 }}>
                        🛠️ Режим разработки
                    </Title>
                    <Text type="secondary">
                        Выберите роль для входа в систему
                    </Text>
                </div>

                <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                    {DEV_USERS.map((user) => (
                        <Button
                            key={user.id}
                            block
                            size="large"
                            type={user.role === 'staff' ? 'primary' : 'default'}
                            icon={user.role === 'staff' ? <DesktopOutlined /> : <CarOutlined />}
                            onClick={() => handleSelect(user)}
                            style={{
                                height: 64,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'flex-start',
                                paddingLeft: 16,
                            }}
                        >
                            <Space>
                                <Avatar
                                    icon={<UserOutlined />}
                                    style={{
                                        backgroundColor: user.role === 'staff' ? '#1890ff' : '#52c41a',
                                        marginLeft: 8,
                                    }}
                                />
                                <div style={{ textAlign: 'left', marginLeft: 8 }}>
                                    <div style={{ fontWeight: 500 }}>
                                        {user.first_name} {user.last_name}
                                    </div>
                                    <div style={{ fontSize: 12, opacity: 0.8 }}>
                                        {user.role === 'staff' ? 'Диспетчер' : `Водитель (ID: ${user.driver_id})`}
                                    </div>
                                </div>
                            </Space>
                        </Button>
                    ))}
                </Space>

                <div style={{ marginTop: 24, textAlign: 'center' }}>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                        ⚠️ Этот экран виден только в dev-режиме
                    </Text>
                </div>
            </Card>
        </div>
    );
};
