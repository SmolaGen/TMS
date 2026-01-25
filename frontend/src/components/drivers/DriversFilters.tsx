import React from 'react';
import { Space, Select, Input, Button, Switch, Typography } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import { DriverStatus } from '../../types/api';

const { Text } = Typography;

export interface DriversFiltersState {
  status: DriverStatus[];
  search: string;
  isActive: boolean | null;
}

interface DriversFiltersProps {
  filters: DriversFiltersState;
  onChange: (filters: Partial<DriversFiltersState>) => void;
  onReset: () => void;
}

const statusOptions = [
  { value: DriverStatus.AVAILABLE, label: '🟢 Доступен' },
  { value: DriverStatus.BUSY, label: '🟡 Занят' },
  { value: DriverStatus.OFFLINE, label: '⚫ Оффлайн' },
];

export const DriversFilters: React.FC<DriversFiltersProps> = ({ filters, onChange, onReset }) => {
  return (
    <div
      className="glass-card"
      style={{
        padding: '12px 16px',
      }}
    >
      <Space wrap size="middle">
        {/* Поиск */}
        <Input
          placeholder="Поиск по имени, телефону..."
          prefix={<SearchOutlined />}
          value={filters.search}
          onChange={(e) => onChange({ search: e.target.value })}
          style={{ width: 220 }}
          allowClear
        />

        {/* Статус */}
        <Select
          mode="multiple"
          placeholder="Статус"
          value={filters.status}
          onChange={(value) => onChange({ status: value })}
          options={statusOptions}
          style={{ minWidth: 180 }}
          allowClear
          maxTagCount={2}
        />

        {/* Активность */}
        <Space>
          <Text type="secondary">Только активные:</Text>
          <Switch
            checked={filters.isActive === true}
            onChange={(checked) =>
              onChange({
                isActive: checked ? true : null,
              })
            }
          />
        </Space>

        {/* Сброс */}
        <Button icon={<ReloadOutlined />} onClick={onReset}>
          Сбросить
        </Button>
      </Space>
    </div>
  );
};
