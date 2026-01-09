import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { isDevMode } from '../components/DevAuthSelector';
import dayjs, { Dayjs } from 'dayjs';

export interface DetailedStats {
    period: {
        start: string;
        end: string;
    };
    orders: {
        total: number;
        byStatus: Record<string, number>;
        byPriority: Record<string, number>;
        byHour: Array<{ hour: number; count: number }>;
        byDay: Array<{ date: string; count: number; revenue: number }>;
        averageRevenue: number;
        totalRevenue: number;
    };
    drivers: {
        total: number;
        active: number;
        topDrivers: Array<{
            driver_id: number;
            name: string;
            completed_orders: number;
            total_revenue: number;
            average_rating?: number;
        }>;
    };
    routes: {
        totalDistance: number;
        averageDistance: number;
        longestRoute: {
            distance: number;
            order_id: number;
        };
    };
}

const MOCK_DETAILED_STATS: DetailedStats = {
    period: {
        start: dayjs().subtract(7, 'day').toISOString(),
        end: dayjs().toISOString(),
    },
    orders: {
        total: 345,
        byStatus: {
            completed: 280,
            cancelled: 35,
            pending: 15,
            in_progress: 15,
        },
        byPriority: {
            normal: 250,
            high: 50,
            urgent: 30,
            low: 15,
        },
        byHour: Array.from({ length: 24 }, (_, i) => ({
            hour: i,
            count: Math.floor(Math.random() * 30) + 5,
        })),
        byDay: Array.from({ length: 7 }, (_, i) => ({
            date: dayjs().subtract(6 - i, 'day').format('DD.MM'),
            count: Math.floor(Math.random() * 50) + 30,
            revenue: Math.floor(Math.random() * 50000) + 20000,
        })),
        averageRevenue: 450,
        totalRevenue: 155250,
    },
    drivers: {
        total: 15,
        active: 12,
        topDrivers: [
            { driver_id: 1, name: 'Иван Петров', completed_orders: 45, total_revenue: 22500, average_rating: 4.9 },
            { driver_id: 2, name: 'Сергей Сидоров', completed_orders: 42, total_revenue: 18900, average_rating: 4.8 },
            { driver_id: 3, name: 'Алексей Козлов', completed_orders: 38, total_revenue: 17100, average_rating: 4.7 },
            { driver_id: 4, name: 'Дмитрий Новиков', completed_orders: 35, total_revenue: 15750, average_rating: 4.6 },
            { driver_id: 5, name: 'Михаил Морозов', completed_orders: 32, total_revenue: 14400, average_rating: 4.5 },
        ],
    },
    routes: {
        totalDistance: 2450,
        averageDistance: 7.1,
        longestRoute: {
            distance: 18.5,
            order_id: 123,
        },
    },
};

export const useDetailedStats = (dateRange?: [Dayjs, Dayjs]) => {
    return useQuery<DetailedStats>({
        queryKey: ['detailed-stats', dateRange],
        queryFn: async () => {
            if (isDevMode()) {
                await new Promise(resolve => setTimeout(resolve, 500));
                return MOCK_DETAILED_STATS;
            }
            const params = dateRange ? {
                start: dateRange[0].toISOString(),
                end: dateRange[1].toISOString(),
            } : {};
            const { data } = await apiClient.get<DetailedStats>('/stats/detailed', { params });
            return data;
        },
        refetchInterval: 60000,
        staleTime: 30000,
    });
};
