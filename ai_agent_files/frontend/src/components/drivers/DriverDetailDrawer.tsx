import React from 'react';
import {
    Drawer,
    Descriptions,
    Avatar,
    Space,
    Typography,
    Tag,
    Statistic,
    Row,
    Col,
    Card,
    Divider,
    Spin,
    Button,
    Empty,
} from 'antd';
import {
    UserOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    TrophyOutlined,
    CarOutlined,
    DollarCircleOutlined,
    HistoryOutlined,
    EnvironmentOutlined,
    EditOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import { apiClient } from '../../api/client';
import { useTheme } from '../../hooks/useTheme';
import type { DriverResponse, DriverLocation, DriverStats } from '../../types/api';
import { DriverStatus } from '../../types/api';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';

dayjs.locale('ru');

const { Title } = Typography;

interface DriverDetailDrawerProps {
    driverId: number | null;
    open: boolean;
    onClose: () => void;
}

const statusConfig: Record<DriverStatus, { color: string; text: string }> = {
    [DriverStatus.AVAILABLE]: { color: 'success', text: 'Доступен' },
    [DriverStatus.BUSY]: { color: 'warning', text: 'Занят' },
    [DriverStatus.OFFLINE]: { color: 'default', text: 'Оффлайн' },
};

// Тайлы для карты
const TILE_LIGHT = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
const TILE_DARK = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';

export const DriverDetailDrawer: React.FC<DriverDetailDrawerProps> = ({
    driverId,
    open,
    onClose,
}) => {
    const { isDark } = useTheme();
    // Загрузить данные водителя
    const { data: driver, isLoading: isLoadingDriver } = useQuery<DriverResponse>({
        queryKey: ['driver', driverId],
        queryFn: async () => {
            const { data } = await apiClient.get(`/drivers/${driverId}`);
            return data;
        },
        enabled: !!driverId && open,
    });

    // Загрузить статистику водителя
    const { data: stats, isLoading: isLoadingStats } = useQuery<DriverStats>({
        queryKey: ['driver-stats', driverId],
        queryFn: async () => {
            const { data } = await apiClient.get(`/drivers/${driverId}/stats?days=30`);
            return data;
        },
        enabled: !!driverId && open,
    });

    // Загрузить текущую локацию водителя
    const { data: locations = [] } = useQuery<DriverLocation[]>({
        queryKey: ['drivers-live'],
        queryFn: async () => {
            const { data } = await apiClient.get('/drivers/live');
            return data;
        },
        enabled: open,
        refetchInterval: open ? 5000 : false,
    });

    const driverLocation = locations.find(l => l.driver_id === driverId);

    const isLoading = isLoadingDriver || isLoadingStats;

    return (
        <Drawer
            title={
                driver ? (
                    <Space>
                        <Avatar
                            size={40}
                            icon={<UserOutlined />}
                            style={{
                                backgroundColor: statusConfig[driver.status]?.color === 'success'
                                    ? '#52c41a'
                                    : statusConfig[driver.status]?.color === 'warning'
                                        ? '#faad14'
                                        : '#8c8c8c'
                            }}
                        />
                        <div>
                            <Title level={5} style={{ margin: 0 }}>
                                {driver.name}
                            </Title>
                            <Tag color={statusConfig[driver.status]?.color}>
                                {statusConfig[driver.status]?.text}
                            </Tag>
                        </div>
                    </Space>
                ) : 'Загрузка...'
            }
            placement="right"
            width={520}
            open={open}
            onClose={onClose}
            extra={
                <Button icon={<EditOutlined />}>
                    Редактировать
                </Button>
            }
        >
            <Spin spinning={isLoading}>
                {driver && (
                    <Space direction="vertical" style={{ width: '100%' }} size="large">
                        {/* Основная информация */}
                        <Descriptions column={1} size="small">
                            <Descriptions.Item label="ID">{driver.id}</Descriptions.Item>
                            <Descriptions.Item label="Telegram ID">
                                {driver.telegram_id}
                            </Descriptions.Item>
                            <Descriptions.Item label="Телефон">
                                {driver.phone || '—'}
                            </Descriptions.Item>
                            <Descriptions.Item label="Статус аккаунта">
                                <Tag color={driver.is_active ? 'green' : 'red'}>
                                    {driver.is_active ? 'Активен' : 'Деактивирован'}
                                </Tag>
                            </Descriptions.Item>
                            <Descriptions.Item label="Регистрация">
                                {dayjs(driver.created_at).format('DD MMMM YYYY, HH:mm')}
                            </Descriptions.Item>
                            <Descriptions.Item label="Последнее обновление">
                                {dayjs(driver.updated_at).format('DD MMMM YYYY, HH:mm')}
                            </Descriptions.Item>
                        </Descriptions>

                        <Divider />

                        {/* Статистика за 30 дней */}
                        <div>
                            <Title level={5}>
                                <HistoryOutlined /> Статистика за 30 дней
                            </Title>
                            {stats ? (
                                <Row gutter={[16, 16]}>
                                    <Col span={8}>
                                        <Card size="small">
                                            <Statistic
                                                title="Всего заказов"
                                                value={stats.total_orders}
                                                prefix={<CarOutlined />}
                                            />
                                        </Card>
                                    </Col>
                                    <Col span={8}>
                                        <Card size="small">
                                            <Statistic
                                                title="Завершено"
                                                value={stats.completed_orders}
                                                valueStyle={{ color: '#52c41a' }}
                                                prefix={<CheckCircleOutlined />}
                                            />
                                        </Card>
                                    </Col>
                                    <Col span={8}>
                                        <Card size="small">
                                            <Statistic
                                                title="Отменено"
                                                value={stats.cancelled_orders}
                                                valueStyle={{ color: '#ff4d4f' }}
                                                prefix={<CloseCircleOutlined />}
                                            />
                                        </Card>
                                    </Col>
                                    <Col span={8}>
                                        <Card size="small">
                                            <Statistic
                                                title="Активных"
                                                value={stats.active_orders}
                                                valueStyle={{ color: '#1890ff' }}
                                            />
                                        </Card>
                                    </Col>
                                    <Col span={8}>
                                        <Card size="small">
                                            <Statistic
                                                title="Успешность"
                                                value={stats.completion_rate}
                                                suffix="%"
                                                precision={1}
                                                prefix={<TrophyOutlined />}
                                            />
                                        </Card>
                                    </Col>
                                    <Col span={8}>
                                        <Card size="small">
                                            <Statistic
                                                title="Заработок"
                                                value={stats.total_revenue}
                                                suffix="₽"
                                                precision={0}
                                                prefix={<DollarCircleOutlined />}
                                            />
                                        </Card>
                                    </Col>
                                    <Col span={24}>
                                        <Card size="small">
                                            <Statistic
                                                title="Пройдено"
                                                value={stats.total_distance_km}
                                                suffix="км"
                                                precision={1}
                                            />
                                        </Card>
                                    </Col>
                                </Row>
                            ) : (
                                <Empty description="Нет данных" />
                            )}
                        </div>

                        <Divider />

                        {/* Мини-карта с текущей локацией */}
                        <div>
                            <Title level={5}>
                                <EnvironmentOutlined /> Текущая локация
                            </Title>
                            {driverLocation ? (
                                <div style={{ height: 200, borderRadius: 8, overflow: 'hidden' }}>
                                    <MapContainer
                                        center={[driverLocation.latitude, driverLocation.longitude]}
                                        zoom={15}
                                        style={{ height: '100%', width: '100%' }}
                                        scrollWheelZoom={false}
                                    >
                                        <TileLayer
                                            key={isDark ? 'dark' : 'light'}
                                            url={isDark ? TILE_DARK : TILE_LIGHT}
                                        />
                                        <Marker position={[driverLocation.latitude, driverLocation.longitude]}>
                                            <Popup>
                                                {driver.name}
                                                <br />
                                                Обновлено: {dayjs(driverLocation.updated_at).format('HH:mm:ss')}
                                            </Popup>
                                        </Marker>
                                    </MapContainer>
                                </div>
                            ) : (
                                <Empty
                                    description="Локация недоступна"
                                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                                />
                            )}
                        </div>
                    </Space>
                )}
            </Spin>
        </Drawer>
    );
};
