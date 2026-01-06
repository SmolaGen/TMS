import React from 'react';
import { Row, Col, Card, Statistic, Skeleton } from 'antd';
import {
    ShoppingCartOutlined,
    CarOutlined,
    CheckCircleOutlined,
    StarOutlined,
    ClockCircleOutlined,
} from '@ant-design/icons';
import { useKPIStats } from '../../hooks/useKPIStats';

const cardStyle: React.CSSProperties = {
    borderRadius: 12,
    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
    border: 'none',
    height: '100%',
};

const iconStyle = (color: string): React.CSSProperties => ({
    fontSize: 24,
    color,
    padding: 12,
    borderRadius: 12,
    backgroundColor: `${color}15`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
});

export const KPIWidgets: React.FC = () => {
    const { data, isLoading, error } = useKPIStats();

    if (isLoading) {
        return (
            <Row gutter={[16, 16]}>
                {[1, 2, 3, 4, 5].map((i) => (
                    <Col key={i} xs={12} sm={8} md={6} lg={4.8} xl={4.8}>
                        <Card style={cardStyle} size="small">
                            <Skeleton active paragraph={{ rows: 0 }} title={{ width: '100%' }} />
                        </Card>
                    </Col>
                ))}
            </Row>
        );
    }

    if (error || !data) {
        return null;
    }

    const { stats } = data;

    const kpiItems = [
        {
            title: 'Активных заказов',
            value: stats.activeOrders,
            icon: <ShoppingCartOutlined style={iconStyle('#1890ff')} />,
            color: '#1890ff',
        },
        {
            title: 'Свободных водителей',
            value: stats.freeDrivers,
            icon: <CarOutlined style={iconStyle('#52c41a')} />,
            color: '#52c41a',
        },
        {
            title: 'Выполнено сегодня',
            value: stats.completedToday,
            icon: <CheckCircleOutlined style={iconStyle('#722ed1')} />,
            color: '#722ed1',
        },
        {
            title: 'Средняя оценка',
            value: stats.averageRating,
            precision: 1,
            suffix: '⭐',
            icon: <StarOutlined style={iconStyle('#faad14')} />,
            color: '#faad14',
        },
        {
            title: 'Среднее ожидание',
            value: stats.averageWaitTime,
            suffix: 'мин',
            icon: <ClockCircleOutlined style={iconStyle('#eb2f96')} />,
            color: '#eb2f96',
        },
    ];

    return (
        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            {kpiItems.map((item, index) => (
                <Col key={index} xs={12} sm={8} md={6} lg={4.8} xl={4.8} style={{ flexBasis: '20%', maxWidth: '20%' }}>
                    <Card
                        size="small"
                        style={cardStyle}
                        className="kpi-card"
                        hoverable
                    >
                        <div style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 16
                        }}>
                            {item.icon}
                            <Statistic
                                title={<span style={{ color: '#8c8c8c', fontSize: 13 }}>{item.title}</span>}
                                value={item.value}
                                precision={item.precision}
                                suffix={<span style={{ fontSize: 14, color: '#8c8c8c', marginLeft: 4 }}>{item.suffix}</span>}
                                valueStyle={{
                                    color: item.color,
                                    fontSize: 22,
                                    fontWeight: 700,
                                    lineHeight: '28px'
                                }}
                            />
                        </div>
                    </Card>
                </Col>
            ))}
        </Row>
    );
};
