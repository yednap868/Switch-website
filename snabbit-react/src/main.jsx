import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { HelmetProvider } from 'react-helmet-async'
import './index.css'
import App from './App.jsx'
import RouteAnalytics from './components/RouteAnalytics.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <HelmetProvider>
      <BrowserRouter>
        <RouteAnalytics />
        <App />
      </BrowserRouter>
    </HelmetProvider>
  </StrictMode>,
)
