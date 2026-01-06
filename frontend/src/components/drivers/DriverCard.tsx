import React from 'react';
import { Card, Avatar, Typography, Space, Tag, Badge } from 'antd';
import {
    UserOutlined,
    PhoneOutlined,
    ClockCircleOutlined,
} from '@ant-design/icons';
import type { DriverResponse } from '../../types/api';
import { DriverStatus } from '../../types/api';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/ru';

dayjs.extend(relativeTime);
dayjs.locale('ru');

const { Text, Title } = Typography;

interface DriverCardProps {
    driver: DriverResponse;
    onClick: () => void;
}

const statusConfig: Record<DriverStatus, { color: string; text: string; badge: 'success' | 'warning' | 'default' }> = {
    [DriverStatus.AVAILABLE]: { color: '#52c41a', text: 'Доступен', badge: 'success' },
    [DriverStatus.BUSY]: { color: '#faad14', text: 'Занят', badge: 'warning' },
    [DriverStatus.OFFLINE]: { color: '#8c8c8c', text: 'Оффлайн', badge: 'default' },
};

export const DriverCard: React.FC<DriverCardProps> = ({ driver, onClick }) => {
    const config = statusConfig[driver.status] || statusConfig[DriverStatus.OFFLINE];

    return (
        <Card
            hoverable
            onClick={onClick}
            style={{
                opacity: driver.is_active ? 1 : 0.6,
                borderLeft: `3px solid ${config.color}`,
            }}
            styles={{
                body: { padding: 16 },
            }}
        >
            <Space direction="vertical" style={{ width: '100%' }} size="small">
                {/* Заголовок с аватаром */}
                <Space>
                    <Badge status={config.badge} dot offset={[-4, 30]}>
                        <Avatar
                            size={48}
                            icon={<UserOutlined />}
                            style={{ backgroundColor: config.color }}
                        />
                    </Badge>
                    <div>
                        <Title level={5} style={{ margin: 0 }}>
                            {driver.name}
                        </Title>
                        <Tag color={config.color} style={{ marginTop: 4 }}>
                            {config.text}
                        </Tag>
                    </div>
                </Space>

                {/* Телефон */}
                {driver.phone && (
                    <Space>
                        <PhoneOutlined style={{ color: '#8c8c8c' }} />
                        <Text>{driver.phone}</Text>
                    </Space>
                )}

                {/* Последнее обновление */}
                <Space>
                    <ClockCircleOutlined style={{ color: '#8c8c8c' }} />
                    <Text type="secondary">
                        {dayjs(driver.updated_at).fromNow()}
                    </Text>
                </Space>

                {/* Статус активности */}
                {!driver.is_active && (
                    <Tag color="red">Деактивирован</Tag>
                )}
            </Space>
        </Card>
    );
};
