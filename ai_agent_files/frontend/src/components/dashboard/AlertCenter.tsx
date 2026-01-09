import React from 'react';
import { Badge, Dropdown, Typography, Empty, Tag, Button } from 'antd';
import {
    BellOutlined,
    WarningOutlined,
    CloseCircleOutlined,
    InfoCircleOutlined,
} from '@ant-design/icons';
import { useKPIStats } from '../../hooks/useKPIStats';
import type { Alert } from '../../hooks/useKPIStats';
import dayjs from 'dayjs';
import relativeTime from 'dayjs/plugin/relativeTime';
import 'dayjs/locale/ru';

// Инициализируем плагин для относительного времени
dayjs.extend(relativeTime);
dayjs.locale('ru');

const alertIconMap = {
    warning: <WarningOutlined style={{ color: '#faad14', fontSize: 20 }} />,
    error: <CloseCircleOutlined style={{ color: '#ff4d4f', fontSize: 20 }} />,
    info: <InfoCircleOutlined style={{ color: '#1890ff', fontSize: 20 }} />,
};

const alertColorMap = {
    warning: 'orange',
    error: 'red',
    info: 'blue',
} as const;

export const AlertCenter: React.FC = () => {
    const { data } = useKPIStats();
    const alerts = data?.alerts || [];

    const unreadCount = alerts.length;

    const alertList = (
        <div style={{
            width: 400,
            background: '#fff',
            borderRadius: 8,
            boxShadow: '0 6px 16px rgba(0,0,0,0.12)',
            border: '1px solid #f0f0f0',
        }}>
            <div style={{
                padding: '12px 16px',
                borderBottom: '1px solid #f0f0f0',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
            }}>
                <Typography.Text strong style={{ fontSize: 16 }}>
                    Уведомления ({unreadCount})
                </Typography.Text>
                <Button type="link" size="small" style={{ padding: 0 }}>
                    Очистить все
                </Button>
            </div>

            {alerts.length === 0 ? (
                <Empty
                    description="Нет новых уведомлений"
                    style={{ padding: 32 }}
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                />
            ) : (
                <div style={{ maxHeight: 400, overflow: 'auto' }}>
                    {alerts.map((alert: Alert) => (
                        <div
                            key={alert.id}
                            className="alert-item"
                            style={{
                                padding: '12px 16px',
                                cursor: 'pointer',
                                borderBottom: '1px solid #f0f0f0',
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: '12px'
                            }}
                        >
                            <div style={{ paddingTop: 4 }}>
                                {alertIconMap[alert.type]}
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    marginBottom: 4
                                }}>
                                    <span style={{ fontWeight: 600 }}>{alert.title}</span>
                                    <Tag color={alertColorMap[alert.type]} style={{ marginRight: 0 }}>
                                        {alert.type === 'error' ? 'Срочно' :
                                            alert.type === 'warning' ? 'Внимание' : 'Инфо'}
                                    </Tag>
                                </div>
                                <div style={{ display: 'flex', flexDirection: 'column' }}>
                                    <Typography.Text type="secondary" style={{ color: '#595959', display: 'block' }}>
                                        {alert.description}
                                    </Typography.Text>
                                    <Typography.Text
                                        type="secondary"
                                        style={{ fontSize: 11, marginTop: 4, color: '#bfbfbf' }}
                                    >
                                        {dayjs(alert.timestamp).fromNow()}
                                    </Typography.Text>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            )}
            <div style={{
                padding: '10px 16px',
                borderTop: '1px solid #f0f0f0',
                textAlign: 'center'
            }}>
                <Button type="link" size="small" style={{ color: '#8c8c8c' }}>
                    Смотреть все уведомления
                </Button>
            </div>
        </div>
    );

    return (
        <Dropdown
            popupRender={() => alertList}
            trigger={['click']}
            placement="bottomRight"
            arrow={{ pointAtCenter: true }}
        >
            <div style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '4px 8px', borderRadius: 8, transition: 'all 0.3s' }}>
                <Badge
                    count={unreadCount}
                    size="small"
                    overflowCount={99}
                    offset={[2, 0]}
                >
                    <BellOutlined
                        style={{
                            fontSize: 20,
                            color: '#595959',
                        }}
                    />
                </Badge>
            </div>
        </Dropdown>
    );
};
