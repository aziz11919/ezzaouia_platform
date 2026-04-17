import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from '../components/Layout/Layout'
import { authAPI } from '../api/auth'
import { useAuth } from '../contexts/AuthContext'

const ROLES_FALLBACK = [
  { value: 'admin', label: 'Administrator' },
  { value: 'ingenieur', label: 'Engineer' },
  { value: 'direction', label: 'Management' },
]

export default function CreateUser() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', first_name: '', last_name: '', email: '', role: '', department: '', phone: '' })
  const [errors, setErrors] = useState([])
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

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
    setSuccess('')
    setLoading(true)
    try {
      const res = await authAPI.createUser(form)
      setSuccess(res.data.message)
      setTimeout(() => navigate('/accounts/users'), 2200)
    } catch (err) {
      const errs = err.response?.data?.errors
      setErrors(Array.isArray(errs) ? errs : [err.response?.data?.error || 'Creation failed.'])
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout title="Create User" breadcrumb="Administration › User Management › New User">
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

        {success && (
          <div style={{ background: 'rgba(77,170,122,0.1)', border: '1px solid rgba(77,170,122,0.3)', borderRadius: 6, padding: '12px 16px', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: '#6BC99A' }}>
            <svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
            {success}
          </div>
        )}

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
                {ROLES_FALLBACK.map((r) => (
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
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" /></svg>
                {loading ? 'Creating…' : 'Create User & Send Credentials'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Layout>
  )
}
