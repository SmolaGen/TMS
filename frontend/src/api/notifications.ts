import { apiClient } from './client';
import type {
    NotificationPreference,
    NotificationPreferenceUpdate,
} from '../types/api';

/**
 * Получить все настройки уведомлений текущего водителя
 */
export const fetchNotificationPreferences = async (): Promise<NotificationPreference[]> => {
    const { data } = await apiClient.get<NotificationPreference[]>('/notifications/preferences');
    return Array.isArray(data) ? data : [];
};

/**
 * Обновить настройку уведомлений для указанного типа и канала
 *
 * @param notificationType - тип уведомления
 * @param channel - канал уведомления
 * @param data - данные для обновления
 */
export const updateNotificationPreference = async (
    notificationType: string,
    channel: string,
    data: NotificationPreferenceUpdate
): Promise<NotificationPreference> => {
    const { data: response } = await apiClient.put<NotificationPreference>(
        '/notifications/preferences',
        data,
        {
            params: {
                notification_type: notificationType,
                channel: channel,
            },
        }
    );
    return response;
};

/**
 * Применить пресет настроек уведомлений
 *
 * @param preset - название пресета (minimal, standard, maximum)
 */
export const applyNotificationPreset = async (
    preset: string
): Promise<NotificationPreference[]> => {
    const { data } = await apiClient.post<NotificationPreference[]>(
        '/notifications/preferences/preset',
        null,
        {
            params: {
                preset: preset,
            },
        }
    );
    return Array.isArray(data) ? data : [];
};
