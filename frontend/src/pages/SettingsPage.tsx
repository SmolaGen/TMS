import React from 'react';
import { Typography, Button } from 'antd';

export const SettingsPage: React.FC = () => {
  const triggerError = () => {
    throw new Error('Test error for GlobalErrorBoundary');
  };

  return (
    <div style={{ padding: 24 }}>
      <Typography.Title level={2}>Настройки</Typography.Title>
      <Typography.Text type="secondary">Страница в разработке.</Typography.Text>
      <div style={{ marginTop: 24 }}>
        <Button danger onClick={triggerError}>
          Триггернуть тестовую ошибку
        </Button>
      </div>
    </div>
  );
};
