import React, { useState } from 'react';
import { Button, Space } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { CalendarView } from '../components/schedule/CalendarView';
import { OrderTemplateModal } from '../components/schedule/OrderTemplateModal';
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
      <OrderTemplateModal
        open={isModalOpen}
        onCancel={() => setIsModalOpen(false)}
        onCreate={handleCreate}
        loading={createTemplate.isPending}
      />
    </div>
  );
};
