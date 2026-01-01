import React from 'react';
import { Polyline, Tooltip } from 'react-leaflet';
import type { OrderResponse } from '../../types/api';
import polyline from '@mapbox/polyline';

interface OrderRoutesProps {
    orders: OrderResponse[];
    selectedOrderId?: string | number | null;
}

export const OrderRoutes: React.FC<OrderRoutesProps> = ({ orders, selectedOrderId }) => {
    return (
        <>
            {orders.map((order) => {
                if (!order.route_geometry) return null;

                // Декодируем polyline в массив координат [lat, lng]
                // OSRM использует precision 5 по умолчанию для v1
                const decoded = polyline.decode(order.route_geometry);
                const isSelected = String(order.id) === String(selectedOrderId);

                return (
                    <Polyline
                        key={order.id}
                        positions={decoded}
                        pathOptions={{
                            color: isSelected ? '#1890ff' : '#8c8c8c',
                            weight: isSelected ? 4 : 2,
                            opacity: isSelected ? 0.8 : 0.4,
                            dashArray: isSelected ? undefined : '5, 10',
                        }}
                    >
                        <Tooltip sticky>
                            <div>
                                <strong>Заказ #{order.id}</strong><br />
                                {order.pickup_address} → {order.dropoff_address}<br />
                                {order.price} ₽
                            </div>
                        </Tooltip>
                    </Polyline>
                );
            })}
        </>
    );
};
