import React, { useState } from 'react';
import { Layout, Badge, Button, message, Card, Space } from 'antd';
import { PlusOutlined, CarOutlined, ReloadOutlined } from '@ant-design/icons';
import { LiveMap } from './LiveMap';
import { TimelineView } from './TimelineView';
import { useWebSocketSync } from '../../hooks/useWebSocketSync';
import type { TimelineDriver, TimelineOrder } from '../../types/api';

const { Content } = Layout;

// Владивосток - координаты ключевых точек
const VLADIVOSTOK_LOCATIONS = [
    { name: 'ЖД Вокзал', lat: 43.1155, lng: 131.8855 },
    { name: 'Покровский парк', lat: 43.1134, lng: 131.8903 },
    { name: 'Золотой мост', lat: 43.1067, lng: 131.8954 },
    { name: 'ДВФУ', lat: 43.0227, lng: 131.8957 },
    { name: 'Аэропорт', lat: 43.3961, lng: 132.1481 },
    { name: 'Фокино', lat: 42.9627, lng: 132.4011 },
    { name: 'Артём', lat: 43.3536, lng: 132.1886 },
    { name: 'Уссурийск', lat: 43.8029, lng: 131.9452 },
];

// Временные данные для демонстрации
const mockDrivers: TimelineDriver[] = [
    { id: '1', content: 'Иванов И.И.' },
    { id: '2', content: 'Петров П.П.' },
    { id: '3', content: 'Сидоров С.С.' },
    { id: 'unassigned', content: 'Не назначен' },
];

export const Dashboard: React.FC = () => {
    const { isConnected } = useWebSocketSync();
    const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
    const [orders, setOrders] = useState<TimelineOrder[]>([]);
    const [orderCounter, setOrderCounter] = useState(1);
    const [isCreating, setIsCreating] = useState(false);

    // Создание демо-заказа
    const createDemoOrder = async () => {
        setIsCreating(true);

        // Случайные точки А и Б
        const from = VLADIVOSTOK_LOCATIONS[Math.floor(Math.random() * VLADIVOSTOK_LOCATIONS.length)];
        let to = VLADIVOSTOK_LOCATIONS[Math.floor(Math.random() * VLADIVOSTOK_LOCATIONS.length)];
        while (to.name === from.name) {
            to = VLADIVOSTOK_LOCATIONS[Math.floor(Math.random() * VLADIVOSTOK_LOCATIONS.length)];
        }

        // Случайный водитель (1-3)
        const driverId = String(Math.floor(Math.random() * 3) + 1);

        // Время заказа - от текущего момента до +3 часов
        const now = new Date();
        const startOffset = Math.floor(Math.random() * 60); // 0-60 минут от сейчас
        const duration = 30 + Math.floor(Math.random() * 90); // 30-120 минут

        const start = new Date(now.getTime() + startOffset * 60000);
        const end = new Date(start.getTime() + duration * 60000);

        const newOrder: TimelineOrder = {
            id: `order-${orderCounter}`,
            group: driverId,
            content: `#${orderCounter}: ${from.name} → ${to.name}`,
            start: start,
            end: end,
            className: ['order-pending', 'order-high', 'order-normal'][Math.floor(Math.random() * 3)],
        };

        setOrders(prev => [...prev, newOrder]);
        setOrderCounter(prev => prev + 1);

        message.success(`Заказ #${orderCounter} создан: ${from.name} → ${to.name}`);
        setIsCreating(false);
    };

    // Создать 5 заказов сразу
    const createBatchOrders = async () => {
        for (let i = 0; i < 5; i++) {
            await new Promise(resolve => setTimeout(resolve, 300));
            await createDemoOrder();
        }
    };

    // Очистить все заказы
    const clearOrders = () => {
        setOrders([]);
        setOrderCounter(1);
        message.info('Заказы очищены');
    };

    return (
        <Layout style={{ height: '100vh', background: '#f5f5f5' }}>
            {/* Статус подключения */}
            <div style={{
                position: 'fixed',
                top: 16,
                left: 16,
                zIndex: 1000,
                background: 'white',
                padding: '8px 16px',
                borderRadius: 8,
                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            }}>
                <Badge
                    status={isConnected ? 'success' : 'processing'}
                    text={isConnected ? 'Online' : 'Подключение...'}
                />
            </div>

            {/* Демо-панель */}
            <Card
                size="small"
                style={{
                    position: 'fixed',
                    top: 16,
                    right: 16,
                    zIndex: 1000,
                    width: 280,
                    boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                }}
                title={
                    <span style={{ fontSize: 14 }}>
                        🚗 TMS Demo — Владивосток
                    </span>
                }
            >
                <Space direction="vertical" style={{ width: '100%' }} size="small">
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={createDemoOrder}
                        loading={isCreating}
                        block
                    >
                        Новый заказ
                    </Button>
                    <Button
                        icon={<CarOutlined />}
                        onClick={createBatchOrders}
                        block
                    >
                        +5 заказов сразу
                    </Button>
                    <Button
                        icon={<ReloadOutlined />}
                        onClick={clearOrders}
                        danger
                        block
                    >
                        Очистить всё
                    </Button>
                    <div style={{
                        marginTop: 8,
                        padding: 8,
                        background: '#f5f5f5',
                        borderRadius: 4,
                        fontSize: 12,
                        color: '#666'
                    }}>
                        <strong>Заказов:</strong> {orders.length}<br />
                        <strong>Водителей:</strong> 3 активных
                    </div>
                </Space>
            </Card>

            {selectedOrderId && (
                <div style={{
                    position: 'fixed',
                    bottom: 50,
                    left: 16,
                    zIndex: 1000,
                    background: 'white',
                    padding: '8px 16px',
                    borderRadius: 8,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                }}>
                    Выбран заказ: #{selectedOrderId}
                </div>
            )}

            <Content style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                {/* Карта - 60% высоты */}
                <div style={{ flex: '0 0 60%', position: 'relative' }}>
                    <LiveMap onDriverSelect={(id) => console.log('Selected driver:', id)} />
                </div>

                {/* Таймлайн - 40% высоты */}
                <div style={{
                    flex: '0 0 40%',
                    borderTop: '2px solid #e8e8e8',
                    overflow: 'hidden',
                }}>
                    <TimelineView
                        drivers={mockDrivers}
                        orders={orders}
                        onOrderSelect={setSelectedOrderId}
                    />
                </div>
            </Content>
        </Layout>
    );
};
