import React, { useState } from 'react';
import { Card, Button, DatePicker, Select, Space, Statistic, Row, Col, List, Tag, Modal, Divider } from 'antd';
import { PlayCircleOutlined, EyeOutlined, CalendarOutlined, UserOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import {
    useBatchAssignment,
    useBatchPreview,
    useUnassignedOrders
} from '../../hooks/useBatchAssignment';
import type {
    BatchAssignmentRequest,
    BatchAssignmentResult
} from '../../hooks/useBatchAssignment';

const { Option } = Select;

interface BatchAssignmentPanelProps {
    onAssignmentComplete?: (result: BatchAssignmentResult) => void;
}

export const BatchAssignmentPanel: React.FC<BatchAssignmentPanelProps> = ({
    onAssignmentComplete
}) => {
    const [selectedDate, setSelectedDate] = useState<dayjs.Dayjs | null>(dayjs());
    const [priorityFilter, setPriorityFilter] = useState<string>('');
    const [maxOrdersPerDriver, setMaxOrdersPerDriver] = useState<number>(10);
    const [previewVisible, setPreviewVisible] = useState(false);

    const batchAssign = useBatchAssignment();

    // Получить превью для выбранной даты
    const preview = useBatchPreview(
        selectedDate?.format('YYYY-MM-DD') || '',
        {
            priority_filter: priorityFilter as any,
            max_orders_per_driver: maxOrdersPerDriver,
        }
    );

    // Получить нераспределенные заказы
    const unassigned = useUnassignedOrders(selectedDate?.format('YYYY-MM-DD') || '');

    const handleBatchAssign = async () => {
        if (!selectedDate) return;

        const request: BatchAssignmentRequest = {
            target_date: selectedDate.format('YYYY-MM-DD'),
            priority_filter: priorityFilter as any,
            max_orders_per_driver: maxOrdersPerDriver,
        };

        try {
            const result = await batchAssign.mutateAsync(request);
            onAssignmentComplete?.(result);
            // Обновить данные
            preview.refetch();
            unassigned.refetch();
        } catch (error) {
            console.error('Batch assignment failed:', error);
        }
    };

    const showPreview = () => {
        setPreviewVisible(true);
    };

    const handlePreviewOk = () => {
        setPreviewVisible(false);
    };

    const handlePreviewCancel = () => {
        setPreviewVisible(false);
    };

    return (
        <>
            <Card
                title={
                    <Space>
                        <PlayCircleOutlined />
                        Автоматическое распределение заказов
                    </Space>
                }
                size="small"
            >
                <Space direction="vertical" style={{ width: '100%' }}>
                    {/* Настройки распределения */}
                    <Row gutter={16}>
                        <Col span={6}>
                            <div style={{ marginBottom: 8 }}>
                                <label>Дата распределения:</label>
                            </div>
                            <DatePicker
                                value={selectedDate}
                                onChange={setSelectedDate}
                                format="YYYY-MM-DD"
                                placeholder="Выберите дату"
                                style={{ width: '100%' }}
                            />
                        </Col>
                        <Col span={6}>
                            <div style={{ marginBottom: 8 }}>
                                <label>Приоритет заказов:</label>
                            </div>
                            <Select
                                value={priorityFilter}
                                onChange={setPriorityFilter}
                                placeholder="Все приоритеты"
                                style={{ width: '100%' }}
                                allowClear
                            >
                                <Option value="">Все приоритеты</Option>
                                <Option value="urgent">Срочные</Option>
                                <Option value="high">Высокий</Option>
                                <Option value="normal">Обычный</Option>
                                <Option value="low">Низкий</Option>
                            </Select>
                        </Col>
                        <Col span={6}>
                            <div style={{ marginBottom: 8 }}>
                                <label>Макс. заказов на водителя:</label>
                            </div>
                            <Select
                                value={maxOrdersPerDriver}
                                onChange={setMaxOrdersPerDriver}
                                style={{ width: '100%' }}
                            >
                                <Option value={5}>5</Option>
                                <Option value={10}>10</Option>
                                <Option value={15}>15</Option>
                                <Option value={20}>20</Option>
                            </Select>
                        </Col>
                        <Col span={6}>
                            <Space direction="vertical" style={{ width: '100%' }}>
                                <Button
                                    type="primary"
                                    icon={<EyeOutlined />}
                                    onClick={showPreview}
                                    loading={preview.isLoading}
                                    disabled={!selectedDate}
                                    block
                                >
                                    Предпросмотр
                                </Button>
                                <Button
                                    type="primary"
                                    icon={<PlayCircleOutlined />}
                                    onClick={handleBatchAssign}
                                    loading={batchAssign.isPending}
                                    disabled={!selectedDate}
                                    block
                                >
                                    Распределить
                                </Button>
                            </Space>
                        </Col>
                    </Row>

                    {/* Статистика */}
                    {selectedDate && (
                        <>
                            <Divider />
                            <Row gutter={16}>
                                <Col span={6}>
                                    <Statistic
                                        title="Нераспределенных заказов"
                                        value={unassigned.data?.total_count || 0}
                                        prefix={<CalendarOutlined />}
                                        loading={unassigned.isLoading}
                                    />
                                </Col>
                                <Col span={6}>
                                    <Statistic
                                        title="Будет распределено"
                                        value={preview.data?.result.total_assigned || 0}
                                        prefix={<UserOutlined />}
                                        loading={preview.isLoading}
                                    />
                                </Col>
                                <Col span={6}>
                                    <Statistic
                                        title="Успешность"
                                        value={preview.data ? Math.round(preview.data.result.success_rate * 100) : 0}
                                        suffix="%"
                                        loading={preview.isLoading}
                                    />
                                </Col>
                                <Col span={6}>
                                    <Statistic
                                        title="Не распределено"
                                        value={preview.data?.result.total_failed || 0}
                                        loading={preview.isLoading}
                                    />
                                </Col>
                            </Row>
                        </>
                    )}
                </Space>
            </Card>

            {/* Модальное окно предпросмотра */}
            <Modal
                title="Предпросмотр распределения"
                open={previewVisible}
                onOk={handlePreviewOk}
                onCancel={handlePreviewCancel}
                width={800}
                footer={[
                    <Button key="close" onClick={handlePreviewCancel}>
                        Закрыть
                    </Button>
                ]}
            >
                {preview.data ? (
                    <Space direction="vertical" style={{ width: '100%' }}>
                        <div>
                            <strong>Примечание:</strong> {preview.data.note}
                        </div>

                        <Row gutter={16}>
                            <Col span={12}>
                                <Card title="Будет распределено" size="small">
                                    <List
                                        size="small"
                                        dataSource={preview.data.result.assigned_orders.slice(0, 10)}
                                        renderItem={(item) => (
                                            <List.Item>
                                                <Space>
                                                    <span>Заказ #{item.order_id}</span>
                                                    <Tag color="green">→ {item.driver_name}</Tag>
                                                </Space>
                                            </List.Item>
                                        )}
                                    />
                                    {preview.data.result.assigned_orders.length > 10 && (
                                        <div style={{ textAlign: 'center', marginTop: 8 }}>
                                            ... и ещё {preview.data.result.assigned_orders.length - 10} заказов
                                        </div>
                                    )}
                                </Card>
                            </Col>
                            <Col span={12}>
                                <Card title="Не удалось распределить" size="small">
                                    <List
                                        size="small"
                                        dataSource={preview.data.result.failed_orders.slice(0, 10)}
                                        renderItem={(item) => (
                                            <List.Item>
                                                <Space>
                                                    <span>Заказ #{item.order_id}</span>
                                                    <Tag color="red">{item.reason}</Tag>
                                                </Space>
                                            </List.Item>
                                        )}
                                    />
                                    {preview.data.result.failed_orders.length > 10 && (
                                        <div style={{ textAlign: 'center', marginTop: 8 }}>
                                            ... и ещё {preview.data.result.failed_orders.length - 10} заказов
                                        </div>
                                    )}
                                </Card>
                            </Col>
                        </Row>
                    </Space>
                ) : (
                    <div>Загрузка предпросмотра...</div>
                )}
            </Modal>
        </>
    );
};
