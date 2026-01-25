import { apiClient } from './client';
import type { DriverLocation, DriverResponse } from '../types/api';

export const fetchDriverLocations = async (): Promise<DriverLocation[]> => {
  const { data } = await apiClient.get<DriverLocation[]>('/drivers/live');
  console.log('[API] Drivers data:', data);
  return Array.isArray(data) ? data : [];
};

export const fetchDriversList = async (): Promise<DriverResponse[]> => {
  const { data } = await apiClient.get<DriverResponse[]>('/drivers');
  return data;
};
