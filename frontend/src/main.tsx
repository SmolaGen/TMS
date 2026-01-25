import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './App.css';

// КРИТИЧНО: Сообщаем Telegram, что WebApp загрузился
// Это нужно сделать КАК МОЖНО РАНЬШЕ, иначе будет черный экран
const tg = (window as any).Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  console.log('[Telegram] WebApp ready() called');
}

ReactDOM.createRoot(document.getElementById('app')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
