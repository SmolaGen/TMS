import React from 'react';
import { Modal, Form, Select, DatePicker, Input } from 'antd';
import type { OrderCreate, OrderPriority } from '../../types/api';
import { useDrivers } from '../../hooks/useDrivers';
import dayjs from 'dayjs';

const { Option } = Select;
const { TextArea } = Input;

interface CreateOrderModalProps {
    open: boolean;
    onCancel: () => void;
    onCreate: (values: OrderCreate) => void;
    loading?: boolean;
}

const VLADIVOSTOK_LOCATIONS = [
    { name: 'ЖД Вокзал', lat: 43.1155, lng: 131.8855 },
    { name: 'Покровский парк', lat: 43.1134, lng: 131.8903 },
    { name: 'Золотой мост', lat: 43.1067, lng: 131.8954 },
    { name: 'ДВФУ', lat: 43.0227, lng: 131.8957 },
    { name: 'Аэропорт', lat: 43.3961, lng: 132.1481 },
    { name: 'Фокино', lat: 42.9627, lng: 132.4011 },
    { name: 'Артём', lat: 43.3536, lng: 132.1886 },
    { name: 'Уссурийск', lat: 43.8029, lng: 131.9452 },
];

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

            const fromLoc = VLADIVOSTOK_LOCATIONS.find(l => l.name === values.from);
            const toLoc = VLADIVOSTOK_LOCATIONS.find(l => l.name === values.to);

            if (!fromLoc || !toLoc) return;

            const payload: OrderCreate = {
                driver_id: values.driver_id === 'unassigned' ? null : Number(values.driver_id),
                time_start: values.time[0].toISOString(),
                time_end: values.time[1].toISOString(),
                pickup_lat: fromLoc.lat,
                pickup_lon: fromLoc.lng,
                dropoff_lat: toLoc.lat,
                dropoff_lon: toLoc.lng,
                pickup_address: fromLoc.name,
                dropoff_address: toLoc.name,
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
            destroyOnClose
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
                        name="from"
                        label="Откуда"
                        rules={[{ required: true, message: 'Выберите точку отправления' }]}
                    >
                        <Select placeholder="Выберите место">
                            {VLADIVOSTOK_LOCATIONS.map(l => (
                                <Option key={l.name} value={l.name}>{l.name}</Option>
                            ))}
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="to"
                        label="Куда"
                        rules={[{ required: true, message: 'Выберите точку назначения' }]}
                    >
                        <Select placeholder="Выберите место">
                            {VLADIVOSTOK_LOCATIONS.map(l => (
                                <Option key={l.name} value={l.name}>{l.name}</Option>
                            ))}
                        </Select>
                    </Form.Item>
                </div>

                <Form.Item
                    name="time"
                    label="Интервал времени"
                    rules={[{ required: true, message: 'Выберите интервал времени' }]}
                >
                    <DatePicker.RangePicker
                        showTime
                        style={{ width: '100%' }}
                        format="YYYY-MM-DD HH:mm"
                    />
                </Form.Item>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <Form.Item
                        name="priority"
                        label="Приоритет"
                        rules={[{ required: true }]}
                    >
                        <Select>
                            <Option value="low">Низкий</Option>
                            <Option value="normal">Нормальный</Option>
                            <Option value="high">Высокий</Option>
                            <Option value="urgent">Срочный</Option>
                        </Select>
                    </Form.Item>

                    <Form.Item
                        name="driver_id"
                        label="Водитель"
                        rules={[{ required: true }]}
                    >
                        <Select>
                            {drivers.map(d => (
                                <Option key={d.id} value={d.id}>{d.content}</Option>
                            ))}
                        </Select>
                    </Form.Item>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <Form.Item
                        name="customer_name"
                        label="Имя клиента"
                    >
                        <Input placeholder="Иван Иванов" />
                    </Form.Item>

                    <Form.Item
                        name="customer_phone"
                        label="Телефон клиента"
                    >
                        <Input placeholder="+7 (___) ___-__-__" />
                    </Form.Item>
                </div>

                <Form.Item
                    name="comment"
                    label="Комментарий"
                >
                    <TextArea rows={2} placeholder="Дополнительная информация (опционально)" />
                </Form.Item>
            </Form>
        </Modal>
    );
};
