import React, { useEffect, useState, useMemo } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import { Alert, Button } from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import { useDriverLocations } from '../../hooks/useDriverLocations';
import { useDrivers } from '../../hooks/useDrivers';
import { useTheme } from '../../hooks/useTheme';
import { ClusteredDriverMarkers } from '../map/ClusteredDriverMarkers';
import { MapControls } from '../map/MapControls';
import type { MapControlsState } from '../map/MapControls';
import { MapLegend } from '../map/MapLegend';
import { OrderRoutes } from './OrderRoutes';
import { useOrdersRaw } from '../../hooks/useOrders';
import type { OrderResponse } from '../../types/api';
import 'leaflet/dist/leaflet.css';
import polyline from '@mapbox/polyline';

interface LiveMapProps {
  onDriverSelect?: (driverId: number) => void;
  selectedOrderId?: string | number | null;
  selectedDriverId?: number | null;
  orders?: OrderResponse[];
}

const DEFAULT_CENTER: [number, number] = [43.1155, 131.8855];
const DEFAULT_ZOOM = 12;

// Вспомогательный компонент для управления камерой (по заказам)
const OrderMapController: React.FC<{
  selectedOrderId?: string | number | null;
  orders: OrderResponse[];
}> = ({ selectedOrderId, orders }) => {
  const map = useMap();

  useEffect(() => {
    if (!selectedOrderId) return;

    const order = orders.find((o) => String(o.id) === String(selectedOrderId));
    if (order && order.route_geometry) {
      const decoded = polyline.decode(order.route_geometry);
      if (decoded.length > 0) {
        map.flyTo(decoded[0], 14, { duration: 1.5 });
      }
    }
  }, [selectedOrderId, orders, map]);

  return null;
};

// Вспомогательный компонент для управления центром карты (по водителям)
const MapCenterController: React.FC<{
  selectedDriverId?: number | null;
  drivers: any[];
  follow: boolean;
  resetSignal: number;
  centerSignal: number;
}> = ({ selectedDriverId, drivers, follow, resetSignal, centerSignal }) => {
  const map = useMap();

  // Следование за водителем
  useEffect(() => {
    if (!follow || !selectedDriverId) return;

    const driver = drivers.find((d) => d.id === selectedDriverId);
    if (driver?.lat && driver?.lon) {
      map.panTo([driver.lat, driver.lon], { animate: true });
    }
  }, [selectedDriverId, drivers, follow, map]);

  // Сброс вида
  useEffect(() => {
    if (resetSignal > 0) {
      map.setView(DEFAULT_CENTER, DEFAULT_ZOOM, { animate: true });
    }
  }, [resetSignal, map]);

  // Ручное центрирование на выбранном
  useEffect(() => {
    if (centerSignal > 0 && selectedDriverId) {
      const driver = drivers.find((d) => d.id === selectedDriverId);
      if (driver?.lat && driver?.lon) {
        map.flyTo([driver.lat, driver.lon], 15, { animate: true });
      }
    }
  }, [centerSignal, selectedDriverId, drivers, map]);

  return null;
};

// Тайлы для карты
const TILE_LIGHT = 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
const TILE_DARK = 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';
const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

export const LiveMap: React.FC<LiveMapProps> = ({
  onDriverSelect,
  selectedOrderId,
  selectedDriverId,
  orders: propOrders,
}) => {
  const { isDark } = useTheme();
  const {
    data: hookDriverLocations = [],
    error: locError,
    refetch: refetchLoc,
  } = useDriverLocations();
  const { data: hookDrivers = [], error: driversError, refetch: refetchDrivers } = useDrivers();
  const { data: hookOrders = [], error: ordersError, refetch: refetchOrders } = useOrdersRaw();

  const error = locError || driversError || ordersError;

  const orders = propOrders || hookOrders;

  // Мэппинг данных для кластеризации
  const mappedDrivers = useMemo(() => {
    return hookDriverLocations.map((loc) => {
      const info = hookDrivers.find((d) => d.id === loc.driver_id);
      return {
        id: loc.driver_id,
        name: info?.name || `Водитель #${loc.driver_id}`,
        lat: loc.latitude,
        lon: loc.longitude,
        status: loc.status as any,
      };
    });
  }, [hookDriverLocations, hookDrivers]);

  const [controlsState, setControlsState] = useState<MapControlsState>({
    showRoutes: true,
    showOnlyFreeDrivers: false,
    followSelected: false,
  });

  const [resetSignal, setResetSignal] = useState(0);
  const [centerSignal, setCenterSignal] = useState(0);

  const handleControlsChange = (newState: Partial<MapControlsState>) => {
    setControlsState((prev) => ({ ...prev, ...newState }));
  };

  if (error) {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--tms-bg-container)',
          padding: 20,
        }}
      >
        <Alert
          message="Ошибка карты"
          description="Не удалось загрузить данные для отображения на карте."
          type="error"
          showIcon
          action={
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => {
                refetchLoc();
                refetchDrivers();
                refetchOrders();
              }}
            >
              Обновить
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div style={{ height: '100%', position: 'relative' }}>
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ height: '100%', width: '100%', background: '#0a0f18' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          key={isDark ? 'dark' : 'light'}
          url={isDark ? TILE_DARK : TILE_LIGHT}
          attribution={TILE_ATTRIBUTION}
        />

        <OrderMapController selectedOrderId={selectedOrderId} orders={orders} />

        {controlsState.showRoutes && (
          <OrderRoutes orders={orders} selectedOrderId={selectedOrderId} />
        )}

        <ClusteredDriverMarkers
          drivers={mappedDrivers}
          onDriverClick={onDriverSelect}
          showOnlyFree={controlsState.showOnlyFreeDrivers}
        />

        <MapCenterController
          selectedDriverId={selectedDriverId}
          drivers={mappedDrivers}
          follow={controlsState.followSelected}
          resetSignal={resetSignal}
          centerSignal={centerSignal}
        />
      </MapContainer>

      <MapControls
        state={controlsState}
        onChange={handleControlsChange}
        onCenterOnSelected={() => setCenterSignal((s) => s + 1)}
        onResetView={() => setResetSignal((s) => s + 1)}
      />

      <MapLegend />
    </div>
  );
};
