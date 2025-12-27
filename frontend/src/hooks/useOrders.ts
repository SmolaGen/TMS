import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notification } from 'antd';
import { useRef, useCallback } from 'react';
import { fetchOrders, moveOrder } from '../api/orders';
import type { OrderResponse, TimelineOrder, OrderMoveRequest } from '../types/api';

// Локальный тип для vis-timeline item
interface VisTimelineItem {
    id: string | number;
    group?: string | number;
    content: string;
    start: Date;
    end?: Date;
    className?: string;
    editable?: boolean;
}

// Преобразование API ответа в формат Timeline
const toTimelineOrder = (order: OrderResponse): TimelineOrder | null => {
    if (!order.time_start || !order.time_end) return null;

    return {
        id: String(order.id),
        group: order.driver_id ? String(order.driver_id) : 'unassigned',
        content: `Заказ #${order.id}`,
        start: new Date(order.time_start),
        end: new Date(order.time_end),
        className: `order-${order.priority}`,
        editable: order.status !== 'completed' && order.status !== 'cancelled',
    };
};

export const useOrders = (dateRange?: [Date, Date]) => {
    return useQuery({
        queryKey: ['orders', dateRange?.map(d => d.toISOString())],
        queryFn: () => fetchOrders(dateRange),
        select: (data) => data.map(toTimelineOrder).filter(Boolean) as TimelineOrder[],
        staleTime: 30_000,
        refetchInterval: 60_000,
    });
};

// Мутация с Optimistic UI и Rollback
export const useMoveOrder = () => {
    const queryClient = useQueryClient();

    // Сохраняем callback для отката Timeline
    const pendingCallbackRef = useRef<((item: VisTimelineItem | null) => void) | null>(null);

    const mutation = useMutation({
        mutationFn: async ({ orderId, payload }: { orderId: number; payload: OrderMoveRequest }) => {
            return moveOrder(orderId, payload);
        },

        // Optimistic Update
        onMutate: async ({ orderId, payload }) => {
            // Отменяем исходящие запросы
            await queryClient.cancelQueries({ queryKey: ['orders'] });

            // Сохраняем snapshot для отката
            const previousOrders = queryClient.getQueryData<OrderResponse[]>(['orders']);

            // Optimistic update кэша
            queryClient.setQueryData<OrderResponse[]>(['orders'], (old) =>
                old?.map((order) =>
                    order.id === orderId
                        ? { ...order, time_start: payload.new_time_start, time_end: payload.new_time_end }
                        : order
                ) ?? []
            );

            return { previousOrders };
        },

        // Откат при ошибке
        onError: (error: unknown, _variables, context) => {
            // Откат кэша
            if (context?.previousOrders) {
                queryClient.setQueryData(['orders'], context.previousOrders);
            }

            // Откат визуального положения в Timeline
            if (pendingCallbackRef.current) {
                pendingCallbackRef.current(null);
                pendingCallbackRef.current = null;
            }

            // Обработка 409 Conflict
            const axiosError = error as { response?: { status?: number }; message?: string };
            if (axiosError.response?.status === 409) {
                notification.error({
                    message: 'Конфликт расписания',
                    description: 'Водитель уже занят в это время. Заказ возвращён в исходное положение.',
                    duration: 5,
                });
            } else {
                notification.error({
                    message: 'Ошибка перемещения',
                    description: axiosError.message || 'Не удалось переместить заказ',
                });
            }
        },

        // Всегда инвалидируем для синхронизации
        onSettled: () => {
            queryClient.invalidateQueries({ queryKey: ['orders'] });
            pendingCallbackRef.current = null;
        },
    });

    // Обёртка для использования в vis-timeline onMove
    const handleMove = useCallback(
        (item: VisTimelineItem, callback: (item: VisTimelineItem | null) => void) => {
            // Сохраняем callback для возможного отката
            pendingCallbackRef.current = callback;

            // Сразу показываем успех (Optimistic UI)
            callback(item);

            // Отправляем на сервер
            mutation.mutate({
                orderId: Number(item.id),
                payload: {
                    new_time_start: item.start.toISOString(),
                    new_time_end: item.end?.toISOString() || item.start.toISOString(),
                },
            });
        },
        [mutation]
    );

    return { ...mutation, handleMove };
};
