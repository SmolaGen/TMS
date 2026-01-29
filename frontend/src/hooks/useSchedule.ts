import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { message } from 'antd';
import { apiClient } from '../api/client';
import { isDevMode } from '../components/DevAuthSelector';
import dayjs, { Dayjs } from 'dayjs';

// TypeScript interfaces based on backend schemas
export interface ScheduleDayView {
  date: string;
  orders: Array<{
    id: number;
    driver_id?: number;
    contractor_id?: number;
    external_id?: string;
    time_start: string;
    time_end?: string;
    pickup_lat?: number;
    pickup_lon?: number;
    dropoff_lat?: number;
    dropoff_lon?: number;
    pickup_address?: string;
    dropoff_address?: string;
    customer_phone?: string;
    customer_name?: string;
    priority: string;
    status: string;
    scheduled_date?: string;
    comment?: string;
  }>;
  available_drivers: number[];
  unavailable_periods: Array<{
    id: number;
    driver_id: number;
    availability_type: string;
    time_start: string;
    time_end: string;
    description?: string;
  }>;
}

export interface ScheduleViewResponse {
  date_from: string;
  date_until: string;
  days: ScheduleDayView[];
  total_orders: number;
  total_drivers: number;
}

export interface DriverScheduleResponse {
  driver: {
    id: number;
    name: string;
    phone?: string;
    telegram_id?: number;
    is_active: boolean;
  };
  date_from: string;
  date_until: string;
  orders: Array<{
    id: number;
    time_start: string;
    time_end?: string;
    pickup_address?: string;
    dropoff_address?: string;
    priority: string;
    status: string;
    scheduled_date?: string;
  }>;
  unavailable_periods: Array<{
    id: number;
    availability_type: string;
    time_start: string;
    time_end: string;
    description?: string;
  }>;
}

export interface CreateScheduledOrderRequest {
  scheduled_date: string;
  driver_id?: number;
  contractor_id?: number;
  external_id?: string;
  time_start: string;
  time_end?: string;
  pickup_lat?: number;
  pickup_lon?: number;
  dropoff_lat?: number;
  dropoff_lon?: number;
  pickup_address?: string;
  dropoff_address?: string;
  customer_phone?: string;
  customer_name?: string;
  comment?: string;
}

export interface CreateScheduledOrderResponse {
  id: number;
  scheduled_date: string;
  driver_id?: number;
  time_start: string;
  time_end?: string;
  pickup_address?: string;
  dropoff_address?: string;
  status: string;
  priority: string;
}

// Mock data for development mode
const MOCK_SCHEDULE_VIEW: ScheduleViewResponse = {
  date_from: dayjs().toISOString(),
  date_until: dayjs().add(7, 'day').toISOString(),
  days: Array.from({ length: 7 }, (_, i) => {
    const date = dayjs().add(i, 'day');
    return {
      date: date.toISOString(),
      orders: Array.from({ length: Math.floor(Math.random() * 5) + 2 }, (_, j) => ({
        id: i * 100 + j,
        driver_id: Math.random() > 0.3 ? Math.floor(Math.random() * 5) + 1 : undefined,
        time_start: date.hour(9 + j * 2).toISOString(),
        time_end: date.hour(10 + j * 2).toISOString(),
        pickup_address: `Москва, ул. Пушкина, ${10 + j}`,
        dropoff_address: `Москва, ул. Ленина, ${20 + j}`,
        pickup_lat: 55.751244 + Math.random() * 0.05,
        pickup_lon: 37.618423 + Math.random() * 0.05,
        dropoff_lat: 55.755826 + Math.random() * 0.05,
        dropoff_lon: 37.617299 + Math.random() * 0.05,
        customer_name: `Клиент ${i}-${j}`,
        customer_phone: `+7 (495) ${100 + i}${j}0-00-00`,
        priority: ['low', 'normal', 'high', 'urgent'][Math.floor(Math.random() * 4)],
        status: ['pending', 'assigned', 'completed'][Math.floor(Math.random() * 3)],
        scheduled_date: date.toISOString(),
        comment: Math.random() > 0.5 ? `Комментарий к заказу ${i}-${j}` : undefined,
      })),
      available_drivers: [1, 2, 3, 4, 5].filter(() => Math.random() > 0.3),
      unavailable_periods: Math.random() > 0.7
        ? [
            {
              id: i * 10,
              driver_id: Math.floor(Math.random() * 5) + 1,
              availability_type: ['vacation', 'sick_leave', 'day_off'][
                Math.floor(Math.random() * 3)
              ],
              time_start: date.hour(0).toISOString(),
              time_end: date.hour(23).toISOString(),
              description: 'Плановая недоступность',
            },
          ]
        : [],
    };
  }),
  total_orders: 35,
  total_drivers: 5,
};

const MOCK_DRIVER_SCHEDULE: DriverScheduleResponse = {
  driver: {
    id: 1,
    name: 'Иван Петров',
    phone: '+7 (495) 123-45-67',
    is_active: true,
  },
  date_from: dayjs().toISOString(),
  date_until: dayjs().add(7, 'day').toISOString(),
  orders: Array.from({ length: 12 }, (_, i) => ({
    id: 100 + i,
    time_start: dayjs()
      .add(Math.floor(i / 2), 'day')
      .hour(9 + (i % 2) * 3)
      .toISOString(),
    time_end: dayjs()
      .add(Math.floor(i / 2), 'day')
      .hour(10 + (i % 2) * 3)
      .toISOString(),
    pickup_address: `Москва, ул. Садовая, ${i + 5}`,
    dropoff_address: `Москва, ул. Цветная, ${i + 10}`,
    priority: ['normal', 'high', 'urgent'][i % 3],
    status: ['pending', 'assigned', 'completed'][Math.floor(Math.random() * 3)],
    scheduled_date: dayjs()
      .add(Math.floor(i / 2), 'day')
      .toISOString(),
  })),
  unavailable_periods: [
    {
      id: 1,
      availability_type: 'day_off',
      time_start: dayjs().add(3, 'day').hour(0).toISOString(),
      time_end: dayjs().add(3, 'day').hour(23).toISOString(),
      description: 'Выходной',
    },
  ],
};

const API_BASE = '/api/v1';

// Get schedule view (calendar view with orders and driver availability)
export const useScheduleView = (
  dateRange?: [Dayjs, Dayjs],
  filters?: { driver_ids?: number[] },
) => {
  return useQuery<ScheduleViewResponse>({
    queryKey: ['schedule', dateRange, filters],
    queryFn: async () => {
      if (isDevMode()) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        return MOCK_SCHEDULE_VIEW;
      }

      const params = new URLSearchParams();
      if (dateRange) {
        params.append('date_from', dateRange[0].toISOString());
        params.append('date_until', dateRange[1].toISOString());
      }
      if (filters?.driver_ids && filters.driver_ids.length > 0) {
        params.append('driver_ids', filters.driver_ids.join(','));
      }

      const { data } = await apiClient.get<ScheduleViewResponse>(
        `${API_BASE}/schedule${params.toString() ? `?${params}` : ''}`,
      );
      return data;
    },
    refetchInterval: 60000, // Refetch every minute
    staleTime: 30000, // Data is fresh for 30 seconds
    throwOnError: true,
  });
};

// Get driver schedule (driver-specific schedule view)
export const useDriverSchedule = (driverId: number | null, dateRange?: [Dayjs, Dayjs]) => {
  return useQuery<DriverScheduleResponse>({
    queryKey: ['driver-schedule', driverId, dateRange],
    queryFn: async () => {
      if (!driverId) {
        throw new Error('Driver ID is required');
      }

      if (isDevMode()) {
        await new Promise((resolve) => setTimeout(resolve, 400));
        return {
          ...MOCK_DRIVER_SCHEDULE,
          driver: { ...MOCK_DRIVER_SCHEDULE.driver, id: driverId },
        };
      }

      const params = new URLSearchParams();
      if (dateRange) {
        params.append('date_from', dateRange[0].toISOString());
        params.append('date_until', dateRange[1].toISOString());
      }

      const { data } = await apiClient.get<DriverScheduleResponse>(
        `${API_BASE}/schedule/drivers/${driverId}${params.toString() ? `?${params}` : ''}`,
      );
      return data;
    },
    enabled: !!driverId,
    throwOnError: true,
  });
};

// Create scheduled order (order with future scheduled_date)
export const useCreateScheduledOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      orderData: CreateScheduledOrderRequest,
    ): Promise<CreateScheduledOrderResponse> => {
      if (isDevMode()) {
        await new Promise((resolve) => setTimeout(resolve, 600));
        return {
          id: Math.floor(Math.random() * 10000) + 1000,
          scheduled_date: orderData.scheduled_date,
          driver_id: orderData.driver_id,
          time_start: orderData.time_start,
          time_end: orderData.time_end,
          pickup_address: orderData.pickup_address,
          dropoff_address: orderData.dropoff_address,
          status: 'pending',
          priority: 'normal',
        };
      }

      const response = await fetch(`${API_BASE}/schedule/orders`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(orderData),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create scheduled order');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['schedule'] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['driver-schedule'] });
      message.success('Запланированный заказ успешно создан');
    },
    onError: (error: Error) => {
      message.error(`Ошибка создания заказа: ${error.message}`);
    },
  });
};
