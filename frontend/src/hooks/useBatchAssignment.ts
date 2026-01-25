import { useMutation, useQuery } from '@tanstack/react-query';
import { message } from 'antd';

export interface BatchAssignmentRequest {
  target_date: string;
  priority_filter?: 'low' | 'normal' | 'high' | 'urgent';
  driver_ids?: number[];
  max_orders_per_driver?: number;
}

export interface BatchAssignmentResult {
  assigned_orders: Array<{
    order_id: number;
    driver_id: number;
    driver_name: string;
  }>;
  failed_orders: Array<{
    order_id: number;
    reason: string;
    order_details?: any;
  }>;
  total_processed: number;
  total_assigned: number;
  total_failed: number;
  success_rate: number;
}

export interface BatchPreviewResponse {
  result: BatchAssignmentResult;
  note: string;
}

export interface UnassignedOrder {
  id: number;
  pickup_address?: string;
  dropoff_address?: string;
  priority: string;
  time_start?: string;
  time_end?: string;
  distance_meters?: number;
  duration_seconds?: number;
}

export interface UnassignedOrdersResponse {
  orders: UnassignedOrder[];
  total_count: number;
  target_date: string;
}

export interface DriverScheduleItem {
  order_id: number;
  time_start?: string;
  time_end?: string;
  pickup_address?: string;
  dropoff_address?: string;
  status: string;
  priority: string;
}

export interface DriverScheduleResponse {
  driver_id: number;
  driver_name: string;
  target_date: string;
  schedule: DriverScheduleItem[];
  total_orders: number;
  available_slots: number;
}

const API_BASE = '/api/v1';

// Batch assignment mutation
export const useBatchAssignment = () => {
  return useMutation({
    mutationFn: async (request: BatchAssignmentRequest): Promise<BatchAssignmentResult> => {
      const response = await fetch(`${API_BASE}/orders/batch-assign`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to assign orders');
      }

      return response.json();
    },
    onSuccess: (data) => {
      message.success(
        `Распределено ${data.total_assigned} из ${data.total_processed} заказов ` +
          `(${Math.round(data.success_rate * 100)}% успешности)`,
      );
    },
    onError: (error: Error) => {
      message.error(`Ошибка распределения: ${error.message}`);
    },
  });
};

// Batch preview query
export const useBatchPreview = (
  targetDate: string,
  options: {
    priority_filter?: 'low' | 'normal' | 'high' | 'urgent';
    driver_ids?: string;
    max_orders_per_driver?: number;
  } = {},
) => {
  const { priority_filter, driver_ids, max_orders_per_driver = 10 } = options;

  return useQuery({
    queryKey: ['batch-preview', targetDate, priority_filter, driver_ids, max_orders_per_driver],
    queryFn: async (): Promise<BatchPreviewResponse> => {
      const params = new URLSearchParams({
        max_orders_per_driver: max_orders_per_driver.toString(),
      });

      if (priority_filter) params.append('priority_filter', priority_filter);
      if (driver_ids) params.append('driver_ids', driver_ids);

      const response = await fetch(`${API_BASE}/orders/batch-preview/${targetDate}?${params}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to get preview');
      }

      return response.json();
    },
    enabled: !!targetDate,
    throwOnError: true,
  });
};

// Unassigned orders query
export const useUnassignedOrders = (targetDate: string) => {
  return useQuery({
    queryKey: ['unassigned-orders', targetDate],
    queryFn: async (): Promise<UnassignedOrdersResponse> => {
      const response = await fetch(`${API_BASE}/orders/unassigned/${targetDate}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to get unassigned orders');
      }

      return response.json();
    },
    enabled: !!targetDate,
    throwOnError: true,
  });
};

// Driver schedule query
export const useDriverSchedule = (driverId: number, targetDate: string) => {
  return useQuery({
    queryKey: ['driver-schedule', driverId, targetDate],
    queryFn: async (): Promise<DriverScheduleResponse> => {
      const response = await fetch(`${API_BASE}/drivers/${driverId}/schedule/${targetDate}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to get driver schedule');
      }

      return response.json();
    },
    enabled: !!driverId && !!targetDate,
    throwOnError: true,
  });
};
