import React, { useEffect, useState, useMemo } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import { useDriverLocations } from '../../hooks/useDriverLocations';
import { useDrivers } from '../../hooks/useDrivers';
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
const OrderMapController: React.FC<{ selectedOrderId?: string | number | null, orders: OrderResponse[] }> = ({ selectedOrderId, orders }) => {
    const map = useMap();

    useEffect(() => {
        if (!selectedOrderId) return;

        const order = orders.find(o => String(o.id) === String(selectedOrderId));
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

export const LiveMap: React.FC<LiveMapProps> = ({
    onDriverSelect,
    selectedOrderId,
    selectedDriverId,
    orders: propOrders
}) => {
    const { data: hookDriverLocations = [] } = useDriverLocations();
    const { data: hookDrivers = [] } = useDrivers();
    const { data: hookOrders = [] } = useOrdersRaw();

    const orders = propOrders || hookOrders;

    // Мэппинг данных для кластеризации
    const mappedDrivers = useMemo(() => {
        return hookDriverLocations.map(loc => {
            const info = hookDrivers.find(d => d.id === loc.driver_id);
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

    return (
        <div style={{ height: '100%', position: 'relative' }}>
            <MapContainer
                center={DEFAULT_CENTER}
                zoom={DEFAULT_ZOOM}
                style={{ height: '100%', width: '100%' }}
                scrollWheelZoom={true}
            >
                <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
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
                onCenterOnSelected={() => setCenterSignal(s => s + 1)}
                onResetView={() => setResetSignal(s => s + 1)}
            />

            <MapLegend />
        </div>
    );
};
