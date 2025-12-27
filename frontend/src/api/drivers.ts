import { apiClient } from './client';
import type { DriverLocation } from '../types/api';

export const fetchDriverLocations = async (): Promise<DriverLocation[]> => {
    const { data } = await apiClient.get<DriverLocation[]>('/drivers/live');
    console.log('[API] Drivers data:', data);
    return Array.isArray(data) ? data : [];
};
