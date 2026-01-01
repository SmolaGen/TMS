// Статусы водителя
export enum DriverStatus {
  AVAILABLE = 'available',
  BUSY = 'busy',
  OFFLINE = 'offline',
}

// Статусы заказа
export enum OrderStatus {
  PENDING = 'pending',
  ASSIGNED = 'assigned',
  DRIVER_ARRIVED = 'driver_arrived',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  CANCELLED = 'cancelled',
}

// Приоритеты заказа
export enum OrderPriority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent',
}

// Ответ API для заказов
export interface OrderResponse {
  id: number;
  driver_id: number | null;
  status: OrderStatus;
  priority: OrderPriority;
  pickup_lat: number | null;
  pickup_lon: number | null;
  dropoff_lat: number | null;
  dropoff_lon: number | null;
  time_start: string | null;  // ISO datetime
  time_end: string | null;
  comment: string | null;
  pickup_address: string | null;
  dropoff_address: string | null;
  customer_name: string | null;
  customer_phone: string | null;
  price: number | null;
  created_at: string;
  updated_at: string;

  // Lifecycle timestamps
  arrived_at: string | null;
  started_at: string | null;
  end_time: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
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

// Ответ API для водителей
export interface DriverResponse {
  id: number;
  telegram_id: number;
  name: string;
  phone: string | null;
  status: DriverStatus;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Схема создания заказа
export interface OrderCreate {
  driver_id?: number | null;
  time_start: string; // ISO
  time_end: string;   // ISO
  pickup_lat: number;
  pickup_lon: number;
  dropoff_lat: number;
  dropoff_lon: number;
  pickup_address?: string | null;
  dropoff_address?: string | null;
  customer_name?: string | null;
  customer_phone?: string | null;
  priority: OrderPriority;
  comment?: string | null;
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
