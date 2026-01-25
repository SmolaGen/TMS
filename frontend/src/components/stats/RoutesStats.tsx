import React from 'react';
import { Card, Row, Col, Statistic, Typography } from 'antd';
import { GlobalOutlined, ThunderboltOutlined, CarOutlined } from '@ant-design/icons';
import type { DetailedStats } from '../../hooks/useDetailedStats';

const { Text } = Typography;

interface RoutesStatsProps {
  data: DetailedStats['routes'];
  isMobile?: boolean;
}

export const RoutesStats: React.FC<RoutesStatsProps> = ({ data, isMobile = false }) => {
  const stats = [
    {
      title: 'Общий пробег',
      value: data.totalDistance,
      suffix: 'км',
      icon: <CarOutlined style={{ color: '#52c41a' }} />,
      prefix: null,
    },
    {
      title: 'Средняя дистанция',
      value: data.averageDistance.toFixed(1),
      suffix: 'км',
      icon: <GlobalOutlined style={{ color: '#1890ff' }} />,
      prefix: null,
    },
    {
      title: 'Самый длинный маршрут',
      value: data.longestRoute.distance,
      suffix: 'км',
      icon: <ThunderboltOutlined style={{ color: '#faad14' }} />,
      prefix: '#',
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
            <div style={{ marginBottom: 8, fontSize: 24 }}>{stat.icon}</div>
            <Statistic
              title={<Text type="secondary">{stat.title}</Text>}
              value={stat.value}
              suffix={stat.suffix}
              prefix={stat.prefix}
              valueStyle={{ fontSize: isMobile ? 20 : 24, fontWeight: 700 }}
            />
          </Card>
        </Col>
      ))}
    </Row>
  );
};
