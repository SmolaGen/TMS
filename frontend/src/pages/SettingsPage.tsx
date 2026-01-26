import React from 'react';
import { Typography } from 'antd';
import { NotificationPreferences } from '../components/settings/NotificationPreferences';

export const SettingsPage: React.FC = () => {
    return (
        <div style={{ padding: 24 }}>
            <Typography.Title level={2}>Настройки уведомлений</Typography.Title>
            <NotificationPreferences />
        </div>
    );
};
