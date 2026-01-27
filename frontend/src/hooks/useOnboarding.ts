import { useState, useEffect, useCallback } from 'react';
import { getOnboardingStatus, updateOnboardingProgress } from '../api/onboarding';
import type { OnboardingStatus, OnboardingUpdateRequest } from '../types/api';

interface OnboardingState {
    isLoading: boolean;
    status: OnboardingStatus | null;
    error: string | null;
    currentStep: number | null;
}

/**
 * Хук для управления состоянием онбординга пользователя.
 *
 * Provides:
 * - Загрузку статуса онбординга при монтировании
 * - Обновление прогресса онбординга
 * - Навигацию по шагам онбординга
 * - Пропуск и перезапуск онбординга
 */
export function useOnboarding() {
    const [state, setState] = useState<OnboardingState>({
        isLoading: true,
        status: null,
        error: null,
        currentStep: null,
    });

    /**
     * Загрузить статус онбординга с сервера
     */
    const loadStatus = useCallback(async () => {
        try {
            const status = await getOnboardingStatus();
            const currentStep = status.onboarding_step ? parseInt(status.onboarding_step) : null;

            setState({
                isLoading: false,
                status,
                error: null,
                currentStep,
            });
        } catch (error: any) {
            setState({
                isLoading: false,
                status: null,
                error: error.response?.data?.detail || 'Ошибка загрузки статуса онбординга',
                currentStep: null,
            });
        }
    }, []);

    /**
     * Обновить прогресс онбординга
     */
    const updateProgress = useCallback(async (payload: OnboardingUpdateRequest) => {
        try {
            const updatedStatus = await updateOnboardingProgress(payload);
            const currentStep = updatedStatus.onboarding_step ? parseInt(updatedStatus.onboarding_step) : null;

            setState(prev => ({
                ...prev,
                status: updatedStatus,
                currentStep,
                error: null,
            }));

            return updatedStatus;
        } catch (error: any) {
            const errorMessage = error.response?.data?.detail || 'Ошибка обновления прогресса онбординга';
            setState(prev => ({
                ...prev,
                error: errorMessage,
            }));
            throw error;
        }
    }, []);

    /**
     * Перейти к указанному шагу онбординга
     */
    const goToStep = useCallback(async (step: number) => {
        return updateProgress({ onboarding_step: step });
    }, [updateProgress]);

    /**
     * Перейти к следующему шагу онбординга
     */
    const nextStep = useCallback(async () => {
        const step = state.currentStep ?? 0;
        const nextStepValue = step + 1;

        if (nextStepValue > 5) {
            // Завершаем онбординг после последнего шага
            return updateProgress({ onboarding_completed: true });
        }

        return updateProgress({ onboarding_step: nextStepValue });
    }, [state.currentStep, updateProgress]);

    /**
     * Предыдущий шаг онбординга
     */
    const previousStep = useCallback(async () => {
        const step = state.currentStep ?? 1;
        const prevStepValue = Math.max(1, step - 1);

        return updateProgress({ onboarding_step: prevStepValue });
    }, [state.currentStep, updateProgress]);

    /**
     * Завершить онбординг
     */
    const completeOnboarding = useCallback(async () => {
        return updateProgress({ onboarding_completed: true });
    }, [updateProgress]);

    /**
     * Пропустить онбординг
     */
    const skipOnboarding = useCallback(async () => {
        return updateProgress({ onboarding_skipped: true });
    }, [updateProgress]);

    /**
     * Перезапустить онбординг (сбросить прогресс)
     */
    const restartOnboarding = useCallback(async () => {
        return updateProgress({
            onboarding_step: 1,
            onboarding_completed: false,
            onboarding_skipped: false,
        });
    }, [updateProgress]);

    /**
     * Проверить, нужно ли показать онбординг
     */
    const shouldShowOnboarding = useCallback(() => {
        return !state.status?.onboarding_completed && !state.status?.onboarding_skipped;
    }, [state.status]);

    // Загружаем статус при монтировании
    useEffect(() => {
        loadStatus();
    }, [loadStatus]);

    return {
        ...state,
        loadStatus,
        updateProgress,
        goToStep,
        nextStep,
        previousStep,
        completeOnboarding,
        skipOnboarding,
        restartOnboarding,
        shouldShowOnboarding,
    };
}
