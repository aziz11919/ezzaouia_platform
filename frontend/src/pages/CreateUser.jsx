import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout/Layout'
import { authAPI } from '../api/auth'
import { useAuth } from '../contexts/AuthContext'

const ROLES = [
  { value: 'admin', label: 'Admin' },
  { value: 'user',  label: 'User' },
]

function PasswordModal({ username, email, password, emailSent, onClose }) {
  const [copied, setCopied] = useState(false)

  function copyPassword() {
    navigator.clipboard.writeText(password).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2500)
    })
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.75)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div style={{
        background: 'var(--bg, #1a1d23)',
        border: '1px solid var(--border, #2e3340)',
        borderRadius: 12,
        padding: '32px 36px',
        maxWidth: 480, width: '92%',
        boxShadow: '0 16px 60px rgba(0,0,0,0.6)',
      }}>

        {/* ── Header ── */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <div style={{
            width: 40, height: 40, borderRadius: '50%',
            background: 'rgba(77,170,122,0.15)',
            border: '1px solid rgba(77,170,122,0.35)',
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            <svg width="20" height="20" fill="none" stroke="#6BC99A" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: 'var(--gold, #C9A84C)', lineHeight: 1.2 }}>
              User {username} created
            </div>
            <div style={{ fontSize: 14, color: '#9CA3AF', marginTop: 2 }}>
              Account ready — see credentials below
            </div>
          </div>
        </div>

        {/* ── Email status ── */}
        {emailSent ? (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: 'rgba(77,170,122,0.1)',
            border: '1px solid rgba(77,170,122,0.25)',
            borderRadius: 7, padding: '10px 14px', marginBottom: 20,
          }}>
            <svg width="15" height="15" fill="none" stroke="#6BC99A" viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <span style={{ fontSize: 13, color: '#6BC99A' }}>
              Password sent to <strong>{email}</strong>
            </span>
          </div>
        ) : (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            background: 'rgba(224,85,85,0.1)',
            border: '1px solid rgba(224,85,85,0.3)',
            borderRadius: 7, padding: '10px 14px', marginBottom: 20,
          }}>
            <svg width="16" height="16" fill="none" stroke="#E05555" viewBox="0 0 24 24" style={{ flexShrink: 0 }}>
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
            </svg>
            <span style={{ fontSize: 13, color: '#E05555', fontWeight: 500 }}>
              Email delivery failed. Save this password manually!
            </span>
          </div>
        )}

        {/* ── Password box ── */}
        <div style={{ marginBottom: 20 }}>
          <div style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '1px',
            textTransform: 'uppercase', color: 'var(--text-muted, #8b92a5)',
            marginBottom: 8,
          }}>
            Temporary password
          </div>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 10,
            background: 'rgba(201,168,76,0.07)',
            border: '1px solid rgba(201,168,76,0.35)',
            borderRadius: 8, padding: '12px 16px',
          }}>
            <code style={{
              flex: 1, fontSize: 18, fontFamily: '"Courier New", Courier, monospace',
              fontWeight: 700, color: '#C9A84C',
              letterSpacing: '1px', wordBreak: 'break-all', lineHeight: 1.3,
            }}>
              {password}
            </code>
            <button
              onClick={copyPassword}
              title="Copy password"
              style={{
                flexShrink: 0,
                background: copied ? 'rgba(77,170,122,0.18)' : 'rgba(201,168,76,0.14)',
                border: '1px solid ' + (copied ? 'rgba(77,170,122,0.45)' : 'rgba(201,168,76,0.4)'),
                borderRadius: 6, padding: '7px 13px', cursor: 'pointer',
                fontSize: 12, fontWeight: 600,
                color: copied ? '#6BC99A' : '#C9A84C',
                display: 'flex', alignItems: 'center', gap: 5,
                transition: 'all 0.15s',
              }}
            >
              {copied ? (
                <>
                  <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M5 13l4 4L19 7" />
                  </svg>
                  Copied!
                </>
              ) : (
                <>
                  <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  Copy
                </>
              )}
            </button>
          </div>
        </div>

        {/* ── Footer note ── */}
        <p style={{ fontSize: 12, color: 'var(--text-muted, #8b92a5)', margin: '0 0 24px', lineHeight: 1.6 }}>
          The user will be required to change this password on first login.
        </p>

        {/* ── Close button ── */}
        <button
          onClick={onClose}
          style={{
            width: '100%', padding: '11px 0',
            background: 'var(--gold, #C9A84C)', color: '#000',
            border: 'none', borderRadius: 7,
            fontSize: 13, fontWeight: 700, letterSpacing: '0.6px',
            textTransform: 'uppercase', cursor: 'pointer',
            transition: 'opacity 0.15s',
          }}
          onMouseEnter={e => e.currentTarget.style.opacity = '0.85'}
          onMouseLeave={e => e.currentTarget.style.opacity = '1'}
        >
          Close &amp; go to user list
        </button>

      </div>
    </div>
  )
}

export default function CreateUser() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', first_name: '', last_name: '', email: '', role: '', department: '', phone: '' })
  const [errors, setErrors] = useState([])
  const [loading, setLoading] = useState(false)
  const [modal, setModal] = useState(null)

  if (!user?.role || user.role !== 'admin') {
    navigate('/dashboard', { replace: true })
    return null
  }

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setErrors([])
    setLoading(true)
    try {
      const res = await authAPI.createUser(form)
      setModal({
        username:  form.username,
        email:     form.email,
        password:  res.data.temp_password,
        emailSent: res.data.email_sent,
      })
    } catch (err) {
      const errs = err.response?.data?.errors
      setErrors(Array.isArray(errs) ? errs : [err.response?.data?.error || 'Creation failed.'])
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout title="Create User" breadcrumb="Administration › User Management › New User">
      {modal && (
        <PasswordModal
          username={modal.username}
          email={modal.email}
          password={modal.password}
          emailSent={modal.emailSent}
          onClose={() => navigate('/accounts/users')}
        />
      )}

      <div style={{ maxWidth: 720 }}>

        <div style={{ background: 'rgba(201,168,76,0.06)', border: '1px solid rgba(201,168,76,0.2)', borderRadius: 6, padding: '14px 16px', marginBottom: 20, display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <svg width="18" height="18" fill="none" stroke="var(--gold)" viewBox="0 0 24 24" style={{ flexShrink: 0, marginTop: 1 }}>
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
          </svg>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5, margin: 0 }}>
            <strong style={{ color: 'var(--gold)' }}>Automatic credentials delivery</strong> — A secure random password will be generated
            and sent directly to the user's MARETAP email. The user will be required to change it upon first login.
          </p>
        </div>

        {errors.length > 0 && (
          <div style={{ background: 'rgba(224,85,85,0.08)', border: '1px solid rgba(224,85,85,0.25)', borderRadius: 6, padding: '12px 16px', marginBottom: 16 }}>
            {errors.map((e, i) => (
              <div key={i} style={{ fontSize: 13, color: 'var(--red)', display: 'flex', alignItems: 'center', gap: 8, marginBottom: i < errors.length - 1 ? 4 : 0 }}>
                <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" /></svg>
                {e}
              </div>
            ))}
          </div>
        )}

        <div className="page-panel">
          <div className="section-label" style={{ marginBottom: 20 }}>Account Details</div>
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>Username *</label>
              <input className="input-field" type="text" value={form.username} onChange={set('username')} placeholder="e.g. j.dupont" autoComplete="off" required />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 16 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>First Name</label>
                <input className="input-field" type="text" value={form.first_name} onChange={set('first_name')} placeholder="Jean" />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>Last Name</label>
                <input className="input-field" type="text" value={form.last_name} onChange={set('last_name')} placeholder="Dupont" />
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>Email (@maretap.tn) *</label>
              <input className="input-field" type="email" value={form.email} onChange={set('email')} placeholder="j.dupont@maretap.tn" required />
            </div>

            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>Role *</label>
              <select className="input-field" value={form.role} onChange={set('role')} required style={{ cursor: 'pointer' }}>
                <option value="" disabled>— Select a role —</option>
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>{r.label}</option>
                ))}
              </select>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 24 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>Department</label>
                <input className="input-field" type="text" value={form.department} onChange={set('department')} placeholder="e.g. Production" />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>Phone</label>
                <input className="input-field" type="text" value={form.phone} onChange={set('phone')} placeholder="+216 xx xxx xxx" />
              </div>
            </div>

            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button type="button" className="btn-secondary" onClick={() => navigate('/accounts/users')}>Cancel</button>
              <button type="submit" className="btn-primary" disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
                </svg>
                {loading ? 'Creating…' : 'Create User & Send Credentials'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Layout>
  )
}
