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
                padding: '10px 20px',
                borderRadius: 40,
                border: '1px solid rgba(255, 255, 255, 0.05)',
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
                display: 'flex',
                alignItems: 'center',
            }}
        >
            <Space size={24}>
                {legendItems.map((item) => (
                    <Space key={item.status} size={8} align="center">
                        <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                            <div style={{
                                width: 8,
                                height: 8,
                                borderRadius: '50%',
                                backgroundColor: item.color,
                                boxShadow: `0 0 10px ${item.color}`,
                            }} />
                            {item.pulse && (
                                <div style={{
                                    position: 'absolute',
                                    width: 8,
                                    height: 8,
                                    borderRadius: '50%',
                                    backgroundColor: item.color,
                                    opacity: 0.4,
                                    animation: 'markerPulse 2s infinite'
                                }} />
                            )}
                        </div>
                        <span style={{
                            fontSize: 11,
                            fontWeight: 700,
                            letterSpacing: '0.02em',
                            textTransform: 'uppercase',
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
