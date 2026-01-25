import { theme } from 'antd';
import type { ThemeConfig } from 'antd';

// Основные цвета бренда TMS
const brandColors = {
  primary: '#3b82f6', // Более насыщенный современный синий
  success: '#10b981', // Emerald 500
  warning: '#f59e0b', // Amber 500
  error: '#ef4444', // Red 500
  info: '#3b82f6',
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
    borderRadius: 12, // Увеличено для более мягкого вида
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    fontSize: 14,
    // Shadows
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
    boxShadowSecondary: '0 8px 24px rgba(0, 0, 0, 0.08)',
  },
  components: {
    Button: {
      borderRadius: 10,
      controlHeight: 40,
      fontWeight: 500,
    },
    Card: {
      borderRadiusLG: 16,
    },
    Modal: {
      borderRadiusLG: 20,
    },
    Drawer: {
      borderRadiusLG: 20,
    },
    Badge: {
      dotSize: 8,
    },
    Table: {
      borderRadius: 12,
    },
  },
};

// Темная тема
export const darkTheme: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    ...lightTheme.token,
    colorBgLayout: '#0a0f18', // Глубокий сине-черный
    colorBgContainer: '#111827', // Графитовый
    colorBgElevated: '#1f2937', // Для модалок и выпадающих меню
    colorBorder: 'rgba(255, 255, 255, 0.08)',
    colorBorderSecondary: 'rgba(255, 255, 255, 0.04)',
  },
  components: {
    ...lightTheme.components,
    Table: {
      ...lightTheme.components?.Table,
      headerBg: 'rgba(255, 255, 255, 0.02)',
    },
  },
};

export type ThemeMode = 'light' | 'dark' | 'system';

export const getThemeConfig = (mode: ThemeMode): ThemeConfig => {
  if (mode === 'dark') return darkTheme;
  if (mode === 'light') return lightTheme;

  // System preference
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
  return prefersDark ? darkTheme : lightTheme;
};
