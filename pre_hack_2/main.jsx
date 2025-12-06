import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './frontend/RAGFlashcardApp.jsx';
import './index.css'; // Importa el CSS (que incluye Tailwind)

// Monta la aplicación principal (App) en el elemento con id="root" del index.html
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);