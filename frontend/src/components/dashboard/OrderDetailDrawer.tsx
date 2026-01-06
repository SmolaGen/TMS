import React from 'react';
import { Drawer, Descriptions, Tag, Button, Space, Timeline, Typography, Popconfirm, Select, Divider } from 'antd';
import {
    ClockCircleOutlined,
    UserOutlined,
    EnvironmentOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    PlayCircleOutlined,
} from '@ant-design/icons';
import { useOrder, useUpdateOrderStatus } from '../../hooks/useOrders';
import type { OrderAction } from '../../hooks/useOrders';
import { useDrivers } from '../../hooks/useDrivers';
import dayjs from 'dayjs';
import { OrderStatus, OrderPriority } from '../../types/api';

const { Text, Title } = Typography;

interface OrderDetailDrawerProps {
    orderId: string | number | null;
    visible: boolean;
    onClose: () => void;
}

const statusColors: Record<string, string> = {
    [OrderStatus.PENDING]: 'default',
    [OrderStatus.ASSIGNED]: 'blue',
    [OrderStatus.DRIVER_ARRIVED]: 'cyan',
    [OrderStatus.IN_PROGRESS]: 'processing',
    [OrderStatus.COMPLETED]: 'success',
    [OrderStatus.CANCELLED]: 'error',
};

const priorityColors: Record<string, string> = {
    [OrderPriority.LOW]: 'blue',
    [OrderPriority.NORMAL]: 'gold',
    [OrderPriority.HIGH]: 'red',
};

export const OrderDetailDrawer: React.FC<OrderDetailDrawerProps> = ({ orderId, visible, onClose }) => {
    const { data: order, isLoading } = useOrder(orderId || undefined);
    const { mutate: updateStatus, isPending: isUpdating } = useUpdateOrderStatus();
    const { data: drivers = [] } = useDrivers();

    if (!order && !isLoading) return null;

    const handleAction = (action: OrderAction, params: { reason?: string, driverId?: number } = {}) => {
        if (!orderId) return;
        updateStatus({ orderId, action, ...params });
    };

    const renderActions = () => {
        if (!order) return null;

        const actions: React.ReactNode[] = [];

        if (order.status === OrderStatus.PENDING) {
            actions.push(
                <div key="assign-group" style={{ width: '100%', marginTop: 16 }}>
                    <Text type="secondary" style={{ marginBottom: 8, display: 'block' }}>Назначить водителя:</Text>
                    <Select
                        placeholder="Выберите водителя"
                        style={{ width: '100%' }}
                        onChange={(value) => handleAction('assign', { driverId: value })}
                        disabled={isUpdating}
                    >
                        {drivers.map(d => (
                            <Select.Option key={d.id} value={d.id}>{d.name}</Select.Option>
                        ))}
                    </Select>
                </div>
            );
        }

        if (order.status === OrderStatus.ASSIGNED) {
            actions.push(
                <Button
                    key="arrive"
                    type="primary"
                    icon={<CheckCircleOutlined />}
                    onClick={() => handleAction('arrive')}
                    loading={isUpdating}
                    block
                >
                    Водитель прибыл
                </Button>
            );
        }

        if (order.status === OrderStatus.DRIVER_ARRIVED) {
            actions.push(
                <Button
                    key="start"
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={() => handleAction('start')}
                    loading={isUpdating}
                    block
                >
                    Начать поездку
                </Button>
            );
        }

        if (order.status === OrderStatus.IN_PROGRESS) {
            actions.push(
                <Button
                    key="complete"
                    type="primary"
                    icon={<CheckCircleOutlined />}
                    onClick={() => handleAction('complete')}
                    loading={isUpdating}
                    block
                >
                    Завершить заказ
                </Button>
            );
        }

        if (![OrderStatus.COMPLETED, OrderStatus.CANCELLED].includes(order.status as OrderStatus)) {
            actions.push(
                <Popconfirm
                    key="cancel-confirm"
                    title="Отменить заказ?"
                    description="Это действие нельзя будет отменить."
                    onConfirm={() => handleAction('cancel')}
                    okText="Да"
                    cancelText="Нет"
                >
                    <Button
                        danger
                        icon={<CloseCircleOutlined />}
                        loading={isUpdating}
                        block
                        style={{ marginTop: 8 }}
                    >
                        Отменить заказ
                    </Button>
                </Popconfirm>
            );
        }

        return <Space orientation="vertical" style={{ width: '100%' }}>{actions}</Space>;
    };

    return (
        <Drawer
            title={order ? `Заказ #${order.id}` : 'Детали заказа'}
            placement="right"
            width={400}
            onClose={onClose}
            open={visible}
            loading={isLoading}
        >
            {order && (
                <>
                    <div style={{ marginBottom: 24 }}>
                        <Space align="center">
                            <Tag color={statusColors[order.status]}>
                                {order.status.toUpperCase()}
                            </Tag>
                            <Tag color={priorityColors[order.priority]}>
                                {order.priority.toUpperCase()}
                            </Tag>
                        </Space>
                    </div>

                    <Descriptions title="Информация" column={1} layout="vertical" bordered size="small">
                        <Descriptions.Item label={<><EnvironmentOutlined /> Откуда</>}>
                            <Text strong>{order.pickup_address || `${order.pickup_lat}, ${order.pickup_lon}`}</Text>
                        </Descriptions.Item>
                        <Descriptions.Item label={<><EnvironmentOutlined /> Куда</>}>
                            <Text strong>{order.dropoff_address || `${order.dropoff_lat}, ${order.dropoff_lon}`}</Text>
                        </Descriptions.Item>
                        <Descriptions.Item label={<><ClockCircleOutlined /> Время</>}>
                            {dayjs(order.time_start).format('DD.MM HH:mm')} — {dayjs(order.time_end).format('HH:mm')}
                        </Descriptions.Item>
                        <Descriptions.Item label={<><UserOutlined /> Водитель</>}>
                            {order.driver_id ? `Водитель #${order.driver_id}` : <Text type="danger">Не назначен</Text>}
                        </Descriptions.Item>
                        {order.price && (
                            <Descriptions.Item label="Стоимость">
                                <Text strong>{order.price} ₽</Text>
                            </Descriptions.Item>
                        )}
                    </Descriptions>

                    <Divider />

                    <Title level={5}>Управление</Title>
                    {renderActions()}

                    <Divider />

                    <Title level={5}>История</Title>
                    <Timeline
                        items={[
                            {
                                children: `Заказ создан: ${dayjs(order.created_at).format('HH:mm:ss')}`,
                                color: 'green',
                            },
                            order.arrived_at && {
                                children: `Водитель прибыл: ${dayjs(order.arrived_at).format('HH:mm:ss')}`,
                                color: 'cyan',
                            },
                            order.started_at && {
                                children: `Поездка началась: ${dayjs(order.started_at).format('HH:mm:ss')}`,
                                color: 'orange',
                            },
                            order.end_time && order.status === OrderStatus.COMPLETED && {
                                children: `Завершён: ${dayjs(order.end_time).format('HH:mm:ss')}`,
                                color: 'success',
                            },
                            order.cancelled_at && {
                                children: `Отменён: ${dayjs(order.cancelled_at).format('HH:mm:ss')}`,
                                color: 'red',
                            },
                        ].filter(Boolean) as any[]}
                    />
                </>
            )}
        </Drawer>
    );
};
