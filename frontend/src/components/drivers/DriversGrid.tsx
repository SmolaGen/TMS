import React from 'react';
import { Row, Col, Empty } from 'antd';
import type { DriverResponse } from '../../types/api';
import { DriverCard } from './DriverCard';

interface DriversGridProps {
  drivers: DriverResponse[];
  loading?: boolean;
  onSelect: (driverId: number) => void;
}

export const DriversGrid: React.FC<DriversGridProps> = ({ drivers, loading, onSelect }) => {
  if (!loading && drivers.length === 0) {
    return <Empty description="Водители не найдены" />;
  }

  return (
    <Row gutter={[16, 16]}>
      {drivers.map((driver) => (
        <Col xs={24} sm={12} md={8} lg={6} xl={6} key={driver.id}>
          <DriverCard driver={driver} onClick={() => onSelect(driver.id)} />
        </Col>
      ))}
    </Row>
  );
};
