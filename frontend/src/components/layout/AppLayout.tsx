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
    typeof window !== 'undefined' ? window.innerWidth <= breakpoint : false,
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
  isDark,
}) => {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const isMobile = useIsMobile();

  // На мобильных сайдбар полностью скрыт
  // На десктопе 260px (expanded) или 88px (collapsed) + 16px отступ слева
  const siderWidth = isMobile ? 0 : collapsed ? 104 : 276; // 88+16 or 260+16

  return (
    <Layout style={{ minHeight: '100vh', background: 'transparent' }}>
      {/* Десктоп: обычный Sidebar */}
      {!isMobile && <Sidebar collapsed={collapsed} onCollapse={setCollapsed} />}

      {/* Мобильный: Drawer вместо Sidebar */}
      {isMobile && (
        <Drawer
          placement="left"
          open={mobileMenuOpen}
          onClose={() => setMobileMenuOpen(false)}
          width={280}
          styles={{
            body: { padding: 0 },
            header: { display: 'none' },
          }}
        >
          <Sidebar collapsed={false} onCollapse={() => setMobileMenuOpen(false)} isMobileDrawer />
        </Drawer>
      )}

      <Layout
        style={{
          marginLeft: siderWidth,
          transition: 'margin-left 0.3s cubic-bezier(0.2, 0, 0, 1)',
          background: 'transparent',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <HeaderBar
          collapsed={collapsed}
          onThemeChange={onThemeChange}
          themeMode={themeMode}
          isDark={isDark}
          isMobile={isMobile}
          onMenuClick={() => setMobileMenuOpen(true)}
          siderWidth={siderWidth}
        />
        <Content
          style={{
            margin: isMobile ? '0 8px' : '0 16px 16px 16px',
            // Удаляем белый фон и паддинги, чтобы контент мог использовать glass-карточки
            background: 'transparent',
            borderRadius: 20,
            overflow: 'visible', // разрешаем теням выходить за границы
            minHeight: 280,
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          {children}
        </Content>
        <Footer
          style={{
            textAlign: 'center',
            padding: isMobile ? '8px' : '12px',
            fontSize: 12,
            color: 'var(--tms-text-tertiary)',
            background: 'transparent',
          }}
        >
          TMS ©2026 | New Face Logistics
        </Footer>
      </Layout>
    </Layout>
  );
};
