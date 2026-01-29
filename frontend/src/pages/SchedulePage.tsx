import React, { useState } from 'react';
import { Button, Typography } from 'antd';
import { PlusOutlined, CalendarOutlined, UnorderedListOutlined } from '@ant-design/icons';
import { CalendarView } from '../components/schedule/CalendarView';
import { OrderTemplateModal } from '../components/schedule/OrderTemplateModal';
import { TemplatesList } from '../components/schedule/TemplatesList';
import { useCreateTemplate } from '../hooks/useOrderTemplates';

const { Title } = Typography;

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
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: '0 8px 16px' }}>
      {/* Заголовок */}
      <div
        style={{
          padding: '16px 0',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <Title level={4} style={{ margin: 0 }}>
          <CalendarOutlined style={{ marginRight: 8 }} />
          Планирование расписания
        </Title>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setIsModalOpen(true)}
          size="large"
          shape="round"
        >
          Создать шаблон
        </Button>
      </div>

      {/* Календарь */}
      <div style={{ marginBottom: 16 }} className="glass-card">
        <CalendarView />
      </div>

      {/* Шаблоны заказов */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <Title level={5} style={{ margin: '16px 0' }}>
          <UnorderedListOutlined style={{ marginRight: 8 }} />
          Шаблоны заказов
        </Title>
        <div style={{ flex: 1, overflow: 'auto' }} className="glass-card">
          <TemplatesList onEdit={handleEdit} />
        </div>
      </div>

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
