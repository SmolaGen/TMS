import { apiClient } from './client';
import type { GeocodingResult } from '../types/api';

export const searchAddress = async (query: string): Promise<GeocodingResult[]> => {
  if (!query || query.length < 3) return [];
  const { data } = await apiClient.get<GeocodingResult[]>('/geocoding/search', {
    params: { q: query },
  });
  return data;
};

export const reverseGeocode = async (lat: number, lon: number): Promise<GeocodingResult | null> => {
  const { data } = await apiClient.get<GeocodingResult>('/geocoding/reverse', {
    params: { lat, lon },
  });
  return data;
};
