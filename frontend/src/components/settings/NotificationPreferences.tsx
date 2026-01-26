import React, { useState, useEffect } from 'react';
import {
    Card,
    Form,
    Checkbox,
    Select,
    Button,
    Space,
    Typography,
    message,
    Spin,
    Divider,
} from 'antd';
import {
    SaveOutlined,
    ReloadOutlined,
} from '@ant-design/icons';
import {
    fetchNotificationPreferences,
    updateNotificationPreference,
    applyNotificationPreset,
} from '../../api/notifications';
import type {
    NotificationPreference,
} from '../../types/api';
import {
    NotificationType,
    NotificationChannel,
    NotificationFrequency,
    PresetProfile,
} from '../../types/api';

const { Text } = Typography;

interface NotificationSettings {
    [key: string]: {
        enabled: boolean;
        channels: NotificationChannel[];
        frequency: NotificationFrequency;
    };
}

const NOTIFICATION_TYPES: { key: NotificationType; label: string }[] = [
    { key: NotificationType.NEW_ORDER, label: 'Новый заказ' },
    { key: NotificationType.ORDER_STATUS_CHANGE, label: 'Изменение статуса заказа' },
    { key: NotificationType.ORDER_ASSIGNED, label: 'Назначение заказа' },
    { key: NotificationType.ORDER_CANCELLED, label: 'Отмена заказа' },
    { key: NotificationType.DRIVER_LOCATION, label: 'Локация водителя' },
    { key: NotificationType.SYSTEM_ALERT, label: 'Системные оповещения' },
];

const NOTIFICATION_CHANNELS: { key: NotificationChannel; label: string; icon: string }[] = [
    { key: NotificationChannel.TELEGRAM, label: 'Telegram', icon: '📱' },
    { key: NotificationChannel.EMAIL, label: 'Email', icon: '📧' },
    { key: NotificationChannel.IN_APP, label: 'В приложении', icon: '🔔' },
    { key: NotificationChannel.PUSH, label: 'Push-уведомления', icon: '📲' },
];

const FREQUENCY_OPTIONS: { key: NotificationFrequency; label: string }[] = [
    { key: NotificationFrequency.IMMEDIATE, label: 'Мгновенно' },
    { key: NotificationFrequency.HOURLY, label: 'Раз в час' },
    { key: NotificationFrequency.DAILY, label: 'Раз в день' },
    { key: NotificationFrequency.DISABLED, label: 'Отключено' },
];

const PRESET_OPTIONS: { key: PresetProfile; label: string; description: string }[] = [
    {
        key: PresetProfile.MINIMAL,
        label: 'Минимальный',
        description: 'Только критические уведомления в Telegram',
    },
    {
        key: PresetProfile.STANDARD,
        label: 'Стандартный',
        description: 'Важные уведомления во всех каналах',
    },
    {
        key: PresetProfile.MAXIMUM,
        label: 'Максимальный',
        description: 'Все уведомления мгновенно во всех каналах',
    },
];

interface NotificationPreferencesProps {
    onSuccess?: () => void;
}

export const NotificationPreferences: React.FC<NotificationPreferencesProps> = ({
    onSuccess,
}) => {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Загрузка настроек при монтировании
    useEffect(() => {
        loadPreferences();
    }, []);

    const loadPreferences = async () => {
        try {
            setLoading(true);
            const data = await fetchNotificationPreferences();

            // Преобразуем в удобный формат для формы
            const transformedSettings: NotificationSettings = {};
            NOTIFICATION_TYPES.forEach(({ key }) => {
                const typePrefs = data.filter(p => p.notification_type === key);
                const enabledChannels = typePrefs.filter(p => p.is_enabled).map(p => p.channel);

                transformedSettings[key] = {
                    enabled: enabledChannels.length > 0,
                    channels: enabledChannels,
                    frequency: typePrefs.find(p => p.is_enabled)?.frequency || NotificationFrequency.IMMEDIATE,
                };
            });

            form.setFieldsValue(transformedSettings);
        } catch (error) {
            message.error('Не удалось загрузить настройки уведомлений');
            console.error('Error loading preferences:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleApplyPreset = async (preset: PresetProfile) => {
        try {
            setLoading(true);
            const updated = await applyNotificationPreset(preset);

            // Обновляем состояние формы
            const transformedSettings: NotificationSettings = {};
            NOTIFICATION_TYPES.forEach(({ key }) => {
                const typePrefs = updated.filter(p => p.notification_type === key);
                const enabledChannels = typePrefs.filter(p => p.is_enabled).map(p => p.channel);

                transformedSettings[key] = {
                    enabled: enabledChannels.length > 0,
                    channels: enabledChannels,
                    frequency: typePrefs.find(p => p.is_enabled)?.frequency || NotificationFrequency.IMMEDIATE,
                };
            });

            form.setFieldsValue(transformedSettings);
            message.success(`Пресет "${PRESET_OPTIONS.find(p => p.key === preset)?.label}" применён`);
        } catch (error) {
            message.error('Не удалось применить пресет');
            console.error('Error applying preset:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        try {
            const values = await form.validateFields();
            setSaving(true);

            // Собираем все изменения
            const updates: Promise<NotificationPreference>[] = [];

            NOTIFICATION_TYPES.forEach(({ key }) => {
                const setting = values[key];

                if (!setting || !setting.enabled) {
                    // Отключаем все каналы для этого типа
                    NOTIFICATION_CHANNELS.forEach(({ key: channel }) => {
                        updates.push(
                            updateNotificationPreference(key, channel, {
                                notification_type: key,
                                channel: channel,
                                frequency: NotificationFrequency.DISABLED,
                                is_enabled: false,
                            })
                        );
                    });
                } else {
                    // Включаем выбранные каналы
                    NOTIFICATION_CHANNELS.forEach(({ key: channel }) => {
                        const isEnabled = setting.channels.includes(channel);
                        updates.push(
                            updateNotificationPreference(key, channel, {
                                notification_type: key,
                                channel: channel,
                                frequency: isEnabled ? setting.frequency : NotificationFrequency.DISABLED,
                                is_enabled: isEnabled,
                            })
                        );
                    });
                }
            });

            await Promise.all(updates);
            message.success('Настройки уведомлений сохранены');
            onSuccess?.();
        } catch (error) {
            message.error('Не удалось сохранить настройки');
            console.error('Error saving preferences:', error);
        } finally {
            setSaving(false);
        }
    };

    const handleReset = () => {
        loadPreferences();
        message.info('Настройки сброшены');
    };

    if (loading) {
        return (
            <div style={{ textAlign: 'center', padding: '40px' }}>
                <Spin size="large" />
                <div style={{ marginTop: 16 }}>
                    <Text type="secondary">Загрузка настроек...</Text>
                </div>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
            {/* Выбор пресета */}
            <Card
                title="Быстрая настройка"
                size="small"
                style={{ marginBottom: 0 }}
            >
                <Space wrap>
                    {PRESET_OPTIONS.map(({ key, label, description }) => (
                        <Button
                            key={key}
                            onClick={() => handleApplyPreset(key)}
                            style={{ textAlign: 'left', height: 'auto', padding: '8px 16px' }}
                        >
                            <div>
                                <div style={{ fontWeight: 500 }}>{label}</div>
                                <div style={{ fontSize: 12, opacity: 0.7 }}>
                                    {description}
                                </div>
                            </div>
                        </Button>
                    ))}
                </Space>
            </Card>

            {/* Форма настроек */}
            <Card
                title="Детальные настройки"
                size="small"
                extra={
                    <Space>
                        <Button
                            icon={<ReloadOutlined />}
                            onClick={handleReset}
                            disabled={saving}
                        >
                            Сбросить
                        </Button>
                        <Button
                            type="primary"
                            icon={<SaveOutlined />}
                            onClick={handleSave}
                            loading={saving}
                        >
                            Сохранить
                        </Button>
                    </Space>
                }
            >
                <Form
                    form={form}
                    layout="vertical"
                >
                    {NOTIFICATION_TYPES.map(({ key, label }) => {
                        return (
                            <div key={key} style={{ marginBottom: 24 }}>
                                <div style={{
                                    display: 'flex',
                                    justifyContent: 'space-between',
                                    alignItems: 'center',
                                    marginBottom: 12,
                                }}>
                                    <Text strong>{label}</Text>
                                    <Form.Item
                                        name={[key, 'enabled']}
                                        valuePropName="checked"
                                        style={{ margin: 0 }}
                                    >
                                        <Checkbox>Включено</Checkbox>
                                    </Form.Item>
                                </div>

                                <Form.Item noStyle shouldUpdate={(prev, curr) => {
                                    return prev[key]?.enabled !== curr[key]?.enabled;
                                }}>
                                    {({ getFieldValue }) => {
                                        const isEnabled = getFieldValue([key, 'enabled']);

                                        return (
                                            <div
                                                style={{
                                                    opacity: isEnabled ? 1 : 0.4,
                                                    pointerEvents: isEnabled ? 'auto' : 'none',
                                                    transition: 'opacity 0.2s',
                                                }}
                                            >
                                                {/* Каналы уведомлений */}
                                                <div style={{ marginBottom: 12 }}>
                                                    <Text type="secondary" style={{ fontSize: 12 }}>
                                                        Каналы уведомлений:
                                                    </Text>
                                                    <Form.Item
                                                        name={[key, 'channels']}
                                                        style={{ marginTop: 8, marginBottom: 0 }}
                                                    >
                                                        <Checkbox.Group
                                                            options={NOTIFICATION_CHANNELS.map(ch => ({
                                                                label: (
                                                                    <span>
                                                                        {ch.icon} {ch.label}
                                                                    </span>
                                                                ),
                                                                value: ch.key,
                                                            }))}
                                                        />
                                                    </Form.Item>
                                                </div>

                                                {/* Частота уведомлений */}
                                                <div>
                                                    <Text type="secondary" style={{ fontSize: 12 }}>
                                                        Частота уведомлений:
                                                    </Text>
                                                    <Form.Item
                                                        name={[key, 'frequency']}
                                                        style={{ marginTop: 8, marginBottom: 0 }}
                                                    >
                                                        <Select
                                                            options={FREQUENCY_OPTIONS.map(f => ({
                                                                label: f.label,
                                                                value: f.key,
                                                            }))}
                                                            style={{ width: '100%' }}
                                                        />
                                                    </Form.Item>
                                                </div>
                                            </div>
                                        );
                                    }}
                                </Form.Item>

                                {key !== NOTIFICATION_TYPES[NOTIFICATION_TYPES.length - 1].key && (
                                    <Divider style={{ margin: '16px 0' }} />
                                )}
                            </div>
                        );
                    })}
                </Form>
            </Card>
        </div>
    );
};
