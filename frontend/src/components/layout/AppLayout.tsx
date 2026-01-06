import React, { useState } from 'react';
import { Layout } from 'antd';
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

export const AppLayout: React.FC<AppLayoutProps> = ({
    children,
    onThemeChange,
    themeMode,
    isDark
}) => {
    const [collapsed, setCollapsed] = useState(false);

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Sidebar
                collapsed={collapsed}
                onCollapse={setCollapsed}
            />
            <Layout>
                <HeaderBar
                    collapsed={collapsed}
                    onThemeChange={onThemeChange}
                    themeMode={themeMode}
                    isDark={isDark}
                />
                <Content style={{
                    margin: '16px',
                    padding: '16px',
                    background: '#fff',
                    borderRadius: 8,
                    overflow: 'auto',
                    minHeight: 280,
                }}>
                    {children}
                </Content>
                <Footer style={{ textAlign: 'center', padding: '12px' }}>
                    TMS ©2026 | версия 1.0
                </Footer>
            </Layout>
        </Layout>
    );
};
