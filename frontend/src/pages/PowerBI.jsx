import { useState, useEffect } from 'react'
import { BarChart2, ExternalLink } from 'lucide-react'
import Layout from '../components/Layout/Layout'
import { powerbiAPI } from '../api/powerbi'
import { useAuth } from '../contexts/AuthContext'

export default function PowerBI() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const [reports,      setReports]      = useState([])
  const [activeReport, setActiveReport] = useState(null)
  const [loading,      setLoading]      = useState(true)
  const [opened,       setOpened]       = useState(false)
  const [saving,       setSaving]       = useState(false)
  const [adminMessage, setAdminMessage] = useState('')
  const [newReport,    setNewReport]    = useState({
    title: '',
    description: '',
    embed_url: '',
    icon: '📊',
    role: 'all',
    order: 0,
  })
  const [editUrl,      setEditUrl]      = useState('')

  function hydrateActive(list) {
    setReports(list)
    const lastId = localStorage.getItem('powerbi-last-report')
    const last = list.find(r => String(r.id) === String(lastId))
    const selected = last || list[0] || null
    setActiveReport(selected)
    setEditUrl(selected?.embed_url || '')
  }

  useEffect(() => {
    async function loadReports() {
      try {
        // Preferred source: DB-backed reports with role filtering.
        const primary = await powerbiAPI.list()
        let list = primary?.data?.reports || []

        // Backward compatibility: fallback to legacy JSON endpoint.
        if (!Array.isArray(list) || list.length === 0) {
          const legacy = await powerbiAPI.reports()
          list = legacy?.data?.reports || []
        }

        hydrateActive(list)
      } catch (e) {
        setReports([])
        setActiveReport(null)
        setEditUrl('')
      } finally {
        setLoading(false)
      }
    }

    loadReports()
  }, [])

  useEffect(() => {
    if (activeReport?.embed_url) {
      window.open(activeReport.embed_url, '_blank')
      setOpened(true)
    }
  }, [activeReport])

  function openReport(report) {
    setActiveReport(report)
    setEditUrl(report?.embed_url || '')
    localStorage.setItem('powerbi-last-report', report.id)
    window.open(report.embed_url, '_blank')
  }

  async function reloadReports() {
    const primary = await powerbiAPI.list()
    const list = primary?.data?.reports || []
    hydrateActive(list)
  }

  async function handleAddReport(e) {
    e.preventDefault()
    setSaving(true)
    setAdminMessage('')
    try {
      await powerbiAPI.create({
        ...newReport,
        order: Number(newReport.order || 0),
      })
      await reloadReports()
      setNewReport({
        title: '',
        description: '',
        embed_url: '',
        icon: '📊',
        role: 'all',
        order: 0,
      })
      setAdminMessage('Report added successfully.')
    } catch (err) {
      setAdminMessage(err?.response?.data?.error || 'Failed to add report.')
    } finally {
      setSaving(false)
    }
  }

  async function handleUpdateUrl(e) {
    e.preventDefault()
    if (!activeReport?.id) return
    setSaving(true)
    setAdminMessage('')
    try {
      await powerbiAPI.update(activeReport.id, { embed_url: editUrl })
      await reloadReports()
      setAdminMessage('Report URL updated successfully.')
    } catch (err) {
      setAdminMessage(err?.response?.data?.error || 'Failed to update URL.')
    } finally {
      setSaving(false)
    }
  }

  async function handleDeleteReport() {
    if (!activeReport?.id) return
    const ok = window.confirm(`Delete report "${activeReport.title}"?`)
    if (!ok) return

    setSaving(true)
    setAdminMessage('')
    try {
      await powerbiAPI.remove(activeReport.id)
      await reloadReports()
      setAdminMessage('Report deleted successfully.')
    } catch (err) {
      setAdminMessage(err?.response?.data?.error || 'Failed to delete report.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Layout title="Power BI" breadcrumb="Analytics / Power BI Dashboards">
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 'calc(100vh - 120px)', gap: '32px', padding: '48px 24px', textAlign: 'center' }}>

        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-muted)', fontSize: '13px' }}>
            <div style={{ width: '18px', height: '18px', border: '2px solid var(--border)', borderTopColor: 'var(--gold)', borderRadius: '50%', animation: 'spin 0.7s linear infinite', flexShrink: 0 }} />
            Chargement...
          </div>
        ) : activeReport?.embed_url ? (
          <>
            {/* Icon */}
            <div style={{ width: 80, height: 80, borderRadius: '50%', background: 'rgba(201,168,76,0.1)', border: '1px solid rgba(201,168,76,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <BarChart2 size={36} color="var(--gold, #C9A84C)" />
            </div>

            {/* Title */}
            <div>
              <h2 style={{ fontSize: '22px', fontWeight: '700', color: 'var(--gold, #C9A84C)', fontFamily: 'Rajdhani, sans-serif', margin: '0 0 8px' }}>
                {activeReport.title}
              </h2>
              <p style={{ fontSize: '14px', color: '#9CA3AF', margin: 0 }}>
                {opened
                  ? 'Your Power BI report is opening in a new tab.'
                  : 'Click the button below to open the dashboard.'}
              </p>
              {activeReport.description && (
                <p style={{ fontSize: '12px', color: 'var(--text-muted, #6b7280)', margin: '6px 0 0' }}>
                  {activeReport.description}
                </p>
              )}
            </div>

            {/* Open button */}
            <button
              onClick={() => openReport(activeReport)}
              style={{
                display:       'flex',
                alignItems:    'center',
                gap:           '8px',
                padding:       '12px 28px',
                background:    'var(--gold, #C9A84C)',
                color:         '#000',
                border:        'none',
                borderRadius:  '8px',
                fontSize:      '13px',
                fontWeight:    '700',
                fontFamily:    'Rajdhani, sans-serif',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                cursor:        'pointer',
                transition:    'opacity 0.15s',
              }}
              onMouseEnter={e => e.currentTarget.style.opacity = '0.85'}
              onMouseLeave={e => e.currentTarget.style.opacity = '1'}
            >
              <ExternalLink size={15} />
              Open Dashboard
            </button>

            {/* Report switcher — only when multiple reports */}
            {reports.length > 1 && (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '10px', marginTop: '8px' }}>
                <p style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', margin: 0 }}>Other reports</p>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center' }}>
                  {reports.filter(r => r.id !== activeReport.id).map(r => (
                    <button
                      key={r.id}
                      onClick={() => openReport(r)}
                      style={{
                        padding:       '6px 14px',
                        fontSize:      '11px',
                        fontWeight:    '600',
                        fontFamily:    'Rajdhani, sans-serif',
                        letterSpacing: '0.06em',
                        textTransform: 'uppercase',
                        borderRadius:  '6px',
                        border:        '1px solid var(--border)',
                        background:    'var(--dark3, #1e2129)',
                        color:         'var(--text-muted)',
                        cursor:        'pointer',
                        transition:    'border-color 0.15s, color 0.15s',
                      }}
                      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold)'; e.currentTarget.style.color = 'var(--gold)' }}
                      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-muted)' }}
                    >
                      {r.title}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {isAdmin && (
              <div style={{ marginTop: '24px', width: '100%', maxWidth: 860, textAlign: 'left', border: '1px solid var(--border)', borderRadius: 10, padding: 16, background: 'var(--dark3, #1e2129)' }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--gold)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Admin Only - Manage Reports
                </div>
                {adminMessage ? (
                  <div style={{ fontSize: 12, marginBottom: 10, color: 'var(--text-muted)' }}>{adminMessage}</div>
                ) : null}
                <form onSubmit={handleAddReport} style={{ display: 'grid', gap: 8, marginBottom: 14 }}>
                  <input value={newReport.title} onChange={(e) => setNewReport(prev => ({ ...prev, title: e.target.value }))} placeholder="Report title" required />
                  <input value={newReport.embed_url} onChange={(e) => setNewReport(prev => ({ ...prev, embed_url: e.target.value }))} placeholder="Embed URL" required />
                  <input value={newReport.description} onChange={(e) => setNewReport(prev => ({ ...prev, description: e.target.value }))} placeholder="Description (optional)" />
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input value={newReport.icon} onChange={(e) => setNewReport(prev => ({ ...prev, icon: e.target.value }))} placeholder="Icon" />
                    <select value={newReport.role} onChange={(e) => setNewReport(prev => ({ ...prev, role: e.target.value }))}>
                      <option value="all">All</option>
                      <option value="admin">Admin only</option>
                      <option value="user">User</option>
                    </select>
                    <input type="number" value={newReport.order} onChange={(e) => setNewReport(prev => ({ ...prev, order: e.target.value }))} placeholder="Order" />
                  </div>
                  <button type="submit" disabled={saving}>Add Report</button>
                </form>

                <form onSubmit={handleUpdateUrl} style={{ display: 'grid', gap: 8 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    Edit URL for: <strong>{activeReport?.title || 'No report selected'}</strong>
                  </div>
                  <input value={editUrl} onChange={(e) => setEditUrl(e.target.value)} placeholder="New embed URL" required disabled={!activeReport} />
                  <button type="submit" disabled={saving || !activeReport}>Edit Report URL</button>
                </form>

                <div style={{ marginTop: 10 }}>
                  <button
                    type="button"
                    onClick={handleDeleteReport}
                    disabled={saving || !activeReport}
                    style={{
                      background: '#7f1d1d',
                      color: '#fff',
                      border: '1px solid #b91c1c',
                      borderRadius: 6,
                      padding: '8px 12px',
                      cursor: saving || !activeReport ? 'not-allowed' : 'pointer',
                      opacity: saving || !activeReport ? 0.7 : 1,
                    }}
                  >
                    Delete Report
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          <>
            <BarChart2 size={48} color="var(--border)" />
            <h3 style={{ color: 'var(--text-muted)', fontSize: '16px', fontWeight: '600', fontFamily: 'Rajdhani, sans-serif', margin: 0 }}>
              Aucun rapport Power BI configuré
            </h3>
            <p style={{ color: '#9CA3AF', fontSize: '13px', maxWidth: '360px', margin: 0 }}>
              Contactez l'administrateur pour configurer les URL d'intégration Power BI.
            </p>
          </>
        )}

      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </Layout>
  )
}
