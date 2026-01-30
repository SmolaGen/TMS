import React, { useState } from 'react';
import { Calendar, Badge, Card, Space, Typography, Tag, List, Empty, Tooltip } from 'antd';
import { ClockCircleOutlined, EnvironmentOutlined, UserOutlined } from '@ant-design/icons';
import { useOrdersRaw } from '../../hooks/useOrders';
import type { OrderResponse } from '../../types/api';
import dayjs, { Dayjs } from 'dayjs';
import isBetween from 'dayjs/plugin/isBetween';

dayjs.extend(isBetween);

const { Text } = Typography;

interface CalendarViewProps {
  onOrderSelect?: (orderId: number) => void;
  selectedOrderId?: number | string | null;
}

export const CalendarView: React.FC<CalendarViewProps> = ({
  onOrderSelect,
  selectedOrderId,
}) => {
  const [selectedDate, setSelectedDate] = useState<Dayjs>(dayjs());
  const [viewMode, setViewMode] = useState<'month' | 'year'>('month');

  // Получаем заказы за месяц
  const startOfMonth = selectedDate.startOf('month').toDate();
  const endOfMonth = selectedDate.endOf('month').toDate();
  const { data: orders = [], isLoading, error } = useOrdersRaw([startOfMonth, endOfMonth]);

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

  // Получаем заказы для конкретной даты
  const getOrdersForDate = (date: Dayjs): OrderResponse[] => {
    return orders.filter((order) => {
      if (!order.time_start) return false;
      const orderDate = dayjs(order.time_start);
      return orderDate.isSame(date, 'day');
    });
  };

  // Заказы выбранной даты
  const selectedDateOrders = getOrdersForDate(selectedDate).sort((a, b) => {
    const timeA = a.time_start ? new Date(a.time_start).getTime() : 0;
    const timeB = b.time_start ? new Date(b.time_start).getTime() : 0;
    return timeA - timeB;
  });

  // Рендер ячейки календаря с Badge для заказов
  const dateCellRender = (date: Dayjs) => {
    const dayOrders = getOrdersForDate(date);
    if (dayOrders.length === 0) return null;

    // Группируем по статусам
    const statusCounts: Record<string, number> = {};
    dayOrders.forEach((order) => {
      statusCounts[order.status] = (statusCounts[order.status] || 0) + 1;
    });

    return (
      <div style={{ overflow: 'hidden' }}>
        {Object.entries(statusCounts).slice(0, 3).map(([status, count]) => (
          <Badge
            key={status}
            status={getStatusColor(status) as any}
            text={
              <Text style={{ fontSize: '12px' }}>
                {getStatusText(status)}: {count}
              </Text>
            }
            style={{ display: 'block', whiteSpace: 'nowrap' }}
          />
        ))}
        {Object.keys(statusCounts).length > 3 && (
          <Text type="secondary" style={{ fontSize: '12px' }}>
            +{Object.keys(statusCounts).length - 3} ещё
          </Text>
        )}
      </div>
    );
  };

  // Обработчик выбора даты
  const onSelect = (date: Dayjs) => {
    setSelectedDate(date);
  };

  // Обработчик изменения панели календаря
  const onPanelChange = (date: Dayjs, mode: 'month' | 'year') => {
    setSelectedDate(date);
    setViewMode(mode);
  };

  if (isLoading) {
    return <Card loading={true}>Загрузка календаря...</Card>;
  }

  if (error) {
    return (
      <Card>
        <Empty description="Ошибка загрузки заказов" image={Empty.PRESENTED_IMAGE_SIMPLE} />
      </Card>
    );
  }

  return (
    <div style={{ display: 'flex', gap: '16px', height: '100%' }}>
      {/* Календарь */}
      <Card
        style={{ flex: 1 }}
        size="small"
        title={
          <Space>
            <ClockCircleOutlined />
            <span>Календарь заказов</span>
            <Tag color="blue">{selectedDate.format('MMMM YYYY')}</Tag>
          </Space>
        }
      >
        <Calendar
          value={selectedDate}
          onSelect={onSelect}
          onPanelChange={onPanelChange}
          mode={viewMode}
          cellRender={viewMode === 'month' ? dateCellRender : undefined}
          fullscreen={true}
        />
      </Card>

      {/* Список заказов выбранной даты */}
      <Card
        style={{ width: '400px', maxHeight: '100%', overflowY: 'auto' }}
        size="small"
        title={
          <Space>
            <CalendarOutlined />
            <span>Заказы на {selectedDate.format('DD.MM.YYYY')}</span>
          </Space>
        }
      >
        {selectedDateOrders.length > 0 ? (
          <List
            size="small"
            dataSource={selectedDateOrders}
            renderItem={(order) => (
              <List.Item
                style={{
                  cursor: onOrderSelect ? 'pointer' : 'default',
                  background:
                    String(selectedOrderId) === String(order.id) ? '#f0f5ff' : 'transparent',
                  padding: '12px',
                  borderRadius: '4px',
                  marginBottom: '8px',
                }}
                onClick={() => onOrderSelect?.(order.id)}
              >
                <List.Item.Meta
                  avatar={<ClockCircleOutlined style={{ color: '#1890ff', fontSize: '20px' }} />}
                  title={
                    <Space wrap>
                      <Text strong>Заказ #{order.id}</Text>
                      <Tag color={getStatusColor(order.status)}>
                        {getStatusText(order.status)}
                      </Tag>
                      <Tag color={getPriorityColor(order.priority)}>
                        {getPriorityText(order.priority)}
                      </Tag>
                    </Space>
                  }
                  description={
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      {/* Время */}
                      <Space>
                        <ClockCircleOutlined />
                        <Text>
                          {order.time_start
                            ? dayjs(order.time_start).format('HH:mm')
                            : '??:??'}{' '}
                          - {order.time_end ? dayjs(order.time_end).format('HH:mm') : '??:??'}
                        </Text>
                      </Space>

                      {/* Водитель */}
                      {order.driver_name && (
                        <Space>
                          <UserOutlined style={{ color: '#52c41a' }} />
                          <Text strong>{order.driver_name}</Text>
                        </Space>
                      )}

                      {/* Адрес отправления */}
                      {order.pickup_address && (
                        <Tooltip title={order.pickup_address}>
                          <Space>
                            <EnvironmentOutlined style={{ color: '#52c41a' }} />
                            <Text ellipsis style={{ maxWidth: 250 }}>
                              <strong>От:</strong> {order.pickup_address}
                            </Text>
                          </Space>
                        </Tooltip>
                      )}

                      {/* Адрес назначения */}
                      {order.dropoff_address && (
                        <Tooltip title={order.dropoff_address}>
                          <Space>
                            <EnvironmentOutlined style={{ color: '#f5222d' }} />
                            <Text ellipsis style={{ maxWidth: 250 }}>
                              <strong>До:</strong> {order.dropoff_address}
                            </Text>
                          </Space>
                        </Tooltip>
                      )}

                      {/* Цена */}
                      {order.price && (
                        <Text strong style={{ color: '#52c41a' }}>
                          {order.price} ₽
                        </Text>
                      )}

                      {/* Комментарий */}
                      {order.comment && (
                        <Text type="secondary" style={{ fontSize: '12px', fontStyle: 'italic' }}>
                          {order.comment}
                        </Text>
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

        {/* Статистика */}
        {selectedDateOrders.length > 0 && (
          <div
            style={{
              marginTop: '16px',
              padding: '12px',
              background: '#f5f5f5',
              borderRadius: '4px',
            }}
          >
            <Space direction="vertical" size="small" style={{ width: '100%' }}>
              <Text strong>Статистика дня:</Text>
              <Space>
                <Text>Всего заказов: {selectedDateOrders.length}</Text>
              </Space>
              <Space wrap>
                {Object.entries(
                  selectedDateOrders.reduce(
                    (acc, order) => {
                      acc[order.status] = (acc[order.status] || 0) + 1;
                      return acc;
                    },
                    {} as Record<string, number>,
                  ),
                ).map(([status, count]) => (
                  <Tag key={status} color={getStatusColor(status)}>
                    {getStatusText(status)}: {count}
                  </Tag>
                ))}
              </Space>
            </Space>
          </div>
        )}
      </Card>
    </div>
  );
};

// Icon helper component
const CalendarOutlined: React.FC = () => (
  <svg
    viewBox="64 64 896 896"
    focusable="false"
    width="1em"
    height="1em"
    fill="currentColor"
    aria-hidden="true"
  >
    <path d="M880 184H712v-64c0-4.4-3.6-8-8-8h-56c-4.4 0-8 3.6-8 8v64H384v-64c0-4.4-3.6-8-8-8h-56c-4.4 0-8 3.6-8 8v64H144c-17.7 0-32 14.3-32 32v664c0 17.7 14.3 32 32 32h736c17.7 0 32-14.3 32-32V216c0-17.7-14.3-32-32-32zm-40 656H184V460h656v380zM184 392V256h128v48c0 4.4 3.6 8 8 8h56c4.4 0 8-3.6 8-8v-48h256v48c0 4.4 3.6 8 8 8h56c4.4 0 8-3.6 8-8v-48h128v136H184z" />
  </svg>
);
