import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Dashboard } from './components/dashboard/Dashboard';
import { DriverApp } from './pages/DriverApp';
import { AuthGuard } from './components/AuthGuard';
import { useTelegramAuth } from './hooks/useTelegramAuth';
import './App.css';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            retry: 2,
            refetchOnWindowFocus: false,
        },
    },
});

function App() {
    return (
        <QueryClientProvider client={queryClient}>
            <ConfigProvider locale={ruRU}>
                <BrowserRouter>
                    <AuthGuard>
                        <AppRoutes />
                    </AuthGuard>
                </BrowserRouter>
            </ConfigProvider>
        </QueryClientProvider>
    );
}

function AppRoutes() {
    const { user } = useTelegramAuth();
    const role = user?.role;

    // Определяем главный экран в зависимости от роли
    // Админы и диспетчеры видят Dashboard
    // Водители (и все остальные по умолчанию) видят DriverApp
    const isStaff = role === 'admin' || role === 'dispatcher';

    return (
        <Routes>
            <Route path="/" element={isStaff ? <Dashboard /> : <DriverApp />} />
            <Route path="/webapp" element={<DriverApp />} />
        </Routes>
    );
}

export default App;
