import React from 'react';
import { Typography } from 'antd';

const { Text } = Typography;

interface HourlyChartProps {
  data: Array<{ hour: number; count: number }>;
  isMobile?: boolean;
}

export const HourlyChart: React.FC<HourlyChartProps> = ({ data, isMobile = false }) => {
  const maxCount = Math.max(...data.map((d) => d.count));

  return (
    <div
      style={{
        height: 200,
        display: 'flex',
        alignItems: 'flex-end',
        gap: isMobile ? 2 : 4,
        padding: isMobile ? '16px 8px' : '20px',
        background: 'var(--tms-bg-container)',
        borderRadius: 8,
      }}
    >
      {data.map((item) => {
        const height = (item.count / maxCount) * 100;
        const isActive = item.hour >= 8 && item.hour <= 20;

        return (
          <div
            key={item.hour}
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              height: '100%',
            }}
          >
            <div
              style={{
                width: '100%',
                height: `${height}%`,
                minHeight: 4,
                background: isActive ? 'var(--tms-primary)' : 'rgba(24, 144, 255, 0.3)',
                borderRadius: '4px 4px 0 0',
                transition: 'all 0.2s',
                cursor: 'pointer',
                position: 'relative',
              }}
              title={`${item.count} заказов в ${item.hour}:00`}
              onMouseEnter={(e) => {
                e.currentTarget.style.opacity = '0.8';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.opacity = '1';
              }}
            >
              {item.count > 0 && (
                <Text
                  style={{
                    position: 'absolute',
                    top: -18,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    fontSize: 10,
                    color: 'var(--tms-text-secondary)',
                    display: isMobile ? 'none' : 'block',
                  }}
                >
                  {item.count}
                </Text>
              )}
            </div>
            {item.hour % 6 === 0 && (
              <Text
                style={{
                  fontSize: isMobile ? 9 : 10,
                  color: 'var(--tms-text-tertiary)',
                  marginTop: 4,
                  textAlign: 'center',
                }}
              >
                {item.hour}ч
              </Text>
            )}
          </div>
        );
      })}
    </div>
  );
};
