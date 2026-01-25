import React, { useMemo } from 'react';
import { Row, Col, Card, Statistic, Progress, Space, Alert, Button } from 'antd';
import {
  CheckCircleOutlined,
  SyncOutlined,
  CloseCircleOutlined,
  ShoppingOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import { useOrdersRaw } from '../../hooks/useOrders';
import type { OrderResponse } from '../../types/api';
import { OrderStatus } from '../../types/api';

interface DashboardStatsProps {
  dateRange?: [Date, Date];
}

export const DashboardStats: React.FC<DashboardStatsProps> = ({ dateRange }) => {
  const { data: orders = [], error, refetch } = useOrdersRaw(dateRange);

  const stats = useMemo(() => {
    const total = orders.length;
    const completed = orders.filter(
      (o: OrderResponse) => o.status === OrderStatus.COMPLETED,
    ).length;
    const inProgress = orders.filter(
      (o: OrderResponse) =>
        o.status === OrderStatus.IN_PROGRESS ||
        o.status === OrderStatus.DRIVER_ARRIVED ||
        o.status === OrderStatus.EN_ROUTE_PICKUP,
    ).length;
    const cancelled = orders.filter(
      (o: OrderResponse) => o.status === OrderStatus.CANCELLED,
    ).length;
    const pending = orders.filter(
      (o: OrderResponse) => o.status === OrderStatus.PENDING || o.status === OrderStatus.ASSIGNED,
    ).length;

    const completionRate =
      total > 0 ? Math.round((completed / (total - (cancelled || 0))) * 100) : 0;

    return { total, completed, inProgress, cancelled, pending, completionRate };
  }, [orders]);

  if (error) {
    return (
      <div style={{ marginBottom: 16 }}>
        <Alert
          message="Ошибка статистики"
          description="Не удалось загрузить данные заказов для расчета статистики."
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

  return (
    <div style={{ marginBottom: 16 }}>
      <Row gutter={16}>
        <Col span={6}>
          <Card bordered={false} hoverable>
            <Statistic
              title="Всего заказов"
              value={stats.total}
              prefix={<ShoppingOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card bordered={false} hoverable>
            <Statistic
              title="Выполнено"
              value={stats.completed}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
              suffix={
                <small style={{ fontSize: '0.6em', color: '#8c8c8c' }}>
                  {stats.completionRate}%
                </small>
              }
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card bordered={false} hoverable>
            <Statistic
              title="В процессе"
              value={stats.inProgress}
              prefix={<SyncOutlined spin={stats.inProgress > 0} />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card bordered={false} hoverable>
            <Statistic
              title="Отменено"
              value={stats.cancelled}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Card bordered={false} size="small" style={{ marginTop: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <span>Общий прогресс выполнения (без учета отмененных)</span>
          <Progress
            percent={stats.completionRate}
            status={stats.completionRate === 100 ? 'success' : 'active'}
            strokeColor={{
              '0%': '#108ee9',
              '100%': '#87d068',
            }}
          />
        </Space>
      </Card>
    </div>
  );
};
