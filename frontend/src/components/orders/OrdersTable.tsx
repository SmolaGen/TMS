import React from 'react';
import { Table, Space, Button, Tooltip, Typography } from 'antd';
import { EditOutlined, DeleteOutlined, UserAddOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { OrderResponse, DriverResponse } from '../../types/api';
import dayjs from 'dayjs';

interface OrdersTableProps {
  orders: OrderResponse[];
  drivers: DriverResponse[];
  loading?: boolean;
  onSelect: (orderId: number) => void;
  onAssign?: (orderId: number) => void;
  onCancel?: (orderId: number) => void;
}

const statusConfig: Record<string, { color: string; gradient: string; text: string }> = {
  pending: {
    color: '#f59e0b',
    gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    text: 'Ожидает',
  },
  assigned: {
    color: '#3b82f6',
    gradient: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    text: 'Назначен',
  },
  driver_arrived: {
    color: '#06b6d4',
    gradient: 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)',
    text: 'Прибыл',
  },
  in_progress: {
    color: '#10b981',
    gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    text: 'В пути',
  },
  completed: {
    color: '#64748b',
    gradient: 'linear-gradient(135deg, #64748b 0%, #475569 100%)',
    text: 'Завершен',
  },
  cancelled: {
    color: '#ef4444',
    gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
    text: 'Отменен',
  },
};

export const OrdersTable: React.FC<OrdersTableProps> = ({
  orders,
  drivers,
  loading,
  onSelect,
  onAssign,
  onCancel,
}) => {
  const columns: ColumnsType<OrderResponse> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 70,
      sorter: (a, b) => a.id - b.id,
      render: (id) => (
        <Typography.Text
          style={{
            fontFamily: 'monospace',
            color: 'var(--tms-text-tertiary)',
            fontSize: 12,
          }}
        >
          #{id}
        </Typography.Text>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 130,
      render: (status: string) => {
        const config = statusConfig[status] || { color: '#64748b', gradient: '', text: status };
        return (
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              padding: '4px 12px',
              borderRadius: 20,
              background: isDark ? 'rgba(255, 255, 255, 0.05)' : 'rgba(0,0,0,0.03)',
              border: `1px solid ${config.color}33`,
              fontSize: 12,
              fontWeight: 600,
              color: config.color,
            }}
          >
            <div
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: config.color,
                marginRight: 8,
                boxShadow: `0 0 8px ${config.color}`,
              }}
            />
            {config.text}
          </div>
        );
      },
    },
    {
      title: 'Откуда',
      dataIndex: 'pickup_address',
      key: 'pickup',
      ellipsis: true,
      render: (address) => (
        <Tooltip title={address}>
          <Space size={8}>
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                border: '2px solid #10b981',
              }}
            />
            <span style={{ fontSize: 13 }}>{address}</span>
          </Space>
        </Tooltip>
      ),
    },
    {
      title: 'Куда',
      dataIndex: 'dropoff_address',
      key: 'dropoff',
      ellipsis: true,
      render: (address) => (
        <Tooltip title={address}>
          <Space size={8}>
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                border: '2px solid #ef4444',
              }}
            />
            <span style={{ fontSize: 13 }}>{address}</span>
          </Space>
        </Tooltip>
      ),
    },
    {
      title: 'Водитель',
      dataIndex: 'driver_id',
      key: 'driver',
      width: 160,
      render: (driverId) => {
        const driver = drivers.find((d) => d.id === driverId);
        return driver ? (
          <Space size={8}>
            <div
              style={{
                width: 24,
                height: 24,
                borderRadius: '50%',
                background: 'var(--tms-gradient-primary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 10,
                color: '#fff',
                fontWeight: 700,
              }}
            >
              {driver.name.charAt(0)}
            </div>
            <Typography.Text strong style={{ fontSize: 13 }}>
              {driver.name}
            </Typography.Text>
          </Space>
        ) : (
          <Typography.Text type="secondary" style={{ fontSize: 13, fontStyle: 'italic' }}>
            Не назначен
          </Typography.Text>
        );
      },
    },
    {
      title: 'Начало',
      dataIndex: 'time_start',
      key: 'time_start',
      width: 80,
      render: (time) =>
        time ? (
          <Typography.Text style={{ fontSize: 13, fontWeight: 500 }}>
            {dayjs(time).format('HH:mm')}
          </Typography.Text>
        ) : (
          '-'
        ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Space size={4}>
          {!record.driver_id && record.status === 'pending' && (
            <Tooltip title="Назначить">
              <Button
                type="text"
                size="small"
                icon={<UserAddOutlined style={{ color: 'var(--tms-primary)' }} />}
                onClick={(e) => {
                  e.stopPropagation();
                  onAssign?.(record.id);
                }}
              />
            </Tooltip>
          )}
          <Tooltip title="Детали">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined style={{ color: 'var(--tms-text-secondary)' }} />}
              onClick={(e) => {
                e.stopPropagation();
                onSelect(record.id);
              }}
            />
          </Tooltip>
          {['pending', 'assigned'].includes(record.status) && (
            <Tooltip title="Отменить">
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  onCancel?.(record.id);
                }}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  // Определение цветовой схемы (темная/светлая) для бейджей
  const isDark = document.body.classList.contains('dark-theme');

  return (
    <div
      style={{
        background: 'transparent',
        borderRadius: 16,
        overflow: 'hidden',
      }}
    >
      <Table
        columns={columns}
        dataSource={orders}
        rowKey="id"
        loading={loading}
        size="middle"
        pagination={{
          defaultPageSize: 10,
          showSizeChanger: true,
          pageSizeOptions: ['10', '20', '50'],
          showTotal: (total) => `Всего ${total} заказов`,
        }}
        onRow={(record) => ({
          onClick: () => onSelect(record.id),
          style: { cursor: 'pointer' },
          // Добавляем эффект появления строк при загрузке или фильтрации
          className: `order-row animate-in`,
        })}
        rowClassName={(record) =>
          !record.driver_id && record.status === 'pending' ? 'order-row-warning' : ''
        }
        style={{
          background: 'transparent',
        }}
      />
    </div>
  );
};
