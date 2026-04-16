import { useEffect, useState } from 'react'
import Layout from '../components/Layout/Layout'
import { authAPI } from '../api/auth'
import { useAuth } from '../contexts/AuthContext'

export default function Profile() {
  const { user, refreshUser } = useAuth()
  const [profile, setProfile] = useState({ first_name: '', last_name: '', email: '', phone: '', department: '' })
  const [passwords, setPasswords] = useState({ current_password: '', new_password: '', confirm_password: '' })
  const [message, setMessage] = useState(null)

  useEffect(() => {
    setProfile({
      first_name: user?.first_name || '',
      last_name: user?.last_name || '',
      email: user?.email || '',
      phone: user?.phone || '',
      department: user?.department || '',
    })
  }, [user])

  async function saveProfile(event) {
    event.preventDefault()
    setMessage(null)
    try {
      await authAPI.updateProfile(profile)
      await refreshUser()
      setMessage({ type: 'success', text: 'Profile updated successfully.' })
    } catch (error) {
      const errors = error.response?.data?.errors
      setMessage({ type: 'error', text: Array.isArray(errors) ? errors.join(' ') : 'Update failed.' })
    }
  }

  async function changePassword(event) {
    event.preventDefault()
    setMessage(null)
    try {
      await authAPI.changePassword(passwords)
      setPasswords({ current_password: '', new_password: '', confirm_password: '' })
      await refreshUser()
      setMessage({ type: 'success', text: 'Password changed successfully.' })
    } catch (error) {
      const errors = error.response?.data?.errors
      setMessage({ type: 'error', text: Array.isArray(errors) ? errors.join(' ') : 'Password change failed.' })
    }
  }

  const initials = [user?.first_name?.[0], user?.last_name?.[0]].filter(Boolean).join('').toUpperCase() || user?.username?.[0]?.toUpperCase() || '?'

  return (
    <Layout title="My Profile" breadcrumb={user?.username || ''}>
      {message ? <div className={`alert ${message.type === 'error' ? 'alert-error' : 'alert-success'}`}>{message.text}</div> : null}

      <div className="page-panel" style={{ marginBottom: 24, textAlign: 'center', position: 'relative', overflow: 'hidden' }}>
        <div style={{ width: 72, height: 72, borderRadius: 14, background: 'var(--dark4)', border: '2px solid var(--gold)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'Rajdhani, sans-serif', fontSize: 32, fontWeight: 700, color: 'var(--gold)', margin: '0 auto 14px' }}>
          {initials}
        </div>
        <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 22, fontWeight: 700, color: 'var(--text)', marginBottom: 4 }}>
          {user?.first_name || user?.username}
        </div>
        <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 12 }}>@{user?.username}</div>
        <span className={`role-badge role-${user?.role}`}>{user?.role}</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
        <div className="page-panel">
          <div className="section-label" style={{ marginBottom: 14 }}>Personal information</div>
          <form onSubmit={saveProfile}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 7 }}>First name</label>
                <input className="input-field" value={profile.first_name} onChange={(e) => setProfile((p) => ({ ...p, first_name: e.target.value }))} />
              </div>
              <div>
                <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 7 }}>Last name</label>
                <input className="input-field" value={profile.last_name} onChange={(e) => setProfile((p) => ({ ...p, last_name: e.target.value }))} />
              </div>
            </div>
            <div style={{ marginTop: 14 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 7 }}>Email</label>
              <input className="input-field" type="email" value={profile.email} onChange={(e) => setProfile((p) => ({ ...p, email: e.target.value }))} />
            </div>
            <div style={{ marginTop: 14 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 7 }}>Department</label>
              <input className="input-field" value={profile.department} onChange={(e) => setProfile((p) => ({ ...p, department: e.target.value }))} />
            </div>
            <div style={{ marginTop: 14 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 7 }}>Phone</label>
              <input className="input-field" value={profile.phone} onChange={(e) => setProfile((p) => ({ ...p, phone: e.target.value }))} />
            </div>
            <div style={{ marginTop: 18 }}>
              <button className="btn-primary" type="submit">Save</button>
            </div>
          </form>
        </div>

        <div className="page-panel">
          <div className="section-label" style={{ marginBottom: 14 }}>Change password</div>
          <form onSubmit={changePassword}>
            <div>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 7 }}>Current password</label>
              <input className="input-field" type="password" value={passwords.current_password} onChange={(e) => setPasswords((p) => ({ ...p, current_password: e.target.value }))} />
            </div>
            <div style={{ marginTop: 14 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 7 }}>New password</label>
              <input className="input-field" type="password" value={passwords.new_password} onChange={(e) => setPasswords((p) => ({ ...p, new_password: e.target.value }))} required />
            </div>
            <div style={{ marginTop: 14 }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 7 }}>Confirm new password</label>
              <input className="input-field" type="password" value={passwords.confirm_password} onChange={(e) => setPasswords((p) => ({ ...p, confirm_password: e.target.value }))} required />
            </div>
            <div style={{ marginTop: 14, padding: '12px 14px', background: 'rgba(201,168,76,0.06)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.7 }}>
              Password must contain at least 8 characters and include one uppercase letter and one number.
            </div>
            <div style={{ marginTop: 18 }}>
              <button className="btn-danger" type="submit">Change password</button>
            </div>
          </form>
        </div>
      </div>
    </Layout>
  )
}
