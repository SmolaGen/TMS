import React, { useState } from 'react';
import { Layout, Badge } from 'antd';
import { LiveMap } from './LiveMap';
import { TimelineView } from './TimelineView';
import { useWebSocketSync } from '../../hooks/useWebSocketSync';
import type { TimelineDriver } from '../../types/api';

const { Content } = Layout;

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

            {selectedOrderId && (
                <div style={{
                    position: 'fixed',
                    top: 16,
                    right: 16,
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
                        onOrderSelect={setSelectedOrderId}
                    />
                </div>
            </Content>
        </Layout>
    );
};
