import React from 'react';
import { Table, Tag, Space, Button, Tooltip, Typography } from 'antd';
import {
    EditOutlined,
    DeleteOutlined,
    UserAddOutlined,
    EnvironmentOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { OrderResponse } from '../../types/api';
import dayjs from 'dayjs';

interface OrdersTableProps {
    orders: OrderResponse[];
    loading?: boolean;
    onSelect: (orderId: string) => void;
    onAssign?: (orderId: string) => void;
    onCancel?: (orderId: string) => void;
}

const statusConfig: Record<string, { color: string; text: string }> = {
    pending: { color: 'warning', text: 'Ожидает' },
    assigned: { color: 'processing', text: 'Назначен' },
    driver_arrived: { color: 'processing', text: 'Прибыл' },
    in_progress: { color: 'success', text: 'В пути' },
    completed: { color: 'default', text: 'Завершён' },
    cancelled: { color: 'error', text: 'Отменён' },
};

const priorityConfig: Record<string, { color: string; text: string }> = {
    urgent: { color: 'red', text: 'Срочный' },
    high: { color: 'orange', text: 'Высокий' },
    normal: { color: 'blue', text: 'Обычный' },
    low: { color: 'green', text: 'Низкий' },
};

export const OrdersTable: React.FC<OrdersTableProps> = ({
    orders,
    loading,
    onSelect,
    onAssign,
    onCancel,
}) => {
    const columns: ColumnsType<OrderResponse> = [
        {
            title: 'ID',
            dataIndex: 'id',
            key: 'id',
            width: 80,
            sorter: (a, b) => a.id - b.id,
            render: (id) => <Typography.Text code>#{id}</Typography.Text>,
        },
        {
            title: 'Статус',
            dataIndex: 'status',
            key: 'status',
            width: 120,
            filters: Object.entries(statusConfig).map(([value, { text }]) => ({
                text,
                value,
            })),
            onFilter: (value, record) => record.status === value,
            render: (status: string) => {
                const config = statusConfig[status] || { color: 'default', text: status };
                return <Tag color={config.color}>{config.text}</Tag>;
            },
        },
        {
            title: 'Приоритет',
            dataIndex: 'priority',
            key: 'priority',
            width: 100,
            render: (priority: string) => {
                const config = priorityConfig[priority] || { color: 'default', text: priority };
                return <Tag color={config.color}>{config.text}</Tag>;
            },
        },
        {
            title: 'Откуда',
            dataIndex: 'pickup_address',
            key: 'pickup',
            ellipsis: true,
            render: (address) => (
                <Tooltip title={address}>
                    <Space>
                        <EnvironmentOutlined style={{ color: '#52c41a' }} />
                        <span>{address}</span>
                    </Space>
                </Tooltip>
            ),
        },
        {
            title: 'Куда',
            dataIndex: 'dropoff_address',
            key: 'dropoff',
            ellipsis: true,
            render: (address) => (
                <Tooltip title={address}>
                    <Space>
                        <EnvironmentOutlined style={{ color: '#ff4d4f' }} />
                        <span>{address}</span>
                    </Space>
                </Tooltip>
            ),
        },
        {
            title: 'Водитель',
            dataIndex: 'driver_name',
            key: 'driver',
            width: 150,
            render: (name, record) =>
                name || (
                    <Button
                        type="link"
                        size="small"
                        icon={<UserAddOutlined />}
                        onClick={(e) => {
                            e.stopPropagation();
                            onAssign?.(String(record.id));
                        }}
                    >
                        Назначить
                    </Button>
                ),
        },
        {
            title: 'Время',
            dataIndex: 'time_start',
            key: 'time',
            width: 100,
            sorter: (a, b) => {
                const timeA = a.time_start ? dayjs(a.time_start).unix() : 0;
                const timeB = b.time_start ? dayjs(b.time_start).unix() : 0;
                return timeA - timeB;
            },
            render: (time) => time ? dayjs(time).format('HH:mm') : '-',
        },
        {
            title: 'Действия',
            key: 'actions',
            width: 100,
            fixed: 'right',
            render: (_, record) => (
                <Space>
                    <Tooltip title="Редактировать">
                        <Button
                            type="text"
                            icon={<EditOutlined />}
                            onClick={(e) => {
                                e.stopPropagation();
                                onSelect(String(record.id));
                            }}
                        />
                    </Tooltip>
                    {record.status !== 'cancelled' && record.status !== 'completed' && (
                        <Tooltip title="Отменить">
                            <Button
                                type="text"
                                danger
                                icon={<DeleteOutlined />}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onCancel?.(String(record.id));
                                }}
                            />
                        </Tooltip>
                    )}
                </Space>
            ),
        },
    ];

    return (
        <Table
            columns={columns}
            dataSource={orders}
            rowKey="id"
            loading={loading}
            size="small"
            pagination={{
                defaultPageSize: 20,
                showSizeChanger: true,
                showTotal: (total) => `Всего: ${total} заказов`,
            }}
            scroll={{ x: 1000 }}
            onRow={(record) => ({
                onClick: () => onSelect(String(record.id)),
                style: { cursor: 'pointer' },
            })}
            rowClassName={(record) =>
                record.status === 'pending' && !record.driver_id
                    ? 'order-row-warning'
                    : ''
            }
        />
    );
};
