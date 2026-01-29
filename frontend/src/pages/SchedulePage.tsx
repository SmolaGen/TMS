import React, { useState } from 'react';
import { Button, Space, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { CalendarView } from '../components/schedule/CalendarView';
import { OrderTemplateModal } from '../components/schedule/OrderTemplateModal';
import { TemplatesList } from '../components/schedule/TemplatesList';
import { useCreateTemplate } from '../hooks/useOrderTemplates';

export const SchedulePage: React.FC = () => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const createTemplate = useCreateTemplate();

  const handleCreate = (values: any) => {
    createTemplate.mutate(values, {
      onSuccess: () => {
        setIsModalOpen(false);
      },
    });
  };

  const handleEdit = (_templateId: number) => {
    // TODO: Implement edit functionality in later subtask
    // For now, just show the modal
    setIsModalOpen(true);
  };

  return (
    <div style={{ padding: '24px', height: 'calc(100vh - 120px)' }}>
      <Space style={{ marginBottom: '16px' }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setIsModalOpen(true)}
        >
          Создать шаблон
        </Button>
      </Space>
      <CalendarView />

      <Typography.Title level={3} style={{ marginTop: '32px', marginBottom: '16px' }}>
        Шаблоны заказов
      </Typography.Title>
      <TemplatesList onEdit={handleEdit} />

      <OrderTemplateModal
        open={isModalOpen}
        onCancel={() => {
          setIsModalOpen(false);
        }}
        onCreate={handleCreate}
        loading={createTemplate.isPending}
      />
    </div>
  );
};
