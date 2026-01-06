import { useQuery } from '@tanstack/react-query';
import { fetchDriversList } from '../api/drivers';
import type { DriverResponse } from '../types/api';

export const useDrivers = () => {
    return useQuery<DriverResponse[]>({
        queryKey: ['drivers'],
        queryFn: fetchDriversList,
        staleTime: 60_000,
    });
};
