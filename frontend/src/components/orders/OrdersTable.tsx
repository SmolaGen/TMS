import React from 'react';
import { Table, Tag, Space, Button, Tooltip, Typography } from 'antd';
import {
    EditOutlined,
    DeleteOutlined,
    UserAddOutlined,
    EnvironmentOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { OrderResponse, DriverResponse } from '../../types/api';
import dayjs from 'dayjs';

interface OrdersTableProps {
    orders: OrderResponse[];
    drivers: DriverResponse[];
    loading?: boolean;
    onSelect: (orderId: number) => void;
    onAssign?: (orderId: number) => void;
    onCancel?: (orderId: number) => void;
}

const statusConfig: Record<string, { color: string; text: string }> = {
    pending: { color: 'orange', text: 'Ожидает' },
    assigned: { color: 'blue', text: 'Назначен' },
    driver_arrived: { color: 'cyan', text: 'Прибыл' },
    in_progress: { color: 'green', text: 'В пути' },
    completed: { color: 'default', text: 'Завершен' },
    cancelled: { color: 'red', text: 'Отменен' },
};

export const OrdersTable: React.FC<OrdersTableProps> = ({
    orders,
    drivers,
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
            render: (status: string) => {
                const config = statusConfig[status] || { color: 'default', text: status };
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
            dataIndex: 'driver_id',
            key: 'driver',
            width: 180,
            render: (driverId) => {
                const driver = drivers.find(d => d.id === driverId);
                return driver ? (
                    <Typography.Text strong>{driver.name}</Typography.Text>
                ) : (
                    <Typography.Text type="secondary">Не назначен</Typography.Text>
                );
            },
        },
        {
            title: 'Начало',
            dataIndex: 'time_start',
            key: 'time_start',
            width: 100,
            render: (time) => time ? dayjs(time).format('HH:mm') : '-',
        },
        {
            title: 'Действия',
            key: 'actions',
            width: 120,
            fixed: 'right',
            render: (_, record) => (
                <Space>
                    {!record.driver_id && record.status === 'pending' && (
                        <Tooltip title="Назначить">
                            <Button
                                type="text"
                                icon={<UserAddOutlined />}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onAssign?.(record.id);
                                }}
                            />
                        </Tooltip>
                    )}
                    <Tooltip title="Детали">
                        <Button
                            type="text"
                            icon={<EditOutlined />}
                            onClick={(e) => {
                                e.stopPropagation();
                                onSelect(record.id);
                            }}
                        />
                    </Tooltip>
                    {['pending', 'assigned'].includes(record.status) && (
                        <Tooltip title="Отменить">
                            <Button
                                type="text"
                                danger
                                icon={<DeleteOutlined />}
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onCancel?.(record.id);
                                }}
                            />
                        </Tooltip>
                    )}
                </Space>
            ),
        },
    ];

    return (
        <div style={{ background: 'var(--tms-bg-container)', borderRadius: 12, overflow: 'hidden', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
            <Table
                columns={columns}
                dataSource={orders}
                rowKey="id"
                loading={loading}
                size="small"
                pagination={{
                    defaultPageSize: 10,
                    showSizeChanger: true,
                    pageSizeOptions: ['10', '20', '50'],
                    showTotal: (total) => `Всего ${total} заказов`,
                }}
                onRow={(record) => ({
                    onClick: () => onSelect(record.id),
                    style: { cursor: 'pointer' },
                })}
                rowClassName={(record) =>
                    !record.driver_id && record.status === 'pending' ? 'order-row-warning' : ''
                }
            />
        </div>
    );
};
