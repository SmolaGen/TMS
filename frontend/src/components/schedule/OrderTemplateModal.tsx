import React from 'react';
import { Modal, Form, Select, Input, InputNumber, Switch } from 'antd';
import { AddressPicker } from '../common/AddressPicker';
import type {
  OrderTemplateCreate,
  OrderTemplateUpdate,
  OrderTemplateResponse,
} from '../../hooks/useOrderTemplates';

const { Option } = Select;
const { TextArea } = Input;

interface OrderTemplateModalProps {
  open: boolean;
  onCancel: () => void;
  onCreate?: (values: OrderTemplateCreate) => void;
  onUpdate?: (values: OrderTemplateUpdate) => void;
  loading?: boolean;
  template?: OrderTemplateResponse | null;
}

export const OrderTemplateModal: React.FC<OrderTemplateModalProps> = ({
  open,
  onCancel,
  onCreate,
  onUpdate,
  loading,
  template,
}) => {
  const [form] = Form.useForm();
  const isEditMode = !!template;

  React.useEffect(() => {
    if (open && template) {
      // Populate form with existing template data
      form.setFieldsValue({
        name: template.name,
        priority: template.priority,
        pickup: template.pickup_address
          ? {
              address: template.pickup_address,
              lat: template.pickup_lat,
              lon: template.pickup_lon,
            }
          : undefined,
        dropoff: template.dropoff_address
          ? {
              address: template.dropoff_address,
              lat: template.dropoff_lat,
              lon: template.dropoff_lon,
            }
          : undefined,
        customer_name: template.customer_name,
        customer_phone: template.customer_phone,
        price: template.price,
        comment: template.comment,
        is_active: template.is_active,
      });
    } else if (open && !template) {
      // Reset form for create mode
      form.resetFields();
    }
  }, [open, template, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();

      if (isEditMode && onUpdate) {
        const payload: OrderTemplateUpdate = {
          name: values.name,
          priority: values.priority,
          pickup_lat: values.pickup?.lat,
          pickup_lon: values.pickup?.lon,
          dropoff_lat: values.dropoff?.lat,
          dropoff_lon: values.dropoff?.lon,
          pickup_address: values.pickup?.address,
          dropoff_address: values.dropoff?.address,
          customer_name: values.customer_name,
          customer_phone: values.customer_phone,
          price: values.price,
          comment: values.comment,
          is_active: values.is_active,
        };
        onUpdate(payload);
      } else if (!isEditMode && onCreate) {
        const payload: OrderTemplateCreate = {
          name: values.name,
          priority: values.priority,
          pickup_lat: values.pickup?.lat,
          pickup_lon: values.pickup?.lon,
          dropoff_lat: values.dropoff?.lat,
          dropoff_lon: values.dropoff?.lon,
          pickup_address: values.pickup?.address,
          dropoff_address: values.dropoff?.address,
          customer_name: values.customer_name,
          customer_phone: values.customer_phone,
          price: values.price,
          comment: values.comment,
          is_active: values.is_active ?? true,
        };
        onCreate(payload);
      }

      form.resetFields();
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  const handleCancel = () => {
    form.resetFields();
    onCancel();
  };

  return (
    <Modal
      title={isEditMode ? 'Редактирование шаблона' : 'Создание шаблона заказа'}
      open={open}
      onOk={handleOk}
      onCancel={handleCancel}
      confirmLoading={loading}
      width={600}
      okText={isEditMode ? 'Сохранить' : 'Создать'}
      cancelText="Отмена"
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          priority: 'normal',
          is_active: true,
        }}
      >
        <Form.Item
          name="name"
          label="Название шаблона"
          rules={[{ required: true, message: 'Введите название шаблона' }]}
        >
          <Input placeholder="Ежедневная доставка на склад" />
        </Form.Item>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <Form.Item
            name="pickup"
            label="Откуда"
            rules={[{ required: true, message: 'Выберите точку отправления' }]}
          >
            <AddressPicker
              placeholder="Введите адрес отправления"
              onChange={(address, lat, lon) => {
                form.setFieldValue('pickup', { address, lat, lon });
              }}
            />
          </Form.Item>

          <Form.Item
            name="dropoff"
            label="Куда"
            rules={[{ required: true, message: 'Выберите точку назначения' }]}
          >
            <AddressPicker
              placeholder="Введите адрес назначения"
              onChange={(address, lat, lon) => {
                form.setFieldValue('dropoff', { address, lat, lon });
              }}
            />
          </Form.Item>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <Form.Item name="priority" label="Приоритет" rules={[{ required: true }]}>
            <Select>
              <Option value="low">Низкий</Option>
              <Option value="normal">Нормальный</Option>
              <Option value="high">Высокий</Option>
              <Option value="urgent">Срочный</Option>
            </Select>
          </Form.Item>

          <Form.Item name="price" label="Стоимость">
            <InputNumber
              style={{ width: '100%' }}
              placeholder="1500"
              min={0}
              addonAfter="₽"
            />
          </Form.Item>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <Form.Item name="customer_name" label="Имя клиента">
            <Input placeholder="ООО Ромашка" />
          </Form.Item>

          <Form.Item name="customer_phone" label="Телефон клиента">
            <Input placeholder="+7 (___) ___-__-__" />
          </Form.Item>
        </div>

        <Form.Item name="comment" label="Комментарий">
          <TextArea rows={2} placeholder="Дополнительная информация (опционально)" />
        </Form.Item>

        <Form.Item name="is_active" label="Активен" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Form>
    </Modal>
  );
};
