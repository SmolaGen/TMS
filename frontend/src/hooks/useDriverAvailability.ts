import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { message } from 'antd';

export type AvailabilityType = 'vacation' | 'sick_leave' | 'day_off' | 'personal' | 'other';

export interface DriverAvailabilityBase {
  driver_id: number;
  availability_type: AvailabilityType;
  time_start: string; // ISO datetime string
  time_end: string; // ISO datetime string
  description?: string;
}

export interface DriverAvailabilityCreate extends DriverAvailabilityBase {}

export interface DriverAvailabilityUpdate {
  availability_type?: AvailabilityType;
  time_start?: string;
  time_end?: string;
  description?: string;
}

export interface DriverAvailabilityResponse extends DriverAvailabilityBase {
  id: number;
  created_at: string;
  updated_at: string;
}

const API_BASE = '/api/v1';

// Get driver availability periods
export const useDriverAvailability = (
  driverId: number,
  dateRange?: { dateFrom: string; dateUntil: string },
) => {
  return useQuery({
    queryKey: ['driver-availability', driverId, dateRange],
    queryFn: async (): Promise<DriverAvailabilityResponse[]> => {
      const params = new URLSearchParams();
      if (dateRange) {
        params.append('date_from', dateRange.dateFrom);
        params.append('date_until', dateRange.dateUntil);
      }

      const queryString = params.toString();
      const url = `${API_BASE}/drivers/${driverId}/availability${queryString ? `?${queryString}` : ''}`;

      const response = await fetch(url, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to get driver availability');
      }

      return response.json();
    },
    enabled: !!driverId,
    throwOnError: true,
  });
};

// Create availability period
export const useCreateAvailability = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (
      data: DriverAvailabilityCreate,
    ): Promise<DriverAvailabilityResponse> => {
      const response = await fetch(`${API_BASE}/drivers/${data.driver_id}/availability`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create availability period');
      }

      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['driver-availability', data.driver_id] });
      message.success('Период недоступности успешно создан');
    },
    onError: (error: Error) => {
      message.error(`Ошибка создания периода: ${error.message}`);
    },
  });
};

// Update availability period
export const useUpdateAvailability = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      availabilityId,
      data,
    }: {
      availabilityId: number;
      data: DriverAvailabilityUpdate;
    }): Promise<DriverAvailabilityResponse> => {
      const response = await fetch(`${API_BASE}/availability/${availabilityId}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update availability period');
      }

      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['driver-availability', data.driver_id] });
      message.success('Период недоступности успешно обновлён');
    },
    onError: (error: Error) => {
      message.error(`Ошибка обновления периода: ${error.message}`);
    },
  });
};

// Delete availability period
export const useDeleteAvailability = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      availabilityId,
    }: {
      availabilityId: number;
      driverId: number;
    }): Promise<void> => {
      const response = await fetch(`${API_BASE}/availability/${availabilityId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete availability period');
      }
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['driver-availability', variables.driverId] });
      message.success('Период недоступности успешно удалён');
    },
    onError: (error: Error) => {
      message.error(`Ошибка удаления периода: ${error.message}`);
    },
  });
};
