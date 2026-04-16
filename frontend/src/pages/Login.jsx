import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import DarkModeToggle from '../components/UI/DarkModeToggle'
import { useAuth } from '../contexts/AuthContext'

export default function Login() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (user) {
      navigate('/dashboard', { replace: true })
    }
  }, [user, navigate])

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await login(username, password)
      const redirect = data?.redirect || location.state?.from?.pathname || '/dashboard'
      navigate(redirect, { replace: true })
    } catch (err) {
      setError(err.response?.data?.error || 'Incorrect username or password.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-left">
        <div className="grid-overlay" />
        <div className="circle-deco" />
        <div className="scanline" />

        <div className="login-brand">
          <img
            src="/static/img/logomaretap.png"
            alt="MARETAP"
            style={{ width: 100, height: 100, marginBottom: 24, filter: 'drop-shadow(0 0 20px rgba(201,40,40,0.3))' }}
            onError={(e) => { e.currentTarget.style.display = 'none' }}
          />
          <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 11, fontWeight: 600, letterSpacing: 4, color: 'var(--gold)', textTransform: 'uppercase', marginBottom: 16 }}>
            MARETAP S.A.
          </div>
          <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 72, fontWeight: 700, color: 'var(--text)', lineHeight: 0.9, letterSpacing: -1, marginBottom: 8 }}>
            EZZ<span style={{ color: 'var(--gold)' }}>AOUIA</span>
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 48 }}>
            Smart Production Platform
          </div>
          <div style={{ fontSize: 14, color: 'var(--text-muted)', lineHeight: 1.8, maxWidth: 380, borderLeft: '2px solid var(--border)', paddingLeft: 20 }}>
            Centralized decision-support system for monitoring, analyzing, and optimizing production in the Ezzaouia oil field.
          </div>
          <div style={{ display: 'flex', gap: 40, marginTop: 56 }}>
            <div>
              <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 28, fontWeight: 700, color: 'var(--gold)' }}>16</div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1, marginTop: 4 }}>Active wells</div>
            </div>
            <div>
              <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 28, fontWeight: 700, color: 'var(--gold)' }}>100%</div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1, marginTop: 4 }}>On-premise</div>
            </div>
            <div>
              <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 28, fontWeight: 700, color: 'var(--gold)' }}>AI</div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1, marginTop: 4 }}>Integrated</div>
            </div>
          </div>
        </div>
      </div>

      <div className="login-right">
        <div style={{ position: 'absolute', top: 20, right: 20 }}>
          <DarkModeToggle />
        </div>

        <div style={{ marginBottom: 40 }}>
          <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 28, fontWeight: 600, color: 'var(--text)', marginBottom: 8 }}>
            Secure access
          </div>
          <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
            Sign in with your MARETAP credentials
          </div>
        </div>

        {error ? (
          <div className="alert alert-error">
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            {error}
          </div>
        ) : null}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 24 }}>
            <label htmlFor="username" style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 10 }}>
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Your username"
              autoFocus
              className="input-field"
              style={{ height: 48 }}
              required
            />
          </div>

          <div style={{ marginBottom: 24 }}>
            <label htmlFor="password" style={{ display: 'block', fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 1.5, marginBottom: 10 }}>
              Password
            </label>
            <div style={{ position: 'relative' }}>
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="********"
                className="input-field"
                style={{ height: 48, paddingRight: 42 }}
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-dim)' }}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          <button type="submit" className="btn-primary" style={{ width: '100%', height: 50 }} disabled={loading}>
            {loading ? 'Login in progress...' : 'Access platform'}
          </button>

          <div style={{ textAlign: 'center', marginTop: 14 }}>
            <a href="/accounts/forgot-password/" style={{ fontSize: 12, color: '#C0392B', textDecoration: 'none', opacity: 0.85 }}>
              Forgot your password?
            </a>
          </div>
        </form>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 32, padding: '12px 16px', background: 'rgba(201,168,76,0.05)', border: '1px solid var(--border)', borderRadius: 6 }}>
          <svg width="20" height="20" fill="none" stroke="#C9A84C" viewBox="0 0 24 24" style={{ opacity: 0.7 }}>
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
          </svg>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.5 }}>
            Access restricted to authorized MARETAP personnel. All data remains on the internal network.
          </div>
        </div>
      </div>
    </div>
  )
}
