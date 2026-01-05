import { create } from 'zustand';

interface WebSocketState {
    socket: WebSocket | null;
    isConnected: boolean;
    reconnectAttempts: number;
    connect: () => void;
    disconnect: () => void;
    addMessageHandler: (handler: (event: MessageEvent) => void) => void;
    removeMessageHandler: (handler: (event: MessageEvent) => void) => void;
}

const MAX_RECONNECT_ATTEMPTS = 10;
const BASE_DELAY_MS = 1000;

// Храним обработчики вне состояния для избежания re-renders
const messageHandlers = new Set<(event: MessageEvent) => void>();

export const useWebSocketStore = create<WebSocketState>((set, get) => ({
    socket: null,
    isConnected: false,
    reconnectAttempts: 0,

    connect: () => {
        const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('[WS] Connected');
            set({ socket: ws, isConnected: true, reconnectAttempts: 0 });
        };

        ws.onmessage = (event) => {
            // Вызываем все зарегистрированные обработчики
            messageHandlers.forEach((handler) => handler(event));
        };

        ws.onclose = () => {
            set({ isConnected: false });

            const { reconnectAttempts } = get();
            if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
                // Экспоненциальная задержка: 1s, 2s, 4s, 8s...
                const delay = BASE_DELAY_MS * Math.pow(2, reconnectAttempts);
                console.log(`[WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1})`);

                setTimeout(() => {
                    set({ reconnectAttempts: reconnectAttempts + 1 });
                    get().connect();
                }, delay);
            } else {
                console.error('[WS] Max reconnect attempts reached');
            }
        };

        ws.onerror = (error) => {
            console.error('[WS] Error:', error);
        };

        set({ socket: ws });
    },

    disconnect: () => {
        const { socket } = get();
        if (socket) {
            socket.close();
            set({ socket: null, isConnected: false, reconnectAttempts: 0 });
        }
    },

    addMessageHandler: (handler) => {
        messageHandlers.add(handler);
    },

    removeMessageHandler: (handler) => {
        messageHandlers.delete(handler);
    },
}));
