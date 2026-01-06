import React, { useState, useMemo } from 'react';
import { Spin, Row, Col, Statistic } from 'antd';
import {
    TeamOutlined,
    CheckCircleOutlined,
    ClockCircleOutlined,
    StopOutlined
} from '@ant-design/icons';
import { DriversFilters } from '../components/drivers/DriversFilters';
import type { DriversFiltersState } from '../components/drivers/DriversFilters';
import { DriversTable } from '../components/drivers/DriversTable';
import { DriversGrid } from '../components/drivers/DriversGrid';
import { DriversViewToggle } from '../components/drivers/DriversViewToggle';
import type { ViewMode } from '../components/drivers/DriversViewToggle';
import { DriverDetailDrawer } from '../components/drivers/DriverDetailDrawer';
import { useDriversList } from '../hooks/useDriversList';
import { DriverStatus } from '../types/api';

const defaultFilters: DriversFiltersState = {
    status: [],
    search: '',
    isActive: null,
};

export const DriversPage: React.FC = () => {
    const [viewMode, setViewMode] = useState<ViewMode>('table');
    const [filters, setFilters] = useState<DriversFiltersState>(defaultFilters);
    const [selectedDriverId, setSelectedDriverId] = useState<number | null>(null);

    const { data: drivers = [], isLoading } = useDriversList();

    const safeDrivers = Array.isArray(drivers) ? drivers : [];

    // Подсчёт статистики
    const stats = useMemo(() => {
        const available = safeDrivers.filter(d => d.status === DriverStatus.AVAILABLE).length;
        const busy = safeDrivers.filter(d => d.status === DriverStatus.BUSY).length;
        const offline = safeDrivers.filter(d => d.status === DriverStatus.OFFLINE).length;
        return { total: safeDrivers.length, available, busy, offline };
    }, [safeDrivers]);

    // Фильтрация водителей
    const filteredDrivers = useMemo(() => {
        return safeDrivers.filter((driver) => {
            // Фильтр по статусу
            if (filters.status.length > 0 && !filters.status.includes(driver.status)) {
                return false;
            }
            // Фильтр по активности
            if (filters.isActive !== null && driver.is_active !== filters.isActive) {
                return false;
            }
            // Поиск
            if (filters.search) {
                const searchLower = filters.search.toLowerCase();
                const matchName = driver.name.toLowerCase().includes(searchLower);
                const matchPhone = driver.phone?.toLowerCase().includes(searchLower);
                const matchId = String(driver.id).includes(filters.search);
                if (!matchName && !matchPhone && !matchId) {
                    return false;
                }
            }
            return true;
        });
    }, [safeDrivers, filters]);

    const handleFiltersChange = (newFilters: Partial<DriversFiltersState>) => {
        setFilters((prev) => ({ ...prev, ...newFilters }));
    };

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: 16 }}>
            {/* Заголовок с KPI */}
            <div style={{ marginBottom: 16 }}>
                <Row gutter={16}>
                    <Col span={6}>
                        <div className="glass-card" style={{ padding: '12px' }}>
                            <Statistic
                                title="Всего водителей"
                                value={stats.total}
                                prefix={<TeamOutlined />}
                            />
                        </div>
                    </Col>
                    <Col span={6}>
                        <div className="glass-card" style={{ padding: '12px' }}>
                            <Statistic
                                title="Доступны"
                                value={stats.available}
                                valueStyle={{ color: '#52c41a' }}
                                prefix={<CheckCircleOutlined />}
                            />
                        </div>
                    </Col>
                    <Col span={6}>
                        <div className="glass-card" style={{ padding: '12px' }}>
                            <Statistic
                                title="Заняты"
                                value={stats.busy}
                                valueStyle={{ color: '#faad14' }}
                                prefix={<ClockCircleOutlined />}
                            />
                        </div>
                    </Col>
                    <Col span={6}>
                        <div className="glass-card" style={{ padding: '12px' }}>
                            <Statistic
                                title="Оффлайн"
                                value={stats.offline}
                                valueStyle={{ color: '#8c8c8c' }}
                                prefix={<StopOutlined />}
                            />
                        </div>
                    </Col>
                </Row>
            </div>

            {/* Панель фильтров и переключатель вида */}
            <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'flex-start',
                marginBottom: 16,
            }}>
                <DriversFilters
                    filters={filters}
                    onChange={handleFiltersChange}
                    onReset={() => setFilters(defaultFilters)}
                />
                <DriversViewToggle value={viewMode} onChange={setViewMode} />
            </div>

            {/* Контент */}
            <div style={{ flex: 1, overflow: 'auto' }}>
                <Spin spinning={isLoading}>
                    {viewMode === 'table' ? (
                        <div className="glass-card">
                            <DriversTable
                                drivers={filteredDrivers}
                                loading={isLoading}
                                onSelect={(id) => setSelectedDriverId(id)}
                            />
                        </div>
                    ) : (
                        <div className="glass-card">
                            <DriversGrid
                                drivers={filteredDrivers}
                                loading={isLoading}
                                onSelect={(id) => setSelectedDriverId(id)}
                            />
                        </div>
                    )}
                </Spin>
            </div>

            {/* Drawer деталей водителя */}
            <DriverDetailDrawer
                driverId={selectedDriverId}
                open={!!selectedDriverId}
                onClose={() => setSelectedDriverId(null)}
            />
        </div>
    );
};
