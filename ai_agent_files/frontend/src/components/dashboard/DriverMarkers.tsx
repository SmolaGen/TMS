import { useEffect, useRef, useCallback } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import { DriverStatus } from '../../types/api';
import type { DriverLocation } from '../../types/api';

// Иконки по статусу - используем SVG иконку автомобиля
const createIcon = (status: DriverStatus): L.DivIcon => {
    const colors: Record<DriverStatus, string> = {
        [DriverStatus.AVAILABLE]: '#52c41a',  // зелёный
        [DriverStatus.BUSY]: '#faad14',       // жёлтый
        [DriverStatus.OFFLINE]: '#ff4d4f',    // красный
    };

    const color = colors[status] || colors[DriverStatus.OFFLINE];

    return L.divIcon({
        className: 'driver-marker',
        html: `
      <div style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="10" fill="white" />
          <path d="M18.92 11.01C18.72 10.42 18.16 10 17.5 10H6.5C5.84 10 5.28 10.42 5.08 11.01L3 17V24H5V22H19V24H21V17L18.92 11.01ZM6.5 11H17.5L18.5 14H5.5L6.5 11ZM5 19V16H19V19H5Z" fill="${color}"/>
          <circle cx="7" cy="17.5" r="1.5" fill="${color}"/>
          <circle cx="17" cy="17.5" r="1.5" fill="${color}"/>
        </svg>
      </div>
    `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
    });
};

const icons: Record<DriverStatus, L.DivIcon> = {
    [DriverStatus.AVAILABLE]: createIcon(DriverStatus.AVAILABLE),
    [DriverStatus.BUSY]: createIcon(DriverStatus.BUSY),
    [DriverStatus.OFFLINE]: createIcon(DriverStatus.OFFLINE),
};

interface DriverMarkersProps {
    drivers: DriverLocation[];
    onDriverClick?: (driverId: number) => void;
}

export const DriverMarkers: React.FC<DriverMarkersProps> = ({ drivers, onDriverClick }) => {
    const map = useMap();

    // Хранилище маркеров: driver_id -> L.Marker
    const markersRef = useRef<Map<number, L.Marker>>(new Map());

    // Помощник для безопасного получения иконки
    const getIcon = useCallback((status?: DriverStatus) => {
        if (status && icons[status]) return icons[status];
        return icons[DriverStatus.AVAILABLE];
    }, []);

    // Для плавной анимации
    const animationFrameRef = useRef<number | null>(null);
    const targetPositionsRef = useRef<Map<number, L.LatLng>>(new Map());

    // Анимация с requestAnimationFrame
    const animateMarkers = useCallback(() => {
        const LERP_FACTOR = 0.15;
        let hasActiveAnimations = false;

        for (const [driverId, targetLatLng] of targetPositionsRef.current) {
            const marker = markersRef.current.get(driverId);
            if (!marker) continue;

            const currentLatLng = marker.getLatLng();
            const distance = currentLatLng.distanceTo(targetLatLng);

            if (distance > 0.5) {
                hasActiveAnimations = true;

                // Линейная интерполяция
                const newLat = currentLatLng.lat + (targetLatLng.lat - currentLatLng.lat) * LERP_FACTOR;
                const newLng = currentLatLng.lng + (targetLatLng.lng - currentLatLng.lng) * LERP_FACTOR;

                // ИМПЕРАТИВНОЕ обновление - минуем React reconciliation
                marker.setLatLng([newLat, newLng]);
            } else {
                marker.setLatLng(targetLatLng);
                targetPositionsRef.current.delete(driverId);
            }
        }

        if (hasActiveAnimations) {
            animationFrameRef.current = requestAnimationFrame(animateMarkers);
        } else {
            animationFrameRef.current = null;
        }
    }, []);

    // Синхронизация маркеров с данными
    useEffect(() => {
        const currentMarkers = markersRef.current;
        const currentDriverIds = new Set(drivers.map((d) => d.driver_id));

        // Удаляем маркеры отсутствующих водителей
        for (const [driverId, marker] of currentMarkers) {
            if (!currentDriverIds.has(driverId)) {
                map.removeLayer(marker);
                currentMarkers.delete(driverId);
                targetPositionsRef.current.delete(driverId);
            }
        }

        // Обновляем/создаём маркеры
        for (const driver of drivers) {
            const newLatLng = L.latLng(driver.latitude, driver.longitude);
            let marker = currentMarkers.get(driver.driver_id);

            if (!marker) {
                // Создаём новый маркер
                marker = L.marker(newLatLng, { icon: getIcon(driver.status) })
                    .addTo(map)
                    .bindTooltip(`Водитель #${driver.driver_id}`, { permanent: false });

                if (onDriverClick) {
                    marker.on('click', () => onDriverClick(driver.driver_id));
                }

                currentMarkers.set(driver.driver_id, marker);
            } else {
                // Обновляем существующий - устанавливаем целевую позицию для анимации
                targetPositionsRef.current.set(driver.driver_id, newLatLng);
                marker.setIcon(getIcon(driver.status));
            }
        }

        // Запускаем анимацию если есть обновления
        if (!animationFrameRef.current && targetPositionsRef.current.size > 0) {
            animationFrameRef.current = requestAnimationFrame(animateMarkers);
        }
    }, [drivers, map, onDriverClick, animateMarkers, getIcon]);

    // Cleanup при размонтировании - предотвращаем утечки памяти
    useEffect(() => {
        return () => {
            if (animationFrameRef.current) {
                cancelAnimationFrame(animationFrameRef.current);
            }
            for (const marker of markersRef.current.values()) {
                map.removeLayer(marker);
            }
            markersRef.current.clear();
            targetPositionsRef.current.clear();
        };
    }, [map]);

    // Компонент ничего не рендерит - всё через императивный Leaflet API
    return null;
};
