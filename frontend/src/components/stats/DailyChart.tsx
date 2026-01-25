import React from 'react';
import { Typography } from 'antd';

const { Text } = Typography;

interface DailyChartProps {
  data: Array<{ date: string; count: number; revenue: number }>;
  isMobile?: boolean;
}

export const DailyChart: React.FC<DailyChartProps> = ({ data, isMobile = false }) => {
  const maxCount = Math.max(...data.map((d) => d.count));
  const maxRevenue = Math.max(...data.map((d) => d.revenue));

  const chartHeight = isMobile ? 150 : 200;
  const barWidth = isMobile ? 20 : 30;
  const gap = isMobile ? 12 : 16;
  const totalWidth = data.length * (barWidth + gap);

  return (
    <div
      style={{
        height: chartHeight + 60,
        padding: isMobile ? '16px 8px' : '20px',
        background: 'var(--tms-bg-container)',
        borderRadius: 8,
        overflow: 'auto',
      }}
    >
      <div
        style={{
          width: '100%',
          minWidth: totalWidth,
          height: chartHeight,
          display: 'flex',
          alignItems: 'flex-end',
          gap,
          position: 'relative',
        }}
      >
        {data.map((item) => {
          const countHeight = (item.count / maxCount) * 100;
          const revenueHeight = (item.revenue / maxRevenue) * 100;

          return (
            <div
              key={item.date}
              style={{
                width: barWidth,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <div
                style={{
                  width: '100%',
                  height: chartHeight,
                  display: 'flex',
                  alignItems: 'flex-end',
                  gap: 4,
                  position: 'relative',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = 'scale(1.05)';
                  e.currentTarget.style.transition = 'transform 0.2s';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = 'scale(1)';
                }}
              >
                <div
                  style={{
                    width: '45%',
                    height: `${countHeight}%`,
                    background: '#52c41a',
                    borderRadius: '4px 4px 0 0',
                    transition: 'all 0.3s',
                    position: 'relative',
                    cursor: 'pointer',
                  }}
                  title={`${item.count} заказов`}
                >
                  <Text
                    style={{
                      position: 'absolute',
                      top: -16,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      fontSize: 9,
                      color: 'var(--tms-text-secondary)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {item.count}
                  </Text>
                </div>

                <div
                  style={{
                    width: '45%',
                    height: `${revenueHeight}%`,
                    background: '#1890ff',
                    borderRadius: '4px 4px 0 0',
                    transition: 'all 0.3s',
                    position: 'relative',
                    cursor: 'pointer',
                  }}
                  title={`${item.revenue.toLocaleString()} ₽`}
                >
                  <Text
                    style={{
                      position: 'absolute',
                      top: -16,
                      left: '50%',
                      transform: 'translateX(-50%)',
                      fontSize: 9,
                      color: 'var(--tms-text-secondary)',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {(item.revenue / 1000).toFixed(1)}k
                  </Text>
                </div>
              </div>

              <Text
                style={{
                  fontSize: isMobile ? 9 : 10,
                  color: 'var(--tms-text-tertiary)',
                  textAlign: 'center',
                }}
              >
                {item.date}
              </Text>
            </div>
          );
        })}
      </div>

      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          gap: 24,
          marginTop: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div
            style={{
              width: 12,
              height: 12,
              background: '#52c41a',
              borderRadius: 2,
            }}
          />
          <Text style={{ fontSize: isMobile ? 11 : 12, color: 'var(--tms-text-secondary)' }}>
            Заказы
          </Text>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div
            style={{
              width: 12,
              height: 12,
              background: '#1890ff',
              borderRadius: 2,
            }}
          />
          <Text style={{ fontSize: isMobile ? 11 : 12, color: 'var(--tms-text-secondary)' }}>
            Выручка (₽)
          </Text>
        </div>
      </div>
    </div>
  );
};
