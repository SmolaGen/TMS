import { useQuery } from '@tanstack/react-query';
import { fetchDriverLocations } from '../api/drivers';
import { isDevMode } from '../components/DevAuthSelector';
import { MOCK_DRIVER_LOCATIONS } from '../api/mockData';

export const useDriverLocations = () => {
    return useQuery({
        queryKey: ['driver-locations'],
        queryFn: async () => {
            // В dev-режиме возвращаем мок-данные
            if (isDevMode()) {
                console.log('[DEV] Using mock driver locations');
                return MOCK_DRIVER_LOCATIONS;
            }
            return fetchDriverLocations();
        },
        staleTime: 3_000,       // 3 сек
        refetchInterval: 5_000, // Fallback polling если WS недоступен
    });
};
