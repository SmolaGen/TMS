import { useQuery } from '@tanstack/react-query';
import { fetchDriverLocations } from '../api/drivers';

export const useDriverLocations = () => {
    return useQuery({
        queryKey: ['driver-locations'],
        queryFn: fetchDriverLocations,
        staleTime: 3_000,       // 3 сек
        refetchInterval: 5_000, // Fallback polling если WS недоступен
    });
};
