import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider } from 'antd';
import ruRU from 'antd/locale/ru_RU';
import { Dashboard } from './components/dashboard/Dashboard';
import { AuthGuard } from './components/AuthGuard';
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
                <AuthGuard>
                    <Dashboard />
                </AuthGuard>
            </ConfigProvider>
        </QueryClientProvider>
    );
}

export default App;
