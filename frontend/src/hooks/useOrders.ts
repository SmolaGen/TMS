import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { notification } from 'antd';
import { useRef, useCallback } from 'react';
import {
  fetchOrders,
  moveOrder,
  createOrder,
  fetchOrderById,
  cancelOrder,
  completeOrder,
  markArrived,
  startTrip,
  assignOrder,
  importOrdersExcel,
} from '../api/orders';
import { MOCK_ORDERS } from '../api/mockData';
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

  const statusClassMap: Record<string, string> = {
    pending: 'timeline-item-pending',
    assigned: 'timeline-item-accepted',
    driver_arrived: 'timeline-item-accepted',
    in_progress: 'timeline-item-progress',
    completed: 'timeline-item-completed',
    cancelled: 'timeline-item-cancelled',
  };

  return {
    id: String(order.id),
    group: order.driver_id ? String(order.driver_id) : 'unassigned',
    content: `Заказ #${order.id}`,
    start: new Date(order.time_start),
    end: new Date(order.time_end),
    className: `order-${order.priority} ${statusClassMap[order.status] || ''}`,
    editable: order.status !== 'completed' && order.status !== 'cancelled',
    title: `${order.pickup_address || '...'} ➔ ${order.dropoff_address || '...'} (${order.status})`,
  };
};

export const useOrdersRaw = (dateRange?: [Date, Date]) => {
  return useQuery({
    queryKey: ['orders', dateRange?.map((d) => d.toISOString())],
    queryFn: async () => {
      // В dev-режиме возвращаем мок-данные
      if (localStorage.getItem('tms_use_mocks') === 'true') {
        console.log('[DEV] Using mock orders data');
        return MOCK_ORDERS;
      }
      return fetchOrders(dateRange);
    },
    staleTime: 30_000,
    refetchInterval: 60_000,
    throwOnError: true,
  });
};

export const useOrders = (dateRange?: [Date, Date]) => {
  return useQuery({
    queryKey: ['orders', dateRange?.map((d) => d.toISOString())],
    queryFn: () => fetchOrders(dateRange),
    select: (data) => data.map(toTimelineOrder).filter(Boolean) as TimelineOrder[],
    staleTime: 30_000,
    refetchInterval: 60_000,
    throwOnError: true,
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
      queryClient.setQueryData<OrderResponse[]>(
        ['orders'],
        (old) =>
          old?.map((order) =>
            order.id === orderId
              ? { ...order, time_start: payload.new_time_start, time_end: payload.new_time_end }
              : order,
          ) ?? [],
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
          new_driver_id: item.group === 'unassigned' ? null : Number(item.group),
        },
      });
    },
    [mutation],
  );

  return { ...mutation, handleMove };
};

export const useCreateOrder = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      notification.success({
        message: 'Заказ создан',
        description: 'Новый заказ успешно добавлен в систему',
      });
    },
    onError: (error: any) => {
      notification.error({
        message: 'Ошибка создания',
        description: error.response?.data?.detail || 'Не удалось создать заказ',
      });
    },
  });
};

export const useOrder = (orderId?: number | string) => {
  return useQuery({
    queryKey: ['order', orderId],
    queryFn: () => (orderId ? fetchOrderById(orderId) : null),
    enabled: !!orderId,
    throwOnError: true,
  });
};

export type OrderAction = 'cancel' | 'complete' | 'arrive' | 'start' | 'assign';

export const useUpdateOrderStatus = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      orderId,
      action,
      reason,
      driverId,
    }: {
      orderId: number | string;
      action: OrderAction;
      reason?: string;
      driverId?: number;
    }) => {
      switch (action) {
        case 'cancel':
          return cancelOrder(orderId, reason);
        case 'complete':
          return completeOrder(orderId);
        case 'arrive':
          return markArrived(orderId);
        case 'start':
          return startTrip(orderId);
        case 'assign':
          if (!driverId) throw new Error('Driver ID is required for assignment');
          return assignOrder(orderId, driverId);
        default:
          throw new Error(`Unknown action: ${action}`);
      }
    },
    onSuccess: (_data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['order', variables.orderId] });

      const messages = {
        cancel: 'Заказ отменён',
        complete: 'Заказ завершён',
        arrive: 'Водитель прибыл',
        start: 'Поездка началась',
        assign: 'Водитель назначен',
      };

      notification.success({
        message: messages[variables.action],
      });
    },
    onError: (error: any) => {
      notification.error({
        message: 'Ошибка при обновлении статуса',
        description: error.response?.data?.detail || 'Не удалось выполнить действие',
      });
    },
  });
};

export const useImportOrders = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: importOrdersExcel,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      notification.success({
        message: 'Импорт завершен',
        description: `Создано: ${data.created}, Ошибок: ${data.failed}`,
      });
    },
    onError: (error: any) => {
      notification.error({
        message: 'Ошибка импорта',
        description: error.response?.data?.detail || 'Не удалось импортировать заказы',
      });
    },
  });
};
