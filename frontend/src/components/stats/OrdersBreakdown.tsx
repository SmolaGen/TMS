import React from 'react';
import { Card, Progress, Row, Col, Statistic, Typography } from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  CarOutlined,
} from '@ant-design/icons';
import type { DetailedStats } from '../../hooks/useDetailedStats';

const { Text } = Typography;

interface OrdersBreakdownProps {
  data: DetailedStats['orders'];
  isMobile?: boolean;
}

const statusConfig = {
  completed: { icon: <CheckCircleOutlined />, color: '#52c41a', label: 'Выполнено' },
  cancelled: { icon: <CloseCircleOutlined />, color: '#ff4d4f', label: 'Отменено' },
  pending: { icon: <ClockCircleOutlined />, color: '#faad14', label: 'Ожидает' },
  in_progress: { icon: <CarOutlined />, color: '#1890ff', label: 'В процессе' },
};

const priorityConfig = {
  urgent: { color: '#ff4d4f', label: 'Срочно' },
  high: { color: '#faad14', label: 'Высокий' },
  normal: { color: '#52c41a', label: 'Обычный' },
  low: { color: '#8c8c8c', label: 'Низкий' },
};

export const OrdersBreakdown: React.FC<OrdersBreakdownProps> = ({ data, isMobile = false }) => {
  const total = data.total;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: isMobile ? 12 : 16 }}>
      <Row gutter={isMobile ? [12, 12] : [16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card
            size="small"
            style={{
              background: 'var(--tms-bg-container)',
              borderRadius: 8,
              textAlign: 'center',
            }}
          >
            <Statistic
              title={<Text type="secondary">Всего заказов</Text>}
              value={total}
              valueStyle={{ fontSize: isMobile ? 20 : 24, fontWeight: 700 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            size="small"
            style={{
              background: 'var(--tms-bg-container)',
              borderRadius: 8,
              textAlign: 'center',
            }}
          >
            <Statistic
              title={<Text type="secondary">Средний чек</Text>}
              value={data.averageRevenue}
              suffix="₽"
              valueStyle={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            size="small"
            style={{
              background: 'var(--tms-bg-container)',
              borderRadius: 8,
              textAlign: 'center',
            }}
          >
            <Statistic
              title={<Text type="secondary">Общая выручка</Text>}
              value={data.totalRevenue}
              suffix="₽"
              valueStyle={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card
            size="small"
            style={{
              background: 'var(--tms-bg-container)',
              borderRadius: 8,
              textAlign: 'center',
            }}
          >
            <Statistic
              title={<Text type="secondary">Выполнено</Text>}
              value={data.byStatus.completed}
              suffix={`/ ${total}`}
              valueStyle={{ fontSize: isMobile ? 20 : 24, fontWeight: 700, color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      <Card
        title={<Text strong>По статусам</Text>}
        size="small"
        style={{ background: 'var(--tms-bg-container)', borderRadius: 8 }}
      >
        <Row gutter={[16, 16]}>
          {Object.entries(data.byStatus).map(([status, count]) => {
            const config = statusConfig[status as keyof typeof statusConfig];
            if (!config) return null;

            const percent = ((count / total) * 100).toFixed(1);

            return (
              <Col xs={12} md={6} key={status}>
                <div style={{ marginBottom: 8 }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      marginBottom: 4,
                    }}
                  >
                    <span style={{ color: config.color }}>{config.icon}</span>
                    <Text style={{ fontSize: isMobile ? 12 : 13 }}>{config.label}</Text>
                    <Text strong style={{ marginLeft: 'auto' }}>
                      {count}
                    </Text>
                  </div>
                  <Progress
                    percent={parseFloat(percent)}
                    strokeColor={config.color}
                    showInfo={false}
                    size="small"
                    strokeWidth={8}
                    style={{ marginBottom: 4 }}
                  />
                  <Text type="secondary" style={{ fontSize: isMobile ? 10 : 11 }}>
                    {percent}%
                  </Text>
                </div>
              </Col>
            );
          })}
        </Row>
      </Card>

      <Card
        title={<Text strong>По приоритету</Text>}
        size="small"
        style={{ background: 'var(--tms-bg-container)', borderRadius: 8 }}
      >
        <Row gutter={[16, 12]}>
          {Object.entries(data.byPriority).map(([priority, count]) => {
            const config = priorityConfig[priority as keyof typeof priorityConfig];
            if (!config) return null;

            const percent = ((count / total) * 100).toFixed(1);

            return (
              <Col xs={12} md={6} key={priority}>
                <div>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      marginBottom: 4,
                    }}
                  >
                    <div
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: config.color,
                      }}
                    />
                    <Text style={{ fontSize: isMobile ? 12 : 13 }}>{config.label}</Text>
                    <Text strong style={{ marginLeft: 'auto' }}>
                      {count}
                    </Text>
                  </div>
                  <Progress
                    percent={parseFloat(percent)}
                    strokeColor={config.color}
                    showInfo={false}
                    size="small"
                    strokeWidth={6}
                  />
                </div>
              </Col>
            );
          })}
        </Row>
      </Card>
    </div>
  );
};
