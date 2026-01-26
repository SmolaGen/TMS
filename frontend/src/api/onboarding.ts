import { apiClient } from './client';
import type { OnboardingStatus, OnboardingUpdateRequest } from '../types/api';

export const getOnboardingStatus = async (): Promise<OnboardingStatus> => {
    const { data } = await apiClient.get<OnboardingStatus>('/users/me/onboarding');
    return data;
};

export const updateOnboardingProgress = async (
    payload: OnboardingUpdateRequest
): Promise<OnboardingStatus> => {
    const { data } = await apiClient.patch<OnboardingStatus>(
        '/users/me/onboarding',
        payload
    );
    return data;
};
