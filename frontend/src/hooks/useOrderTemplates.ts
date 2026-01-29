import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { message } from 'antd';
import { apiClient } from '../api/client';
import { isDevMode } from '../components/DevAuthSelector';

export type OrderPriority = 'low' | 'normal' | 'high' | 'urgent';

export interface OrderTemplateBase {
  name: string;
  contractor_id?: number;
  priority: OrderPriority;
  pickup_lat?: number;
  pickup_lon?: number;
  dropoff_lat?: number;
  dropoff_lon?: number;
  pickup_address?: string;
  dropoff_address?: string;
  customer_phone?: string;
  customer_name?: string;
  customer_telegram_id?: number;
  customer_webhook_url?: string;
  price?: number;
  comment?: string;
  is_active: boolean;
}

export interface OrderTemplateCreate extends OrderTemplateBase {}

export interface OrderTemplateUpdate {
  name?: string;
  contractor_id?: number;
  priority?: OrderPriority;
  pickup_lat?: number;
  pickup_lon?: number;
  dropoff_lat?: number;
  dropoff_lon?: number;
  pickup_address?: string;
  dropoff_address?: string;
  customer_phone?: string;
  customer_name?: string;
  customer_telegram_id?: number;
  customer_webhook_url?: string;
  price?: number;
  comment?: string;
  is_active?: boolean;
}

export interface OrderTemplateResponse extends OrderTemplateBase {
  id: number;
  created_at: string;
  updated_at: string;
}

export interface GenerateOrdersRequest {
  date_from: string;
  date_until: string;
  driver_id?: number;
}

export interface GenerateOrdersResponse {
  generated_count: number;
  orders: Array<{
    id: number;
    scheduled_date: string;
  }>;
}

const MOCK_TEMPLATES: OrderTemplateResponse[] = [
  {
    id: 1,
    name: 'Ежедневная доставка на склад',
    priority: 'normal',
    pickup_address: 'Москва, ул. Ленина, 10',
    dropoff_address: 'Москва, ул. Пушкина, 25',
    pickup_lat: 55.751244,
    pickup_lon: 37.618423,
    dropoff_lat: 55.755826,
    dropoff_lon: 37.617299,
    customer_name: 'ООО "Ромашка"',
    customer_phone: '+7 (495) 123-45-67',
    price: 1500,
    is_active: true,
    comment: 'Ежедневная доставка с 9:00 до 18:00',
    created_at: '2026-01-15T10:00:00Z',
    updated_at: '2026-01-15T10:00:00Z',
  },
  {
    id: 2,
    name: 'Еженедельная доставка продуктов',
    priority: 'high',
    pickup_address: 'Москва, ул. Садовая, 5',
    dropoff_address: 'Москва, ул. Цветочная, 12',
    pickup_lat: 55.748264,
    pickup_lon: 37.621123,
    dropoff_lat: 55.752341,
    dropoff_lon: 37.619876,
    customer_name: 'ИП Петров',
    customer_phone: '+7 (495) 987-65-43',
    price: 2000,
    is_active: true,
    comment: 'Каждый понедельник утром',
    created_at: '2026-01-10T14:30:00Z',
    updated_at: '2026-01-20T09:15:00Z',
  },
  {
    id: 3,
    name: 'Доставка документов (неактивный)',
    priority: 'urgent',
    pickup_address: 'Москва, Тверская, 1',
    dropoff_address: 'Москва, Арбат, 20',
    pickup_lat: 55.756822,
    pickup_lon: 37.614495,
    dropoff_lat: 55.750446,
    dropoff_lon: 37.593434,
    customer_name: 'Курьерская служба',
    customer_phone: '+7 (495) 111-22-33',
    price: 800,
    is_active: false,
    comment: 'Временно приостановлен',
    created_at: '2026-01-05T08:00:00Z',
    updated_at: '2026-01-25T16:45:00Z',
  },
];

const API_BASE = '/api/v1';

// List all templates
export const useTemplates = (filters?: { is_active?: boolean }) => {
  return useQuery<OrderTemplateResponse[]>({
    queryKey: ['templates', filters],
    queryFn: async () => {
      if (isDevMode()) {
        await new Promise((resolve) => setTimeout(resolve, 300));
        let templates = MOCK_TEMPLATES;
        if (filters?.is_active !== undefined) {
          templates = templates.filter((t) => t.is_active === filters.is_active);
        }
        return templates;
      }
      const params = new URLSearchParams();
      if (filters?.is_active !== undefined) {
        params.append('is_active', filters.is_active.toString());
      }
      const { data } = await apiClient.get<OrderTemplateResponse[]>(
        `${API_BASE}/templates${params.toString() ? `?${params}` : ''}`,
      );
      return data;
    },
    refetchInterval: 60000,
    staleTime: 30000,
    throwOnError: true,
  });
};

// Get single template
export const useTemplate = (templateId: number | null) => {
  return useQuery<OrderTemplateResponse>({
    queryKey: ['template', templateId],
    queryFn: async () => {
      if (!templateId) {
        throw new Error('Template ID is required');
      }
      if (isDevMode()) {
        await new Promise((resolve) => setTimeout(resolve, 200));
        const template = MOCK_TEMPLATES.find((t) => t.id === templateId);
        if (!template) {
          throw new Error('Template not found');
        }
        return template;
      }
      const { data } = await apiClient.get<OrderTemplateResponse>(
        `${API_BASE}/templates/${templateId}`,
      );
      return data;
    },
    enabled: !!templateId,
    throwOnError: true,
  });
};

// Create template
export const useCreateTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (template: OrderTemplateCreate): Promise<OrderTemplateResponse> => {
      if (isDevMode()) {
        await new Promise((resolve) => setTimeout(resolve, 500));
        const newTemplate: OrderTemplateResponse = {
          ...template,
          id: Math.max(...MOCK_TEMPLATES.map((t) => t.id)) + 1,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        MOCK_TEMPLATES.push(newTemplate);
        return newTemplate;
      }
      const response = await fetch(`${API_BASE}/templates`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(template),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create template');
      }

      return response.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      message.success('Шаблон успешно создан');
    },
    onError: (error: Error) => {
      message.error(`Ошибка создания шаблона: ${error.message}`);
    },
  });
};

// Update template
export const useUpdateTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: number;
      data: OrderTemplateUpdate;
    }): Promise<OrderTemplateResponse> => {
      if (isDevMode()) {
        await new Promise((resolve) => setTimeout(resolve, 400));
        const index = MOCK_TEMPLATES.findIndex((t) => t.id === id);
        if (index === -1) {
          throw new Error('Template not found');
        }
        const updatedTemplate = {
          ...MOCK_TEMPLATES[index],
          ...data,
          updated_at: new Date().toISOString(),
        };
        MOCK_TEMPLATES[index] = updatedTemplate;
        return updatedTemplate;
      }
      const response = await fetch(`${API_BASE}/templates/${id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to update template');
      }

      return response.json();
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      queryClient.invalidateQueries({ queryKey: ['template', variables.id] });
      message.success('Шаблон успешно обновлён');
    },
    onError: (error: Error) => {
      message.error(`Ошибка обновления шаблона: ${error.message}`);
    },
  });
};

// Delete template
export const useDeleteTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (templateId: number): Promise<void> => {
      if (isDevMode()) {
        await new Promise((resolve) => setTimeout(resolve, 300));
        const index = MOCK_TEMPLATES.findIndex((t) => t.id === templateId);
        if (index === -1) {
          throw new Error('Template not found');
        }
        MOCK_TEMPLATES.splice(index, 1);
        return;
      }
      const response = await fetch(`${API_BASE}/templates/${templateId}`, {
        method: 'DELETE',
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to delete template');
      }
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] });
      message.success('Шаблон успешно удалён');
    },
    onError: (error: Error) => {
      message.error(`Ошибка удаления шаблона: ${error.message}`);
    },
  });
};

// Generate orders from template
export const useGenerateFromTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      templateId,
      request,
    }: {
      templateId: number;
      request: GenerateOrdersRequest;
    }): Promise<GenerateOrdersResponse> => {
      if (isDevMode()) {
        await new Promise((resolve) => setTimeout(resolve, 800));
        const dateFrom = new Date(request.date_from);
        const dateUntil = new Date(request.date_until);
        const daysCount = Math.ceil(
          (dateUntil.getTime() - dateFrom.getTime()) / (1000 * 60 * 60 * 24),
        );
        const orders = Array.from({ length: Math.min(daysCount, 10) }, (_, i) => ({
          id: 1000 + i,
          scheduled_date: new Date(
            dateFrom.getTime() + i * 24 * 60 * 60 * 1000,
          ).toISOString(),
        }));
        return {
          generated_count: orders.length,
          orders,
        };
      }
      const response = await fetch(`${API_BASE}/templates/${templateId}/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to generate orders');
      }

      return response.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['schedule'] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      message.success(`Создано ${data.generated_count} заказов из шаблона`);
    },
    onError: (error: Error) => {
      message.error(`Ошибка генерации заказов: ${error.message}`);
    },
  });
};
