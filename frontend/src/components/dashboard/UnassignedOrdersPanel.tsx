import React from 'react';
import { Card, Table, Tag, Button, Space, Typography, Tooltip } from 'antd';
import { UserOutlined, ClockCircleOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { useUnassignedOrders } from '../../hooks/useBatchAssignment';
import moment from 'moment';

const { Text } = Typography;

interface UnassignedOrdersPanelProps {
    targetDate: string;
    onAssignClick?: (orderId: number) => void;
}

export const UnassignedOrdersPanel: React.FC<UnassignedOrdersPanelProps> = ({
    targetDate,
    onAssignClick
}) => {
    const { data: response, isLoading } = useUnassignedOrders(targetDate);
    const orders = response?.orders || [];

    const columns = [
        {
            title: 'ID',
            dataIndex: 'id',
            key: 'id',
            width: 80,
            render: (id: number) => <Text strong>#{id}</Text>
        },
        {
            title: 'Время',
            dataIndex: 'time_start',
            key: 'time',
            width: 100,
            render: (time: string) => (
                <Space>
                    <ClockCircleOutlined />
                    {moment(time).format('HH:mm')}
                </Space>
            )
        },
        {
            title: 'Адрес погрузки',
            dataIndex: 'pickup_address',
            key: 'pickup',
            ellipsis: true,
        },
        {
            title: 'Адрес выгрузки',
            dataIndex: 'dropoff_address',
            key: 'dropoff',
            ellipsis: true,
        },
        {
            title: 'Приоритет',
            dataIndex: 'priority',
            key: 'priority',
            width: 100,
            render: (priority: string) => {
                let color = 'default';
                if (priority === 'urgent') color = 'error';
                else if (priority === 'high') color = 'warning';
                else if (priority === 'low') color = 'processing';

                return <Tag color={color}>{priority.toUpperCase()}</Tag>;
            }
        },
        {
            title: 'Действия',
            key: 'actions',
            width: 150,
            render: (_: any, record: any) => (
                <Space size="middle">
                    <Button
                        type="primary"
                        size="small"
                        icon={<UserOutlined />}
                        onClick={() => onAssignClick?.(record.id)}
                    >
                        Назначить
                    </Button>
                </Space>
            ),
        },
    ];

    return (
        <Card
            title={
                <Space>
                    <span>Нераспределенные заказы</span>
                    <Tooltip title="Заказы на выбранную дату, которым еще не назначен водитель">
                        <InfoCircleOutlined style={{ color: '#1890ff' }} />
                    </Tooltip>
                </Space>
            }
            extra={
                <Tag color="blue">{orders.length} заказов</Tag>
            }
            bodyStyle={{ padding: 0 }}
        >
            <Table
                dataSource={orders}
                columns={columns}
                rowKey="id"
                loading={isLoading}
                pagination={{ pageSize: 5 }}
                size="small"
                locale={{ emptyText: 'Нет нераспределенных заказов' }}
            />
        </Card>
    );
};
