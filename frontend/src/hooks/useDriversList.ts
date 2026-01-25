import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import type { DriverResponse } from '../types/api';

export const useDriversList = () => {
  return useQuery<DriverResponse[]>({
    queryKey: ['drivers-list'],
    queryFn: async () => {
      const { data } = await apiClient.get<DriverResponse[]>('/drivers');
      return data;
    },
    staleTime: 30_000, // 30 секунд
    refetchInterval: 60_000, // Обновление каждую минуту
    throwOnError: true,
  });
};
