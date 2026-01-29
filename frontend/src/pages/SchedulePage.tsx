import React from 'react';
import { CalendarView } from '../components/schedule/CalendarView';

export const SchedulePage: React.FC = () => {
  return (
    <div style={{ padding: '24px', height: 'calc(100vh - 120px)' }}>
      <CalendarView />
    </div>
  );
};
