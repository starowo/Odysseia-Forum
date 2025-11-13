import React from 'react';
import ReactDOM from 'react-dom/client';
import { Toaster } from 'sonner';
import { App } from './app/App';
import './styles/globals.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
    <Toaster 
      position="top-center"
      theme="dark"
      toastOptions={{
        style: {
          background: '#2b2d31',
          color: '#f2f3f5',
          border: '1px solid #1e1f22',
        },
      }}
    />
  </React.StrictMode>
);
