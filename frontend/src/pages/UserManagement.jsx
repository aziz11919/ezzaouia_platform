import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../components/Layout/Layout'
import { authAPI } from '../api/auth'

export default function UserManagement() {
  const [users, setUsers] = useState([])
  const [roles, setRoles] = useState([])
  const [stats, setStats] = useState({ total: 0, actifs: 0, admins: 0, ingenieurs: 0, directions: 0 })
  const [filters, setFilters] = useState({ q: '', role: '', active: '' })

  async function load() {
    try {
      const res = await authAPI.listUsers(filters)
      setUsers(res.data?.results || [])
      setRoles(res.data?.roles || [])
      setStats(res.data?.stats || { total: 0, actifs: 0, admins: 0, ingenieurs: 0, directions: 0 })
    } catch {
      setUsers([])
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function toggleUser(userId) {
    await authAPI.toggleUser(userId)
    await load()
  }

  async function deleteUser(userId, userName) {
    const ok = window.confirm(`Delete account '${userName}'?`)
    if (!ok) return
    await authAPI.deleteUser(userId)
    await load()
  }

  return (
    <Layout
      title="User Management"
      breadcrumb="Administration - Accounts and Access"
      rightNode={<Link to="/profile" className="btn-secondary" style={{ textDecoration: 'none' }}>My Profile</Link>}
    >
      <div className="grid-kpi" style={{ marginBottom: 18 }}>
        <div className="page-panel"><div className="kpi-label">Total accounts</div><div className="kpi-value v-gold" style={{ marginBottom: 0, fontSize: 26 }}>{stats.total}</div></div>
        <div className="page-panel"><div className="kpi-label">Active accounts</div><div className="kpi-value v-green" style={{ marginBottom: 0, fontSize: 26 }}>{stats.actifs}</div></div>
        <div className="page-panel"><div className="kpi-label">Administrators</div><div className="kpi-value v-gold" style={{ marginBottom: 0, fontSize: 26 }}>{stats.admins}</div></div>
        <div className="page-panel"><div className="kpi-label">Engineers</div><div className="kpi-value v-blue" style={{ marginBottom: 0, fontSize: 26 }}>{stats.ingenieurs}</div></div>
      </div>

      <div className="page-panel" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <input
            className="input-field"
            style={{ minWidth: 260, flex: 1 }}
            placeholder="Search by username, email..."
            value={filters.q}
            onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
          />
          <select className="input-field" style={{ width: 160 }} value={filters.role} onChange={(e) => setFilters((f) => ({ ...f, role: e.target.value }))}>
            <option value="">All roles</option>
            {roles.map((role) => <option key={role.value} value={role.value}>{role.label}</option>)}
          </select>
          <select className="input-field" style={{ width: 140 }} value={filters.active} onChange={(e) => setFilters((f) => ({ ...f, active: e.target.value }))}>
            <option value="">All status</option>
            <option value="1">Active</option>
            <option value="0">Inactive</option>
          </select>
          <button className="btn-primary" onClick={load}>Apply</button>
          <button className="btn-secondary" onClick={() => { setFilters({ q: '', role: '', active: '' }); setTimeout(load, 0) }}>Reset</button>
          <button
            className="btn-primary"
            style={{ marginLeft: 'auto' }}
            onClick={() => { window.location.href = '/accounts/users/create/' }}
          >
            New user
          </button>
        </div>
      </div>

      <div className="table-card">
        <div className="table-header">
          <div className="table-title">Users</div>
          <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>{users.length} results</div>
        </div>
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Department</th>
              <th>Status</th>
              <th>Last login</th>
              <th style={{ textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.length ? users.map((u) => (
              <tr key={u.id}>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <div className="user-avatar" style={{ width: 32, height: 32 }}>{(u.username || '?').charAt(0).toUpperCase()}</div>
                    <div>
                      <div style={{ fontSize: 13, color: 'var(--text)', fontWeight: 500 }}>{u.full_name || '-'}</div>
                      <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>@{u.username}</div>
                    </div>
                  </div>
                </td>
                <td>{u.email || '-'}</td>
                <td><span className={`role-badge role-${u.role}`}>{u.role}</span></td>
                <td>{u.department || '-'}</td>
                <td>
                  <span className={`badge ${u.is_active ? 'badge-success' : 'badge-error'}`}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td>{u.last_login || 'Never'}</td>
                <td style={{ textAlign: 'center' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}>
                    <button className="btn-secondary" style={{ height: 30, padding: '0 10px' }} onClick={() => toggleUser(u.id)}>
                      {u.is_active ? 'Disable' : 'Enable'}
                    </button>
                    {!u.is_self ? (
                      <button className="btn-danger" style={{ height: 30, padding: '0 10px' }} onClick={() => deleteUser(u.id, u.full_name || u.username)}>
                        Delete
                      </button>
                    ) : null}
                  </div>
                </td>
              </tr>
            )) : (
              <tr>
                <td colSpan={7} className="empty-row">No users found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Layout>
  )
}
