import { useNavigate } from 'react-router-dom'

export default function NotFound() {
  const navigate = useNavigate()

  return (
    <div style={{ minHeight: '100vh', background: 'var(--dark)', color: 'var(--text)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: 24 }}>
      <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 120, lineHeight: 1, color: 'rgba(201,168,76,0.15)' }}>404</div>
      <h1 style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 28, margin: '0 0 8px' }}>Page not found</h1>
      <p style={{ color: 'var(--text-muted)', fontSize: 14, marginBottom: 24 }}>The requested page does not exist.</p>
      <div style={{ display: 'flex', gap: 10 }}>
        <button className="btn-secondary" onClick={() => navigate(-1)}>Back</button>
        <button className="btn-primary" onClick={() => navigate('/dashboard')}>Dashboard</button>
      </div>
    </div>
  )
}
