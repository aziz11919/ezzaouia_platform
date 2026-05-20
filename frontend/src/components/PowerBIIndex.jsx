import { useState, useEffect } from 'react'
import Layout from './Layout/Layout'
import { powerbiAPI } from '../api/powerbi'

const LS_KEY = 'powerbi-last-report'

export default function PowerBIIndex() {
  const [reports,  setReports]  = useState([])
  const [selected, setSelected] = useState(null)
  const [loading,  setLoading]  = useState(true)
  const [error,    setError]    = useState(null)

  useEffect(() => {
    powerbiAPI.reports()
      .then(r => {
        const list = r.data?.reports || []
        setReports(list)
        if (list.length > 0) {
          const lastId  = localStorage.getItem(LS_KEY)
          const initial = list.find(r => r.id === lastId) || list[0]
          setSelected(initial)
        }
      })
      .catch(() => setError('Impossible de charger les rapports.'))
      .finally(() => setLoading(false))
  }, [])

  const handleSelect = (report) => {
    setSelected(report)
    localStorage.setItem(LS_KEY, report.id)
  }

  return (
    <Layout title="Power BI" breadcrumb="Analytics / Power BI">
      <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)' }}>

        {/* Top bar with report selector */}
        {reports.length > 1 && (
          <div style={{
            display:    'flex',
            gap:        '8px',
            padding:    '12px 24px',
            borderBottom: '1px solid var(--border)',
            flexShrink: 0,
            flexWrap:   'wrap',
          }}>
            {reports.map(r => (
              <button
                key={r.id}
                onClick={() => handleSelect(r)}
                style={{
                  background:    selected?.id === r.id ? 'var(--gold)' : 'var(--dark2)',
                  color:         selected?.id === r.id ? 'var(--dark)' : 'var(--text-muted)',
                  border:        `1px solid ${selected?.id === r.id ? 'var(--gold)' : 'var(--border)'}`,
                  borderRadius:  '6px',
                  padding:       '6px 14px',
                  fontSize:      '12px',
                  fontWeight:    '600',
                  fontFamily:    'Rajdhani, sans-serif',
                  letterSpacing: '0.05em',
                  cursor:        'pointer',
                  transition:    'background 0.15s, color 0.15s',
                }}
              >
                {r.title}
              </button>
            ))}
          </div>
        )}

        {/* Content area */}
        <div style={{ flex: 1, overflow: 'hidden', position: 'relative' }}>
          {loading && <LoadingState />}

          {!loading && error && (
            <div style={{ padding: '48px 32px' }}>
              <div style={{
                color:        'var(--red)',
                background:   'rgba(224,85,85,0.08)',
                border:       '1px solid rgba(224,85,85,0.2)',
                borderRadius: '8px',
                padding:      '14px 18px',
                fontSize:     '13px',
              }}>
                {error}
              </div>
            </div>
          )}

          {!loading && !error && reports.length === 0 && (
            <div style={{ padding: '48px 32px', color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center' }}>
              Aucun rapport disponible.
            </div>
          )}

          {!loading && selected?.embed_url && (
            <iframe
              key={selected.id}
              src={selected.embed_url}
              title={selected.title}
              allowFullScreen
              sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox"
              allow="fullscreen"
              style={{
                width:        '100%',
                height:       'calc(100vh - 120px)',
                border:       'none',
                borderRadius: '8px',
                display:      'block',
              }}
            />
          )}
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </Layout>
  )
}

function LoadingState() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text-muted)', fontSize: '13px', padding: '48px 32px' }}>
      <div style={{ width: '20px', height: '20px', border: '2px solid var(--border)', borderTopColor: 'var(--gold)', borderRadius: '50%', animation: 'spin 0.7s linear infinite', flexShrink: 0 }} />
      Chargement…
    </div>
  )
}
