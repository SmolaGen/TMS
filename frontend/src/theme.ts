import { theme } from 'antd';
import type { ThemeConfig } from 'antd';

// Основные цвета бренда TMS
const brandColors = {
    primary: '#1677ff',      // Ant Design 5 primary
    success: '#52c41a',
    warning: '#faad14',
    error: '#ff4d4f',
    info: '#1677ff',
};

// Светлая тема
export const lightTheme: ThemeConfig = {
    algorithm: theme.defaultAlgorithm,
    token: {
        colorPrimary: brandColors.primary,
        colorSuccess: brandColors.success,
        colorWarning: brandColors.warning,
        colorError: brandColors.error,
        colorInfo: brandColors.info,
        borderRadius: 8,
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        fontSize: 14,
        // Shadows
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.08)',
        boxShadowSecondary: '0 4px 16px rgba(0, 0, 0, 0.12)',
    },
    components: {
        Button: {
            borderRadius: 8,
            controlHeight: 40,
        },
        Card: {
            borderRadiusLG: 12,
        },
        Modal: {
            borderRadiusLG: 16,
        },
        Drawer: {
            borderRadiusLG: 16,
        },
        Badge: {
            dotSize: 8,
        },
    },
};

// Темная тема
export const darkTheme: ThemeConfig = {
    algorithm: theme.darkAlgorithm,
    token: {
        ...lightTheme.token,
        colorBgContainer: '#1f1f1f',
        colorBgElevated: '#262626',
        colorBgLayout: '#141414',
    },
    components: lightTheme.components,
};

export type ThemeMode = 'light' | 'dark' | 'system';

export const getThemeConfig = (mode: ThemeMode): ThemeConfig => {
    if (mode === 'dark') return darkTheme;
    if (mode === 'light') return lightTheme;

    // System preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? darkTheme : lightTheme;
};
