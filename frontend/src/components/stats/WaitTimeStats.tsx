import React from 'react';
import { Row, Col, Card, Statistic, Typography } from 'antd';
import { ClockCircleOutlined, LoginOutlined, SendOutlined } from '@ant-design/icons';
import type { DetailedStats } from '../../hooks/useDetailedStats';

const { Text } = Typography;

interface WaitTimeStatsProps {
    data: DetailedStats['waitTimes'];
    isMobile?: boolean;
}

export const WaitTimeStats: React.FC<WaitTimeStatsProps> = ({ data, isMobile = false }) => {
    const stats = [
        {
            title: 'Среднее ожидание назначения',
            value: data.averageWaitTime.toFixed(1),
            suffix: 'мин',
            icon: <ClockCircleOutlined style={{ color: '#1890ff' }} />,
        },
        {
            title: 'Среднее время подачи (Pickup)',
            value: data.averagePickupTime.toFixed(1),
            suffix: 'мин',
            icon: <LoginOutlined style={{ color: '#52c41a' }} />,
        },
        {
            title: 'Среднее время доставки',
            value: data.averageDeliveryTime.toFixed(1),
            suffix: 'мин',
            icon: <SendOutlined style={{ color: '#faad14' }} />,
        },
    ];

    return (
        <Row gutter={isMobile ? [12, 12] : [16, 16]}>
            {stats.map((stat, index) => (
                <Col xs={24} sm={8} key={index}>
                    <Card
                        size="small"
                        style={{
                            background: 'var(--tms-bg-container)',
                            borderRadius: 8,
                            textAlign: 'center',
                        }}
                    >
                        <div style={{ marginBottom: 8, fontSize: 24 }}>
                            {stat.icon}
                        </div>
                        <Statistic
                            title={<Text type="secondary">{stat.title}</Text>}
                            value={stat.value}
                            suffix={stat.suffix}
                            valueStyle={{ fontSize: isMobile ? 20 : 24, fontWeight: 700 }}
                        />
                    </Card>
                </Col>
            ))}
        </Row>
    );
};
