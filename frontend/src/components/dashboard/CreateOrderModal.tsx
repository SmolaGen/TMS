import React from 'react';
import { Modal, Form, Select, DatePicker, Input } from 'antd';
import type { OrderCreate, OrderPriority } from '../../types/api';
import { useDrivers } from '../../hooks/useDrivers';
import { AddressPicker } from '../common/AddressPicker';
import dayjs from 'dayjs';

const { Option } = Select;
const { TextArea } = Input;

interface CreateOrderModalProps {
  open: boolean;
  onCancel: () => void;
  onCreate: (values: OrderCreate) => void;
  loading?: boolean;
}

export const CreateOrderModal: React.FC<CreateOrderModalProps> = ({
  open,
  onCancel,
  onCreate,
  loading,
}) => {
  const [form] = Form.useForm();
  const { data: drivers = [] } = useDrivers();

  const handleOk = async () => {
    try {
      const values = await form.validateFields();

      const payload: OrderCreate = {
        driver_id: values.driver_id === 'unassigned' ? null : Number(values.driver_id),
        time_start: values.time[0].toISOString(),
        time_end: values.time[1].toISOString(),
        pickup_lat: values.pickup.lat,
        pickup_lon: values.pickup.lon,
        dropoff_lat: values.dropoff.lat,
        dropoff_lon: values.dropoff.lon,
        pickup_address: values.pickup.address,
        dropoff_address: values.dropoff.address,
        customer_name: values.customer_name,
        customer_phone: values.customer_phone,
        priority: values.priority as OrderPriority,
        comment: values.comment,
      };

      onCreate(payload);
      form.resetFields();
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  return (
    <Modal
      title="Создание нового заказа"
      open={open}
      onOk={handleOk}
      onCancel={onCancel}
      confirmLoading={loading}
      width={600}
      okText="Создать"
      cancelText="Отмена"
      destroyOnHidden
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{
          priority: 'normal',
          driver_id: 'unassigned',
          time: [dayjs(), dayjs().add(1, 'hour')],
        }}
      >
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

        <Form.Item
          name="time"
          label="Интервал времени"
          rules={[{ required: true, message: 'Выберите интервал времени' }]}
        >
          <DatePicker.RangePicker showTime style={{ width: '100%' }} format="YYYY-MM-DD HH:mm" />
        </Form.Item>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <Form.Item name="priority" label="Приоритет" rules={[{ required: true }]}>
            <Select>
              <Option value="low">Низкий</Option>
              <Option value="normal">Нормальный</Option>
              <Option value="high">Высокий</Option>
              <Option value="urgent">Срочный</Option>
            </Select>
          </Form.Item>

          <Form.Item name="driver_id" label="Водитель" rules={[{ required: true }]}>
            <Select>
              <Option value="unassigned">Не назначен</Option>
              {drivers.map((d) => (
                <Option key={d.id} value={d.id}>
                  {d.name}
                </Option>
              ))}
            </Select>
          </Form.Item>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <Form.Item name="customer_name" label="Имя клиента">
            <Input placeholder="Иван Иванов" />
          </Form.Item>

          <Form.Item name="customer_phone" label="Телефон клиента">
            <Input placeholder="+7 (___) ___-__-__" />
          </Form.Item>
        </div>

        <Form.Item name="comment" label="Комментарий">
          <TextArea rows={2} placeholder="Дополнительная информация (опционально)" />
        </Form.Item>
      </Form>
    </Modal>
  );
};
