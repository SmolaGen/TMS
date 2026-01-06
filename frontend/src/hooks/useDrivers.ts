import { useQuery } from '@tanstack/react-query';
import { fetchDriversList } from '../api/drivers';
import type { TimelineDriver } from '../types/api';

export const useDrivers = () => {
    return useQuery({
        queryKey: ['drivers'],
        queryFn: fetchDriversList,
        select: (data) => {
            const drivers: TimelineDriver[] = data.map((d) => ({
                id: String(d.id),
                content: d.name,
                name: d.name,
            }));

            // Добавляем техническую группу для неназначенных заказов
            return [...drivers, { id: 'unassigned', content: 'Не назначен', name: 'Не назначен' }];
        },
        staleTime: 60_000,
    });
};
