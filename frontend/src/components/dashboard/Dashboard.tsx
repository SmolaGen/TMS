import React, { useState, useMemo } from 'react';
import { Space, Button } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { LiveMap } from './LiveMap';
import { TimelineView } from './TimelineView';
import { CreateOrderModal } from './CreateOrderModal';
import { OrderDetailDrawer } from './OrderDetailDrawer';
import { useWebSocketSync } from '../../hooks/useWebSocketSync';
import { useDrivers } from '../../hooks/useDrivers';
import { useCreateOrder, useOrdersRaw } from '../../hooks/useOrders';
import { KPIWidgets } from './KPIWidgets';
import type { TimelineDriver } from '../../types/api';

export const Dashboard: React.FC = () => {
    const { isConnected } = useWebSocketSync();
    const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);
    const [selectedDriverId, setSelectedDriverId] = useState<number | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);

    // Реальные данные через хуки
    const { data: drivers = [] } = useDrivers();
    const { mutate: createOrder, isPending: isCreating } = useCreateOrder();
    const { data: orders = [] } = useOrdersRaw();

    // Преобразование водителей для Timeline
    const timelineDrivers: TimelineDriver[] = useMemo(() => {
        const transformed: TimelineDriver[] = drivers.map(d => ({
            id: String(d.id),
            content: d.name || 'Безымянный',
        }));

        return [
            { id: 'unassigned', content: '❌ Не назначено' },
            ...transformed
        ];
    }, [drivers]);

    const handleCreateOrder = (values: any) => {
        createOrder(values, {
            onSuccess: () => {
                setIsModalOpen(false);
            },
        });
    };

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#f0f2f5', position: 'relative' }}>
            {/* KPI Панель */}
            <div style={{ padding: '16px 16px 0' }}>
                <KPIWidgets />
            </div>

            {/* Статус подключения и кнопка */}
            <div style={{
                position: 'absolute',
                top: 100, // Смещаем ниже из-за KPI
                right: 32,
                zIndex: 1000,
                display: 'flex',
                flexDirection: 'column',
                gap: 12,
                alignItems: 'flex-end',
            }}>
                <Space
                    style={{
                        background: 'rgba(255, 255, 255, 0.9)',
                        padding: '4px 12px',
                        borderRadius: 20,
                        boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                        fontSize: 12,
                        fontWeight: 500
                    }}
                >
                    <span style={{
                        display: 'inline-block',
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        backgroundColor: isConnected ? '#52c41a' : '#faad14',
                    }} />
                    {isConnected ? 'Online' : 'Подключение...'}
                </Space>
                <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    size="large"
                    shape="round"
                    onClick={() => setIsModalOpen(true)}
                    style={{
                        boxShadow: '0 4px 12px rgba(24, 144, 255, 0.35)',
                        height: 48,
                        padding: '0 24px',
                        fontSize: 16,
                        fontWeight: 600
                    }}
                >
                    Новый заказ
                </Button>
            </div>

            <OrderDetailDrawer
                orderId={selectedOrderId ? String(selectedOrderId) : null}
                visible={!!selectedOrderId}
                onClose={() => setSelectedOrderId(null)}
            />

            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '0 16px 16px', gap: 16 }}>
                {/* Карта - 55% высоты */}
                <div style={{
                    flex: '0 0 55%',
                    position: 'relative',
                    borderRadius: 12,
                    overflow: 'hidden',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.06)'
                }}>
                    <LiveMap
                        onDriverSelect={setSelectedDriverId}
                        selectedOrderId={selectedOrderId}
                        selectedDriverId={selectedDriverId}
                        orders={orders}
                    />
                </div>


                {/* Таймлайн - 45% высоты */}
                <div style={{
                    flex: '1 1 auto',
                    background: '#fff',
                    borderRadius: 12,
                    padding: '8px 16px',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                    overflow: 'hidden'
                }}>
                    <TimelineView
                        drivers={timelineDrivers}
                        onOrderSelect={setSelectedOrderId}
                        selectedOrderId={selectedOrderId}
                    />
                </div>
            </div>

            <CreateOrderModal
                open={isModalOpen}
                onCancel={() => setIsModalOpen(false)}
                onCreate={handleCreateOrder}
                loading={isCreating}
            />
        </div>
    );
};
