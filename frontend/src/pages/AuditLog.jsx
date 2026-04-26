import { useEffect, useState } from 'react'
import Layout from '../components/Layout/Layout'
import { auditAPI } from '../api/audit'

function badgeClass(action) {
  if (action === 'LOGIN') return 'badge badge-success'
  if (action === 'LOGOUT') return 'badge badge-pending'
  if (action === 'UPLOAD_FILE') return 'badge badge-processing'
  return 'badge badge-error'
}

export default function AuditLog() {
  const [filters, setFilters] = useState({ user: '', action: '', start_date: '', end_date: '' })
  const [logs, setLogs] = useState([])
  const [users, setUsers] = useState([])
  const [actions, setActions] = useState([])
  const [pageInfo, setPageInfo] = useState({ page: 1, pages: 1, total: 0 })

  async function load(page = 1) {
    try {
      const res = await auditAPI.list({ ...filters, page })
      setLogs(res.data?.results || [])
      setUsers(res.data?.users || [])
      setActions(res.data?.actions || [])
      setPageInfo({
        page: res.data?.page || 1,
        pages: res.data?.pages || 1,
        total: res.data?.total || 0,
      })
    } catch {
      setLogs([])
    }
  }

  useEffect(() => {
    load(1)
  }, [])

  return (
    <Layout title="Audit log" breadcrumb="User action traceability">
      <div className="section-label">Filters</div>
      <div className="page-panel" style={{ marginBottom: 18 }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, minmax(0, 1fr))', gap: 12, alignItems: 'end' }}>
          <div>
            <label style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1.2, marginBottom: 6, display: 'block', fontWeight: 600 }}>User</label>
            <select className="input-field" value={filters.user} onChange={(e) => setFilters((f) => ({ ...f, user: e.target.value }))}>
              <option value="">All</option>
              {users.map((u) => <option key={u.id} value={u.id}>{u.name}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1.2, marginBottom: 6, display: 'block', fontWeight: 600 }}>Action type</label>
            <select className="input-field" value={filters.action} onChange={(e) => setFilters((f) => ({ ...f, action: e.target.value }))}>
              <option value="">All</option>
              {actions.map((a) => <option key={a} value={a}>{a}</option>)}
            </select>
          </div>
          <div>
            <label style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1.2, marginBottom: 6, display: 'block', fontWeight: 600 }}>Start date</label>
            <input className="input-field" type="date" value={filters.start_date} onChange={(e) => setFilters((f) => ({ ...f, start_date: e.target.value }))} />
          </div>
          <div>
            <label style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: 1.2, marginBottom: 6, display: 'block', fontWeight: 600 }}>End date</label>
            <input className="input-field" type="date" value={filters.end_date} onChange={(e) => setFilters((f) => ({ ...f, end_date: e.target.value }))} />
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn-primary" style={{ height: 38 }} onClick={() => load(1)}>Filter</button>
            <button
              className="btn-secondary"
              style={{ height: 38 }}
              onClick={() => {
                setFilters({ user: '', action: '', start_date: '', end_date: '' })
                setTimeout(() => load(1), 0)
              }}
            >
              Reset
            </button>
          </div>
        </div>
      </div>

      <div className="section-label">History</div>
      <div className="table-card">
        <table>
          <thead>
            <tr>
              <th>Date/time</th>
              <th>User</th>
              <th>Action</th>
              <th>Details</th>
              <th>IP</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {logs.length ? logs.map((log) => (
              <tr key={log.id}>
                <td>{log.created_at}</td>
                <td>{log.user_name || 'Anonymous'}</td>
                <td><span className={badgeClass(log.action)}>{log.action}</span></td>
                <td style={{ maxWidth: 360 }}>{log.details_display || '-'}</td>
                <td>{log.ip_address || '-'}</td>
                <td>{log.duration_display || '-'}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan={6} className="empty-row">No logs available at the moment.</td>
              </tr>
            )}
          </tbody>
        </table>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px', borderTop: '1px solid var(--border-soft)', color: 'var(--text-dim)', fontSize: 12 }}>
          <div>Page {pageInfo.page} / {pageInfo.pages} ({pageInfo.total} rows)</div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn-secondary" style={{ height: 32, minWidth: 84 }} disabled={pageInfo.page <= 1} onClick={() => load(pageInfo.page - 1)}>Previous</button>
            <button className="btn-secondary" style={{ height: 32, minWidth: 84 }} disabled={pageInfo.page >= pageInfo.pages} onClick={() => load(pageInfo.page + 1)}>Next</button>
          </div>
        </div>
      </div>
    </Layout>
  )
}
