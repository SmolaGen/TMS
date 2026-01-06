import React from 'react';
import { Layout, Input, Avatar, Dropdown, Space, Button } from 'antd';
import {
    SearchOutlined,
    UserOutlined,
    LogoutOutlined,
    MenuOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useTelegramAuth } from '../../hooks/useTelegramAuth';
import { AlertCenter } from '../dashboard/AlertCenter';
import { ThemeToggle } from '../common/ThemeToggle';
import type { ThemeMode } from '../../theme';

const { Header } = Layout;

interface HeaderBarProps {
    collapsed: boolean;
    onThemeChange: (mode: ThemeMode) => void;
    themeMode: ThemeMode;
    isDark: boolean;
    isMobile?: boolean;
    onMenuClick?: () => void;
    siderWidth?: number;
}

export const HeaderBar: React.FC<HeaderBarProps> = ({
    collapsed,
    onThemeChange,
    themeMode,
    isDark,
    isMobile = false,
    onMenuClick,
    siderWidth = 200,
}) => {
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
            padding: isMobile ? '0 12px' : '0 24px',
            background: 'var(--tms-bg-container)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
            marginLeft: isMobile ? 0 : (collapsed ? 80 : siderWidth),
            transition: 'margin-left 0.2s',
            zIndex: 1000,
            gap: 12,
        }}>
            {/* Левая часть */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1 }}>
                {/* Кнопка меню для мобильных */}
                {isMobile && (
                    <Button
                        type="text"
                        icon={<MenuOutlined />}
                        onClick={onMenuClick}
                        style={{ fontSize: 18 }}
                    />
                )}

                {/* Поиск - скрывается на мобильных */}
                {!isMobile && (
                    <Input
                        placeholder="Поиск заказов, водителей..."
                        prefix={<SearchOutlined />}
                        style={{ maxWidth: 400 }}
                        className="tms-search-desktop"
                        allowClear
                    />
                )}
            </div>

            {/* Правая часть */}
            <Space size={isMobile ? 'small' : 'large'}>
                <ThemeToggle
                    mode={themeMode}
                    onModeChange={onThemeChange}
                    isDark={isDark}
                    showDropdown={!isMobile}
                />

                <AlertCenter />

                <Dropdown menu={{ items: profileMenuItems }} placement="bottomRight">
                    <Space style={{ cursor: 'pointer' }}>
                        <Avatar
                            size="small"
                            icon={<UserOutlined />}
                            src={user?.photo_url}
                        />
                        {!isMobile && (
                            <span>{user?.first_name || 'Пользователь'}</span>
                        )}
                    </Space>
                </Dropdown>
            </Space>
        </Header>
    );
};
