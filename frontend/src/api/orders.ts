import { apiClient } from './client';
import type { OrderResponse, OrderMoveRequest, OrderCreate } from '../types/api';

export const fetchOrders = async (dateRange?: [Date, Date]): Promise<OrderResponse[]> => {
    const params = dateRange ? {
        start: dateRange[0].toISOString(),
        end: dateRange[1].toISOString(),
    } : {};

    const { data } = await apiClient.get<OrderResponse[]>('/orders', { params });
    return data;
};

export const moveOrder = async (
    orderId: number,
    payload: OrderMoveRequest
): Promise<OrderResponse> => {
    const { data } = await apiClient.patch<OrderResponse>(
        `/orders/${orderId}/move`,
        payload
    );
    return data;
};

export const createOrder = async (
    payload: OrderCreate
): Promise<OrderResponse> => {
    const { data } = await apiClient.post<OrderResponse>('/orders', payload);
    return data;
};
