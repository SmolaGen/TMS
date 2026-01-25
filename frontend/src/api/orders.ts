import { apiClient } from './client';
import type { OrderResponse, OrderMoveRequest, OrderCreate } from '../types/api';

export const fetchOrders = async (dateRange?: [Date, Date]): Promise<OrderResponse[]> => {
  const params = dateRange
    ? {
        start: dateRange[0].toISOString(),
        end: dateRange[1].toISOString(),
      }
    : {};

  const { data } = await apiClient.get<OrderResponse[]>('/orders', { params });
  return data;
};

export const moveOrder = async (
  orderId: number,
  payload: OrderMoveRequest,
): Promise<OrderResponse> => {
  const { data } = await apiClient.patch<OrderResponse>(`/orders/${orderId}/move`, payload);
  return data;
};

export const createOrder = async (payload: OrderCreate): Promise<OrderResponse> => {
  const { data } = await apiClient.post<OrderResponse>('/orders', payload);
  return data;
};

export const fetchOrderById = async (orderId: number | string): Promise<OrderResponse> => {
  const { data } = await apiClient.get<OrderResponse>(`/orders/${orderId}`);
  return data;
};

export const cancelOrder = async (
  orderId: number | string,
  reason?: string,
): Promise<OrderResponse> => {
  const { data } = await apiClient.post<OrderResponse>(`/orders/${orderId}/cancel`, null, {
    params: reason ? { reason } : {},
  });
  return data;
};

export const completeOrder = async (orderId: number | string): Promise<OrderResponse> => {
  const { data } = await apiClient.post<OrderResponse>(`/orders/${orderId}/complete`);
  return data;
};

export const markArrived = async (orderId: number | string): Promise<OrderResponse> => {
  const { data } = await apiClient.post<OrderResponse>(`/orders/${orderId}/arrive`);
  return data;
};

export const startTrip = async (orderId: number | string): Promise<OrderResponse> => {
  const { data } = await apiClient.post<OrderResponse>(`/orders/${orderId}/start`);
  return data;
};

export const assignOrder = async (
  orderId: number | string,
  driverId: number,
): Promise<OrderResponse> => {
  const { data } = await apiClient.post<OrderResponse>(`/orders/${orderId}/assign/${driverId}`);
  return data;
};

export const importOrdersExcel = async (
  file: File,
): Promise<{ created: number; failed: number; errors: any[] }> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post('/orders/import/excel', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return data;
};
