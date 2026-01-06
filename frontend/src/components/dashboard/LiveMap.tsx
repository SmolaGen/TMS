import React from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import { useDriverLocations } from '../../hooks/useDriverLocations';
import { DriverMarkers } from './DriverMarkers';
import { OrderRoutes } from './OrderRoutes';
import { useOrdersRaw } from '../../hooks/useOrders';
import type { OrderResponse } from '../../types/api';
import 'leaflet/dist/leaflet.css';

interface LiveMapProps {
    onDriverSelect?: (driverId: number) => void;
    selectedOrderId?: string | number | null;
    orders?: OrderResponse[];
}

export const LiveMap: React.FC<LiveMapProps> = ({ onDriverSelect, selectedOrderId, orders: propOrders }) => {
    const { data: hookDrivers = [] } = useDriverLocations();
    const { data: hookOrders = [] } = useOrdersRaw();

    const orders = propOrders || hookOrders;
    // Используем мок-данные для водителей если нужно, но хук уже это делает
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
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                />
                <OrderRoutes orders={orders} selectedOrderId={selectedOrderId} />
                <DriverMarkers drivers={drivers} onDriverClick={onDriverSelect} />
            </MapContainer>
        </div>
    );
};
