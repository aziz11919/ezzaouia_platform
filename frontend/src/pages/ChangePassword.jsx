import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authAPI } from '../api/auth'
import { useAuth } from '../contexts/AuthContext'
import DarkModeToggle from '../components/UI/DarkModeToggle'

export default function ChangePassword() {
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()
  const isForced = user?.must_change_password === true

  const [form, setForm] = useState({ current_password: '', new_password: '', confirm_password: '' })
  const [errors, setErrors] = useState([])
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setErrors([])
    setLoading(true)
    try {
      await authAPI.changePassword(form)
      await refreshUser()
      setSuccess(true)
      setTimeout(() => navigate('/dashboard'), 1800)
    } catch (err) {
      const errs = err.response?.data?.errors
      setErrors(Array.isArray(errs) ? errs : [err.response?.data?.error || 'Password change failed.'])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ fontFamily: "'Inter', sans-serif", background: 'var(--dark)', color: 'var(--text)', minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ position: 'fixed', top: 16, right: 16, zIndex: 10 }}>
        <DarkModeToggle />
      </div>

      <div style={{ width: '100%', maxWidth: 460, background: 'var(--dark2)', border: '1px solid var(--border)', borderRadius: 10, padding: 40, position: 'relative', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: 2, background: 'linear-gradient(90deg,transparent,var(--red),transparent)' }} />

        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <img src="/static/img/logomaretap.png" alt="MARETAP" style={{ width: 48, height: 48, borderRadius: 8, background: '#fff', padding: 2 }} onError={(e) => { e.currentTarget.style.display = 'none' }} />
        </div>

        {isForced && (
          <div style={{ background: 'rgba(192,57,43,0.12)', border: '1px solid rgba(192,57,43,0.35)', borderRadius: 8, padding: '14px 16px', marginBottom: 24, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <svg width="18" height="18" fill="none" stroke="#C0392B" viewBox="0 0 24 24" style={{ flexShrink: 0, marginTop: 1 }}>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
            <div style={{ fontSize: 13, color: '#E08070', lineHeight: 1.5 }}>
              <strong style={{ color: '#E05555', display: 'block', marginBottom: 2 }}>Security Notice — Action Required</strong>
              You must change your temporary password before continuing.
            </div>
          </div>
        )}

        <div style={{ fontFamily: "'Rajdhani', sans-serif", fontSize: 24, fontWeight: 700, textAlign: 'center', marginBottom: 4 }}>
          {isForced ? 'Set New Password' : 'Change Password'}
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)', textAlign: 'center', marginBottom: 28 }}>
          {isForced ? 'Create a strong password for your account' : 'Update your account password'}
        </div>

        {success && (
          <div style={{ background: 'rgba(77,170,122,0.1)', border: '1px solid rgba(77,170,122,0.3)', borderRadius: 6, padding: '14px 16px', marginBottom: 20, display: 'flex', gap: 10, alignItems: 'center' }}>
            <svg width="18" height="18" fill="none" stroke="#4DAA7A" viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span style={{ fontSize: 13, color: '#6BC99A' }}>Password changed successfully. Redirecting…</span>
          </div>
        )}

        {errors.length > 0 && (
          <div style={{ background: 'rgba(192,57,43,0.1)', border: '1px solid rgba(192,57,43,0.3)', borderRadius: 6, padding: '12px 16px', marginBottom: 20 }}>
            {errors.map((e, i) => (
              <div key={i} style={{ fontSize: 13, color: '#E08070', display: 'flex', alignItems: 'center', gap: 8, marginBottom: i < errors.length - 1 ? 4 : 0 }}>
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                {e}
              </div>
            ))}
          </div>
        )}

        {!success && (
          <form onSubmit={handleSubmit}>
            {!isForced && (
              <div style={{ marginBottom: 20 }}>
                <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1.5px', marginBottom: 8 }}>Current Password</label>
                <input type="password" className="form-input" value={form.current_password} onChange={(e) => setForm((f) => ({ ...f, current_password: e.target.value }))} required autoComplete="current-password" />
              </div>
            )}
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1.5px', marginBottom: 8 }}>New Password</label>
              <input type="password" className="form-input" value={form.new_password} onChange={(e) => setForm((f) => ({ ...f, new_password: e.target.value }))} required autoComplete="new-password" />
            </div>
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', fontSize: 11, fontWeight: 500, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '1.5px', marginBottom: 8 }}>Confirm New Password</label>
              <input type="password" className="form-input" value={form.confirm_password} onChange={(e) => setForm((f) => ({ ...f, confirm_password: e.target.value }))} required autoComplete="new-password" />
            </div>

            <div style={{ background: 'rgba(61,82,114,0.15)', border: '1px solid var(--border-soft)', borderRadius: 6, padding: '12px 16px', marginBottom: 20 }}>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: 8, fontWeight: 600 }}>Password requirements</div>
              {['At least 8 characters', 'At least one uppercase letter (A–Z)', 'At least one number (0–9)'].map((r) => (
                <div key={r} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: 'var(--text-dim)', marginBottom: 4 }}>
                  <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4" /></svg>
                  {r}
                </div>
              ))}
            </div>

            <button type="submit" disabled={loading} style={{ width: '100%', background: 'var(--red)', color: '#fff', border: 'none', borderRadius: 6, padding: 14, fontFamily: "'Rajdhani', sans-serif", fontSize: 16, fontWeight: 700, letterSpacing: '1.5px', textTransform: 'uppercase', cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1 }}>
              {loading ? 'Saving…' : isForced ? 'Set New Password' : 'Update Password'}
            </button>
          </form>
        )}

        {!isForced && (
          <Link to="/dashboard" style={{ display: 'block', textAlign: 'center', marginTop: 18, fontSize: 13, color: 'var(--text-dim)', textDecoration: 'none' }}>
            ← Back to dashboard
          </Link>
        )}
      </div>
    </div>
  )
}
