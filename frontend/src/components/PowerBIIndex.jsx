import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Layout from './Layout/Layout'
import { powerbiAPI } from '../api/powerbi'

export default function PowerBIIndex() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    powerbiAPI.list()
      .then(r => setReports(r.data?.reports || []))
      .catch(() => setError('Failed to load reports.'))
      .finally(() => setLoading(false))
  }, [])

  return (
    <Layout title="Power BI" breadcrumb="Analytics / Power BI">
      <div style={{ padding: '28px 32px' }}>

        <div style={{ marginBottom: '28px' }}>
          <h1 style={{ color: 'var(--gold)', fontFamily: 'Rajdhani, sans-serif', fontSize: '22px', fontWeight: '700', letterSpacing: '0.06em', margin: 0 }}>
            📊 Power BI Reports
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '13px', marginTop: '6px' }}>
            Interactive dashboards connected to EZZAOUIA production data
          </p>
        </div>

        {loading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--text-muted)', fontSize: '13px', padding: '40px 0' }}>
            <div style={{ width: '20px', height: '20px', border: '2px solid var(--border)', borderTopColor: 'var(--gold)', borderRadius: '50%', animation: 'spin 0.7s linear infinite' }} />
            Loading reports...
          </div>
        )}

        {error && (
          <div style={{ color: 'var(--red)', background: 'rgba(224,85,85,0.08)', border: '1px solid rgba(224,85,85,0.2)', borderRadius: '8px', padding: '14px 18px', fontSize: '13px' }}>
            {error}
          </div>
        )}

        {!loading && !error && reports.length === 0 && (
          <div style={{ color: 'var(--text-muted)', fontSize: '13px', padding: '40px 0', textAlign: 'center' }}>
            No reports available for your role.
          </div>
        )}

        {!loading && reports.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(270px, 1fr))', gap: '16px' }}>
            {reports.map(report => (
              <ReportCard key={report.id} report={report} onOpen={() => navigate(`/powerbi/${report.id}`)} />
            ))}
          </div>
        )}
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </Layout>
  )
}

function ReportCard({ report, onOpen }) {
  const [hovered, setHovered] = useState(false)
  return (
    <div
      onClick={onOpen}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background:    'var(--dark2)',
        border:        `1px solid ${hovered ? 'var(--gold)' : 'var(--border)'}`,
        borderRadius:  '12px',
        padding:       '24px',
        cursor:        'pointer',
        transition:    'border-color 0.18s, transform 0.18s, box-shadow 0.18s',
        transform:     hovered ? 'translateY(-3px)' : 'none',
        boxShadow:     hovered ? '0 8px 24px rgba(201,168,76,0.1)' : 'none',
        display:       'flex',
        flexDirection: 'column',
        gap:           '10px',
      }}
    >
      <div style={{ fontSize: '36px', lineHeight: 1 }}>{report.icon}</div>

      <div style={{ color: 'var(--gold)', fontFamily: 'Rajdhani, sans-serif', fontWeight: '700', fontSize: '16px', letterSpacing: '0.04em' }}>
        {report.title}
      </div>

      {report.description ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '12px', lineHeight: '1.55', flexGrow: 1 }}>
          {report.description}
        </div>
      ) : (
        <div style={{ flexGrow: 1 }} />
      )}

      <div style={{ marginTop: '4px' }}>
        <span style={{
          display:       'inline-flex',
          alignItems:    'center',
          gap:           '6px',
          background:    hovered ? 'var(--gold)' : 'var(--gold-dim)',
          color:         hovered ? 'var(--dark)' : 'var(--gold)',
          borderRadius:  '6px',
          padding:       '7px 14px',
          fontSize:      '12px',
          fontWeight:    '600',
          fontFamily:    'Rajdhani, sans-serif',
          letterSpacing: '0.05em',
          transition:    'background 0.18s, color 0.18s',
        }}>
          View Report
          <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"/>
          </svg>
        </span>
      </div>
    </div>
  )
}
