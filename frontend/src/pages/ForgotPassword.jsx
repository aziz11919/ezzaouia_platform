import { useState } from 'react'
import { Link } from 'react-router-dom'
import { authAPI } from '../api/auth'
import DarkModeToggle from '../components/UI/DarkModeToggle'

export default function ForgotPassword() {
  const [email, setEmail]     = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await authAPI.forgotPassword({ email })
      setSuccess(res.data.message)
    } catch (err) {
      setError(err.response?.data?.errors?.[0] || err.response?.data?.error || 'Request failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ fontFamily: "'Inter', sans-serif", background: 'var(--dark)', color: 'var(--text)', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ position: 'fixed', top: 16, right: 16, zIndex: 10 }}>
        <DarkModeToggle />
      </div>

      <div style={{ width: '100%', maxWidth: 440, background: 'var(--dark2)', border: '1px solid var(--border)', borderRadius: 10, padding: 40, position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: 'linear-gradient(90deg,transparent,var(--gold),transparent)' }} />

        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <img src="/static/img/logomaretap.png" alt="MARETAP" style={{ width: 48, height: 48, borderRadius: 8, background: '#fff', padding: 2 }} onError={(e) => { e.currentTarget.style.display = 'none' }} />
        </div>

        <div style={{ fontFamily: "'Rajdhani', sans-serif", fontSize: 24, fontWeight: 700, textAlign: 'center', marginBottom: 6 }}>
          Forgot your password?
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', lineHeight: 1.6, marginBottom: 28 }}>
          Enter your MARETAP email address and we will send you a reset link.
        </div>

        {success ? (
          <div style={{ background: 'rgba(77,170,122,0.1)', border: '1px solid rgba(77,170,122,0.3)', borderRadius: 6, padding: '14px 16px', marginBottom: 20, display: 'flex', gap: 10, alignItems: 'flex-start' }}>
            <svg width="18" height="18" fill="none" stroke="#4DAA7A" viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p style={{ fontSize: 13, color: '#6BC99A', lineHeight: 1.5, margin: 0 }}>{success}</p>
          </div>
        ) : (
          <>
            {error && (
              <div style={{ background: 'rgba(192,57,43,0.1)', border: '1px solid rgba(192,57,43,0.3)', borderRadius: 6, padding: '12px 16px', marginBottom: 16, fontSize: 13, color: '#E08070' }}>
                {error}
              </div>
            )}
            <form onSubmit={handleSubmit}>
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1.5px', marginBottom: 8 }}>Email address</label>
                <input
                  type="email"
                  className="form-input"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="yourname@maretap.tn"
                  autoComplete="email"
                  autoFocus
                  required
                />
              </div>
              <button type="submit" disabled={loading} style={{ width: '100%', background: 'var(--red)', color: '#fff', border: 'none', borderRadius: 6, padding: 14, fontFamily: "'Rajdhani', sans-serif", fontSize: 16, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1 }}>
                {loading ? 'Sending…' : 'Send Reset Link'}
              </button>
            </form>
          </>
        )}

        <Link to="/login" style={{ display: 'block', textAlign: 'center', marginTop: 18, fontSize: 13, color: 'var(--text-dim)', textDecoration: 'none' }}>
          ← Back to Login
        </Link>
      </div>
    </div>
  )
}
