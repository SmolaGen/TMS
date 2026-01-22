import { useQuery } from '@tanstack/react-query';
import { fetchDriversList } from '../api/drivers';
import { MOCK_DRIVERS } from '../api/mockData';
import type { DriverResponse } from '../types/api';

export const useDrivers = () => {
    return useQuery<DriverResponse[]>({
        queryKey: ['drivers'],
        queryFn: async () => {
            if (localStorage.getItem('tms_use_mocks') === 'true') {
                console.log('[DEV] Using mock drivers data');
                return MOCK_DRIVERS;
            }
            return fetchDriversList();
        },
        staleTime: 60_000,
        throwOnError: true,
    });
};
