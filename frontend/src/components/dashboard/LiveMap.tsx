import React from 'react';
import { MapContainer, TileLayer } from 'react-leaflet';
import { useDriverLocations } from '../../hooks/useDriverLocations';
import { DriverMarkers } from './DriverMarkers';
import 'leaflet/dist/leaflet.css';

interface LiveMapProps {
    onDriverSelect?: (driverId: number) => void;
}

export const LiveMap: React.FC<LiveMapProps> = ({ onDriverSelect }) => {
    const { data: drivers = [], isLoading } = useDriverLocations();

    return (
        <div style={{ height: '100%', position: 'relative' }}>
            {isLoading && (
                <div style={{
                    position: 'absolute',
                    top: 10,
                    right: 10,
                    zIndex: 1000,
                    background: 'rgba(255,255,255,0.9)',
                    padding: '8px 16px',
                    borderRadius: 8,
                    boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
                    fontSize: 14,
                }}>
                    Загрузка карты...
                </div>
            )}

            <MapContainer
                center={[43.1198, 131.8869]} // Владивосток
                zoom={12}
                style={{ height: '100%', width: '100%' }}
            >
                <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution="&copy; OpenStreetMap contributors"
                />
                <DriverMarkers drivers={drivers} onDriverClick={onDriverSelect} />
            </MapContainer>
        </div>
    );
};
