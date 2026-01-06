import React, { useState, useMemo } from 'react';
import { Button, Space, Spin, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { OrderFilters } from '../components/orders/OrderFilters';
import type { OrderFiltersState } from '../components/orders/OrderFilters';
import { OrdersTable } from '../components/orders/OrdersTable';
import { ViewToggle } from '../components/common/ViewToggle';
import type { ViewMode } from '../components/common/ViewToggle';
import { TimelineView } from '../components/dashboard/TimelineView';
import { LiveMap } from '../components/dashboard/LiveMap';
import { OrderDetailDrawer } from '../components/dashboard/OrderDetailDrawer';
import { CreateOrderModal } from '../components/dashboard/CreateOrderModal';
import { useOrdersRaw, useCreateOrder } from '../hooks/useOrders';
import { useDrivers } from '../hooks/useDrivers';
import dayjs from 'dayjs';
import isBetween from 'dayjs/plugin/isBetween';
import type { TimelineDriver } from '../types/api';

dayjs.extend(isBetween);

const { Title } = Typography;

const defaultFilters: OrderFiltersState = {
    status: [],
    driverIds: [],
    dateRange: null,
    search: '',
    priority: [],
};

export const OrdersPage: React.FC = () => {
    const [viewMode, setViewMode] = useState<ViewMode>('table-map');
    const [filters, setFilters] = useState<OrderFiltersState>(defaultFilters);
    const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

    const { data: orders = [], isLoading: isOrdersLoading } = useOrdersRaw();
    const { data: drivers = [], isLoading: isDriversLoading } = useDrivers();
    const { mutate: createOrder, isPending: isCreating } = useCreateOrder();

    // Преобразование водителей для Timeline
    const timelineDrivers: TimelineDriver[] = useMemo(() => {
        const transformed: TimelineDriver[] = drivers.map(d => ({
            id: String(d.id),
            content: d.name || 'Безымянный',
            name: d.name || 'Безымянный'
        }));

        return [
            { id: 'unassigned', content: '❌ Не назначено', name: 'Не назначено' },
            ...transformed
        ];
    }, [drivers]);

    // Фильтрация заказов
    const filteredOrders = useMemo(() => {
        return orders.filter((order) => {
            // Фильтр по статусу
            if (filters.status.length > 0 && !filters.status.includes(order.status)) {
                return false;
            }
            // Фильтр по водителю (driver_id может быть 0 или null для неназначенных)
            if (filters.driverIds.length > 0) {
                const orderDriverId = order.driver_id || 0;
                if (!filters.driverIds.includes(orderDriverId)) {
                    return false;
                }
            }
            // Фильтр по дате
            if (filters.dateRange && filters.dateRange[0] && filters.dateRange[1]) {
                const orderDate = dayjs(order.time_start);
                if (!orderDate.isBetween(filters.dateRange[0], filters.dateRange[1], 'day', '[]')) {
                    return false;
                }
            }
            // Фильтр по приоритету
            if (filters.priority.length > 0 && !filters.priority.includes(order.priority)) {
                return false;
            }
            // Поиск
            if (filters.search) {
                const searchLower = filters.search.toLowerCase();
                const matchAddress =
                    (order.pickup_address?.toLowerCase().includes(searchLower)) ||
                    (order.dropoff_address?.toLowerCase().includes(searchLower));
                if (!matchAddress && !String(order.id).includes(filters.search)) {
                    return false;
                }
            }
            return true;
        });
    }, [orders, filters]);

    const handleFiltersChange = (newFilters: Partial<OrderFiltersState>) => {
        setFilters((prev) => ({ ...prev, ...newFilters }));
    };

    const handleCreateOrder = (values: any) => {
        createOrder(values, {
            onSuccess: () => setIsCreateModalOpen(false),
        });
    };

    const isLoading = isOrdersLoading || isDriversLoading;

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--tms-bg-layout)', padding: '0 24px 24px' }}>
            <div style={{
                padding: '16px 0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
            }}>
                <Title level={4} style={{ margin: 0 }}>Управление заказами</Title>
                <Space>
                    <ViewToggle value={viewMode} onChange={setViewMode} />
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setIsCreateModalOpen(true)}
                        size="large"
                        shape="round"
                    >
                        Новый заказ
                    </Button>
                </Space>
            </div>

            <OrderFilters
                filters={filters}
                onChange={handleFiltersChange}
                onReset={() => setFilters(defaultFilters)}
            />

            <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
                <Spin spinning={isLoading} tip="Загрузка данных...">
                    {viewMode === 'table-only' && (
                        <div style={{ height: '100%' }}>
                            <OrdersTable
                                orders={filteredOrders}
                                drivers={drivers}
                                loading={isLoading}
                                onSelect={setSelectedOrderId}
                            />
                        </div>
                    )}

                    {viewMode === 'table-map' && (
                        <div style={{ display: 'flex', height: '100%', gap: 16 }}>
                            <div style={{ flex: 1, overflow: 'auto' }}>
                                <OrdersTable
                                    orders={filteredOrders}
                                    drivers={drivers}
                                    loading={isLoading}
                                    onSelect={setSelectedOrderId}
                                />
                            </div>
                            <div style={{ width: '40%', minWidth: 400, borderRadius: 12, overflow: 'hidden', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
                                <LiveMap selectedOrderId={selectedOrderId} orders={filteredOrders} />
                            </div>
                        </div>
                    )}

                    {viewMode === 'map-timeline' && (
                        <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 16 }}>
                            <div style={{ flex: '0 0 55%', position: 'relative', borderRadius: 12, overflow: 'hidden', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }}>
                                <LiveMap selectedOrderId={selectedOrderId} orders={filteredOrders} />
                            </div>
                            <div style={{
                                flex: '1 1 auto',
                                background: 'var(--tms-bg-container)',
                                borderRadius: 12,
                                overflow: 'hidden',
                                boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
                                padding: '8px 16px'
                            }}>
                                <TimelineView
                                    drivers={timelineDrivers}
                                    onOrderSelect={setSelectedOrderId}
                                    selectedOrderId={selectedOrderId}
                                />
                            </div>
                        </div>
                    )}
                </Spin>
            </div>

            <OrderDetailDrawer
                orderId={selectedOrderId ? String(selectedOrderId) : null}
                visible={!!selectedOrderId}
                onClose={() => setSelectedOrderId(null)}
            />

            <CreateOrderModal
                open={isCreateModalOpen}
                onCancel={() => setIsCreateModalOpen(false)}
                onCreate={handleCreateOrder}
                loading={isCreating}
            />
        </div>
    );
};
