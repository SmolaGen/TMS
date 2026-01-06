import React, { useState, useMemo } from 'react';
import { Button, Space, Spin, message } from 'antd';
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
import { useOrdersRaw, useCreateOrder, useUpdateOrderStatus } from '../hooks/useOrders';
import { useDrivers } from '../hooks/useDrivers';
import dayjs from 'dayjs';
import isBetween from 'dayjs/plugin/isBetween';

dayjs.extend(isBetween);

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
    const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);
    const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

    const { data: orders = [], isLoading } = useOrdersRaw();
    const { data: drivers = [] } = useDrivers();
    const { mutate: createOrder, isPending: isCreating } = useCreateOrder();
    const { mutate: updateStatus } = useUpdateOrderStatus();

    // Фильтрация заказов
    const filteredOrders = useMemo(() => {
        return orders.filter((order) => {
            // Фильтр по статусу
            if (filters.status.length > 0 && !filters.status.includes(order.status)) {
                return false;
            }
            // Фильтр по водителю
            if (filters.driverIds.length > 0) {
                const hasUnassigned = filters.driverIds.includes('unassigned');
                const matchedDriver = order.driver_id && filters.driverIds.includes(order.driver_id);
                const isUnassignedMatch = hasUnassigned && !order.driver_id;

                if (!matchedDriver && !isUnassignedMatch) {
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
            // Поиск
            if (filters.search) {
                const searchLower = filters.search.toLowerCase();
                const matchAddress =
                    order.pickup_address?.toLowerCase().includes(searchLower) ||
                    order.dropoff_address?.toLowerCase().includes(searchLower);
                const matchId = String(order.id).includes(filters.search);
                const matchCustomer =
                    order.customer_name?.toLowerCase().includes(searchLower) ||
                    order.customer_phone?.includes(filters.search);

                if (!matchAddress && !matchId && !matchCustomer) {
                    return false;
                }
            }
            // Приоритет
            if (filters.priority.length > 0 && !filters.priority.includes(order.priority)) {
                return false;
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

    const handleCancelOrder = (orderId: string) => {
        updateStatus({ orderId, action: 'cancel', reason: 'Отмена диспетчером' });
    };

    const handleAssignOrder = (orderId: string) => {
        setSelectedOrderId(orderId);
        message.info('Выберите водителя в деталях заказа');
    };

    return (
        <div style={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column' }}>
            {/* Верхняя панель */}
            <div style={{
                padding: '16px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                flexWrap: 'wrap',
                gap: '16px',
                background: '#fff',
                borderBottom: '1px solid #f0f0f0'
            }}>
                <OrderFilters
                    filters={filters}
                    onChange={handleFiltersChange}
                    onReset={() => setFilters(defaultFilters)}
                />
                <Space>
                    <ViewToggle value={viewMode} onChange={setViewMode} />
                    <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setIsCreateModalOpen(true)}
                    >
                        Новый заказ
                    </Button>
                </Space>
            </div>

            {/* Контент в зависимости от режима */}
            <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
                <Spin spinning={isLoading}>
                    {viewMode === 'table-only' && (
                        <div style={{ height: '100%', padding: '16px' }}>
                            <OrdersTable
                                orders={filteredOrders}
                                loading={isLoading}
                                onSelect={setSelectedOrderId}
                                onCancel={handleCancelOrder}
                                onAssign={handleAssignOrder}
                            />
                        </div>
                    )}

                    {viewMode === 'table-map' && (
                        <div style={{ display: 'flex', height: '100%', gap: 16, padding: '16px' }}>
                            <div style={{ flex: 1, overflow: 'auto' }}>
                                <OrdersTable
                                    orders={filteredOrders}
                                    loading={isLoading}
                                    onSelect={setSelectedOrderId}
                                    onCancel={handleCancelOrder}
                                    onAssign={handleAssignOrder}
                                />
                            </div>
                            <div style={{ width: '40%', minWidth: 400, borderRadius: 8, overflow: 'hidden', border: '1px solid #f0f0f0' }}>
                                <LiveMap selectedOrderId={selectedOrderId} />
                            </div>
                        </div>
                    )}

                    {viewMode === 'map-timeline' && (
                        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
                            <div style={{ flex: '1 1 50%', position: 'relative' }}>
                                <LiveMap selectedOrderId={selectedOrderId} />
                            </div>
                            <div style={{ flex: '0 0 300px', borderTop: '2px solid #e8e8e8' }}>
                                <TimelineView
                                    drivers={drivers}
                                    onOrderSelect={setSelectedOrderId}
                                />
                            </div>
                        </div>
                    )}
                </Spin>
            </div>

            {/* Drawer деталей заказа */}
            <OrderDetailDrawer
                orderId={selectedOrderId ? Number(selectedOrderId) : null}
                visible={!!selectedOrderId}
                onClose={() => setSelectedOrderId(null)}
            />

            {/* Модал создания заказа */}
            <CreateOrderModal
                open={isCreateModalOpen}
                onCancel={() => setIsCreateModalOpen(false)}
                onCreate={handleCreateOrder}
                loading={isCreating}
            />
        </div>
    );
};
