import React, { useEffect } from 'react';
import { Layout, Card, Button, Typography, Space, Badge, Tag } from 'antd';
import {
    EnvironmentOutlined,
    SyncOutlined,
    CheckCircleOutlined,
    ClockCircleOutlined,
    CarOutlined
} from '@ant-design/icons';
import { useTelegramAuth } from '../hooks/useTelegramAuth';
import { useGeoTracking } from '../hooks/useGeoTracking';
import { useOrdersRaw } from '../hooks/useOrders';

const { Header, Content } = Layout;
const { Title, Text } = Typography;

export const DriverApp: React.FC = () => {
    const { user } = useTelegramAuth();
    const { latitude, longitude, error, isTracking, startTracking, stopTracking } = useGeoTracking(user?.id);
    const { data: orders = [] } = useOrdersRaw();

    // Фильтруем заказы для текущего водителя по внутреннему ID (не Telegram ID!)
    const myOrders = orders.filter(o => o.driver_id === user?.driver_id);

    useEffect(() => {
        // Автоматически запускаем трекинг при входе
        if (!isTracking) {
            startTracking();
        }
    }, [isTracking, startTracking]);

    return (
        <Layout style={{ minHeight: '100vh', background: '#f0f2f5' }}>
            <Header style={{
                background: '#fff',
                padding: '0 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <CarOutlined style={{ fontSize: '20px', color: '#1890ff' }} />
                    <Title level={4} style={{ margin: 0 }}>Driver App</Title>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Badge status={isTracking ? 'success' : 'default'} text={isTracking ? 'Online' : 'Offline'} />
                </div>
            </Header>

            <Content style={{ padding: '20px' }}>
                <Space orientation="vertical" size="large" style={{ width: '100%' }}>
                    {/* Статус GPS */}
                    <Card size="small" style={{ borderRadius: '12px' }}>
                        <Space align="center">
                            <EnvironmentOutlined style={{ fontSize: '24px', color: isTracking ? '#52c41a' : '#bfbfbf' }} />
                            <div>
                                <Text strong style={{ display: 'block' }}>{isTracking ? 'Геолокация активна' : 'Геолокация выключена'}</Text>
                                <Text type="secondary" style={{ fontSize: '12px' }}>
                                    {latitude && longitude
                                        ? `${latitude.toFixed(4)}, ${longitude.toFixed(4)}`
                                        : error || 'Ожидание координат...'}
                                </Text>
                            </div>
                        </Space>
                    </Card>

                    {/* Кнопка смены */}
                    <Button
                        type={isTracking ? 'default' : 'primary'}
                        danger={isTracking}
                        icon={isTracking ? <SyncOutlined spin={isTracking} /> : <CheckCircleOutlined />}
                        size="large"
                        block
                        style={{ height: '50px', borderRadius: '12px', fontWeight: 'bold' }}
                        onClick={isTracking ? stopTracking : startTracking}
                    >
                        {isTracking ? 'Завершить смену' : 'Начать смену'}
                    </Button>

                    {/* Список заказов */}
                    <Title level={5}>Мои заказы ({myOrders.length})</Title>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                        {myOrders.length === 0 ? (
                            <div style={{ textAlign: 'center', padding: '24px', color: '#8c8c8c' }}>
                                Нет назначенных заказов
                            </div>
                        ) : (
                            myOrders.map((order) => (
                                <Card
                                    key={order.id}
                                    size="small"
                                    style={{ width: '100%', borderRadius: '12px' }}
                                    hoverable
                                >
                                    <Space orientation="vertical" style={{ width: '100%' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                            <Text strong>Заказ #{order.id}</Text>
                                            <Tag color={
                                                order.status === 'completed' ? 'green' :
                                                    order.status === 'in_progress' ? 'blue' : 'orange'
                                            }>
                                                {order.status.toUpperCase()}
                                            </Tag>
                                        </div>
                                        <Space size="small">
                                            <ClockCircleOutlined />
                                            <Text type="secondary">
                                                {order.time_start ? new Date(order.time_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--'}
                                            </Text>
                                        </Space>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                                            <Text style={{ fontSize: '13px' }}>
                                                <Badge status="processing" color="blue" /> {order.pickup_address || 'Не указан'}
                                            </Text>
                                            <Text style={{ fontSize: '13px' }}>
                                                <Badge status="success" color="green" /> {order.dropoff_address || 'Не указан'}
                                            </Text>
                                        </div>
                                    </Space>
                                </Card>
                            ))
                        )}
                    </div>
                </Space>
            </Content>
        </Layout>
    );
};
