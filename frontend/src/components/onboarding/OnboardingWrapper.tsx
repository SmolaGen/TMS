import React, { useEffect, useState } from 'react';
import { useOnboarding } from '../../hooks/useOnboarding';
import { OnboardingModal } from './OnboardingModal';
import { useTelegramAuth } from '../../hooks/useTelegramAuth';

interface OnboardingWrapperProps {
    children: React.ReactNode;
}

/**
 * Обертка для управления онбордингом новых пользователей.
 *
 * - Проверяет статус онбординга при монтировании
 * - Показывает OnboardingModal для новых пользователей
 * - Позволяет пропустить или завершить онбординг
 * - Не блокирует рендеринг дочерних компонентов
 */
export const OnboardingWrapper: React.FC<OnboardingWrapperProps> = ({ children }) => {
    const { user } = useTelegramAuth();
    const { shouldShowOnboarding, isLoading, status } = useOnboarding();
    const [modalOpen, setModalOpen] = useState(false);

    // Показываем онбординг только для staff ролей
    const isStaff = user?.role === 'admin' || user?.role === 'dispatcher' || user?.role === 'staff';

    useEffect(() => {
        // Открываем модальное окно если нужно показать онбординг
        if (!isLoading && status && shouldShowOnboarding() && isStaff) {
            // Небольшая задержка для лучшего UX
            const timer = setTimeout(() => {
                setModalOpen(true);
            }, 500);

            return () => clearTimeout(timer);
        }
    }, [isLoading, status, shouldShowOnboarding, isStaff]);

    const handleCloseModal = () => {
        setModalOpen(false);
    };

    return (
        <>
            {children}
            <OnboardingModal open={modalOpen} onClose={handleCloseModal} />
        </>
    );
};
