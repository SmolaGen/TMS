import React from 'react';
import { Card, Statistic, Skeleton } from 'antd';
import {
    ShoppingCartOutlined,
    CarOutlined,
    CheckCircleOutlined,
    StarOutlined,
    ClockCircleOutlined,
} from '@ant-design/icons';
import { useKPIStats } from '../../hooks/useKPIStats';

const iconStyle = (color: string, isMobile: boolean): React.CSSProperties => ({
    fontSize: isMobile ? 18 : 24,
    color,
    padding: isMobile ? 8 : 12,
    borderRadius: 10,
    backgroundColor: `${color}15`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
});

// Хук для определения мобильного устройства
const useIsMobile = () => {
    const [isMobile, setIsMobile] = React.useState(
        typeof window !== 'undefined' ? window.innerWidth <= 768 : false
    );

    React.useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth <= 768);
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, []);

    return isMobile;
};

export const KPIWidgets: React.FC = () => {
    const { data, isLoading, error } = useKPIStats();
    const isMobile = useIsMobile();

    if (isLoading) {
        return (
            <div style={{
                display: 'flex',
                gap: isMobile ? 8 : 16,
                overflowX: 'auto',
                paddingBottom: 8,
                marginBottom: isMobile ? 8 : 16,
            }}>
                {[1, 2, 3, 4, 5].map((i) => (
                    <Card key={i} size="small" style={{
                        minWidth: isMobile ? 120 : 180,
                        borderRadius: 12,
                        flexShrink: 0,
                    }}>
                        <Skeleton active paragraph={{ rows: 0 }} title={{ width: '100%' }} />
                    </Card>
                ))}
            </div>
        );
    }

    if (error || !data) {
        return null;
    }

    const { stats } = data;

    const kpiItems = [
        {
            title: 'Активных',
            fullTitle: 'Активных заказов',
            value: stats.activeOrders,
            icon: <ShoppingCartOutlined style={iconStyle('#1890ff', isMobile)} />,
            color: '#1890ff',
        },
        {
            title: 'Свободных',
            fullTitle: 'Свободных водителей',
            value: stats.freeDrivers,
            icon: <CarOutlined style={iconStyle('#52c41a', isMobile)} />,
            color: '#52c41a',
        },
        {
            title: 'Выполнено',
            fullTitle: 'Выполнено сегодня',
            value: stats.completedToday,
            icon: <CheckCircleOutlined style={iconStyle('#722ed1', isMobile)} />,
            color: '#722ed1',
        },
        {
            title: 'Оценка',
            fullTitle: 'Средняя оценка',
            value: stats.averageRating,
            precision: 1,
            suffix: '⭐',
            icon: <StarOutlined style={iconStyle('#faad14', isMobile)} />,
            color: '#faad14',
        },
        {
            title: 'Ожидание',
            fullTitle: 'Среднее ожидание',
            value: stats.averageWaitTime,
            suffix: 'мин',
            icon: <ClockCircleOutlined style={iconStyle('#eb2f96', isMobile)} />,
            color: '#eb2f96',
        },
    ];

    return (
        <div style={{
            display: 'flex',
            gap: isMobile ? 8 : 16,
            overflowX: 'auto',
            paddingBottom: 8,
            marginBottom: isMobile ? 8 : 16,
            WebkitOverflowScrolling: 'touch',
        }}>
            {kpiItems.map((item, index) => (
                <Card
                    key={index}
                    size="small"
                    style={{
                        minWidth: isMobile ? 100 : 180,
                        borderRadius: 12,
                        flexShrink: 0,
                        boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                        border: 'none',
                    }}
                    className="kpi-card"
                    hoverable
                >
                    <div style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: isMobile ? 8 : 16,
                        flexDirection: isMobile ? 'column' : 'row',
                    }}>
                        {item.icon}
                        <Statistic
                            title={
                                <span style={{
                                    color: 'var(--tms-text-secondary)',
                                    fontSize: isMobile ? 11 : 13,
                                    whiteSpace: 'nowrap',
                                }}>
                                    {isMobile ? item.title : item.fullTitle}
                                </span>
                            }
                            value={item.value}
                            precision={item.precision}
                            suffix={
                                <span style={{
                                    fontSize: isMobile ? 12 : 14,
                                    color: 'var(--tms-text-secondary)',
                                    marginLeft: 2,
                                }}>
                                    {item.suffix}
                                </span>
                            }
                            styles={{
                                content: {
                                    color: item.color,
                                    fontSize: isMobile ? 18 : 22,
                                    fontWeight: 700,
                                    lineHeight: isMobile ? '22px' : '28px',
                                }
                            }}
                        />
                    </div>
                </Card>
            ))}
        </div>
    );
};
