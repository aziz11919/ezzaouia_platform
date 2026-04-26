import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Layout from './Layout/Layout'
import { powerbiAPI } from '../api/powerbi'

export default function PowerBIReport() {
  const { id }    = useParams()
  const navigate  = useNavigate()
  const [report,  setReport]  = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    setLoading(true)
    powerbiAPI.detail(id)
      .then(r => setReport(r.data?.report || null))
      .catch(() => setError('Rapport introuvable ou accès refusé.'))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return (
      <Layout title="Power BI">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', padding: '48px 32px', color: 'var(--text-muted)', fontSize: '13px' }}>
          <Spinner />
          Chargement…
        </div>
      </Layout>
    )
  }

  if (error || !report) {
    return (
      <Layout title="Power BI">
        <div style={{ padding: '48px 32px' }}>
          <p style={{ color: 'var(--text-muted)', fontSize: '14px', marginBottom: '16px' }}>
            {error || 'Rapport introuvable.'}
          </p>
          <BackButton onClick={() => navigate('/powerbi')} />
        </div>
      </Layout>
    )
  }

  return (
    <Layout title="Power BI" breadcrumb={`Analytics / Power BI / ${report.title}`}>
      <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)' }}>

        {/* Thin header strip */}
        <div style={{
          display:      'flex',
          alignItems:   'center',
          gap:          '12px',
          padding:      '10px 24px',
          borderBottom: '1px solid var(--border)',
          flexShrink:   0,
        }}>
          <BackButton onClick={() => navigate('/powerbi')} />
          <span style={{ color: 'var(--gold)', fontFamily: 'Rajdhani, sans-serif', fontWeight: '700', fontSize: '15px', letterSpacing: '0.05em' }}>
            {report.icon && <span style={{ marginRight: '6px' }}>{report.icon}</span>}
            {report.title}
          </span>
          {report.description && (
            <span style={{ color: 'var(--text-muted)', fontSize: '12px', marginLeft: '4px' }}>
              — {report.description}
            </span>
          )}
        </div>

        {/* Iframe fills remaining height */}
        {report.embed_url ? (
          <iframe
            src={report.embed_url}
            title={report.title}
            allowFullScreen
            sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox allow-top-navigation"
            allow="fullscreen; clipboard-write"
            style={{
              flex:         1,
              width:        '100%',
              height:       'calc(100vh - 120px)',
              border:       'none',
              borderRadius: '8px',
              display:      'block',
            }}
          />
        ) : (
          <div style={{ padding: '48px 32px', color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center' }}>
            URL du rapport non configurée.
          </div>
        )}
      </div>
    </Layout>
  )
}

function BackButton({ onClick }) {
  const [hovered, setHovered] = useState(false)
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display:      'inline-flex',
        alignItems:   'center',
        gap:          '6px',
        background:   hovered ? 'var(--dark3)' : 'transparent',
        border:       '1px solid var(--border)',
        color:        hovered ? 'var(--text)' : 'var(--text-muted)',
        borderRadius: '8px',
        padding:      '6px 14px',
        fontSize:     '13px',
        cursor:       'pointer',
        transition:   'background 0.15s, color 0.15s',
        fontFamily:   'inherit',
        flexShrink:   0,
      }}
    >
      <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18"/>
      </svg>
      Retour
    </button>
  )
}

function Spinner() {
  return (
    <>
      <div style={{
        width: '18px', height: '18px',
        border: '2px solid var(--border)',
        borderTopColor: 'var(--gold)',
        borderRadius: '50%',
        animation: 'spin 0.7s linear infinite',
        flexShrink: 0,
      }} />
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </>
  )
}
