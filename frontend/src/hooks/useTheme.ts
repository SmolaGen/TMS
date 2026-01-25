import { useState, useEffect, useCallback } from 'react';
import { getThemeConfig } from '../theme';
import type { ThemeMode } from '../theme';

const THEME_STORAGE_KEY = 'tms-theme-mode';

export const useTheme = () => {
  const [mode, setMode] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem(THEME_STORAGE_KEY);
    return (saved as ThemeMode) || 'system';
  });

  const themeConfig = getThemeConfig(mode);
  const isDark =
    mode === 'dark' ||
    (mode === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);

  // Сохранение в localStorage
  useEffect(() => {
    localStorage.setItem(THEME_STORAGE_KEY, mode);
  }, [mode]);

  // Слушаем изменения системной темы
  useEffect(() => {
    if (mode !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => setMode('system'); // Триггерим ререндер

    mediaQuery.addEventListener('change', handler);
    return () => mediaQuery.removeEventListener('change', handler);
  }, [mode]);

  // Применение CSS-класса к body
  useEffect(() => {
    document.body.classList.toggle('dark-theme', isDark);
  }, [isDark]);

  const toggleTheme = useCallback(() => {
    setMode((prev) => (prev === 'light' ? 'dark' : 'light'));
  }, []);

  return {
    mode,
    setMode,
    themeConfig,
    isDark,
    toggleTheme,
  };
};
