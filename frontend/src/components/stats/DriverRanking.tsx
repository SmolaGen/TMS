import React from 'react';
import { Table, Typography } from 'antd';
import { TrophyOutlined, StarOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import type { DetailedStats } from '../../hooks/useDetailedStats';

const { Text } = Typography;

interface DriverRankingProps {
    drivers: DetailedStats['drivers']['topDrivers'];
    isMobile?: boolean;
}

export const DriverRanking: React.FC<DriverRankingProps> = ({ drivers, isMobile = false }) => {
    const columns: ColumnsType<any> = [
        {
            title: '#',
            dataIndex: 'rank',
            width: 50,
            align: 'center',
            render: (_, __, index) => {
                if (index === 0) return <TrophyOutlined style={{ color: '#ffd700', fontSize: 16 }} />;
                if (index === 1) return <TrophyOutlined style={{ color: '#c0c0c0', fontSize: 16 }} />;
                if (index === 2) return <TrophyOutlined style={{ color: '#cd7f32', fontSize: 16 }} />;
                return index + 1;
            },
        },
        {
            title: 'Водитель',
            dataIndex: 'name',
            key: 'name',
            render: (text, _record, index) => (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div
                        style={{
                            width: 32,
                            height: 32,
                            borderRadius: '50%',
                            background: `hsl(${index * 60}, 70%, 60%)`,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            color: 'white',
                            fontSize: 12,
                            fontWeight: 600,
                        }}
                    >
                        {text.charAt(0)}
                    </div>
                    <span style={{ fontWeight: 500 }}>{text}</span>
                </div>
            ),
        },
        {
            title: 'Заказы',
            dataIndex: 'completed_orders',
            key: 'completed_orders',
            align: 'right',
            sorter: (a, b) => a.completed_orders - b.completed_orders,
            render: (value) => <Text strong>{value}</Text>,
        },
        {
            title: 'Доход',
            dataIndex: 'total_revenue',
            key: 'total_revenue',
            align: 'right',
            sorter: (a, b) => a.total_revenue - b.total_revenue,
            render: (value) => (
                <Text strong style={{ color: '#52c41a' }}>
                    {value.toLocaleString()} ₽
                </Text>
            ),
        },
        {
            title: 'Рейтинг',
            dataIndex: 'average_rating',
            key: 'average_rating',
            align: 'center',
            render: (value) => (
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, justifyContent: 'center' }}>
                    <StarOutlined style={{ color: '#faad14' }} />
                    <Text strong>{value?.toFixed(1) || '-'}</Text>
                </div>
            ),
        },
    ];

    const mobileColumns = columns.filter(col => col.title !== '#' && col.title !== 'Рейтинг');

    return (
        <Table
            columns={isMobile ? mobileColumns : columns}
            dataSource={drivers}
            rowKey="driver_id"
            pagination={false}
            size="small"
            scroll={{ x: true }}
            style={{ fontSize: isMobile ? 12 : 14 }}
        />
    );
};
