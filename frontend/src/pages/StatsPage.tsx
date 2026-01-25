import React, { useState } from 'react';
import { Card, Row, Col, DatePicker, Typography, Spin, Alert, Tabs } from 'antd';
import {
  ReloadOutlined,
  BarChartOutlined,
  TeamOutlined,
  CarOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import { useDetailedStats } from '../hooks/useDetailedStats';
import { HourlyChart } from '../components/stats/HourlyChart';
import { DriverRanking } from '../components/stats/DriverRanking';
import { OrdersBreakdown } from '../components/stats/OrdersBreakdown';
import { RoutesStats } from '../components/stats/RoutesStats';
import { WaitTimeStats } from '../components/stats/WaitTimeStats';
import { DailyChart } from '../components/stats/DailyChart';
import { KPIWidgets } from '../components/dashboard/KPIWidgets';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const useIsMobile = () => {
  const [isMobile, setIsMobile] = useState(
    typeof window !== 'undefined' ? window.innerWidth <= 768 : false,
  );

  React.useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth <= 768);
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return isMobile;
};

export const StatsPage: React.FC = () => {
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const isMobile = useIsMobile();
  const { data, isLoading, error, refetch } = useDetailedStats(dateRange || undefined);

  const handleDateChange = (dates: any) => {
    setDateRange(dates);
  };

  if (isLoading) {
    return (
      <div
        style={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          height: 'calc(100vh - 64px)',
        }}
      >
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 24 }}>
        <Alert
          message="Ошибка загрузки статистики"
          description="Не удалось загрузить данные. Попробуйте обновить страницу."
          type="error"
          showIcon
        />
      </div>
    );
  }

  const stats = data!;

  const tabItems = [
    {
      key: 'overview',
      label: (
        <span>
          <BarChartOutlined />
          {!isMobile && ' Обзор'}
        </span>
      ),
      children: (
        <Row gutter={[isMobile ? 12 : 16, isMobile ? 12 : 16]}>
          <Col xs={24} lg={14}>
            <Card
              title={<Text strong>Заказы по часам</Text>}
              size="small"
              style={{
                background: 'var(--tms-bg-container)',
                borderRadius: 8,
                marginBottom: isMobile ? 12 : 16,
              }}
            >
              <HourlyChart data={stats.orders.byHour} isMobile={isMobile} />
            </Card>
            <Card
              title={<Text strong>Заказы по дням</Text>}
              size="small"
              style={{ background: 'var(--tms-bg-container)', borderRadius: 8 }}
            >
              <DailyChart data={stats.orders.byDay} isMobile={isMobile} />
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card
              title={<Text strong>Рейтинг водителей</Text>}
              size="small"
              style={{ background: 'var(--tms-bg-container)', borderRadius: 8 }}
            >
              <DriverRanking drivers={stats.drivers.topDrivers} isMobile={isMobile} />
            </Card>
          </Col>
        </Row>
      ),
    },
    {
      key: 'orders',
      label: (
        <span>
          <BarChartOutlined />
          {!isMobile && ' Заказы'}
        </span>
      ),
      children: (
        <Card
          title={<Text strong>Детализация заказов</Text>}
          size="small"
          style={{ background: 'var(--tms-bg-container)', borderRadius: 8 }}
        >
          <OrdersBreakdown data={stats.orders} isMobile={isMobile} />
        </Card>
      ),
    },
    {
      key: 'drivers',
      label: (
        <span>
          <TeamOutlined />
          {!isMobile && ' Водители'}
        </span>
      ),
      children: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: isMobile ? 12 : 16 }}>
          <Card
            title={<Text strong>Общая статистика водителей</Text>}
            size="small"
            style={{ background: 'var(--tms-bg-container)', borderRadius: 8 }}
          >
            <Row gutter={isMobile ? [12, 12] : [16, 16]}>
              <Col xs={12} md={6}>
                <div style={{ textAlign: 'center', padding: isMobile ? 12 : 16 }}>
                  <div style={{ fontSize: isMobile ? 24 : 32, fontWeight: 700, color: '#1890ff' }}>
                    {stats.drivers.total}
                  </div>
                  <Text type="secondary">Всего водителей</Text>
                </div>
              </Col>
              <Col xs={12} md={6}>
                <div style={{ textAlign: 'center', padding: isMobile ? 12 : 16 }}>
                  <div style={{ fontSize: isMobile ? 24 : 32, fontWeight: 700, color: '#52c41a' }}>
                    {stats.drivers.active}
                  </div>
                  <Text type="secondary">Активны сейчас</Text>
                </div>
              </Col>
            </Row>
          </Card>

          <Card
            title={<Text strong>Топ водителей по эффективности</Text>}
            size="small"
            style={{ background: 'var(--tms-bg-container)', borderRadius: 8 }}
          >
            <DriverRanking drivers={stats.drivers.topDrivers} isMobile={isMobile} />
          </Card>
        </div>
      ),
    },
    {
      key: 'routes',
      label: (
        <span>
          <CarOutlined />
          {!isMobile && ' Маршруты'}
        </span>
      ),
      children: (
        <Card
          title={<Text strong>Статистика маршрутов</Text>}
          size="small"
          style={{ background: 'var(--tms-bg-container)', borderRadius: 8 }}
        >
          <RoutesStats data={stats.routes} isMobile={isMobile} />
        </Card>
      ),
    },
    {
      key: 'wait_times',
      label: (
        <span>
          <ClockCircleOutlined />
          {!isMobile && ' Время ожидания'}
        </span>
      ),
      children: (
        <Card
          title={<Text strong>Аналитика времени ожидания</Text>}
          size="small"
          style={{ background: 'var(--tms-bg-container)', borderRadius: 8 }}
        >
          <WaitTimeStats data={stats.waitTimes} isMobile={isMobile} />
        </Card>
      ),
    },
  ];

  return (
    <div
      style={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}
    >
      <div
        style={{
          padding: isMobile ? '12px 12px 0' : '16px 16px 0',
          display: 'flex',
          flexDirection: 'column',
          gap: isMobile ? 8 : 12,
          overflowY: 'auto',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: isMobile ? 'flex-start' : 'center',
            flexWrap: 'wrap',
            gap: isMobile ? 8 : 16,
          }}
        >
          <div>
            <Title level={2} style={{ margin: 0, fontSize: isMobile ? 18 : 22 }}>
              Статистика
            </Title>
            <Text type="secondary" style={{ fontSize: isMobile ? 12 : 13 }}>
              Период: {dayjs(stats.period.start).format('DD.MM.YYYY')} -{' '}
              {dayjs(stats.period.end).format('DD.MM.YYYY')}
            </Text>
          </div>
          <div style={{ display: 'flex', gap: isMobile ? 8 : 12, flexWrap: 'wrap' }}>
            <RangePicker
              value={dateRange}
              onChange={handleDateChange}
              size={isMobile ? 'small' : 'middle'}
              placeholder={['Начало', 'Конец']}
              style={{ width: isMobile ? 200 : 260 }}
            />
            <button
              onClick={() => refetch()}
              style={{
                padding: isMobile ? '6px 12px' : '8px 16px',
                background: 'var(--tms-primary)',
                color: 'white',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                fontSize: isMobile ? 12 : 14,
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <ReloadOutlined />
              {!isMobile && 'Обновить'}
            </button>
          </div>
        </div>

        <KPIWidgets />

        <div className="glass-card" style={{ padding: 0 }}>
          <Tabs
            defaultActiveKey="overview"
            items={tabItems}
            size={isMobile ? 'small' : 'middle'}
            tabBarStyle={{
              marginBottom: isMobile ? 12 : 16,
              fontWeight: 600,
            }}
            style={{
              background: 'var(--tms-bg-elevated)',
              padding: isMobile ? '12px' : '16px',
              borderRadius: 8,
            }}
          />
        </div>
      </div>
    </div>
  );
};
