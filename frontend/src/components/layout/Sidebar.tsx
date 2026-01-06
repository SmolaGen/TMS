import React from 'react';
import { Layout, Menu } from 'antd';
import { useNavigate, useLocation } from 'react-router-dom';
import {
    DashboardOutlined,
    OrderedListOutlined,
    CarOutlined,
    BarChartOutlined,
    SettingOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';

const { Sider } = Layout;

interface SidebarProps {
    collapsed: boolean;
    onCollapse: (collapsed: boolean) => void;
    isMobileDrawer?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
    collapsed,
    onCollapse,
    isMobileDrawer = false
}) => {
    const navigate = useNavigate();
    const location = useLocation();

    const menuItems: MenuProps['items'] = [
        {
            key: '/',
            icon: <DashboardOutlined />,
            label: 'Дашборд',
        },
        {
            key: '/orders',
            icon: <OrderedListOutlined />,
            label: 'Заказы',
        },
        {
            key: '/drivers',
            icon: <CarOutlined />,
            label: 'Водители',
        },
        {
            key: '/stats',
            icon: <BarChartOutlined />,
            label: 'Статистика',
        },
        {
            type: 'divider',
        },
        {
            key: '/settings',
            icon: <SettingOutlined />,
            label: 'Настройки',
        },
    ];

    const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
        navigate(key);
        // Закрыть drawer после навигации на мобильных
        if (isMobileDrawer) {
            onCollapse(true);
        }
    };

    // Для мобильного drawer - простой вид без Sider обёртки
    if (isMobileDrawer) {
        return (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
                <div style={{
                    height: 64,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff',
                    fontSize: 20,
                    fontWeight: 'bold',
                    borderBottom: '1px solid rgba(255,255,255,0.1)',
                }}>
                    🚗 TMS Park
                </div>

                <Menu
                    theme="dark"
                    mode="inline"
                    selectedKeys={[location.pathname]}
                    items={menuItems}
                    onClick={handleMenuClick}
                    style={{ flex: 1, borderRight: 0 }}
                />
            </div>
        );
    }

    // Десктопный вид
    return (
        <Sider
            collapsible
            collapsed={collapsed}
            onCollapse={onCollapse}
            width={200}
            collapsedWidth={80}
            theme="dark"
            breakpoint="lg"
            style={{
                overflow: 'auto',
                height: '100vh',
                position: 'fixed',
                left: 0,
                top: 0,
                bottom: 0,
                zIndex: 1001,
            }}
        >
            <div style={{
                height: 64,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#fff',
                fontSize: collapsed ? 18 : 20,
                fontWeight: 'bold',
                transition: 'all 0.2s',
            }}>
                {collapsed ? '🚗' : '🚗 TMS Park'}
            </div>

            <Menu
                theme="dark"
                mode="inline"
                selectedKeys={[location.pathname]}
                items={menuItems}
                onClick={handleMenuClick}
            />
        </Sider>
    );
};
