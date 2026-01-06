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
    suffix?: string;
}> = ({ title, value, icon, color, suffix }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <div style={{
            width: 36,
            height: 36,
            borderRadius: 10,
            background: color,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 18,
            boxShadow: `0 4px 10px -2px ${color}60`
        }}>
            {icon}
        </div>
        <div>
            <div style={{
                fontSize: 18,
                fontWeight: 700,
                lineHeight: 1,
                color: 'var(--tms-text-primary)'
            }}>
                {value}
                {suffix && <span style={{ fontSize: 12, fontWeight: 500, color: 'var(--tms-text-tertiary)', marginLeft: 2 }}>{suffix}</span>}
            </div>
            <div style={{
                fontSize: 10,
                color: 'var(--tms-text-secondary)',
                fontWeight: 500,
                marginTop: 2
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
        return null; // Mobile has its own controls usually, or simplified
    }

    return (
        <div
            className="glass-panel"
            style={{
                position: 'absolute',
                top: 16,
                right: 16,
                zIndex: 1000,
                width: collapsed ? 240 : 280,
                padding: 16,
                transform: 'scale(1)',
                transition: 'all 0.3s ease'
            }}
        >
            <div
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    marginBottom: collapsed ? 0 : 16,
                    cursor: 'pointer'
                }}
                onClick={() => setCollapsed(!collapsed)}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{
                        width: 4,
                        height: 16,
                        borderRadius: 2,
                        background: 'var(--tms-gradient-primary)'
                    }} />
                    <span style={{ fontWeight: 700, fontSize: 13, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                        Управление
                    </span>
                </div>
                <Button
                    type="text"
                    size="small"
                    icon={collapsed ? <DownOutlined /> : <UpOutlined />}
                    onClick={(e) => {
                        e.stopPropagation();
                        setCollapsed(!collapsed);
                    }}
                />
            </div>

            {!collapsed && (
                <>
                    {/* Stats Section */}
                    {isLoading || !kpiData ? (
                        <div style={{ marginBottom: 16 }}>
                            <Skeleton active paragraph={{ rows: 2 }} />
                        </div>
                    ) : (
                        <div style={{ marginBottom: 16 }}>
                            <Row gutter={[12, 12]}>
                                <Col span={12}>
                                    <StatItem
                                        title="Активных"
                                        value={kpiData.stats.activeOrders}
                                        icon={<ShoppingCartOutlined />}
                                        color="#3b82f6"
                                    />
                                </Col>
                                <Col span={12}>
                                    <StatItem
                                        title="Свободных"
                                        value={kpiData.stats.freeDrivers}
                                        icon={<CarOutlined />}
                                        color="#10b981"
                                    />
                                </Col>
                                <Col span={12}>
                                    <StatItem
                                        title="Выполнено"
                                        value={kpiData.stats.completedToday}
                                        icon={<CheckCircleOutlined />}
                                        color="#8b5cf6"
                                    />
                                </Col>
                                <Col span={12}>
                                    <StatItem
                                        title="Ожидание"
                                        value={kpiData.stats.averageWaitTime}
                                        suffix="мин"
                                        icon={<ClockCircleOutlined />}
                                        color="#ec4899"
                                    />
                                </Col>
                            </Row>
                        </div>
                    )}

                    <Divider style={{ margin: '12px 0' }} />

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
