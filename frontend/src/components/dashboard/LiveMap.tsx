import React, { useEffect } from 'react';
import { MapContainer, TileLayer, useMap } from 'react-leaflet';
import { useDriverLocations } from '../../hooks/useDriverLocations';
import { DriverMarkers } from './DriverMarkers';
import { OrderRoutes } from './OrderRoutes';
import { useOrdersRaw } from '../../hooks/useOrders';
import type { OrderResponse } from '../../types/api';
import 'leaflet/dist/leaflet.css';
import polyline from '@mapbox/polyline';

interface LiveMapProps {
    onDriverSelect?: (driverId: number) => void;
    selectedOrderId?: string | number | null;
    orders?: OrderResponse[];
}

// Вспомогательный компонент для управления камерой
const MapController: React.FC<{ selectedOrderId?: string | number | null, orders: OrderResponse[] }> = ({ selectedOrderId, orders }) => {
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

export const LiveMap: React.FC<LiveMapProps> = ({ onDriverSelect, selectedOrderId, orders: propOrders }) => {
    const { data: hookDrivers = [] } = useDriverLocations();
    const { data: hookOrders = [] } = useOrdersRaw();

    const orders = propOrders || hookOrders;
    const drivers = hookDrivers;

    return (
        <div style={{ height: '100%', position: 'relative' }}>
            <MapContainer
                center={[43.1155, 131.8855]}
                zoom={12}
                style={{ height: '100%', width: '100%' }}
                scrollWheelZoom={true}
            >
                <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                />
                <MapController selectedOrderId={selectedOrderId} orders={orders} />
                <OrderRoutes orders={orders} selectedOrderId={selectedOrderId} />
                <DriverMarkers drivers={drivers} onDriverClick={onDriverSelect} />
            </MapContainer>
        </div>
    );
};
