import React from 'react';
import { Layout, Tooltip } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
    DashboardOutlined,
    OrderedListOutlined,
    CarOutlined,
    BarChartOutlined,
    SettingOutlined,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
} from '@ant-design/icons';

const { Sider } = Layout;

interface SidebarProps {
    collapsed: boolean;
    onCollapse: (collapsed: boolean) => void;
    isMobileDrawer?: boolean;
}

interface MenuItemProps {
    path: string;
    icon: React.ReactNode;
    label: string;
    collapsed: boolean;
    isActive: boolean;
    onClick: () => void;
}

const SidebarMenuItem: React.FC<MenuItemProps> = ({ icon, label, collapsed, isActive, onClick }) => {
    return (
        <Tooltip title={collapsed ? label : ''} placement="right">
            <div
                onClick={onClick}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: collapsed ? '12px' : '12px 16px',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    margin: '4px 0',
                    cursor: 'pointer',
                    borderRadius: 12,
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    background: isActive
                        ? 'linear-gradient(90deg, rgba(59, 130, 246, 0.15) 0%, rgba(37, 99, 235, 0.05) 100%)'
                        : 'transparent',
                    color: isActive ? '#3b82f6' : 'var(--tms-text-secondary)',
                    position: 'relative',
                    overflow: 'hidden',
                }}
                className={isActive ? 'active-menu-item' : 'menu-item'}
            >
                {isActive && (
                    <div style={{
                        position: 'absolute',
                        left: 0,
                        top: '15%',
                        bottom: '15%',
                        width: 3,
                        background: 'var(--tms-gradient-primary)',
                        borderRadius: '0 4px 4px 0',
                        boxShadow: '0 0 8px rgba(59, 130, 246, 0.5)'
                    }} />
                )}

                <span style={{
                    fontSize: 20,
                    display: 'flex',
                    alignItems: 'center',
                    filter: isActive ? 'drop-shadow(0 0 8px rgba(59, 130, 246, 0.3))' : 'none',
                    transition: 'transform 0.2s',
                    transform: isActive ? 'scale(1.1)' : 'scale(1)'
                }}>
                    {icon}
                </span>

                {!collapsed && (
                    <span style={{
                        marginLeft: 16,
                        fontWeight: isActive ? 600 : 500,
                        fontSize: 14,
                        whiteSpace: 'nowrap',
                        opacity: 1,
                        transition: 'opacity 0.2s'
                    }}>
                        {label}
                    </span>
                )}
            </div>
        </Tooltip>
    );
};

export const Sidebar: React.FC<SidebarProps> = ({
    collapsed,
    onCollapse,
    isMobileDrawer = false
}) => {
    const navigate = useNavigate();
    const location = useLocation();

    const menuData = [
        { path: '/', icon: <DashboardOutlined />, label: 'Дашборд' },
        { path: '/orders', icon: <OrderedListOutlined />, label: 'Заказы' },
        { path: '/drivers', icon: <CarOutlined />, label: 'Водители' },
        { path: '/stats', icon: <BarChartOutlined />, label: 'Статистика' },
    ];

    const bottomMenuData = [
        { path: '/settings', icon: <SettingOutlined />, label: 'Настройки' },
    ];

    const renderMenu = () => (
        <div style={{
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
            padding: isMobileDrawer ? '16px 8px' : '24px 12px 12px',
        }}>
            {/* Logo Area */}
            <div style={{
                height: 64,
                display: 'flex',
                alignItems: 'center',
                justifyContent: collapsed ? 'center' : 'flex-start',
                padding: collapsed ? 0 : '0 12px',
                marginBottom: 24,
            }}>
                <div style={{
                    width: 40,
                    height: 40,
                    background: 'var(--tms-gradient-primary)',
                    borderRadius: 12,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 24,
                    boxShadow: 'var(--tms-shadow-glow-primary)',
                    flexShrink: 0
                }}>
                    🚗
                </div>
                {!collapsed && (
                    <div style={{ marginLeft: 12 }}>
                        <div className="gradient-text" style={{ fontWeight: 800, fontSize: 18, lineHeight: 1.2 }}>TMS Park</div>
                        <div style={{ fontSize: 11, color: 'var(--tms-text-tertiary)' }}>Logistics System</div>
                    </div>
                )}
            </div>

            {/* Main Menu */}
            <div style={{ flex: 1 }}>
                {menuData.map((item) => (
                    <SidebarMenuItem
                        key={item.path}
                        {...item}
                        collapsed={collapsed}
                        isActive={location.pathname === item.path}
                        onClick={() => {
                            navigate(item.path);
                            if (isMobileDrawer) onCollapse(true);
                        }}
                    />
                ))}
            </div>

            {/* Bottom Actions */}
            <div style={{ marginTop: 'auto' }}>
                {bottomMenuData.map((item) => (
                    <SidebarMenuItem
                        key={item.path}
                        {...item}
                        collapsed={collapsed}
                        isActive={location.pathname === item.path}
                        onClick={() => {
                            navigate(item.path);
                            if (isMobileDrawer) onCollapse(true);
                        }}
                    />
                ))}

                {!isMobileDrawer && (
                    <div
                        onClick={() => onCollapse(!collapsed)}
                        style={{
                            marginTop: 8,
                            padding: 12,
                            display: 'flex',
                            justifyContent: 'center',
                            cursor: 'pointer',
                            color: 'var(--tms-text-tertiary)',
                            transition: 'color 0.2s'
                        }}
                        className="hover:text-primary"
                    >
                        {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                    </div>
                )}
            </div>
        </div>
    );

    if (isMobileDrawer) {
        return (
            <div style={{
                height: '100%',
                background: 'var(--tms-bg-container)',
            }}>
                {renderMenu()}
            </div>
        );
    }

    return (
        <Sider
            collapsible
            collapsed={collapsed}
            onCollapse={onCollapse}
            width={260}
            collapsedWidth={88}
            trigger={null}
            style={{
                height: 'calc(100vh - 32px)',
                position: 'fixed',
                left: 16,
                top: 16,
                bottom: 16,
                borderRadius: 24,
                overflow: 'hidden',
                zIndex: 1001,
                boxShadow: 'var(--tms-shadow-glass)',
                border: 'var(--tms-glass-border)',
                backdropFilter: 'blur(20px)',
            }}
            className="glass-panel sidebar-glass"
        >
            {renderMenu()}
        </Sider>
    );
};
