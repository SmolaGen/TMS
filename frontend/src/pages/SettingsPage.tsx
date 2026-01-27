import { Typography, Button } from 'antd';
import { NotificationPreferences } from '../components/settings/NotificationPreferences';

export const SettingsPage: React.FC = () => {
  const triggerError = () => {
    throw new Error('Test error for GlobalErrorBoundary');
  };

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={2}>Настройки</Typography.Title>

      <div style={{ marginBottom: 32 }}>
        <Typography.Title level={4}>Уведомления</Typography.Title>
        <NotificationPreferences />
      </div>

      <div style={{ marginTop: 24, borderTop: '1px solid #f0f0f0', paddingTop: 24 }}>
        <Typography.Title level={4}>Отладка</Typography.Title>
        <Button danger onClick={triggerError}>
          Триггернуть тестовую ошибку
        </Button>
      </div>
    </div>
  );
};
