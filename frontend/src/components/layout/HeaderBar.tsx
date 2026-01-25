import React from 'react';
import { Layout, Input, Avatar, Dropdown, Space, Button, Badge } from 'antd';
import {
  SearchOutlined,
  UserOutlined,
  LogoutOutlined,
  MenuOutlined,
  BellOutlined,
  SettingOutlined,
  SwapOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useTelegramAuth } from '../../hooks/useTelegramAuth';
import { isDevMode, setDevUser, DEV_USERS } from '../DevAuthSelector';
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
  onThemeChange,
  themeMode,
  isDark,
  isMobile = false,
  onMenuClick,
}) => {
  const { user, logout } = useTelegramAuth();

  const switchRole = () => {
    const driver = DEV_USERS.find((u) => u.role === 'driver');
    if (driver) {
      setDevUser(driver);
      window.location.reload();
    }
  };

  const profileMenuItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: 'Профиль',
    },
    {
      key: 'settings',
      icon: <SettingOutlined />,
      label: 'Настройки',
    },
    ...(isDevMode()
      ? [
          {
            key: 'switch_role',
            icon: <SwapOutlined />,
            label: 'Водитель (Dev)',
            onClick: switchRole,
          },
        ]
      : []),
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
    <Header
      style={{
        padding: 0,
        background: 'transparent',
        height: 'auto',
        lineHeight: 'normal',
        zIndex: 1000,
        marginBottom: 16,
        position: 'sticky',
        top: 0, // Прижимаем к верху при скролле
      }}
    >
      <div
        style={{
          margin: isMobile ? '0' : '0 16px 0 0', // Убрали верхний марджин, оставили справа и снизу 0 (паддинг у контента)
          padding: isMobile ? '8px 12px' : '12px 24px',
          // Фон: используем переменную стекла, но с оверрайдом для темной темы
          background: isDark ? 'rgba(20, 30, 50, 0.95)' : 'var(--tms-glass-bg)',
          backdropFilter: 'var(--tms-glass-blur)',
          borderBottom: 'var(--tms-glass-border)',
          borderRight: 'var(--tms-glass-border)',
          borderLeft: 'none', // Слева стыкуемся
          borderTop: 'none', // Сверху стыкуемся
          borderRadius: '0 0 20px 20px', // Закругляем только низ
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          boxShadow: 'var(--tms-shadow-glass)',
          height: isMobile ? 64 : 72,
          transition: 'all 0.3s ease',
        }}
        className="glass-panel header-glass-panel"
      >
        {/* Левая часть */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, flex: 1 }}>
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
            <div
              style={{
                position: 'relative',
                width: '100%',
                maxWidth: 400,
                transition: 'all 0.3s ease',
              }}
            >
              <Input
                placeholder="Поиск заказов, водителей..."
                prefix={
                  <SearchOutlined style={{ color: 'var(--tms-text-tertiary)', fontSize: 16 }} />
                }
                style={{
                  borderRadius: 14,
                  background: isDark ? 'rgba(255, 255, 255, 0.03)' : 'rgba(0, 0, 0, 0.03)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  padding: '10px 16px',
                  fontSize: 14,
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                }}
                className="tms-search-input"
                allowClear
                onFocus={(e) => {
                  e.target.style.background = isDark ? 'rgba(0, 0, 0, 0.4)' : '#fff';
                  e.target.style.boxShadow = '0 8px 24px rgba(0, 0, 0, 0.12)';
                  e.target.style.borderColor = 'var(--tms-primary)';
                }}
                onBlur={(e) => {
                  e.target.style.background = isDark
                    ? 'rgba(255, 255, 255, 0.03)'
                    : 'rgba(0, 0, 0, 0.03)';
                  e.target.style.boxShadow = 'none';
                  e.target.style.borderColor = 'rgba(255,255,255,0.05)';
                }}
              />
            </div>
          )}
        </div>

        {/* Правая часть */}
        <Space size={isMobile ? 'small' : 'middle'} align="center">
          <ThemeToggle
            mode={themeMode}
            onModeChange={onThemeChange}
            isDark={isDark}
            showDropdown={!isMobile}
          />

          <div style={{ width: 1, height: 24, background: 'var(--tms-border-split)' }} />

          <Badge count={2} dot offset={[-4, 4]} color="var(--tms-primary)">
            <Button
              type="text"
              icon={<BellOutlined />}
              shape="circle"
              style={{ color: 'var(--tms-text-secondary)' }}
            />
          </Badge>

          <AlertCenter />

          <div style={{ width: 1, height: 24, background: 'var(--tms-border-split)' }} />

          <Dropdown menu={{ items: profileMenuItems }} placement="bottomRight" trigger={['click']}>
            <div
              style={{
                cursor: 'pointer',
                padding: '4px 8px',
                borderRadius: 12,
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                transition: 'background 0.2s',
              }}
              className="hover:bg-black/5 dark:hover:bg-white/5"
            >
              <Avatar
                size="default"
                icon={<UserOutlined />}
                src={user?.photo_url}
                style={{
                  background: 'var(--tms-gradient-primary)',
                  boxShadow: '0 2px 8px rgba(59, 130, 246, 0.3)',
                }}
              />
              {!isMobile && (
                <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>
                    {user?.first_name || 'Диспетчер'}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--tms-text-tertiary)' }}>
                    {user?.role === 'admin' ? 'Администратор' : 'В сети'}
                  </span>
                </div>
              )}
            </div>
          </Dropdown>
        </Space>
      </div>
    </Header>
  );
};
