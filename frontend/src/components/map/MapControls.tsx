import React, { useState, useEffect } from 'react';
import { Switch, Space, Divider, Button, Tooltip, Skeleton, Row, Col } from 'antd';
import {
    CarOutlined,
    EnvironmentOutlined,
    AimOutlined,
    ReloadOutlined,
    ShoppingCartOutlined,
    CheckCircleOutlined,
    ClockCircleOutlined,
    DownOutlined,
    UpOutlined
} from '@ant-design/icons';
import { useKPIStats } from '../../hooks/useKPIStats';

export interface MapControlsState {
    showRoutes: boolean;
    showOnlyFreeDrivers: boolean;
    followSelected: boolean;
}

interface MapControlsProps {
    state: MapControlsState;
    onChange: (state: Partial<MapControlsState>) => void;
    onCenterOnSelected: () => void;
    onResetView: () => void;
}

const useIsMobile = () => {
    const [isMobile, setIsMobile] = useState(
        typeof window !== 'undefined' ? window.innerWidth <= 768 : false
    );

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth <= 768);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    return isMobile;
};

const ControlItem: React.FC<{
    icon: React.ReactNode;
    label: string;
    checked: boolean;
    onChange: (checked: boolean) => void;
}> = ({ icon, label, checked, onChange }) => (
    <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 0',
        cursor: 'pointer'
    }} onClick={() => onChange(!checked)}>
        <Space>
            <div style={{
                color: checked ? '#3b82f6' : 'var(--tms-text-tertiary)',
                fontSize: 16,
                transition: 'color 0.3s'
            }}>
                {icon}
            </div>
            <span style={{
                fontSize: 13,
                fontWeight: 500,
                color: 'var(--tms-text-primary)'
            }}>
                {label}
            </span>
        </Space>
        <Switch
            size="small"
            checked={checked}
            onChange={onChange}
            style={{
                backgroundColor: checked ? '#3b82f6' : undefined
            }}
        />
    </div>
);

const StatItem: React.FC<{
    title: string;
    value: number | string;
    icon: React.ReactNode;
    color: string;
    gradient: string;
    suffix?: string;
}> = ({ title, value, icon, gradient, suffix }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
        <div style={{
            width: 40,
            height: 40,
            borderRadius: 12,
            background: gradient,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 20,
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
        }}>
            {icon}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div style={{
                fontSize: 20,
                fontWeight: 800,
                lineHeight: 1,
                color: 'var(--tms-text-primary)',
                letterSpacing: '-0.02em'
            }}>
                {value}
                {suffix && <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--tms-text-tertiary)', marginLeft: 3 }}>{suffix}</span>}
            </div>
            <div style={{
                fontSize: 10,
                color: 'var(--tms-text-tertiary)',
                fontWeight: 600,
                marginTop: 4,
                textTransform: 'uppercase',
                letterSpacing: '0.04em'
            }}>
                {title}
            </div>
        </div>
    </div>
);

export const MapControls: React.FC<MapControlsProps> = ({
    state,
    onChange,
    onCenterOnSelected,
    onResetView,
}) => {
    const isMobile = useIsMobile();
    const [collapsed, setCollapsed] = useState(false);
    const { data: kpiData, isLoading } = useKPIStats();

    if (isMobile) {
        return null;
    }

    return (
        <div
            className="glass-panel"
            style={{
                position: 'absolute',
                top: 20,
                right: 20,
                zIndex: 1000,
                width: collapsed ? 240 : 280,
                padding: '20px',
                borderRadius: 20,
                border: '1px solid rgba(255, 255, 255, 0.05)',
                boxShadow: '0 12px 48px rgba(0, 0, 0, 0.3)',
                transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)'
            }}
        >
            <div
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: collapsed ? 0 : 20,
                    cursor: 'pointer'
                }}
                onClick={() => setCollapsed(!collapsed)}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{
                        width: 4,
                        height: 18,
                        borderRadius: 2,
                        background: 'var(--tms-gradient-primary)',
                        boxShadow: '0 0 8px rgba(59, 130, 246, 0.5)'
                    }} />
                    <span style={{
                        fontWeight: 800,
                        fontSize: 12,
                        textTransform: 'uppercase',
                        letterSpacing: '0.08em',
                        color: 'var(--tms-text-secondary)'
                    }}>
                        Управление
                    </span>
                </div>
                <Button
                    type="text"
                    size="small"
                    icon={collapsed ? <DownOutlined /> : <UpOutlined />}
                    style={{ color: 'var(--tms-text-tertiary)' }}
                />
            </div>

            {!collapsed && (
                <>
                    {/* Stats Section */}
                    {isLoading || !kpiData ? (
                        <div style={{ marginBottom: 20 }}>
                            <Skeleton active paragraph={{ rows: 2 }} />
                        </div>
                    ) : (
                        <div style={{ marginBottom: 20 }}>
                            <Row gutter={[16, 16]}>
                                <Col span={12}>
                                    <StatItem
                                        title="Активных"
                                        value={kpiData.stats.activeOrders}
                                        icon={<ShoppingCartOutlined />}
                                        color="#3b82f6"
                                        gradient="linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)"
                                    />
                                </Col>
                                <Col span={12}>
                                    <StatItem
                                        title="Свободных"
                                        value={kpiData.stats.freeDrivers}
                                        icon={<CarOutlined />}
                                        color="#10b981"
                                        gradient="linear-gradient(135deg, #10b981 0%, #059669 100%)"
                                    />
                                </Col>
                                <Col span={12}>
                                    <StatItem
                                        title="Выполнено"
                                        value={kpiData.stats.completedToday}
                                        icon={<CheckCircleOutlined />}
                                        color="#8b5cf6"
                                        gradient="linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)"
                                    />
                                </Col>
                                <Col span={12}>
                                    <StatItem
                                        title="Ожидание"
                                        value={kpiData.stats.averageWaitTime}
                                        suffix="м"
                                        icon={<ClockCircleOutlined />}
                                        color="#ec4899"
                                        gradient="linear-gradient(135deg, #f43f5e 0%, #e11d48 100%)"
                                    />
                                </Col>
                            </Row>
                        </div>
                    )}

                    <Divider style={{ margin: '16px 0', borderColor: 'rgba(255,255,255,0.06)' }} />

                    <ControlItem
                        icon={<EnvironmentOutlined />}
                        label="Маршруты"
                        checked={state.showRoutes}
                        onChange={(c) => onChange({ showRoutes: c })}
                    />

                    <ControlItem
                        icon={<CarOutlined />}
                        label="Только свободные"
                        checked={state.showOnlyFreeDrivers}
                        onChange={(c) => onChange({ showOnlyFreeDrivers: c })}
                    />

                    <ControlItem
                        icon={<AimOutlined />}
                        label="Следовать"
                        checked={state.followSelected}
                        onChange={(c) => onChange({ followSelected: c })}
                    />

                    <Divider style={{ margin: '12px 0' }} />

                    <Space style={{ width: '100%' }}>
                        <Tooltip title="Центрировать на выбранном объекте">
                            <Button
                                type="primary"
                                icon={<AimOutlined />}
                                onClick={onCenterOnSelected}
                                style={{ flex: 1, borderRadius: 8 }}
                                ghost
                            >
                                Центр
                            </Button>
                        </Tooltip>

                        <Tooltip title="Сбросить масштаб и позицию">
                            <Button
                                icon={<ReloadOutlined />}
                                onClick={onResetView}
                                style={{ flex: 1, borderRadius: 8 }}
                            >
                                Сброс
                            </Button>
                        </Tooltip>
                    </Space>
                </>
            )}
        </div>
    );
};
