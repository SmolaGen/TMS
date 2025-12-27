import axios from 'axios';

export const apiClient = axios.create({
    baseURL: import.meta.env.VITE_API_URL || '/api/v1',
    headers: {
        'Content-Type': 'application/json',
    },
});

// Интерцептор для логирования ошибок
apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('[API Error]', error.response?.status, error.response?.data);
        return Promise.reject(error);
    }
);
