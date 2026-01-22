import React from 'react';
import { Statistic, Skeleton, Alert, Button } from 'antd';
import {
    ShoppingCartOutlined,
    CarOutlined,
    CheckCircleOutlined,
    StarOutlined,
    ClockCircleOutlined,
    ReloadOutlined,
} from '@ant-design/icons';
import { useKPIStats } from '../../hooks/useKPIStats';

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
    const { data, isLoading, error, refetch } = useKPIStats();
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
                    <div key={i} className="glass-card" style={{
                        minWidth: isMobile ? 120 : 180,
                        padding: 16,
                        flexShrink: 0,
                        height: 100,
                    }}>
                        <Skeleton active paragraph={{ rows: 1 }} title={{ width: '50%' }} />
                    </div>
                ))}
            </div>
        );
    }

    if (error) {
        return (
            <div style={{ marginBottom: 16 }}>
                <Alert
                    message="Ошибка KPI"
                    description="Не удалось загрузить ключевые показатели."
                    type="error"
                    showIcon
                    action={
                        <Button size="small" icon={<ReloadOutlined />} onClick={() => refetch()}>
                            Повторить
                        </Button>
                    }
                />
            </div>
        );
    }

    if (!data) {
        return null;
    }

    const { stats } = data;

    const kpiItems = [
        {
            title: 'Активных',
            fullTitle: 'Активных заказов',
            value: stats.activeOrders,
            icon: <ShoppingCartOutlined />,
            gradient: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
            color: '#3b82f6',
        },
        {
            title: 'Свободных',
            fullTitle: 'Свободных водителей',
            value: stats.freeDrivers,
            icon: <CarOutlined />,
            gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
            color: '#10b981',
        },
        {
            title: 'Выполнено',
            fullTitle: 'Выполнено сегодня',
            value: stats.completedToday,
            icon: <CheckCircleOutlined />,
            gradient: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
            color: '#8b5cf6',
        },
        {
            title: 'Оценка',
            fullTitle: 'Средняя оценка',
            value: stats.averageRating,
            precision: 1,
            suffix: '⭐',
            icon: <StarOutlined />,
            gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
            color: '#f59e0b',
        },
        {
            title: 'Ожидание',
            fullTitle: 'Среднее ожидание',
            value: stats.averageWaitTime,
            suffix: 'мин',
            icon: <ClockCircleOutlined />,
            gradient: 'linear-gradient(135deg, #ec4899 0%, #db2777 100%)',
            color: '#ec4899',
        },
    ];

    return (
        <div style={{
            display: 'flex',
            gap: isMobile ? 8 : 20,
            overflowX: 'auto',
            paddingBottom: 12,
            marginBottom: isMobile ? 8 : 8,
            WebkitOverflowScrolling: 'touch',
            paddingLeft: 4,
            paddingRight: 4,
        }}>
            {kpiItems.map((item, index) => (
                <div
                    key={index}
                    className="glass-card kpi-card hover-lift"
                    style={{
                        minWidth: isMobile ? 110 : 200,
                        padding: isMobile ? 12 : 16,
                        flexShrink: 0,
                        display: 'flex',
                        flexDirection: isMobile ? 'column' : 'row',
                        alignItems: 'center',
                        gap: isMobile ? 8 : 16,
                        animationDelay: `${index * 0.1}s`,
                        cursor: 'default',
                    }}
                >
                    <div style={{
                        width: isMobile ? 40 : 48,
                        height: isMobile ? 40 : 48,
                        borderRadius: 14,
                        background: item.gradient,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#fff',
                        fontSize: isMobile ? 20 : 24,
                        boxShadow: `0 8px 16px -4px ${item.color}50`,
                        flexShrink: 0,
                    }}>
                        {item.icon}
                    </div>

                    <div style={{ flex: 1, textAlign: isMobile ? 'center' : 'left' }}>
                        <div style={{
                            fontSize: isMobile ? 11 : 13,
                            color: 'var(--tms-text-secondary)',
                            whiteSpace: 'nowrap',
                            fontWeight: 500,
                            marginBottom: 2
                        }}>
                            {isMobile ? item.title : item.fullTitle}
                        </div>
                        <Statistic
                            value={item.value}
                            precision={item.precision}
                            suffix={
                                <span style={{
                                    fontSize: isMobile ? 12 : 14,
                                    color: 'var(--tms-text-tertiary)',
                                    marginLeft: 2,
                                    fontWeight: 500
                                }}>
                                    {item.suffix}
                                </span>
                            }
                            valueStyle={{
                                color: 'var(--tms-text-primary)',
                                fontSize: isMobile ? 20 : 26,
                                fontWeight: 700,
                                lineHeight: 1.1,
                                letterSpacing: '-0.5px'
                            }}
                        />
                    </div>
                </div>
            ))}
        </div>
    );
};
