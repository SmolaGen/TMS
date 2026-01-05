import { useEffect, useRef, useCallback } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import { DriverStatus } from '../../types/api';
import type { DriverLocation } from '../../types/api';

// Иконки по статусу - используем divIcon для простоты
const createIcon = (status: DriverStatus): L.DivIcon => {
    const colors: Record<DriverStatus, string> = {
        [DriverStatus.AVAILABLE]: '#52c41a',  // зелёный
        [DriverStatus.BUSY]: '#faad14',       // жёлтый
        [DriverStatus.OFFLINE]: '#ff4d4f',    // красный
    };

    return L.divIcon({
        className: 'driver-marker',
        html: `
      <div style="
        width: 24px;
        height: 24px;
        border-radius: 50%;
        background-color: ${colors[status]};
        border: 3px solid white;
        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      "></div>
    `,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
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
