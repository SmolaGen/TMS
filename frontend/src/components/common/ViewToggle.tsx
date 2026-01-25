import React from 'react';
import { Segmented } from 'antd';
import { AppstoreOutlined, UnorderedListOutlined, EnvironmentOutlined } from '@ant-design/icons';

export type ViewMode = 'map-timeline' | 'table-map' | 'table-only';

interface ViewToggleProps {
  value: ViewMode;
  onChange: (mode: ViewMode) => void;
}

export const ViewToggle: React.FC<ViewToggleProps> = ({ value, onChange }) => {
  const options = [
    {
      value: 'map-timeline',
      icon: <EnvironmentOutlined />,
      label: 'Карта + Таймлайн',
    },
    {
      value: 'table-map',
      icon: <AppstoreOutlined />,
      label: 'Таблица + Карта',
    },
    {
      value: 'table-only',
      icon: <UnorderedListOutlined />,
      label: 'Только таблица',
    },
  ];

  return (
    <Segmented
      value={value}
      onChange={(val) => onChange(val as ViewMode)}
      options={options}
      style={{ marginBottom: 16 }}
    />
  );
};
