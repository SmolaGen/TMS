import React from 'react';
import { Card, Space, Badge } from 'antd';

interface LegendItem {
    status: string;
    label: string;
    color: string;
}

const legendItems: LegendItem[] = [
    { status: 'available', label: 'Свободен', color: '#52c41a' },
    { status: 'busy', label: 'Занят', color: '#faad14' },
    { status: 'in_progress', label: 'На заказе', color: '#1890ff' },
    { status: 'offline', label: 'Офлайн', color: '#d9d9d9' },
];

export const MapLegend: React.FC = () => {
    return (
        <Card
            size="small"
            style={{
                position: 'absolute',
                bottom: 20,
                left: 10,
                zIndex: 1000,
                boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            }}
        >
            <Space direction="vertical" size="small">
                {legendItems.map((item) => (
                    <Space key={item.status}>
                        <Badge
                            color={item.color}
                            style={{ width: 10, height: 10 }}
                        />
                        <span style={{ fontSize: 12 }}>{item.label}</span>
                    </Space>
                ))}
            </Space>
        </Card>
    );
};
