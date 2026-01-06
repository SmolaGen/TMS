import React, { useState } from 'react';
import { Layout } from 'antd';
import { Sidebar } from './Sidebar';
import { HeaderBar } from './HeaderBar';

const { Content, Footer } = Layout;

interface AppLayoutProps {
    children: React.ReactNode;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children }) => {
    const [collapsed, setCollapsed] = useState(false);

    return (
        <Layout style={{ minHeight: '100vh' }}>
            <Sidebar
                collapsed={collapsed}
                onCollapse={setCollapsed}
            />
            <Layout>
                <HeaderBar collapsed={collapsed} />
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
