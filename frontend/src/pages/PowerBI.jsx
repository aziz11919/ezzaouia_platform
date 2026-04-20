import { useState, useEffect } from 'react'
import { BarChart2, RefreshCw } from 'lucide-react'
import Layout from '../components/Layout/Layout'

export default function PowerBI() {
  const [reports,      setReports]      = useState([])
  const [activeReport, setActiveReport] = useState(null)
  const [loading,      setLoading]      = useState(true)
  const [iframeKey,    setIframeKey]    = useState(0)

  useEffect(() => {
    fetch('/api/powerbi/reports/', { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        const list = data.reports || []
        setReports(list)
        const lastId = localStorage.getItem('powerbi-last-report')
        const last   = list.find(r => r.id === lastId)
        setActiveReport(last || list[0] || null)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleTabClick = (report) => {
    setActiveReport(report)
    localStorage.setItem('powerbi-last-report', report.id)
    setIframeKey(k => k + 1)
  }

  return (
    <Layout title="Power BI" breadcrumb="Analytics / Power BI Dashboards">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px 24px', height: 'calc(100vh - 64px)' }}>

        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', color: 'var(--text-muted)', fontSize: '13px', padding: '40px 0' }}>
            <div style={{ width: '18px', height: '18px', border: '2px solid var(--border)', borderTopColor: 'var(--gold)', borderRadius: '50%', animation: 'spin 0.7s linear infinite', flexShrink: 0 }} />
            Chargement...
          </div>
        )}

        {/* Tab bar — only shown when multiple reports exist */}
        {!loading && reports.length > 1 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap', flexShrink: 0 }}>
            {reports.map(r => (
              <button
                key={r.id}
                onClick={() => handleTabClick(r)}
                style={{
                  padding:       '7px 16px',
                  fontSize:      '11px',
                  fontWeight:    '700',
                  fontFamily:    'Rajdhani, sans-serif',
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  borderRadius:  '6px',
                  border:        'none',
                  cursor:        'pointer',
                  transition:    'background 0.15s, color 0.15s',
                  background:    activeReport?.id === r.id ? 'var(--gold)' : 'var(--dark3)',
                  color:         activeReport?.id === r.id ? 'var(--dark)' : 'var(--text-muted)',
                }}
              >
                {r.title}
              </button>
            ))}
            <button
              onClick={() => setIframeKey(k => k + 1)}
              title="Actualiser"
              style={{ marginLeft: 'auto', background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-dim)', padding: '6px', borderRadius: '6px', display: 'flex', alignItems: 'center' }}
            >
              <RefreshCw size={15} />
            </button>
          </div>
        )}

        {/* Iframe container */}
        {!loading && (
          <div style={{ flex: 1, borderRadius: '10px', overflow: 'hidden', border: '1px solid var(--border)', minHeight: 0 }}>
            {activeReport?.embed_url ? (
              <iframe
                key={iframeKey}
                src={activeReport.embed_url}
                title={activeReport.title}
                allowFullScreen
                sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation"
                allow="fullscreen; clipboard-write"
                style={{
                  width:     '100%',
                  height:    '100%',
                  minHeight: 'calc(100vh - 160px)',
                  border:    'none',
                  display:   'block',
                }}
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '16px', height: '100%', padding: '48px', textAlign: 'center' }}>
                <BarChart2 size={48} color="var(--border)" />
                <h3 style={{ color: 'var(--text-muted)', fontSize: '16px', fontWeight: '600', fontFamily: 'Rajdhani, sans-serif', margin: 0 }}>
                  Aucun rapport Power BI configuré
                </h3>
                <p style={{ color: 'var(--text-dim)', fontSize: '13px', maxWidth: '360px', margin: 0 }}>
                  Contactez l'administrateur pour configurer les URL d'intégration Power BI.
                </p>
              </div>
            )}
          </div>
        )}

      </div>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </Layout>
  )
}
