import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { isDevMode } from '../components/DevAuthSelector';

export interface KPIStats {
    activeOrders: number;
    freeDrivers: number;
    completedToday: number;
    averageRating: number;
    averageWaitTime: number; // в минутах
}

export interface Alert {
    id: string;
    type: 'warning' | 'error' | 'info';
    title: string;
    description: string;
    timestamp: string; // ISO string
    orderId?: number;
    driverId?: number;
}

export interface KPIResponse {
    stats: KPIStats;
    alerts: Alert[];
}

const MOCK_KPI: KPIResponse = {
    stats: {
        activeOrders: 12,
        freeDrivers: 5,
        completedToday: 48,
        averageRating: 4.8,
        averageWaitTime: 4,
    },
    alerts: [
        {
            id: '1',
            type: 'warning',
            title: 'Заказ #123 без водителя',
            description: 'Ожидает назначения более 10 минут',
            timestamp: new Date(Date.now() - 10 * 60 * 1000).toISOString(),
            orderId: 123,
        },
        {
            id: '2',
            type: 'error',
            title: 'Отмена заказа #115',
            description: 'Клиент отменил заказ из-за долгого ожидания',
            timestamp: new Date(Date.now() - 25 * 60 * 1000).toISOString(),
            orderId: 115,
        },
        {
            id: '3',
            type: 'info',
            title: 'Новый водитель в сети',
            description: 'Алексей Петров вышел на смену',
            timestamp: new Date(Date.now() - 45 * 60 * 1000).toISOString(),
            driverId: 5,
        }
    ]
};

export const useKPIStats = () => {
    return useQuery<KPIResponse>({
        queryKey: ['kpi-stats'],
        queryFn: async () => {
            if (isDevMode()) {
                // Имитируем задержку сети
                await new Promise(resolve => setTimeout(resolve, 500));
                return MOCK_KPI;
            }
            const response = await apiClient.get('/stats/overview');
            return response.data;
        },
        refetchInterval: 30000,
        staleTime: 10000,
    });
};
