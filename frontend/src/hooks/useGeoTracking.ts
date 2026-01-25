import { useState, useEffect, useRef } from 'react';
import { apiClient } from '../api/client';

interface GeoState {
  latitude: number | null;
  longitude: number | null;
  error: string | null;
  isTracking: boolean;
}

declare global {
  interface Window {
    Telegram?: {
      WebApp?: {
        LocationManager?: {
          init: () => void;
          getLocation: (
            callback: (location: { latitude: number; longitude: number } | null) => void,
          ) => void;
          isLocationAvailable: boolean;
        };
      };
    };
  }
}

export function useGeoTracking(driverId: number | undefined) {
  const [state, setState] = useState<GeoState>({
    latitude: null,
    longitude: null,
    error: null,
    isTracking: false,
  });

  const watchIdRef = useRef<number | null>(null);
  const intervalIdRef = useRef<NodeJS.Timeout | null>(null);
  const lastUpdateRef = useRef<number>(0);
  const UPDATE_INTERVAL = 10000;

  const sendLocation = async (lat: number, lon: number) => {
    if (!driverId) return;

    try {
      await apiClient.post(`/drivers/${driverId}/location`, {
        latitude: lat,
        longitude: lon,
        status: 'available',
        timestamp: new Date().toISOString(),
      });
      console.log(`[Geo] Sent location for driver ${driverId}: ${lat}, ${lon}`);
      lastUpdateRef.current = Date.now();
    } catch (err) {
      console.error('[Geo] Failed to send location:', err);
    }
  };

  const tryTelegramLocation = () => {
    const tg = window.Telegram?.WebApp?.LocationManager;
    if (tg?.isLocationAvailable) {
      console.log('[Geo] Using Telegram WebApp Location API');
      tg.init();

      const checkLocation = () => {
        tg.getLocation((location) => {
          if (location) {
            const { latitude, longitude } = location;
            setState((s) => ({ ...s, latitude, longitude, error: null }));
            sendLocation(latitude, longitude);
          }
        });
      };

      checkLocation();
      intervalIdRef.current = setInterval(checkLocation, UPDATE_INTERVAL);
      return true;
    }
    return false;
  };

  const startTracking = () => {
    setState((s) => ({ ...s, isTracking: true, error: null }));

    if (tryTelegramLocation()) {
      return;
    }

    if (!navigator.geolocation) {
      setState((s) => ({ ...s, error: 'Геолокация не поддерживается вашим браузером' }));
      return;
    }

    console.log('[Geo] Using browser geolocation API');

    navigator.geolocation.getCurrentPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setState((s) => ({ ...s, latitude, longitude, error: null }));
        sendLocation(latitude, longitude);
      },
      (error) => {
        console.error('[Geo] Initial position error:', error);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      },
    );

    watchIdRef.current = navigator.geolocation.watchPosition(
      (position) => {
        const { latitude, longitude } = position.coords;
        setState((s) => ({ ...s, latitude, longitude, error: null }));

        if (Date.now() - lastUpdateRef.current > UPDATE_INTERVAL) {
          sendLocation(latitude, longitude);
        }
      },
      (error) => {
        let errorMsg = 'Ошибка геолокации';
        switch (error.code) {
          case error.PERMISSION_DENIED:
            errorMsg = 'Доступ к геолокации запрещен. Разрешите в настройках браузера.';
            break;
          case error.POSITION_UNAVAILABLE:
            errorMsg = 'Местоположение недоступно';
            break;
          case error.TIMEOUT:
            errorMsg = 'Тайм-аут запроса геолокации';
            break;
        }
        setState((s) => ({ ...s, error: errorMsg }));
        console.error('[Geo] Error:', error);
      },
      {
        enableHighAccuracy: true,
        maximumAge: 10000,
        timeout: 5000,
      },
    );
  };

  const stopTracking = () => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    if (intervalIdRef.current !== null) {
      clearInterval(intervalIdRef.current);
      intervalIdRef.current = null;
    }
    setState((s) => ({ ...s, isTracking: false }));
  };

  useEffect(() => {
    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current);
      }
      if (intervalIdRef.current !== null) {
        clearInterval(intervalIdRef.current);
      }
    };
  }, []);

  return { ...state, startTracking, stopTracking };
}
