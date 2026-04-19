import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Layout from './Layout/Layout'
import { powerbiAPI } from '../api/powerbi'

export default function PowerBIReport() {
  const { id }   = useParams()
  const navigate = useNavigate()
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

  const openReport = (fullscreen = false) => {
    const url = report.embed_url
    if (fullscreen) {
      const w = window.open(url, '_blank', 'fullscreen=yes,scrollbars=yes,resizable=yes')
      if (w) w.focus()
    } else {
      window.open(url, '_blank', 'noopener,noreferrer')
    }
  }

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
      <div style={{ padding: '32px', maxWidth: '760px' }}>

        {/* Header card */}
        <div style={{
          background:   'var(--dark2)',
          border:       '1px solid var(--border)',
          borderRadius: '14px',
          padding:      '32px 36px',
          marginBottom: '20px',
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '20px' }}>
            <div style={{
              fontSize:     '42px',
              lineHeight:   1,
              background:   'var(--dark3)',
              border:       '1px solid var(--border)',
              borderRadius: '12px',
              padding:      '14px 16px',
              flexShrink:   0,
            }}>
              {report.icon}
            </div>
            <div style={{ flex: 1 }}>
              <h1 style={{
                color:         'var(--gold)',
                fontFamily:    'Rajdhani, sans-serif',
                fontWeight:    '700',
                fontSize:      '22px',
                letterSpacing: '0.06em',
                margin:        '0 0 8px',
              }}>
                {report.title}
              </h1>
              {report.description && (
                <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: '1.6', margin: 0 }}>
                  {report.description}
                </p>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '14px' }}>
                <div style={{
                  width:        '7px',
                  height:       '7px',
                  borderRadius: '50%',
                  background:   'var(--green)',
                  boxShadow:    '0 0 6px var(--green)',
                }} />
                <span style={{ color: 'var(--text-dim)', fontSize: '11px', letterSpacing: '0.04em' }}>
                  Power BI · MARETAP S.A. · CPF Zarzis
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Notice card */}
        <div style={{
          background:   'rgba(201,168,76,0.05)',
          border:       '1px solid rgba(201,168,76,0.2)',
          borderRadius: '10px',
          padding:      '14px 18px',
          marginBottom: '24px',
          display:      'flex',
          gap:          '10px',
          alignItems:   'flex-start',
        }}>
          <svg width="16" height="16" fill="none" stroke="var(--gold)" viewBox="0 0 24 24" style={{ flexShrink: 0, marginTop: '1px' }}>
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
          </svg>
          <span style={{ color: 'var(--text-muted)', fontSize: '12px', lineHeight: '1.6' }}>
            Ce rapport s'ouvre dans Microsoft Power BI. Connectez-vous avec votre compte MARETAP
            pour accéder aux données en temps réel.
          </span>
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <ActionButton
            primary
            onClick={() => openReport(false)}
            icon={
              <svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"/>
              </svg>
            }
          >
            Ouvrir le rapport
          </ActionButton>

          <ActionButton
            onClick={() => openReport(true)}
            icon={
              <svg width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9M3.75 20.25v-4.5m0 4.5h4.5m-4.5 0L9 15M20.25 3.75h-4.5m4.5 0v4.5m0-4.5L15 9m5.25 11.25h-4.5m4.5 0v-4.5m0 4.5L15 15"/>
              </svg>
            }
          >
            Voir en plein écran
          </ActionButton>

          <BackButton onClick={() => navigate('/powerbi')} />
        </div>
      </div>
    </Layout>
  )
}

/* ── Sub-components ─────────────────────────── */

function ActionButton({ children, onClick, icon, primary = false }) {
  const [hovered, setHovered] = useState(false)
  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display:       'inline-flex',
        alignItems:    'center',
        gap:           '8px',
        background:    primary
          ? (hovered ? 'var(--gold-light)' : 'var(--gold)')
          : (hovered ? 'var(--dark3)' : 'var(--dark2)'),
        color:         primary ? 'var(--dark)' : (hovered ? 'var(--text)' : 'var(--text-muted)'),
        border:        primary ? 'none' : '1px solid var(--border)',
        borderRadius:  '8px',
        padding:       '10px 20px',
        fontSize:      '13px',
        fontWeight:    '600',
        fontFamily:    'Rajdhani, sans-serif',
        letterSpacing: '0.05em',
        cursor:        'pointer',
        transition:    'background 0.15s, color 0.15s',
      }}
    >
      {icon}
      {children}
    </button>
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
        padding:      '10px 16px',
        fontSize:     '13px',
        cursor:       'pointer',
        transition:   'background 0.15s, color 0.15s',
        fontFamily:   'inherit',
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
