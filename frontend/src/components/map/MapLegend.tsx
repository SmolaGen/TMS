import React from 'react';
import { Space } from 'antd';

interface LegendItem {
    status: string;
    label: string;
    color: string;
    pulse?: boolean;
}

const legendItems: LegendItem[] = [
    { status: 'available', label: 'Свободен', color: '#10b981', pulse: true },
    { status: 'busy', label: 'Занят', color: '#f59e0b' },
    { status: 'in_progress', label: 'На заказе', color: '#3b82f6' },
    { status: 'offline', label: 'Офлайн', color: '#9ca3af' },
];

export const MapLegend: React.FC = () => {
    return (
        <div
            className="glass-panel"
            style={{
                position: 'absolute',
                bottom: 24,
                left: 24,
                zIndex: 1000,
                padding: '8px 16px',
                borderRadius: 30, // Pill shape
                display: 'flex',
                alignItems: 'center',
            }}
        >
            <Space size="large">
                {legendItems.map((item) => (
                    <Space key={item.status} size="small" align="center">
                        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                            <div style={{
                                width: 10,
                                height: 10,
                                borderRadius: '50%',
                                backgroundColor: item.color,
                                boxShadow: `0 0 8px ${item.color}80`,
                            }} />
                            {item.pulse && (
                                <div style={{
                                    position: 'absolute',
                                    width: 10,
                                    height: 10,
                                    borderRadius: '50%',
                                    backgroundColor: item.color,
                                    opacity: 0.5,
                                    animation: 'markerPulse 2s infinite'
                                }} />
                            )}
                        </div>
                        <span style={{
                            fontSize: 12,
                            fontWeight: 600,
                            color: 'var(--tms-text-secondary)'
                        }}>
                            {item.label}
                        </span>
                    </Space>
                ))}
            </Space>
        </div>
    );
};
