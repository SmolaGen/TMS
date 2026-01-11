import React, { useState, useMemo, useEffect } from 'react';
import { Button, Tooltip, Badge, Tabs, DatePicker, Card, Space } from 'antd';
import moment from 'moment';
import { PlusOutlined } from '@ant-design/icons';
import { LiveMap } from './LiveMap';
import { TimelineView } from './TimelineView';
import { CreateOrderModal } from './CreateOrderModal';
import { OrderDetailDrawer } from './OrderDetailDrawer';
import { BatchAssignmentPanel } from './BatchAssignmentPanel';
import { DashboardStats } from './DashboardStats';
import { UnassignedOrdersPanel } from './UnassignedOrdersPanel';
import { useWebSocketSync } from '../../hooks/useWebSocketSync';
import { useDrivers } from '../../hooks/useDrivers';
import { useCreateOrder, useOrdersRaw } from '../../hooks/useOrders';
import type { TimelineDriver } from '../../types/api';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';

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
    const [dateRange, setDateRange] = useState<[Date, Date]>([
        moment().startOf('day').toDate(),
        moment().endOf('day').toDate()
    ]);
    const isMobile = useIsMobile();

    const { data: drivers = [] } = useDrivers();
    const { mutate: createOrder, isPending: isCreating } = useCreateOrder();
    const { data: orders = [] } = useOrdersRaw(dateRange);

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
            position: 'relative',
            gap: isMobile ? 12 : 24,
        }}>
            {/* Панель управления датой */}
            <Card size="small" style={{ marginBottom: 0 }}>
                <Space>
                    <span>Дата:</span>
                    <DatePicker
                        defaultValue={moment()}
                        onChange={(val) => {
                            if (val) {
                                setDateRange([
                                    val.startOf('day').toDate(),
                                    val.endOf('day').toDate()
                                ]);
                            }
                        }}
                        allowClear={false}
                    />
                </Space>
            </Card>

            {/* Статистика */}
            <DashboardStats dateRange={dateRange} />


            {/* Основной контент */}
            <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                gap: isMobile ? 12 : 24,
                overflow: 'hidden',
                position: 'relative',
            }}>
                <Tabs
                    defaultActiveKey="operations"
                    type="card"
                    size="small"
                    style={{ marginBottom: 0 }}
                    items={[
                        {
                            key: 'operations',
                            label: 'Операции',
                            children: (
                                <>
                                    {/* Карта */}
                                    <div
                                        className="glass-card"
                                        style={{
                                            flex: isMobile ? '0 0 250px' : '0 0 55%',
                                            minHeight: isMobile ? 250 : 350,
                                            position: 'relative',
                                            overflow: 'hidden',
                                            padding: 0, // Map needs no padding
                                            border: 'var(--tms-glass-border)',
                                            marginBottom: isMobile ? 12 : 24,
                                        }}
                                    >
                                        <LiveMap
                                            onDriverSelect={setSelectedDriverId}
                                            selectedOrderId={selectedOrderId}
                                            selectedDriverId={selectedDriverId}
                                            orders={orders}
                                        />

                                        {/* Status Indicator inside Map */}
                                        <div style={{
                                            position: 'absolute',
                                            top: 16,
                                            left: 16, // Left side now because controls are right
                                            zIndex: 1000,
                                        }}>
                                            <Tooltip title={isConnected ? "Подключено к серверу" : "Нет соединения"}>
                                                <div className="glass-panel" style={{
                                                    padding: '6px 12px',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: 8,
                                                    borderRadius: 20,
                                                }}>
                                                    <div style={{
                                                        width: 8,
                                                        height: 8,
                                                        borderRadius: '50%',
                                                        background: isConnected ? '#10b981' : '#f59e0b',
                                                        boxShadow: isConnected ? '0 0 8px #10b981' : 'none',
                                                        animation: isConnected ? 'markerPulse 2s infinite' : 'none'
                                                    }} />
                                                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--tms-text-secondary)' }}>
                                                        {isConnected ? 'LIVE' : 'OFFLINE'}
                                                    </span>
                                                </div>
                                            </Tooltip>
                                        </div>
                                    </div>

                                    {/* Таймлайн */}
                                    <div
                                        className="glass-card"
                                        style={{
                                            flex: '1 1 auto',
                                            minHeight: isMobile ? 180 : 250,
                                            padding: isMobile ? '8px' : '16px',
                                            overflow: 'hidden',
                                            display: 'flex',
                                            flexDirection: 'column'
                                        }}
                                    >
                                        <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <span style={{ fontWeight: 700, fontSize: 16 }}>График заказов</span>
                                            <Badge count={orders.length} style={{ backgroundColor: '#2563eb' }} />
                                        </div>
                                        <div style={{ flex: 1, position: 'relative' }}>
                                            <TimelineView
                                                drivers={timelineDrivers}
                                                onOrderSelect={setSelectedOrderId}
                                                selectedOrderId={selectedOrderId}
                                            />
                                        </div>
                                    </div>
                                </>
                            ),
                        },
                        {
                            key: 'batch-assignment',
                            label: 'Распределение заказов',
                            children: (
                                <div style={{ padding: isMobile ? '8px' : '16px', display: 'flex', flexDirection: 'column', gap: 24 }}>
                                    <BatchAssignmentPanel
                                        onAssignmentComplete={(result) => {
                                            console.log('Batch assignment completed:', result);
                                        }}
                                    />
                                    <UnassignedOrdersPanel
                                        targetDate={moment(dateRange[0]).format('YYYY-MM-DD')}
                                        onAssignClick={(orderId) => setSelectedOrderId(orderId)}
                                    />
                                </div>
                            ),
                        },
                    ]}
                />
            </div>

            {/* Floating Action Button */}
            <div style={{
                position: 'fixed',
                bottom: 32,
                right: 32,
                zIndex: 1100,
            }}>
                <Button
                    type="primary"
                    icon={<PlusOutlined />}
                    size="large"
                    shape="circle"
                    onClick={() => setIsModalOpen(true)}
                    style={{
                        width: 64,
                        height: 64,
                        fontSize: 24,
                        background: 'var(--tms-gradient-primary)',
                        border: 'none',
                        boxShadow: '0 8px 30px rgba(59, 130, 246, 0.4)',
                    }}
                    className="hover-lift"
                />
            </div>

            <OrderDetailDrawer
                orderId={selectedOrderId ? String(selectedOrderId) : null}
                visible={!!selectedOrderId}
                onClose={() => setSelectedOrderId(null)}
            />

            <CreateOrderModal
                open={isModalOpen}
                onCancel={() => setIsModalOpen(false)}
                onCreate={handleCreateOrder}
                loading={isCreating}
            />
        </div>
    );
};
