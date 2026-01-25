import React from 'react';
import { Button, Tooltip, Dropdown } from 'antd';
import { SunOutlined, MoonOutlined, DesktopOutlined } from '@ant-design/icons';
import type { MenuProps } from 'antd';
import type { ThemeMode } from '../../theme';

interface ThemeToggleProps {
  mode: ThemeMode;
  onModeChange: (mode: ThemeMode) => void;
  isDark: boolean;
  showDropdown?: boolean;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({
  mode,
  onModeChange,
  isDark,
  showDropdown = false,
}) => {
  const icon = isDark ? <MoonOutlined /> : <SunOutlined />;

  if (!showDropdown) {
    return (
      <Tooltip title={`Переключить тему (текущая: ${isDark ? 'темная' : 'светлая'})`}>
        <Button type="text" icon={icon} onClick={() => onModeChange(isDark ? 'light' : 'dark')} />
      </Tooltip>
    );
  }

  const items: MenuProps['items'] = [
    {
      key: 'light',
      icon: <SunOutlined />,
      label: 'Светлая',
      onClick: () => onModeChange('light'),
    },
    {
      key: 'dark',
      icon: <MoonOutlined />,
      label: 'Темная',
      onClick: () => onModeChange('dark'),
    },
    {
      key: 'system',
      icon: <DesktopOutlined />,
      label: 'Системная',
      onClick: () => onModeChange('system'),
    },
  ];

  return (
    <Dropdown menu={{ items, selectedKeys: [mode] }} placement="bottomRight">
      <Button type="text" icon={icon} />
    </Dropdown>
  );
};
