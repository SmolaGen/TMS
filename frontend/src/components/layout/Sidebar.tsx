import React from 'react';
import { motion } from 'framer-motion';
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
            <motion.div
                onClick={onClick}
                whileHover={{ x: 4, background: isActive ? undefined : 'rgba(255, 255, 255, 0.03)' }}
                whileTap={{ scale: 0.98 }}
                initial={false}
                animate={{
                    background: isActive
                        ? 'linear-gradient(90deg, rgba(59, 130, 246, 0.12) 0%, rgba(37, 99, 235, 0.03) 100%)'
                        : 'transparent',
                }}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: collapsed ? '12px' : '12px 16px',
                    justifyContent: collapsed ? 'center' : 'flex-start',
                    margin: '4px 0',
                    cursor: 'pointer',
                    borderRadius: 14,
                    transition: 'color 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    color: isActive ? '#3b82f6' : 'var(--tms-text-secondary)',
                    position: 'relative',
                    overflow: 'hidden',
                }}
                className={isActive ? 'active-menu-item' : 'menu-item'}
            >
                {isActive && (
                    <motion.div
                        layoutId="sidebar-active-indicator"
                        style={{
                            position: 'absolute',
                            left: 0,
                            top: '20%',
                            bottom: '20%',
                            width: 3,
                            background: '#3b82f6',
                            borderRadius: '0 4px 4px 0',
                            boxShadow: '0 0 12px rgba(59, 130, 246, 0.6)'
                        }}
                    />
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
                    <motion.span
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        style={{
                            marginLeft: 16,
                            fontWeight: isActive ? 600 : 500,
                            fontSize: 14,
                            whiteSpace: 'nowrap',
                        }}
                    >
                        {label}
                    </motion.span>
                )}
            </motion.div>
        </Tooltip>
    );
};

const TMSLogo = () => (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M4 11L12 3L20 11V19C20 19.5304 19.7893 20.0391 19.4142 20.4142C19.0391 20.7893 18.5304 21 18 21H6C5.46957 21 4.96086 20.7893 4.58579 20.4142C4.21071 20.0391 4 19.5304 4 19V11Z" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M9 13H15M9 17H15" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M12 3V21" stroke="white" strokeWidth="1.5" strokeDasharray="2 2" />
    </svg>
);

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
                    width: 44,
                    height: 44,
                    background: 'var(--tms-gradient-primary)',
                    borderRadius: 14,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 8px 16px rgba(59, 130, 246, 0.25)',
                    flexShrink: 0,
                    transition: 'all 0.3s ease'
                }}>
                    <TMSLogo />
                </div>
                {!collapsed && (
                    <div style={{ marginLeft: 16 }}>
                        <div className="gradient-text" style={{
                            fontWeight: 800,
                            fontSize: 20,
                            lineHeight: 1.1,
                            letterSpacing: '-0.02em'
                        }}>TMS Park</div>
                        <div style={{
                            fontSize: 10,
                            color: 'var(--tms-text-tertiary)',
                            textTransform: 'uppercase',
                            letterSpacing: '0.05em',
                            marginTop: 2
                        }}>Logistics OS</div>
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
