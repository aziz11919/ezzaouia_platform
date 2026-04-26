import { useState, useEffect } from 'react'
import { BarChart2, ExternalLink } from 'lucide-react'
import Layout from '../components/Layout/Layout'
import { powerbiAPI } from '../api/powerbi'

export default function PowerBI() {
  const [reports,      setReports]      = useState([])
  const [activeReport, setActiveReport] = useState(null)
  const [loading,      setLoading]      = useState(true)
  const [opened,       setOpened]       = useState(false)

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

        setReports(list)
        const lastId = localStorage.getItem('powerbi-last-report')
        const last = list.find(r => String(r.id) === String(lastId))
        setActiveReport(last || list[0] || null)
      } catch (e) {
        setReports([])
        setActiveReport(null)
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
    localStorage.setItem('powerbi-last-report', report.id)
    window.open(report.embed_url, '_blank')
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
