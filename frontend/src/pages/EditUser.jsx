import { useState, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import Layout from '../components/Layout/Layout'
import { authAPI } from '../api/auth'
import { useAuth } from '../contexts/AuthContext'

export default function EditUser() {
  const { userId } = useParams()
  const { user: me } = useAuth()
  const navigate = useNavigate()

  const [target, setTarget]   = useState(null)
  const [form, setForm]       = useState({})
  const [roles, setRoles]     = useState([])
  const [message, setMessage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving]   = useState(false)

  const [pwdForm, setPwdForm] = useState({ password: '', password_confirm: '' })
  const [pwdMsg, setPwdMsg]   = useState(null)
  const [pwdSaving, setPwdSaving] = useState(false)

  useEffect(() => {
    if (!me || me.role !== 'admin') { navigate('/dashboard', { replace: true }); return }
    authAPI.getUser(userId)
      .then((res) => {
        const d = res.data
        setTarget(d)
        setRoles(d.roles || [])
        setForm({
          username: d.username, first_name: d.first_name, last_name: d.last_name,
          email: d.email, role: d.role, department: d.department,
          phone: d.phone, is_active: d.is_active,
        })
      })
      .catch(() => navigate('/accounts/users', { replace: true }))
      .finally(() => setLoading(false))
  }, [userId, me, navigate])

  function set(field) {
    return (e) => setForm((f) => ({ ...f, [field]: e.target.type === 'checkbox' ? e.target.checked : e.target.value }))
  }

  async function handleSave(e) {
    e.preventDefault()
    setMessage(null)
    setSaving(true)
    try {
      await authAPI.editUser(userId, form)
      setMessage({ type: 'success', text: 'User updated successfully.' })
    } catch (err) {
      const errs = err.response?.data?.errors
      setMessage({ type: 'error', text: Array.isArray(errs) ? errs.join(' ') : (err.response?.data?.error || 'Update failed.') })
    } finally {
      setSaving(false)
    }
  }

  async function handlePwdReset(e) {
    e.preventDefault()
    setPwdMsg(null)
    setPwdSaving(true)
    try {
      await authAPI.adminResetPassword(userId, pwdForm)
      setPwdForm({ password: '', password_confirm: '' })
      setPwdMsg({ type: 'success', text: 'Password reset. User must change it on next login.' })
    } catch (err) {
      const errs = err.response?.data?.errors
      setPwdMsg({ type: 'error', text: Array.isArray(errs) ? errs.join(' ') : (err.response?.data?.error || 'Reset failed.') })
    } finally {
      setPwdSaving(false)
    }
  }

  async function handleDelete() {
    if (!window.confirm(`Delete account '${target?.username}'? This cannot be undone.`)) return
    try {
      await authAPI.deleteUser(userId)
      navigate('/accounts/users')
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.error || 'Deletion failed.' })
    }
  }

  if (loading) return <Layout title="Edit User" breadcrumb="Loading…"><div className="stats-loading">Loading…</div></Layout>

  const initials = [target?.first_name?.[0], target?.last_name?.[0]].filter(Boolean).join('').toUpperCase() || target?.username?.[0]?.toUpperCase() || '?'
  const displayName = target ? (target.first_name && target.last_name ? `${target.first_name} ${target.last_name}` : target.username) : ''

  return (
    <Layout title={`Edit — ${displayName}`} breadcrumb="Administration › Users › Edit">

      {message && (
        <div className={`alert ${message.type === 'error' ? 'alert-error' : 'alert-success'}`} style={{ marginBottom: 20 }}>
          {message.text}
        </div>
      )}

      {/* User banner */}
      <div style={{ background: 'var(--dark3)', border: '1px solid var(--border)', borderRadius: 8, padding: '16px 20px', display: 'flex', alignItems: 'center', gap: 16, marginBottom: 24 }}>
        <div className="user-avatar" style={{ width: 48, height: 48, borderRadius: 10, fontSize: 22 }}>{initials}</div>
        <div style={{ flex: 1 }}>
          <div style={{ fontFamily: "'Rajdhani', sans-serif", fontSize: 16, fontWeight: 500 }}>{displayName}</div>
          <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 3 }}>@{target?.username} — Member since {target?.date_joined} — Last login: {target?.last_login}</div>
        </div>
        <span className={`badge ${target?.is_active ? 'badge-success' : 'badge-error'}`}>{target?.is_active ? 'ACTIVE' : 'INACTIVE'}</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, alignItems: 'start' }}>

        {/* Left: edit form */}
        <div className="page-panel">
          <div className="section-label" style={{ marginBottom: 18 }}>Account Information</div>
          <form onSubmit={handleSave}>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>Username *</label>
              <input className="input-field" type="text" value={form.username || ''} onChange={set('username')} required />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 16 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>First name</label>
                <input className="input-field" type="text" value={form.first_name || ''} onChange={set('first_name')} />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>Last name</label>
                <input className="input-field" type="text" value={form.last_name || ''} onChange={set('last_name')} />
              </div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>Email</label>
              <input className="input-field" type="email" value={form.email || ''} onChange={set('email')} />
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14, marginBottom: 16 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>Role *</label>
                <select className="input-field" value={form.role || ''} onChange={set('role')} style={{ cursor: 'pointer' }}>
                  {roles.map((r) => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>Phone</label>
                <input className="input-field" type="text" value={form.phone || ''} onChange={set('phone')} />
              </div>
            </div>
            <div style={{ marginBottom: 16 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>Department</label>
              <input className="input-field" type="text" value={form.department || ''} onChange={set('department')} />
            </div>
            {!target?.is_self && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px', background: 'var(--dark3)', border: '1px solid var(--border-soft)', borderRadius: 6, marginBottom: 16 }}>
                <span style={{ fontSize: 13, color: 'var(--text-muted)', flex: 1 }}>Active account</span>
                <label style={{ position: 'relative', width: 40, height: 22, cursor: 'pointer' }}>
                  <input type="checkbox" checked={form.is_active || false} onChange={set('is_active')} style={{ opacity: 0, width: 0, height: 0 }} />
                  <span style={{ position: 'absolute', inset: 0, background: form.is_active ? 'rgba(77,170,122,0.2)' : 'var(--dark4)', borderRadius: 22, border: `1px solid ${form.is_active ? 'var(--green)' : 'var(--border-soft)'}`, transition: '0.2s' }}>
                    <span style={{ position: 'absolute', height: 16, width: 16, left: form.is_active ? 20 : 2, bottom: 2, background: form.is_active ? 'var(--green)' : 'var(--text-dim)', borderRadius: '50%', transition: '0.2s' }} />
                  </span>
                </label>
              </div>
            )}
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
              <button type="button" className="btn-secondary" onClick={() => navigate('/accounts/users')}>Cancel</button>
              <button type="submit" className="btn-primary" disabled={saving}>
                {saving ? 'Saving…' : 'Save Changes'}
              </button>
            </div>
          </form>
        </div>

        {/* Right: password reset + danger zone */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          <div className="page-panel">
            <div className="section-label" style={{ marginBottom: 18 }}>Reset Password</div>
            {pwdMsg && (
              <div className={`alert ${pwdMsg.type === 'error' ? 'alert-error' : 'alert-success'}`} style={{ marginBottom: 14 }}>{pwdMsg.text}</div>
            )}
            <form onSubmit={handlePwdReset}>
              <div style={{ marginBottom: 14 }}>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>New Password</label>
                <input className="input-field" type="password" value={pwdForm.password} onChange={(e) => setPwdForm((f) => ({ ...f, password: e.target.value }))} placeholder="New password" />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px', fontWeight: 600, display: 'block', marginBottom: 7 }}>Confirm</label>
                <input className="input-field" type="password" value={pwdForm.password_confirm} onChange={(e) => setPwdForm((f) => ({ ...f, password_confirm: e.target.value }))} placeholder="Repeat password" />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button type="submit" className="btn-danger" disabled={pwdSaving} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                  <svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z" /></svg>
                  {pwdSaving ? 'Resetting…' : 'Reset Password'}
                </button>
              </div>
            </form>
          </div>

          {!target?.is_self && (
            <div className="page-panel" style={{ border: '1px solid rgba(224,85,85,0.2)' }}>
              <div className="section-label" style={{ marginBottom: 14, color: 'var(--red)' }}>Danger Zone</div>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16, lineHeight: 1.6 }}>Deleting this account is permanent and removes all associated access.</p>
              <button className="btn-danger" onClick={handleDelete} style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                <svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" /></svg>
                Delete this account
              </button>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}
