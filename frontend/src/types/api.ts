// Статусы из бэкенда
export type OrderStatus = 'pending' | 'assigned' | 'in_progress' | 'completed' | 'cancelled';
export type OrderPriority = 'low' | 'normal' | 'high' | 'urgent';
export type DriverStatus = 'available' | 'busy' | 'offline';

// Ответ API для заказов
export interface OrderResponse {
  id: number;
  driver_id: number | null;
  status: OrderStatus;
  priority: OrderPriority;
  time_start: string | null;  // ISO datetime
  time_end: string | null;
  comment: string | null;
  created_at: string;
  updated_at: string;
}

// Преобразованный заказ для Timeline
export interface TimelineOrder {
  id: string;           // vis-timeline требует string
  group: string;        // driver_id как string
  content: string;
  start: Date;
  end: Date;
  className?: string;
  editable?: boolean;
}

// Водитель для Timeline (группа)
export interface TimelineDriver {
  id: string;
  content: string;      // ФИО
}

// Локация водителя
export interface DriverLocation {
  driver_id: number;
  latitude: number;
  longitude: number;
  status: DriverStatus;
  updated_at: string;
}

// Запрос на перемещение заказа
export interface OrderMoveRequest {
  new_time_start: string;
  new_time_end: string;
}

// Ошибка 409 Conflict
export interface ConflictError {
  error: 'time_overlap';
  message: string;
}

// WebSocket сообщения
export type WSMessageType = 
  | 'ORDER_UPDATED' 
  | 'ORDER_CREATED' 
  | 'ORDER_DELETED' 
  | 'DRIVER_LOCATION';

export interface WSMessage {
  type: WSMessageType;
  payload: unknown;
}
