import React from 'react';
import { Table, Tag, Space, Button, Tooltip, Typography, Avatar, Badge } from 'antd';
import {
  EditOutlined,
  EnvironmentOutlined,
  PhoneOutlined,
  UserOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { DriverResponse } from '../../types/api';
import { DriverStatus } from '../../types/api';
import dayjs from 'dayjs';
import { useDriverAvailability, type AvailabilityType } from '../../hooks/useDriverAvailability';

interface DriversTableProps {
  drivers: DriverResponse[];
  loading?: boolean;
  onSelect: (driverId: number) => void;
  onEdit?: (driverId: number) => void;
}

const statusConfig: Record<
  DriverStatus,
  { color: string; text: string; badge: 'success' | 'warning' | 'default' }
> = {
  [DriverStatus.AVAILABLE]: { color: 'success', text: 'Доступен', badge: 'success' },
  [DriverStatus.BUSY]: { color: 'warning', text: 'Занят', badge: 'warning' },
  [DriverStatus.OFFLINE]: { color: 'default', text: 'Оффлайн', badge: 'default' },
};

const availabilityTypeConfig: Record<AvailabilityType, { color: string; text: string }> = {
  vacation: { color: 'blue', text: 'Отпуск' },
  sick_leave: { color: 'red', text: 'Больничный' },
  day_off: { color: 'orange', text: 'Выходной' },
  personal: { color: 'purple', text: 'Личное' },
  other: { color: 'default', text: 'Недоступен' },
};

// Helper component to show driver availability status
const DriverAvailabilityIndicator: React.FC<{ driverId: number }> = ({ driverId }) => {
  const now = dayjs();
  const { data: availability } = useDriverAvailability(driverId, {
    dateFrom: now.format('YYYY-MM-DD'),
    dateUntil: now.add(7, 'days').format('YYYY-MM-DD'),
  });

  if (!availability || availability.length === 0) {
    return <Typography.Text type="secondary">—</Typography.Text>;
  }

  // Check for current unavailability
  const currentUnavailability = availability.find((period) => {
    const start = dayjs(period.time_start);
    const end = dayjs(period.time_end);
    return now.isAfter(start) && now.isBefore(end);
  });

  if (currentUnavailability) {
    const config = availabilityTypeConfig[currentUnavailability.availability_type];
    const endDate = dayjs(currentUnavailability.time_end);
    return (
      <Tooltip
        title={
          <Space direction="vertical" size={0}>
            <span>{config.text}</span>
            <span style={{ fontSize: 11 }}>До: {endDate.format('DD.MM.YYYY HH:mm')}</span>
            {currentUnavailability.description && (
              <span style={{ fontSize: 11 }}>{currentUnavailability.description}</span>
            )}
          </Space>
        }
      >
        <Tag icon={<CalendarOutlined />} color={config.color}>
          {config.text}
        </Tag>
      </Tooltip>
    );
  }

  // Check for upcoming unavailability (within next 7 days)
  const upcomingUnavailability = availability.find((period) => {
    const start = dayjs(period.time_start);
    return start.isAfter(now);
  });

  if (upcomingUnavailability) {
    const config = availabilityTypeConfig[upcomingUnavailability.availability_type];
    const startDate = dayjs(upcomingUnavailability.time_start);
    return (
      <Tooltip
        title={
          <Space direction="vertical" size={0}>
            <span>{config.text}</span>
            <span style={{ fontSize: 11 }}>С: {startDate.format('DD.MM.YYYY HH:mm')}</span>
            {upcomingUnavailability.description && (
              <span style={{ fontSize: 11 }}>{upcomingUnavailability.description}</span>
            )}
          </Space>
        }
      >
        <Tag icon={<CalendarOutlined />} color="default">
          Скоро: {config.text}
        </Tag>
      </Tooltip>
    );
  }

  return <Typography.Text type="secondary">—</Typography.Text>;
};

export const DriversTable: React.FC<DriversTableProps> = ({
  drivers,
  loading,
  onSelect,
  onEdit,
}) => {
  const columns: ColumnsType<DriverResponse> = [
    {
      title: 'Водитель',
      key: 'driver',
      width: 250,
      render: (_, record) => (
        <Space>
          <Badge status={statusConfig[record.status]?.badge || 'default'} dot>
            <Avatar icon={<UserOutlined />} />
          </Badge>
          <div>
            <Typography.Text strong>{record.name}</Typography.Text>
            <br />
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              ID: {record.id}
            </Typography.Text>
          </div>
        </Space>
      ),
    },
    {
      title: 'Онлайн',
      dataIndex: 'is_online',
      key: 'is_online',
      width: 100,
      filters: [
        { text: 'Онлайн', value: true },
        { text: 'Оффлайн', value: false },
      ],
      onFilter: (value, record) => record.is_online === value,
      render: (isOnline: boolean) => (
        <Tag color={isOnline ? 'green' : 'red'} icon={isOnline ? '🟢' : '⚫'}>
          {isOnline ? 'Онлайн' : 'Оффлайн'}
        </Tag>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      filters: Object.entries(statusConfig).map(([value, { text }]) => ({
        text,
        value,
      })),
      onFilter: (value, record) => record.status === value,
      render: (status: DriverStatus) => {
        const config = statusConfig[status];
        return config ? <Tag color={config.color}>{config.text}</Tag> : status;
      },
    },
    {
      title: 'Доступность',
      key: 'availability',
      width: 180,
      render: (_, record) => <DriverAvailabilityIndicator driverId={record.id} />,
    },
    {
      title: 'Телефон',
      dataIndex: 'phone',
      key: 'phone',
      width: 150,
      render: (phone) =>
        phone ? (
          <Space>
            <PhoneOutlined />
            <span>{phone}</span>
          </Space>
        ) : (
          <Typography.Text type="secondary">—</Typography.Text>
        ),
    },
    {
      title: 'Активен',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      filters: [
        { text: 'Да', value: true },
        { text: 'Нет', value: false },
      ],
      onFilter: (value, record) => record.is_active === value,
      render: (isActive) => <Tag color={isActive ? 'green' : 'red'}>{isActive ? 'Да' : 'Нет'}</Tag>,
    },
    {
      title: 'Регистрация',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 140,
      sorter: (a, b) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
      render: (date) => dayjs(date).format('DD.MM.YYYY'),
    },
    {
      title: 'Последнее обновление',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 160,
      sorter: (a, b) => dayjs(a.updated_at).unix() - dayjs(b.updated_at).unix(),
      render: (date) => dayjs(date).format('DD.MM.YYYY HH:mm'),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 100,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Tooltip title="Подробнее">
            <Button
              type="text"
              icon={<EnvironmentOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onSelect(record.id);
              }}
            />
          </Tooltip>
          {onEdit && (
            <Tooltip title="Редактировать">
              <Button
                type="text"
                icon={<EditOutlined />}
                onClick={(e) => {
                  e.stopPropagation();
                  onEdit(record.id);
                }}
              />
            </Tooltip>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Table
      columns={columns}
      dataSource={drivers}
      rowKey="id"
      loading={loading}
      size="middle"
      pagination={{
        defaultPageSize: 20,
        showSizeChanger: true,
        showTotal: (total) => `Всего: ${total} водителей`,
      }}
      scroll={{ x: 1200 }}
      onRow={(record) => ({
        onClick: () => onSelect(record.id),
        style: { cursor: 'pointer' },
      })}
      rowClassName={(record) => (!record.is_active ? 'driver-row-inactive' : '')}
    />
  );
};
