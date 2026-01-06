import { useState, useEffect, useRef } from 'react';
import { apiClient } from '../api/client';

interface GeoState {
    latitude: number | null;
    longitude: number | null;
    error: string | null;
    isTracking: boolean;
}

export function useGeoTracking(driverId: number | undefined) {
    const [state, setState] = useState<GeoState>({
        latitude: null,
        longitude: null,
        error: null,
        isTracking: false,
    });

    const watchIdRef = useRef<number | null>(null);
    const lastUpdateRef = useRef<number>(0);
    const UPDATE_INTERVAL = 30000; // 30 секунд

    const sendLocation = async (lat: number, lon: number) => {
        if (!driverId) return;

        try {
            await apiClient.post(`/drivers/${driverId}/location`, {
                latitude: lat,
                longitude: lon,
                status: 'available',
                timestamp: new Date().toISOString()
            });
            console.log(`[Geo] Sent location for driver ${driverId}: ${lat}, ${lon}`);
            lastUpdateRef.current = Date.now();
        } catch (err) {
            console.error('[Geo] Failed to send location:', err);
        }
    };

    const startTracking = () => {
        if (!navigator.geolocation) {
            setState(s => ({ ...s, error: 'Геолокация не поддерживается вашим браузером' }));
            return;
        }

        setState(s => ({ ...s, isTracking: true, error: null }));

        watchIdRef.current = navigator.geolocation.watchPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                setState(s => ({ ...s, latitude, longitude, error: null }));

                // Отправляем если прошло достаточно времени
                if (Date.now() - lastUpdateRef.current > UPDATE_INTERVAL) {
                    sendLocation(latitude, longitude);
                }
            },
            (error) => {
                let errorMsg = 'Ошибка геолокации';
                switch (error.code) {
                    case error.PERMISSION_DENIED:
                        errorMsg = 'Доступ к геолокации запрещен';
                        break;
                    case error.POSITION_UNAVAILABLE:
                        errorMsg = 'Местоположение недоступно';
                        break;
                    case error.TIMEOUT:
                        errorMsg = 'Тайм-аут запроса геолокации';
                        break;
                }
                setState(s => ({ ...s, error: errorMsg }));
                console.error('[Geo] Error:', error);
            },
            {
                enableHighAccuracy: true,
                maximumAge: 10000,
                timeout: 5000,
            }
        );
    };

    const stopTracking = () => {
        if (watchIdRef.current !== null) {
            navigator.geolocation.clearWatch(watchIdRef.current);
            watchIdRef.current = null;
        }
        setState(s => ({ ...s, isTracking: false }));
    };

    useEffect(() => {
        return () => {
            if (watchIdRef.current !== null) {
                navigator.geolocation.clearWatch(watchIdRef.current);
            }
        };
    }, []);

    return { ...state, startTracking, stopTracking };
}
