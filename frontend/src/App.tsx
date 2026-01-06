import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { Dashboard } from './components/dashboard/Dashboard';
import { OrdersPage } from './pages/OrdersPage';
import { DriversPage } from './pages/DriversPage';
import { StatsPage } from './pages/StatsPage';
import { SettingsPage } from './pages/SettingsPage';
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
    // Админы и диспетчеры видят Dashboard в AppLayout
    // Водители (и все остальные по умолчанию) видят DriverApp
    const isStaff = role === 'admin' || role === 'dispatcher' || role === 'staff';

    if (!isStaff) {
        return (
            <Routes>
                <Route path="*" element={<DriverApp />} />
            </Routes>
        );
    }

    return (
        <AppLayout>
            <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/orders" element={<OrdersPage />} />
                <Route path="/drivers" element={<DriversPage />} />
                <Route path="/stats" element={<StatsPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="*" element={<Dashboard />} />
            </Routes>
        </AppLayout>
    );
}

export default App;
