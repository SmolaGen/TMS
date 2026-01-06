import React from 'react';
import { Space, Select, DatePicker, Button, Input } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import { useDrivers } from '../../hooks/useDrivers';

const { RangePicker } = DatePicker;

export interface OrderFiltersState {
    status: string[];
    driverIds: (number | string)[];
    dateRange: [Dayjs | null, Dayjs | null] | null;
    search: string;
    priority: string[];
}

interface OrderFiltersProps {
    filters: OrderFiltersState;
    onChange: (filters: Partial<OrderFiltersState>) => void;
    onReset: () => void;
}

const statusOptions = [
    { value: 'pending', label: '⏳ Ожидает', color: '#faad14' },
    { value: 'assigned', label: '✓ Назначен', color: '#1890ff' },
    { value: 'driver_arrived', label: '📍 Прибыл', color: '#1890ff' },
    { value: 'in_progress', label: '🚗 В пути', color: '#52c41a' },
    { value: 'completed', label: '✅ Завершён', color: '#52c41a' },
    { value: 'cancelled', label: '❌ Отменён', color: '#ff4d4f' },
];

const priorityOptions = [
    { value: 'urgent', label: '🔥 Срочный' },
    { value: 'high', label: '🔴 Высокий' },
    { value: 'normal', label: '🟡 Обычный' },
    { value: 'low', label: '🟢 Низкий' },
];

export const OrderFilters: React.FC<OrderFiltersProps> = ({
    filters,
    onChange,
    onReset,
}) => {
    const { data: drivers = [] } = useDrivers();

    const driverOptions = drivers.map((d) => ({
        value: d.id === 'unassigned' ? 'unassigned' : Number(d.id),
        label: d.name || d.content,
    }));

    return (
        <div style={{
            padding: '12px 16px',
            background: '#fafafa',
            borderRadius: 8,
            marginBottom: 16,
        }}>
            <Space wrap size="middle">
                {/* Поиск */}
                <Input
                    placeholder="Поиск по адресу, ID..."
                    prefix={<SearchOutlined />}
                    value={filters.search}
                    onChange={(e) => onChange({ search: e.target.value })}
                    style={{ width: 200 }}
                    allowClear
                />

                {/* Статус */}
                <Select
                    mode="multiple"
                    placeholder="Статус"
                    value={filters.status}
                    onChange={(value) => onChange({ status: value })}
                    options={statusOptions}
                    style={{ minWidth: 200 }}
                    allowClear
                    maxTagCount={2}
                />

                {/* Водитель */}
                <Select
                    mode="multiple"
                    placeholder="Водитель"
                    value={filters.driverIds}
                    onChange={(value) => onChange({ driverIds: value })}
                    options={driverOptions}
                    style={{ minWidth: 180 }}
                    allowClear
                    maxTagCount={1}
                    showSearch
                    filterOption={(input, option) =>
                        (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                />

                {/* Период */}
                <RangePicker
                    value={filters.dateRange}
                    onChange={(dates) => onChange({ dateRange: dates as any })}
                    format="DD.MM.YYYY"
                />

                {/* Приоритет */}
                <Select
                    mode="multiple"
                    placeholder="Приоритет"
                    value={filters.priority}
                    onChange={(value) => onChange({ priority: value })}
                    options={priorityOptions}
                    style={{ minWidth: 150 }}
                    allowClear
                />

                {/* Сброс */}
                <Button
                    icon={<ReloadOutlined />}
                    onClick={onReset}
                >
                    Сбросить
                </Button>
            </Space>
        </div>
    );
};
