import React from 'react';
import { Space, Select, DatePicker, Button, Input } from 'antd';
import { SearchOutlined, ReloadOutlined } from '@ant-design/icons';
import type { Dayjs } from 'dayjs';
import { useDrivers } from '../../hooks/useDrivers';

const { RangePicker } = DatePicker;

export interface OrderFiltersState {
    status: string[];
    driverIds: number[];
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
    { value: 'pending', label: '⏳ Ожидает' },
    { value: 'assigned', label: '👤 Назначен' },
    { value: 'driver_arrived', label: '📍 Прибыл' },
    { value: 'in_progress', label: '🚕 В пути' },
    { value: 'completed', label: '✅ Завершен' },
    { value: 'cancelled', label: '❌ Отменен' },
];

const priorityOptions = [
    { value: 'high', label: '🔴 Высокий' },
    { value: 'normal', label: '🟡 Обычный' },
    { value: 'low', label: '🟢 Низкий' },
    { value: 'urgent', label: '⚡ Срочный' },
];

export const OrderFilters: React.FC<OrderFiltersProps> = ({
    filters,
    onChange,
    onReset,
}) => {
    const { data: drivers = [] } = useDrivers();

    const driverOptions = drivers.map((d) => ({
        value: d.id,
        label: d.name,
    }));

    return (
        <div className="glass-card" style={{
            padding: '16px 20px',
            marginBottom: 20,
            border: '1px solid rgba(255,255,255,0.05)',
        }}>
            <Space wrap size="middle" style={{ width: '100%', justifyContent: 'flex-start' }}>
                {/* Поиск */}
                <Input
                    placeholder="Поиск по адресу, ID..."
                    prefix={<SearchOutlined style={{ color: 'var(--tms-text-tertiary)' }} />}
                    value={filters.search}
                    onChange={(e) => onChange({ search: e.target.value })}
                    style={{
                        width: 240,
                        borderRadius: 14,
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(255,255,255,0.05)'
                    }}
                    allowClear
                />

                {/* Статус */}
                <Select
                    mode="multiple"
                    placeholder="Статус"
                    value={filters.status}
                    onChange={(value) => onChange({ status: value })}
                    options={statusOptions}
                    style={{
                        minWidth: 180,
                    }}
                    dropdownStyle={{ borderRadius: 12 }}
                    allowClear
                    maxTagCount="responsive"
                />

                {/* Водитель */}
                <Select
                    mode="multiple"
                    placeholder="Водитель"
                    value={filters.driverIds}
                    onChange={(value) => onChange({ driverIds: value })}
                    options={driverOptions}
                    style={{
                        minWidth: 180,
                    }}
                    dropdownStyle={{ borderRadius: 12 }}
                    allowClear
                    maxTagCount="responsive"
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
                    style={{
                        borderRadius: 14,
                        background: 'rgba(255,255,255,0.03)',
                        border: '1px solid rgba(255,255,255,0.05)'
                    }}
                />

                {/* Приоритет */}
                <Select
                    mode="multiple"
                    placeholder="Приоритет"
                    value={filters.priority}
                    onChange={(value) => onChange({ priority: value })}
                    options={priorityOptions}
                    style={{
                        minWidth: 150,
                    }}
                    dropdownStyle={{ borderRadius: 12 }}
                    allowClear
                />

                {/* Сброс */}
                <Button
                    icon={<ReloadOutlined />}
                    onClick={onReset}
                    style={{ borderRadius: 12 }}
                >
                    Сбросить
                </Button>
            </Space>
        </div>
    );
};
