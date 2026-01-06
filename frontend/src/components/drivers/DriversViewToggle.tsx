import React from 'react';
import { Segmented } from 'antd';
import { UnorderedListOutlined, AppstoreOutlined } from '@ant-design/icons';

export type ViewMode = 'table' | 'grid';

interface DriversViewToggleProps {
    value: ViewMode;
    onChange: (mode: ViewMode) => void;
}

export const DriversViewToggle: React.FC<DriversViewToggleProps> = ({
    value,
    onChange
}) => {
    const options = [
        {
            value: 'table',
            icon: <UnorderedListOutlined />,
            label: 'Таблица',
        },
        {
            value: 'grid',
            icon: <AppstoreOutlined />,
            label: 'Карточки',
        },
    ];

    return (
        <Segmented
            value={value}
            onChange={(val) => onChange(val as ViewMode)}
            options={options}
        />
    );
};
