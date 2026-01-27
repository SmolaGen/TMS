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
  EN_ROUTE_PICKUP = 'en_route_pickup',
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
  driver_name?: string | null;
  status: OrderStatus;
  priority: OrderPriority;
  pickup_lat: number | null;
  pickup_lon: number | null;
  dropoff_lat: number | null;
  dropoff_lon: number | null;
  time_start: string | null; // ISO datetime
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
  route_geometry: string | null; // Polyline
}

// Преобразованный заказ для Timeline
export interface TimelineOrder {
  id: string; // vis-timeline требует string
  group: string; // driver_id как string
  content: string;
  start: Date;
  end: Date;
  className?: string;
  editable?: boolean;
  title?: string;
}

// Водитель для Timeline (группа)
export interface TimelineDriver {
  id: string;
  content: string; // ФИО (для vis-timeline)
  name?: string; // Для фильтров и других списков
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
  new_driver_id?: number | null;
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
  is_online: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Схема создания заказа
export interface OrderCreate {
  driver_id?: number | null;
  time_start: string; // ISO
  time_end: string; // ISO
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
export type WSMessageType = 'ORDER_UPDATED' | 'ORDER_CREATED' | 'ORDER_DELETED' | 'DRIVER_LOCATION';

export interface WSMessage {
  type: WSMessageType;
  payload: unknown;
}

// Результат геокодинга
export interface GeocodingResult {
  name: string;
  lat: number;
  lon: number;
  address_full?: string;
  osm_id?: number;
}

// Статистика водителя
export interface DriverStats {
  driver_id: number;
  period_days: number;
  total_orders: number;
  completed_orders: number;
  cancelled_orders: number;
  active_orders: number;
  completion_rate: number;
  total_revenue: number;
  total_distance_km: number;
}

// Типы уведомлений
export enum NotificationType {
  NEW_ORDER = 'new_order',
  STATUS_CHANGE = 'status_change',
  DRIVER_ASSIGNMENT = 'driver_assignment',
  ORDER_COMPLETION = 'order_completion',
  SYSTEM_ALERT = 'system_alert',
}

// Каналы уведомлений
export enum NotificationChannel {
  TELEGRAM = 'telegram',
  EMAIL = 'email',
  IN_APP = 'in_app',
  PUSH = 'push',
}

// Частота уведомлений
export enum NotificationFrequency {
  INSTANT = 'instant',
  HOURLY = 'hourly',
  DAILY = 'daily',
  DISABLED = 'disabled',
}

// Профили пресетов настроек
export enum PresetProfile {
  MINIMAL = 'minimal',
  STANDARD = 'standard',
  MAXIMUM = 'maximum',
}

// Настройка уведомления
export interface NotificationPreference {
  id: number;
  driver_id: number;
  notification_type: NotificationType;
  channel: NotificationChannel;
  frequency: NotificationFrequency;
  is_enabled: boolean;
  created_at: string;
  updated_at: string;
}

// Запрос на обновление настройки уведомления
export interface NotificationPreferenceUpdate {
  notification_type: NotificationType;
  channel: NotificationChannel;
  frequency: NotificationFrequency;
  is_enabled: boolean;
}

// Запрос на применение пресета
export interface PresetRequest {
  preset: PresetProfile;
}

// Стандартная ошибка API
export interface ApiError {
  message: string;
  status?: number;
  data?: any;
  originalError?: any;
}

// Шаги онбординга
export enum OnboardingStep {
  CREATE_ORDER = '1',
  ASSIGN_DRIVER = '2',
  VIEW_MAP = '3',
  CHANGE_STATUS = '4',
  VIEW_STATS = '5',
}

// Статус онбординга
export interface OnboardingStatus {
  onboarding_completed: boolean;
  onboarding_step: string | null;
  onboarding_skipped: boolean;
}

// Запрос на обновление онбординга
export interface OnboardingUpdateRequest {
  onboarding_step?: number;
  onboarding_completed?: boolean;
  onboarding_skipped?: boolean;
}
