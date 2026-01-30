import React from 'react';
import { Modal, Form, Select, DatePicker, Input } from 'antd';
import type {
  DriverAvailabilityCreate,
  AvailabilityType,
} from '../../hooks/useDriverAvailability';
import { useDrivers } from '../../hooks/useDrivers';
import dayjs from 'dayjs';

const { Option } = Select;
const { TextArea } = Input;

interface DriverAvailabilityModalProps {
  open: boolean;
  onCancel: () => void;
  onCreate: (values: DriverAvailabilityCreate) => void;
  loading?: boolean;
  driverId?: number; // Pre-selected driver (optional)
}

export const DriverAvailabilityModal: React.FC<DriverAvailabilityModalProps> = ({
  open,
  onCancel,
  onCreate,
  loading,
  driverId,
}) => {
  const [form] = Form.useForm();
  const { data: drivers = [] } = useDrivers();

  const handleOk = async () => {
    try {
      const values = await form.validateFields();

      const payload: DriverAvailabilityCreate = {
        driver_id: Number(values.driver_id),
        availability_type: values.availability_type as AvailabilityType,
        time_start: values.time[0].toISOString(),
        time_end: values.time[1].toISOString(),
        description: values.description,
      };

      onCreate(payload);
      form.resetFields();
    } catch (error) {
      console.error('Validation failed:', error);
    }
  };

  return (
    <Modal
      title="Добавление периода недоступности"
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
          availability_type: 'vacation',
          driver_id: driverId,
          time: [dayjs(), dayjs().add(1, 'day')],
        }}
      >
        <Form.Item
          name="driver_id"
          label="Водитель"
          rules={[{ required: true, message: 'Выберите водителя' }]}
        >
          <Select placeholder="Выберите водителя" disabled={!!driverId}>
            {drivers.map((d) => (
              <Option key={d.id} value={d.id}>
                {d.name}
              </Option>
            ))}
          </Select>
        </Form.Item>

        <Form.Item
          name="availability_type"
          label="Тип недоступности"
          rules={[{ required: true, message: 'Выберите тип недоступности' }]}
        >
          <Select>
            <Option value="vacation">Отпуск</Option>
            <Option value="sick_leave">Больничный</Option>
            <Option value="day_off">Выходной</Option>
            <Option value="personal">Личные дела</Option>
            <Option value="other">Другое</Option>
          </Select>
        </Form.Item>

        <Form.Item
          name="time"
          label="Период"
          rules={[{ required: true, message: 'Выберите период недоступности' }]}
        >
          <DatePicker.RangePicker showTime style={{ width: '100%' }} format="YYYY-MM-DD HH:mm" />
        </Form.Item>

        <Form.Item name="description" label="Описание">
          <TextArea rows={3} placeholder="Дополнительная информация (опционально)" />
        </Form.Item>
      </Form>
    </Modal>
  );
};
