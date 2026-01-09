import React from 'react';
import { Typography } from 'antd';

export const SettingsPage: React.FC = () => {
    return (
        <div style={{ padding: 24 }}>
            <Typography.Title level={2}>Настройки</Typography.Title>
            <Typography.Text type="secondary">
                Страница в разработке.
            </Typography.Text>
        </div>
    );
};
