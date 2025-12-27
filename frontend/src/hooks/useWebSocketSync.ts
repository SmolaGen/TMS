import { useEffect, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useWebSocketStore } from '../stores/useWebSocketStore';
import type { WSMessage, DriverLocation } from '../types/api';

export const useWebSocketSync = () => {
    const queryClient = useQueryClient();
    const { isConnected, connect, addMessageHandler, removeMessageHandler } = useWebSocketStore();

    const handleMessage = useCallback(
        (event: MessageEvent) => {
            try {
                const message: WSMessage = JSON.parse(event.data);

                switch (message.type) {
                    case 'ORDER_UPDATED':
                    case 'ORDER_CREATED':
                    case 'ORDER_DELETED':
                        // Помечаем данные как stale -> фоновое обновление
                        queryClient.invalidateQueries({ queryKey: ['orders'] });
                        break;

                    case 'DRIVER_LOCATION':
                        // Мгновенное обновление кэша локаций
                        const location = message.payload as DriverLocation;
                        queryClient.setQueryData<DriverLocation[]>(['driver-locations'], (old) => {
                            if (!old) return [location];
                            const index = old.findIndex((d) => d.driver_id === location.driver_id);
                            if (index === -1) return [...old, location];
                            const updated = [...old];
                            updated[index] = location;
                            return updated;
                        });
                        break;
                }
            } catch (error) {
                console.error('[WS] Parse error:', error);
            }
        },
        [queryClient]
    );

    useEffect(() => {
        // Подключаемся при монтировании
        connect();
        addMessageHandler(handleMessage);

        return () => {
            removeMessageHandler(handleMessage);
        };
    }, [connect, addMessageHandler, removeMessageHandler, handleMessage]);

    return { isConnected };
};
