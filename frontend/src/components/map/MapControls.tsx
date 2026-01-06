import React from 'react';
import { Card, Switch, Space, Typography, Divider, Button } from 'antd';
import {
    CarOutlined,
    EnvironmentOutlined,
    AimOutlined,
} from '@ant-design/icons';

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

export const MapControls: React.FC<MapControlsProps> = ({
    state,
    onChange,
    onCenterOnSelected,
    onResetView,
}) => {
    return (
        <Card
            size="small"
            style={{
                position: 'absolute',
                top: 10,
                right: 10,
                zIndex: 1000,
                width: 220,
                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            }}
        >
            <Space direction="vertical" style={{ width: '100%' }}>
                <Typography.Text strong>
                    🗺️ Управление картой
                </Typography.Text>

                <Divider style={{ margin: '8px 0' }} />

                {/* Показать маршруты */}
                <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                    <Space>
                        <EnvironmentOutlined />
                        <span>Маршруты</span>
                    </Space>
                    <Switch
                        size="small"
                        checked={state.showRoutes}
                        onChange={(checked) => onChange({ showRoutes: checked })}
                    />
                </Space>

                {/* Только свободные водители */}
                <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                    <Space>
                        <CarOutlined />
                        <span>Только свободные</span>
                    </Space>
                    <Switch
                        size="small"
                        checked={state.showOnlyFreeDrivers}
                        onChange={(checked) => onChange({ showOnlyFreeDrivers: checked })}
                    />
                </Space>

                {/* Следить за выбранным */}
                <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                    <Space>
                        <AimOutlined />
                        <span>Следить за выбранным</span>
                    </Space>
                    <Switch
                        size="small"
                        checked={state.followSelected}
                        onChange={(checked) => onChange({ followSelected: checked })}
                    />
                </Space>

                <Divider style={{ margin: '8px 0' }} />

                {/* Кнопки */}
                <Space style={{ width: '100%' }}>
                    <Button
                        size="small"
                        icon={<AimOutlined />}
                        onClick={onCenterOnSelected}
                        style={{ flex: 1 }}
                    >
                        Центр
                    </Button>
                    <Button
                        size="small"
                        onClick={onResetView}
                        style={{ flex: 1 }}
                    >
                        Сбросить
                    </Button>
                </Space>
            </Space>
        </Card>
    );
};
