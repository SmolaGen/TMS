import { useQuery } from '@tanstack/react-query';
import { searchAddress, reverseGeocode } from '../api/geocoding';

export const useGeocoding = (query: string) => {
    return useQuery({
        queryKey: ['geocoding', query],
        queryFn: () => searchAddress(query),
        enabled: !!query && query.length >= 3,
        staleTime: 300_000, // 5 min
    });
};

export const useReverseGeocoding = (lat?: number, lon?: number) => {
    return useQuery({
        queryKey: ['reverse-geocoding', lat, lon],
        queryFn: () => (lat && lon ? reverseGeocode(lat, lon) : null),
        enabled: !!lat && !!lon,
        staleTime: 300_000,
    });
};
