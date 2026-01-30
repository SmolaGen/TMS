import React, { useState } from 'react';
import { Table, Space, Button, Tooltip, Typography, Modal, DatePicker } from 'antd';
import {
  EditOutlined,
  DeleteOutlined,
  PlayCircleOutlined,
  CheckCircleOutlined,
  StopOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { OrderTemplateResponse } from '../../hooks/useOrderTemplates';
import {
  useTemplates,
  useDeleteTemplate,
  useGenerateFromTemplate,
} from '../../hooks/useOrderTemplates';
import dayjs from 'dayjs';

interface TemplatesListProps {
  onEdit?: (templateId: number) => void;
  loading?: boolean;
}

const priorityConfig: Record<
  string,
  { color: string; gradient: string; text: string }
> = {
  low: {
    color: '#64748b',
    gradient: 'linear-gradient(135deg, #64748b 0%, #475569 100%)',
    text: 'Низкий',
  },
  normal: {
    color: '#3b82f6',
    gradient: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
    text: 'Обычный',
  },
  high: {
    color: '#f59e0b',
    gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
    text: 'Высокий',
  },
  urgent: {
    color: '#ef4444',
    gradient: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
    text: 'Срочный',
  },
};

export const TemplatesList: React.FC<TemplatesListProps> = ({ onEdit, loading: externalLoading }) => {
  const { data: templates = [], isLoading } = useTemplates();
  const deleteTemplate = useDeleteTemplate();
  const generateFromTemplate = useGenerateFromTemplate();
  const [generateModalVisible, setGenerateModalVisible] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null);
  const [dateRange, setDateRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);

  const handleDelete = (templateId: number) => {
    Modal.confirm({
      title: 'Удалить шаблон?',
      content: 'Это действие нельзя отменить.',
      okText: 'Удалить',
      okType: 'danger',
      cancelText: 'Отмена',
      onOk: () => {
        deleteTemplate.mutate(templateId);
      },
    });
  };

  const handleGenerateClick = (templateId: number) => {
    setSelectedTemplateId(templateId);
    setGenerateModalVisible(true);
  };

  const handleGenerate = () => {
    if (!selectedTemplateId || !dateRange) {
      return;
    }

    generateFromTemplate.mutate(
      {
        templateId: selectedTemplateId,
        request: {
          date_from: dateRange[0].format('YYYY-MM-DD'),
          date_until: dateRange[1].format('YYYY-MM-DD'),
        },
      },
      {
        onSuccess: () => {
          setGenerateModalVisible(false);
          setSelectedTemplateId(null);
          setDateRange(null);
        },
      },
    );
  };

  const columns: ColumnsType<OrderTemplateResponse> = [
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
      title: 'Название',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (name) => (
        <Typography.Text strong style={{ fontSize: 13 }}>
          {name}
        </Typography.Text>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 120,
      filters: [
        { text: 'Активный', value: true },
        { text: 'Неактивный', value: false },
      ],
      onFilter: (value, record) => record.is_active === value,
      render: (isActive: boolean) => {
        const config = isActive
          ? { color: '#10b981', text: 'Активный', icon: CheckCircleOutlined }
          : { color: '#64748b', text: 'Неактивный', icon: StopOutlined };
        const Icon = config.icon;
        const isDark = document.body.classList.contains('dark-theme');

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
            <Icon style={{ fontSize: 12, marginRight: 6 }} />
            {config.text}
          </div>
        );
      },
    },
    {
      title: 'Приоритет',
      dataIndex: 'priority',
      key: 'priority',
      width: 120,
      render: (priority: string) => {
        const config = priorityConfig[priority] || {
          color: '#64748b',
          gradient: '',
          text: priority,
        };
        const isDark = document.body.classList.contains('dark-theme');

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
            <span style={{ fontSize: 13 }}>{address || '-'}</span>
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
            <span style={{ fontSize: 13 }}>{address || '-'}</span>
          </Space>
        </Tooltip>
      ),
    },
    {
      title: 'Клиент',
      dataIndex: 'customer_name',
      key: 'customer',
      width: 150,
      ellipsis: true,
      render: (name) => (
        <Typography.Text style={{ fontSize: 13 }}>
          {name || <span style={{ color: 'var(--tms-text-tertiary)' }}>-</span>}
        </Typography.Text>
      ),
    },
    {
      title: 'Цена',
      dataIndex: 'price',
      key: 'price',
      width: 100,
      sorter: (a, b) => (a.price || 0) - (b.price || 0),
      render: (price) =>
        price ? (
          <Typography.Text strong style={{ fontSize: 13 }}>
            {price.toLocaleString('ru-RU')} ₽
          </Typography.Text>
        ) : (
          <span style={{ color: 'var(--tms-text-tertiary)' }}>-</span>
        ),
    },
    {
      title: 'Обновлён',
      dataIndex: 'updated_at',
      key: 'updated_at',
      width: 110,
      sorter: (a, b) =>
        dayjs(a.updated_at).valueOf() - dayjs(b.updated_at).valueOf(),
      render: (date) => (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {dayjs(date).format('DD.MM.YY')}
        </Typography.Text>
      ),
    },
    {
      title: 'Действия',
      key: 'actions',
      width: 130,
      fixed: 'right',
      render: (_, record) => (
        <Space size={4}>
          {record.is_active && (
            <Tooltip title="Генерировать заказы">
              <Button
                type="text"
                size="small"
                icon={
                  <PlayCircleOutlined style={{ color: 'var(--tms-primary)' }} />
                }
                onClick={(e) => {
                  e.stopPropagation();
                  handleGenerateClick(record.id);
                }}
              />
            </Tooltip>
          )}
          <Tooltip title="Редактировать">
            <Button
              type="text"
              size="small"
              icon={
                <EditOutlined style={{ color: 'var(--tms-text-secondary)' }} />
              }
              onClick={(e) => {
                e.stopPropagation();
                onEdit?.(record.id);
              }}
            />
          </Tooltip>
          <Tooltip title="Удалить">
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                handleDelete(record.id);
              }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div
        style={{
          background: 'transparent',
          borderRadius: 16,
          overflow: 'hidden',
        }}
      >
        <Table
          columns={columns}
          dataSource={templates}
          rowKey="id"
          loading={isLoading || externalLoading}
          size="middle"
          pagination={{
            defaultPageSize: 10,
            showSizeChanger: true,
            pageSizeOptions: ['10', '20', '50'],
            showTotal: (total) => `Всего ${total} шаблонов`,
          }}
          onRow={(record) => ({
            onClick: () => onEdit?.(record.id),
            style: { cursor: onEdit ? 'pointer' : 'default' },
            className: 'template-row animate-in',
          })}
          rowClassName={(record) =>
            !record.is_active ? 'template-row-inactive' : ''
          }
          style={{
            background: 'transparent',
          }}
        />
      </div>

      <Modal
        title="Генерация заказов из шаблона"
        open={generateModalVisible}
        onOk={handleGenerate}
        onCancel={() => {
          setGenerateModalVisible(false);
          setSelectedTemplateId(null);
          setDateRange(null);
        }}
        okText="Генерировать"
        cancelText="Отмена"
        okButtonProps={{
          disabled: !dateRange,
          loading: generateFromTemplate.isPending,
        }}
      >
        <div style={{ padding: '16px 0' }}>
          <Typography.Paragraph>
            Выберите период для генерации заказов:
          </Typography.Paragraph>
          <DatePicker.RangePicker
            style={{ width: '100%' }}
            format="DD.MM.YYYY"
            placeholder={['Дата начала', 'Дата окончания']}
            value={dateRange}
            onChange={(dates) => setDateRange(dates as [dayjs.Dayjs, dayjs.Dayjs] | null)}
            disabledDate={(current) => {
              return current && current < dayjs().startOf('day');
            }}
          />
          <Typography.Text type="secondary" style={{ fontSize: 12, marginTop: 8, display: 'block' }}>
            Будет создан заказ для каждого дня в выбранном периоде
          </Typography.Text>
        </div>
      </Modal>
    </>
  );
};
