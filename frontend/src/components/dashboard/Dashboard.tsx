import React, { useState } from 'react';
import { Badge, Button } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { LiveMap } from './LiveMap';
import { TimelineView } from './TimelineView';
import { CreateOrderModal } from './CreateOrderModal';
import { OrderDetailDrawer } from './OrderDetailDrawer';
import { useWebSocketSync } from '../../hooks/useWebSocketSync';
import { useDrivers } from '../../hooks/useDrivers';
import { useCreateOrder } from '../../hooks/useOrders';


export const Dashboard: React.FC = () => {
    const { isConnected } = useWebSocketSync();
    const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);

    // Реальные данные через хуки
    const { data: drivers = [] } = useDrivers();
    const { mutate: createOrder, isPending: isCreating } = useCreateOrder();

    const handleCreateOrder = (values: any) => {
        createOrder(values, {
            onSuccess: () => {
                setIsModalOpen(false);
            },
        });
    };

    return (
        <div style={{ height: 'calc(100vh - 160px)', display: 'flex', flexDirection: 'column', position: 'relative' }}>
            {/* Статус подключения и кнопка создания заказа */}
            <div style={{
                position: 'absolute',
                top: 0,
                right: 0,
                zIndex: 1000,
                display: 'flex',
                gap: '12px',
                alignItems: 'center'
            }}>
                <div style={{
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

                <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    onClick={() => setIsModalOpen(true)}
                    size="large"
                    style={{
                        height: '40px',
                        borderRadius: '8px',
                        boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                    }}
                >
                    Новый заказ
                </Button>
            </div>

            <OrderDetailDrawer
                orderId={selectedOrderId}
                visible={!!selectedOrderId}
                onClose={() => setSelectedOrderId(null)}
            />

            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                {/* Карта - 60% высоты */}
                <div style={{ flex: '0 0 60%', position: 'relative' }}>
                    <LiveMap
                        onDriverSelect={(id) => console.log('Selected driver:', id)}
                        selectedOrderId={selectedOrderId}
                    />
                </div>

                {/* Таймлайн - 40% высоты */}
                <div style={{
                    flex: '0 0 40%',
                    borderTop: '2px solid #e8e8e8',
                    overflow: 'hidden',
                }}>
                    <TimelineView
                        drivers={drivers}
                        onOrderSelect={setSelectedOrderId}
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
