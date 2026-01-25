import React, { useEffect, useRef } from 'react';
import { useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet.markercluster';
import 'leaflet.markercluster/dist/MarkerCluster.css';
import 'leaflet.markercluster/dist/MarkerCluster.Default.css';

interface Driver {
  id: number;
  name: string;
  lat: number;
  lon: number;
  status: 'available' | 'busy' | 'in_progress' | 'offline';
  current_order_id?: number;
}

interface ClusteredDriverMarkersProps {
  drivers: Driver[];
  onDriverClick?: (driverId: number) => void;
  showOnlyFree?: boolean;
}

const statusColors: Record<string, string> = {
  available: '#52c41a',
  busy: '#faad14',
  in_progress: '#1890ff',
  offline: '#d9d9d9',
};

const createDriverIcon = (driver: Driver) => {
  const color = statusColors[driver.status] || '#d9d9d9';

  return L.divIcon({
    className: 'custom-driver-marker',
    html: `
            <div class="${driver.status === 'available' ? 'driver-marker-available' : ''}" style="
                width: 36px;
                height: 36px;
                border-radius: 50%;
                background: ${color};
                border: 3px solid white;
                box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
                font-weight: bold;
                font-size: 14px;
            ">
                ${driver.name.charAt(0).toUpperCase()}
            </div>
        `,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
};

export const ClusteredDriverMarkers: React.FC<ClusteredDriverMarkersProps> = ({
  drivers,
  onDriverClick,
  showOnlyFree = false,
}) => {
  const map = useMap();
  const clusterGroupRef = useRef<L.MarkerClusterGroup | null>(null);

  useEffect(() => {
    // Создаём группу кластеров
    const clusterGroup = L.markerClusterGroup({
      maxClusterRadius: 50,
      spiderfyOnMaxZoom: true,
      showCoverageOnHover: false,
      zoomToBoundsOnClick: true,
      iconCreateFunction: (cluster) => {
        const count = cluster.getChildCount();
        return L.divIcon({
          html: `
                        <div style="
                            width: 40px;
                            height: 40px;
                            border-radius: 50%;
                            background: #1890ff;
                            border: 3px solid white;
                            box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            color: white;
                            font-weight: bold;
                            font-size: 16px;
                        ">
                            ${count}
                        </div>
                    `,
          className: 'custom-cluster-icon',
          iconSize: [40, 40],
          iconAnchor: [20, 20],
        });
      },
    });

    clusterGroupRef.current = clusterGroup;
    map.addLayer(clusterGroup);

    return () => {
      map.removeLayer(clusterGroup);
    };
  }, [map]);

  // Обновление маркеров при изменении данных
  useEffect(() => {
    const clusterGroup = clusterGroupRef.current;
    if (!clusterGroup) return;

    clusterGroup.clearLayers();

    const filteredDrivers = showOnlyFree
      ? drivers.filter((d) => d.status === 'available')
      : drivers;

    filteredDrivers.forEach((driver) => {
      if (!driver.lat || !driver.lon) return;

      const marker = L.marker([driver.lat, driver.lon], {
        icon: createDriverIcon(driver),
      });

      // Popup с информацией
      marker.bindPopup(`
                <div style="min-width: 150px;">
                    <strong>${driver.name}</strong><br/>
                    <span style="color: ${statusColors[driver.status]};">
                        ● ${
                          driver.status === 'available'
                            ? 'Свободен'
                            : driver.status === 'busy'
                              ? 'Занят'
                              : driver.status === 'in_progress'
                                ? 'На заказе'
                                : 'Офлайн'
                        }
                    </span>
                    ${
                      driver.current_order_id
                        ? `<br/><small>Заказ: #${driver.current_order_id}</small>`
                        : ''
                    }
                </div>
            `);

      marker.on('click', () => {
        onDriverClick?.(driver.id);
      });

      clusterGroup.addLayer(marker);
    });
  }, [drivers, showOnlyFree, onDriverClick]);

  return null; // Рендерим императивно через Leaflet API
};
