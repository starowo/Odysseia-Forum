import React from 'react';
import ReactDOM from 'react-dom/client';
import { App } from './app/App';
import './styles/globals.css';

async function enableMocking() {
  const isMockEnabled = import.meta.env.VITE_API_MOCKING === 'true';
  const mode = import.meta.env.MODE;

  if (!isMockEnabled) {
    return;
  }

  // 仅在非生产环境下启用 MSW，避免生产环境误用 Mock
  if (mode === 'production') {
    console.warn(
      '[MSW] VITE_API_MOCKING is true but current mode is production; skipping MSW worker startup.'
    );
    return;
  }

  const { worker } = await import('./mocks/browser');
  return worker.start();
}

enableMocking().then(() => {
  ReactDOM.createRoot(document.getElementById('root')!).render(
    <React.StrictMode>
      <App />
    </React.StrictMode>
  );
});
