import React, { useState, useEffect } from 'react';
import { Layout, Drawer } from 'antd';
import { Sidebar } from './Sidebar';
import { HeaderBar } from './HeaderBar';

const { Content, Footer } = Layout;

import type { ThemeMode } from '../../theme';

interface AppLayoutProps {
    children: React.ReactNode;
    onThemeChange: (mode: ThemeMode) => void;
    themeMode: ThemeMode;
    isDark: boolean;
}

// Хук для определения мобильного устройства
const useIsMobile = (breakpoint = 768) => {
    const [isMobile, setIsMobile] = useState(
        typeof window !== 'undefined' ? window.innerWidth <= breakpoint : false
    );

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth <= breakpoint);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, [breakpoint]);

    return isMobile;
};

export const AppLayout: React.FC<AppLayoutProps> = ({
    children,
    onThemeChange,
    themeMode,
    isDark
}) => {
    const [collapsed, setCollapsed] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const isMobile = useIsMobile();

    // На мобильных сайдбар полностью скрыт, используем Drawer
    const siderWidth = isMobile ? 0 : (collapsed ? 80 : 200);

    return (
        <Layout style={{ minHeight: '100vh' }}>
            {/* Десктоп: обычный Sidebar */}
            {!isMobile && (
                <Sidebar
                    collapsed={collapsed}
                    onCollapse={setCollapsed}
                />
            )}

            {/* Мобильный: Drawer вместо Sidebar */}
            {isMobile && (
                <Drawer
                    placement="left"
                    open={mobileMenuOpen}
                    onClose={() => setMobileMenuOpen(false)}
                    width={250}
                    styles={{
                        body: { padding: 0, background: '#001529' },
                        header: { display: 'none' }
                    }}
                >
                    <Sidebar
                        collapsed={false}
                        onCollapse={() => setMobileMenuOpen(false)}
                        isMobileDrawer
                    />
                </Drawer>
            )}

            <Layout style={{
                marginLeft: siderWidth,
                transition: 'margin-left 0.2s'
            }}>
                <HeaderBar
                    collapsed={collapsed}
                    onThemeChange={onThemeChange}
                    themeMode={themeMode}
                    isDark={isDark}
                    isMobile={isMobile}
                    onMenuClick={() => setMobileMenuOpen(true)}
                    siderWidth={siderWidth}
                />
                <Content style={{
                    margin: isMobile ? '8px' : '16px',
                    padding: isMobile ? '12px' : '16px',
                    background: 'var(--tms-bg-container)',
                    borderRadius: 8,
                    overflow: 'auto',
                    minHeight: 280,
                }}>
                    {children}
                </Content>
                <Footer style={{
                    textAlign: 'center',
                    padding: isMobile ? '8px' : '12px',
                    fontSize: isMobile ? 12 : 14,
                }}>
                    TMS ©2026 | версия 1.0
                </Footer>
            </Layout>
        </Layout>
    );
};
