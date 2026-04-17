import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import { useTheme } from '../contexts/ThemeContext'
import api from '../api/axios'

export default function SharedSession() {
  const { token }             = useParams()
  const { toggle, isDark }    = useTheme()
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')

  useEffect(() => {
    api.get(`/chatbot/api/shared/${token}/`)
      .then((r) => setData(r.data))
      .catch((e) => setError(e.response?.data?.error || 'Session not found or not shared.'))
      .finally(() => setLoading(false))
  }, [token])

  const session  = data?.session
  const messages = data?.messages || []
  const initial  = session?.user?.username?.[0]?.toUpperCase() || '?'

  return (
    <div style={{ fontFamily: "'Inter', sans-serif", background: 'var(--dark)', color: 'var(--text)', display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>

      {/* Topbar */}
      <div style={{ background: 'var(--dark2)', borderBottom: '1px solid var(--border)', padding: '0 28px', height: 64, display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <img src="/static/img/logomaretap.png" alt="MARETAP" style={{ width: 30, height: 30 }} onError={(e) => { e.currentTarget.style.display = 'none' }} />
            <span style={{ fontFamily: "'Rajdhani', sans-serif", fontSize: 17, fontWeight: 600 }}>
              EZZ<span style={{ color: 'var(--gold)' }}>AOUIA</span> IA
            </span>
          </div>
          {session && (
            <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>
              Shared by{' '}
              <strong style={{ color: 'var(--text-muted)' }}>{session.user.display_name}</strong>
              {session.shared_at && <> · {session.shared_at}</>}
              {' · '}
              <em>{session.title.length > 45 ? session.title.slice(0, 45) + '…' : session.title}</em>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={toggle}
            style={{ width: 34, height: 34, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: 8, border: '1px solid var(--border-soft)', background: 'transparent', color: 'var(--text-muted)', cursor: 'pointer' }}
          >
            {isDark ? (
              <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            ) : (
              <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 5, padding: '4px 10px', background: 'rgba(224,85,85,0.1)', border: '1px solid rgba(224,85,85,0.25)', borderRadius: 6, fontSize: 11, color: 'var(--red)', fontWeight: 500 }}>
            <svg width="11" height="11" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
            Read-only
          </div>
        </div>
      </div>

      {/* Messages area */}
      <div style={{ flex: 1, maxWidth: 860, width: '100%', margin: '0 auto', padding: '32px 24px', display: 'flex', flexDirection: 'column', gap: 22 }}>
        {loading ? (
          <div style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '60px 0', fontSize: 14 }}>Loading…</div>
        ) : error ? (
          <div style={{ textAlign: 'center', color: 'var(--red)', padding: '60px 0', fontSize: 14 }}>
            <div style={{ marginBottom: 12 }}>{error}</div>
            <Link to="/login" style={{ color: 'var(--gold)', textDecoration: 'none', fontSize: 13 }}>← Go to login</Link>
          </div>
        ) : messages.length === 0 ? (
          <div style={{ textAlign: 'center', color: 'var(--text-dim)', padding: '60px 0', fontSize: 14 }}>
            This session does not contain messages yet.
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {/* User bubble */}
              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', maxWidth: '85%', flexDirection: 'row-reverse', marginLeft: 'auto' }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 600, flexShrink: 0, fontFamily: "'Rajdhani', sans-serif", background: 'var(--dark4)', color: 'var(--gold)', border: '1px solid var(--border)' }}>
                  {initial}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ padding: '14px 18px', borderRadius: '10px 2px 10px 10px', fontSize: 13, lineHeight: 1.8, background: 'var(--dark4)', border: '1px solid var(--border)', color: 'var(--text)', whiteSpace: 'pre-wrap' }}>
                    {msg.question}
                  </div>
                </div>
              </div>

              {/* Bot bubble */}
              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start', maxWidth: '85%', marginRight: 'auto' }}>
                <div style={{ width: 32, height: 32, borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 13, fontWeight: 600, flexShrink: 0, fontFamily: "'Rajdhani', sans-serif", background: 'rgba(201,168,76,0.12)', color: 'var(--gold)', border: '1px solid var(--border)' }}>
                  IA
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ padding: '14px 18px', borderRadius: '2px 10px 10px 10px', fontSize: 13, lineHeight: 1.8, background: 'var(--dark2)', border: '1px solid var(--border-soft)', color: 'var(--text)' }} className="shared-md">
                    <ReactMarkdown>{msg.answer}</ReactMarkdown>
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <svg width="11" height="11" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    {msg.duration.toFixed(2)}s · {msg.created_at}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer */}
      <div style={{ background: 'var(--dark2)', borderTop: '1px solid var(--border)', padding: '16px 28px', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 16, flexShrink: 0 }}>
        <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>This session is read-only.</span>
        <Link
          to="/chatbot/new"
          style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '9px 18px', background: 'rgba(201,168,76,0.12)', border: '1px solid var(--border)', borderRadius: 7, color: 'var(--gold)', fontSize: 13, fontWeight: 500, textDecoration: 'none' }}
        >
          <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Open a new conversation
        </Link>
      </div>
    </div>
  )
}
