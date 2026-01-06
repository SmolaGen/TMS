import React from 'react';
import { Layout, Input, Badge, Avatar, Dropdown, Space } from 'antd';
import {
    SearchOutlined,
    BellOutlined,
    UserOutlined,
    LogoutOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useTelegramAuth } from '../../hooks/useTelegramAuth';

const { Header } = Layout;

interface HeaderBarProps {
    collapsed: boolean;
}

export const HeaderBar: React.FC<HeaderBarProps> = ({ collapsed }) => {
    const { user, logout } = useTelegramAuth();

    const profileMenuItems: MenuProps['items'] = [
        {
            key: 'profile',
            icon: <UserOutlined />,
            label: 'Профиль',
        },
        {
            type: 'divider',
        },
        {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: 'Выйти',
            danger: true,
            onClick: logout,
        },
    ];

    return (
        <Header style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
            marginLeft: collapsed ? 80 : 200,
            transition: 'margin-left 0.2s',
            zIndex: 1000,
        }}>
            {/* Поиск */}
            <Input
                placeholder="Поиск заказов, водителей..."
                prefix={<SearchOutlined />}
                style={{ maxWidth: 400 }}
                allowClear
            />

            {/* Правая часть */}
            <Space size="large">
                <Badge count={0} size="small">
                    <BellOutlined style={{ fontSize: 20, cursor: 'pointer' }} />
                </Badge>

                <Dropdown menu={{ items: profileMenuItems }} placement="bottomRight">
                    <Space style={{ cursor: 'pointer' }}>
                        <Avatar
                            size="small"
                            icon={<UserOutlined />}
                            src={user?.photo_url}
                        />
                        <span>{user?.first_name || 'Пользователь'}</span>
                    </Space>
                </Dropdown>
            </Space>
        </Header>
    );
};
