import React from 'react';
import { Card, List, Tag, Space, Typography, Empty, Timeline } from 'antd';
import { ClockCircleOutlined, EnvironmentOutlined, UserOutlined } from '@ant-design/icons';
import { useDriverSchedule } from '../../hooks/useBatchAssignment';

import dayjs from 'dayjs';

const { Text } = Typography;

interface DriverScheduleViewProps {
  driverId: number;
  targetDate: string;
  onOrderClick?: (orderId: number) => void;
}

export const DriverScheduleView: React.FC<DriverScheduleViewProps> = ({
  driverId,
  targetDate,
  onOrderClick,
}) => {
  const { data, isLoading, error } = useDriverSchedule(driverId, targetDate);

  if (isLoading) {
    return <Card loading={true}>Загрузка расписания...</Card>;
  }

  if (error) {
    return (
      <Card>
        <Empty description="Ошибка загрузки расписания" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </Card>
    );
  }

  if (!data) {
    return (
      <Card>
        <Empty description="Данные не найдены" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </Card>
    );
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'orange';
      case 'assigned':
        return 'blue';
      case 'in_progress':
        return 'purple';
      case 'completed':
        return 'green';
      case 'cancelled':
        return 'red';
      default:
        return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return 'Ожидает';
      case 'assigned':
        return 'Назначен';
      case 'in_progress':
        return 'Выполняется';
      case 'completed':
        return 'Завершён';
      case 'cancelled':
        return 'Отменён';
      default:
        return status;
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'red';
      case 'high':
        return 'orange';
      case 'normal':
        return 'blue';
      case 'low':
        return 'green';
      default:
        return 'default';
    }
  };

  const getPriorityText = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'Срочный';
      case 'high':
        return 'Высокий';
      case 'normal':
        return 'Обычный';
      case 'low':
        return 'Низкий';
      default:
        return priority;
    }
  };

  // Сортировка заказов по времени начала
  const sortedSchedule = [...data.schedule].sort((a, b) => {
    const timeA = a.time_start ? new Date(a.time_start).getTime() : 0;
    const timeB = b.time_start ? new Date(b.time_start).getTime() : 0;
    return timeA - timeB;
  });

  return (
    <Card
      title={
        <Space>
          <UserOutlined />
          <span>Расписание: {data.driver_name}</span>
          <Tag color="blue">{dayjs(targetDate).format('DD.MM.YYYY')}</Tag>
        </Space>
      }
      size="small"
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        {/* Статистика */}
        <Space wrap>
          <Text strong>Всего заказов: {data.total_orders}</Text>
          <Text strong>Свободных слотов: {data.available_slots}</Text>
        </Space>

        {/* Список заказов */}
        {sortedSchedule.length > 0 ? (
          <List
            size="small"
            dataSource={sortedSchedule}
            renderItem={(item) => (
              <List.Item
                style={{ cursor: onOrderClick ? 'pointer' : 'default' }}
                onClick={() => onOrderClick?.(item.order_id)}
              >
                <List.Item.Meta
                  avatar={<ClockCircleOutlined style={{ color: '#1890ff' }} />}
                  title={
                    <Space>
                      <span>Заказ #{item.order_id}</span>
                      <Tag color={getStatusColor(item.status)}>{getStatusText(item.status)}</Tag>
                      <Tag color={getPriorityColor(item.priority)}>
                        {getPriorityText(item.priority)}
                      </Tag>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Space>
                        <ClockCircleOutlined />
                        <Text>
                          {item.time_start ? dayjs(item.time_start).format('HH:mm') : '??:??'} -{' '}
                          {item.time_end ? dayjs(item.time_end).format('HH:mm') : '??:??'}
                        </Text>
                      </Space>

                      {item.pickup_address && (
                        <Space>
                          <EnvironmentOutlined style={{ color: '#52c41a' }} />
                          <Text ellipsis style={{ maxWidth: 300 }}>
                            <strong>От:</strong> {item.pickup_address}
                          </Text>
                        </Space>
                      )}

                      {item.dropoff_address && (
                        <Space>
                          <EnvironmentOutlined style={{ color: '#f5222d' }} />
                          <Text ellipsis style={{ maxWidth: 300 }}>
                            <strong>До:</strong> {item.dropoff_address}
                          </Text>
                        </Space>
                      )}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        ) : (
          <Empty description="На эту дату заказов нет" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        )}

        {/* Временная шкала для визуализации */}
        {sortedSchedule.length > 0 && (
          <Card size="small" title="Временная шкала">
            <Timeline mode="left">
              {sortedSchedule.map((item) => (
                <Timeline.Item
                  key={item.order_id}
                  color={getStatusColor(item.status)}
                  label={
                    <Space direction="vertical" size={0}>
                      <Text strong>
                        {item.time_start ? dayjs(item.time_start).format('HH:mm') : '??:??'}
                      </Text>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        Заказ #{item.order_id}
                      </Text>
                    </Space>
                  }
                >
                  <Space direction="vertical" size={2}>
                    <Text strong>{item.pickup_address || 'Адрес не указан'}</Text>
                    <Text type="secondary">→ {item.dropoff_address || 'Адрес не указан'}</Text>
                    <Space>
                      <Tag color={getPriorityColor(item.priority)}>
                        {getPriorityText(item.priority)}
                      </Tag>
                      <Tag color={getStatusColor(item.status)}>{getStatusText(item.status)}</Tag>
                    </Space>
                  </Space>
                </Timeline.Item>
              ))}
            </Timeline>
          </Card>
        )}
      </Space>
    </Card>
  );
};
