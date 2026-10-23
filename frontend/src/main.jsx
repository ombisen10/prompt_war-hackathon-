import { StrictMode, Component } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './index.css'

class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh',
          backgroundColor: '#0a0e17',
          color: '#f1f5f9',
          padding: '40px 20px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'Inter, -apple-system, sans-serif'
        }}>
          <div style={{
            maxWidth: '640px',
            width: '100%',
            background: '#111827',
            border: '1px solid #ef4444',
            borderRadius: '14px',
            padding: '24px 28px',
            boxShadow: '0 10px 40px rgba(0,0,0,0.5)'
          }}>
            <h2 style={{ color: '#f87171', margin: '0 0 12px 0', fontSize: '1.25rem' }}>
              ⚠️ GuardianAI React Render Warning
            </h2>
            <p style={{ color: '#94a3b8', fontSize: '0.88rem', margin: '0 0 16px 0' }}>
              The application encountered a rendering issue. You can reload or use the standalone emergency dashboard.
            </p>
            <pre style={{
              background: '#030712',
              color: '#fca5a5',
              padding: '12px 14px',
              borderRadius: '8px',
              fontSize: '0.78rem',
              overflow: 'auto',
              maxHeight: '160px',
              marginBottom: '20px'
            }}>
              {String(this.state.error?.message || this.state.error)}
            </pre>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button
                onClick={() => window.location.reload()}
                style={{
                  background: '#2563eb',
                  color: '#fff',
                  border: 'none',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontWeight: 600
                }}>
                Reload Page
              </button>
              <a
                href="/emergency-demo/index.html"
                style={{
                  background: '#1e293b',
                  color: '#93c5fd',
                  border: '1px solid #334155',
                  padding: '8px 16px',
                  borderRadius: '8px',
                  textDecoration: 'none',
                  fontWeight: 600
                }}>
                Launch Emergency Dashboard
              </a>
            </div>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

const rootElement = document.getElementById('root')
if (rootElement) {
  createRoot(rootElement).render(
    <StrictMode>
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    </StrictMode>,
  )
}
