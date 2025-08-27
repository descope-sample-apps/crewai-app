import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css'
import App from './App.jsx'
import { AuthProvider } from "react-oidc-context";

const env = import.meta.env;

const root = ReactDOM.createRoot(document.getElementById('root'));

const oidcConfig = {
  authority: env.VITE_AUTHORITY_URL,
  client_id: env.VITE_CLIENT_ID,
  redirect_uri: env.VITE_REDIRECT_URI,
};

root.render(
    <React.StrictMode>
        <AuthProvider {...oidcConfig}>
            <App />
        </AuthProvider>
    </React.StrictMode>
);