import React from 'react';
import { Polyline, Tooltip, Marker } from 'react-leaflet';
import type { OrderResponse } from '../../types/api';
import polyline from '@mapbox/polyline';
import L from 'leaflet';

interface OrderRoutesProps {
  orders: OrderResponse[];
  selectedOrderId?: string | number | null;
}

// Кастомные иконки для точек
const createPointIcon = (color: string): L.DivIcon =>
  L.divIcon({
    className: 'order-point-icon',
    html: `<div style="width: 12px; height: 12px; background-color: ${color}; border: 2px solid white; border-radius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });

const pickupIcon = createPointIcon('#52c41a');
const dropoffIcon = createPointIcon('#ff4d4f');

export const OrderRoutes: React.FC<OrderRoutesProps> = ({ orders, selectedOrderId }) => {
  return (
    <>
      {orders.map((order) => {
        if (!order.route_geometry) return null;

        const decoded = polyline.decode(order.route_geometry);
        const isSelected = String(order.id) === String(selectedOrderId);

        return (
          <React.Fragment key={order.id}>
            <Polyline
              positions={decoded}
              pathOptions={{
                color: isSelected ? '#1890ff' : '#8c8c8c',
                weight: isSelected ? 5 : 3,
                opacity: isSelected ? 0.9 : 0.4,
                dashArray: order.status === 'pending' ? '5, 10' : undefined,
              }}
            >
              <Tooltip sticky>
                <div>
                  <strong>Заказ #{order.id}</strong>
                  <br />
                  {order.pickup_address} → {order.dropoff_address}
                  <br />
                  {order.price} ₽
                </div>
              </Tooltip>
            </Polyline>

            {/* Отображаем точки только для выбранного заказа или если заказ активен */}
            {(isSelected || order.status === 'in_progress') && (
              <>
                <Marker position={decoded[0]} icon={pickupIcon} zIndexOffset={100} />
                <Marker
                  position={decoded[decoded.length - 1]}
                  icon={dropoffIcon}
                  zIndexOffset={100}
                />
              </>
            )}
          </React.Fragment>
        );
      })}
    </>
  );
};
