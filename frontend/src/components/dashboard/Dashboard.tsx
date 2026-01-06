import React, { useState, useMemo, useEffect } from 'react';
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
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';

// Хук для определения мобильного устройства
const useIsMobile = (breakpoint = 768) => {
    const [isMobile, setIsMobile] = useState(
        typeof window !== 'undefined' ? window.innerWidth <= breakpoint : false
    );

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth <= breakpoint);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, [breakpoint]);

    return isMobile;
};

export const Dashboard: React.FC = () => {
    const { isConnected } = useWebSocketSync();
    const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);
    const [selectedDriverId, setSelectedDriverId] = useState<number | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const isMobile = useIsMobile();

    // Реальные данные через хуки
    const { data: drivers = [] } = useDrivers();
    const { mutate: createOrder, isPending: isCreating } = useCreateOrder();
    const { data: orders = [] } = useOrdersRaw();

    // Горячие клавиши
    useKeyboardShortcuts([
        {
            key: 'n',
            handler: () => setIsModalOpen(true),
            description: 'Новый заказ'
        },
        {
            key: 'Escape',
            handler: () => {
                setIsModalOpen(false);
                setSelectedOrderId(null);
            },
            description: 'Закрыть'
        },
    ]);

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
        <div style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            background: 'var(--tms-bg-layout)',
            position: 'relative',
            overflow: 'hidden',
        }}>
            {/* KPI Панель */}
            <div style={{ padding: isMobile ? '8px 8px 0' : '16px 16px 0' }}>
                <KPIWidgets />
            </div>

            {/* Статус подключения и кнопка */}
            <div style={{
                position: 'absolute',
                top: isMobile ? 'auto' : 100,
                bottom: isMobile ? 90 : 'auto',
                right: isMobile ? 16 : 32,
                zIndex: 1000,
                display: 'flex',
                flexDirection: 'column',
                gap: isMobile ? 8 : 12,
                alignItems: 'flex-end',
            }}>
                <Space
                    style={{
                        background: 'var(--tms-bg-elevated)',
                        padding: isMobile ? '3px 8px' : '4px 12px',
                        borderRadius: 20,
                        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                        fontSize: isMobile ? 11 : 12,
                        fontWeight: 500
                    }}
                >
                    <span style={{
                        display: 'inline-block',
                        width: isMobile ? 6 : 8,
                        height: isMobile ? 6 : 8,
                        borderRadius: '50%',
                        backgroundColor: isConnected ? '#52c41a' : '#faad14',
                    }} />
                    {isConnected ? 'Online' : 'Подключение...'}
                </Space>
                <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    size={isMobile ? 'middle' : 'large'}
                    shape="round"
                    onClick={() => setIsModalOpen(true)}
                    style={{
                        boxShadow: '0 4px 12px rgba(24, 144, 255, 0.35)',
                        height: isMobile ? 40 : 48,
                        padding: isMobile ? '0 16px' : '0 24px',
                        fontSize: isMobile ? 14 : 16,
                        fontWeight: 600
                    }}
                >
                    {isMobile ? '+' : 'Новый заказ'}
                </Button>
            </div>

            <OrderDetailDrawer
                orderId={selectedOrderId ? String(selectedOrderId) : null}
                visible={!!selectedOrderId}
                onClose={() => setSelectedOrderId(null)}
            />

            <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                padding: isMobile ? '0 8px 8px' : '0 16px 16px',
                gap: isMobile ? 8 : 16,
                overflow: 'hidden',
            }}>
                {/* Карта */}
                <div style={{
                    flex: isMobile ? '0 0 200px' : '0 0 55%',
                    minHeight: isMobile ? 180 : 300,
                    position: 'relative',
                    borderRadius: isMobile ? 8 : 12,
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

                {/* Таймлайн */}
                <div style={{
                    flex: '1 1 auto',
                    minHeight: isMobile ? 150 : 200,
                    background: 'var(--tms-bg-container)',
                    borderRadius: isMobile ? 8 : 12,
                    padding: isMobile ? '6px 8px' : '8px 16px',
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
