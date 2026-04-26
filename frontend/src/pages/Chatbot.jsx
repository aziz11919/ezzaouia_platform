import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Chart, registerables } from 'chart.js'
import { useTheme } from '../contexts/ThemeContext'
import { useAuth } from '../contexts/AuthContext'
import { chatbotAPI } from '../api/chatbot'
import './Chatbot.css'

Chart.register(...registerables)

/* ─────────── helpers ─────────── */
function trunc(s, n) { return s && s.length > n ? s.slice(0, n - 1) + '…' : (s || '') }
function getDocExt(name) {
  const ext = (name || '').split('.').pop().toLowerCase()
  if (ext === 'pdf') return 'pdf'
  if (['docx','doc'].includes(ext)) return 'docx'
  if (['xlsx','xls'].includes(ext)) return 'xlsx'
  return 'pdf'
}
function showToast(msg, color = 'green') {
  const t = document.createElement('div')
  t.style.cssText = `position:fixed;bottom:24px;right:24px;padding:11px 18px;background:var(--dark2);border:1px solid var(--${color});border-radius:8px;color:var(--${color});font-size:13px;z-index:2000;box-shadow:0 4px 20px rgba(0,0,0,0.3);`
  t.textContent = msg
  document.body.appendChild(t)
  setTimeout(() => t.remove(), 3000)
}

/* ─────────── BotChart component ─────────── */
function BotChart({ chartData }) {
  const canvasRef = useRef(null)
  const chartRef  = useRef(null)

  useEffect(() => {
    if (!canvasRef.current || !chartData?.labels?.length) return
    const isDark  = document.documentElement.getAttribute('data-theme') !== 'light'
    const txtClr  = isDark ? '#6B85A8' : '#4A5568'
    const gridClr = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)'

    if (chartRef.current) chartRef.current.destroy()
    chartRef.current = new Chart(canvasRef.current, {
      data: { labels: chartData.labels, datasets: chartData.datasets || [] },
      options: {
        responsive: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { labels: { color: txtClr, font: { family: 'Inter', size: 11 }, boxWidth: 12 } },
        },
        scales: {
          x:  { ticks: { color: txtClr, font: { size: 10 }, maxRotation: 45 }, grid: { color: gridClr } },
          y:  { type: 'linear', position: 'left',  ticks: { color: txtClr, font: { size: 10 } }, grid: { color: gridClr },
                title: { display: true, text: 'Oil (STB)', color: '#C9A84C', font: { size: 11 } } },
          y1: { type: 'linear', position: 'right', ticks: { color: txtClr, font: { size: 10 } }, grid: { drawOnChartArea: false },
                title: { display: true, text: 'BSW (%)', color: '#E05555', font: { size: 11 } }, min: 0, max: 100 },
        },
      },
    })
    return () => { chartRef.current?.destroy() }
  }, [chartData])

  if (!chartData?.labels?.length) return null
  return (
    <div className="chart-container">
      <div className="chart-header">
        <div className="chart-title">
          📊 Trend · {chartData.well_code}{chartData.well_name ? ` — ${chartData.well_name}` : ''}
        </div>
      </div>
      <canvas ref={canvasRef} height={200} />
    </div>
  )
}

/* ─────────── CommentZone component ─────────── */
function CommentZone({ messageId, open, onClose }) {
  const [items,    setItems]    = useState(null)
  const [text,     setText]     = useState('')
  const [isPublic, setIsPublic] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open || items !== null) return
    chatbotAPI.getComments(messageId)
      .then(r => setItems(r.data?.comments || []))
      .catch(() => setItems([]))
  }, [open, messageId, items])

  async function submitComment() {
    const content = text.trim()
    if (!content) return
    setSubmitting(true)
    try {
      await chatbotAPI.addComment({ message_id: messageId, content, is_public: isPublic })
      setText('')
      setItems(null)
    } catch { /* silent */ }
    finally { setSubmitting(false) }
  }

  if (!open) return null
  return (
    <div className="comment-zone">
      <div className="comment-list">
        {items === null
          ? <div className="comment-empty">Loading…</div>
          : items.length === 0
          ? <div className="comment-empty">No comments yet.</div>
          : items.map((c, i) => (
            <div key={i} className="comment-item">
              <div className="comment-item-header">
                <span className="comment-author">{c.author}</span>
                <span className="comment-date">{c.created_at}</span>
                {!c.is_public && <span title="Private">🔒</span>}
              </div>
              <div className="comment-text">{c.content}</div>
            </div>
          ))
        }
      </div>
      <div className="comment-form">
        <textarea
          className="comment-textarea"
          rows={2}
          placeholder="Your comment on this response..."
          maxLength={500}
          value={text}
          onChange={e => setText(e.target.value)}
        />
        <div className="comment-form-row">
          <label className="comment-visibility-toggle">
            <input type="checkbox" checked={isPublic} onChange={e => setIsPublic(e.target.checked)} />
            Team-visible
          </label>
          <button className="btn-add-comment" onClick={submitComment} disabled={submitting}>
            {submitting ? 'Sending…' : 'Add'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ─────────── BotMessage component ─────────── */
function BotMessage({ msg, initials, onSuggest }) {
  const [rating,       setRating]       = useState(msg.is_satisfied ?? null)
  const [commentsOpen, setCommentsOpen] = useState(false)

  async function rate(value) {
    if (!msg.messageId) return
    try {
      await chatbotAPI.rate({ message_id: msg.messageId, rating: value })
      setRating(value)
    } catch { /* silent */ }
  }

  return (
    <div className="msg-row bot">
      <div className="msg-avatar bot">AI</div>
      <div className="msg-content">
        <div className="msg-bubble">
          {msg.pending
            ? <div className="thinking-dots"><span/><span/><span/></div>
            : msg.error
            ? <span style={{ color: 'var(--red)' }}>{msg.answer}</span>
            : msg.stopped
            ? <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>Generation stopped.</span>
            : <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  table: ({node, ...props}) => (
                    <table style={{
                      borderCollapse: 'collapse',
                      width: '100%',
                      margin: '12px 0',
                      fontSize: '13px'
                    }} {...props} />
                  ),
                  th: ({node, ...props}) => (
                    <th style={{
                      padding: '8px 12px',
                      borderBottom: '2px solid var(--gold)',
                      textAlign: 'left',
                      color: 'var(--gold)',
                      fontWeight: '600'
                    }} {...props} />
                  ),
                  td: ({node, ...props}) => (
                    <td style={{
                      padding: '7px 12px',
                      borderBottom: '1px solid var(--border-soft)'
                    }} {...props} />
                  ),
                  strong: ({node, ...props}) => (
                    <strong style={{color: 'var(--gold-light)'}} {...props} />
                  ),
                  h2: ({node, ...props}) => (
                    <h2 style={{
                      fontSize: '16px',
                      fontWeight: '600',
                      color: 'var(--gold)',
                      margin: '16px 0 8px',
                      fontFamily: 'Rajdhani, sans-serif'
                    }} {...props} />
                  ),
                  h3: ({node, ...props}) => (
                    <h3 style={{
                      fontSize: '14px',
                      fontWeight: '600',
                      color: 'var(--text)',
                      margin: '12px 0 6px'
                    }} {...props} />
                  ),
                  blockquote: ({node, ...props}) => (
                    <blockquote style={{
                      borderLeft: '3px solid var(--gold)',
                      paddingLeft: '12px',
                      margin: '8px 0',
                      color: 'var(--text-muted)',
                      fontStyle: 'italic'
                    }} {...props} />
                  ),
                  ul: ({node, ...props}) => (
                    <ul style={{paddingLeft: '20px', margin: '6px 0'}} {...props} />
                  ),
                  li: ({node, ...props}) => (
                    <li style={{margin: '3px 0', lineHeight: '1.6'}} {...props} />
                  ),
                  hr: ({node, ...props}) => (
                    <hr style={{border: 'none', borderTop: '1px solid var(--border)', margin: '12px 0'}} {...props} />
                  ),
                  em: ({node, ...props}) => (
                    <em style={{color: 'var(--text-dim)', fontSize: '12px'}} {...props} />
                  ),
                }}
              >
                {msg.answer || ''}
              </ReactMarkdown>
          }
        </div>

        {!msg.pending && !msg.error && !msg.stopped && (
          <>
            {msg.duration != null && (
              <div className="msg-meta">
                <svg width="11" height="11" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                {msg.duration}s
                {msg.createdAt && <span>· {msg.createdAt}</span>}
              </div>
            )}

            {msg.messageId && (
              <div className="msg-rating">
                <span className="rating-label">Rating:</span>
                <button className={`rate-btn up${rating === true ? ' active' : ''}`} onClick={() => rate(true)} title="Satisfied">👍</button>
                <button className={`rate-btn down${rating === false ? ' active' : ''}`} onClick={() => rate(false)} title="Unsatisfied">👎</button>
              </div>
            )}

            {msg.messageId && (
              <button className="comment-toggle-btn" onClick={() => setCommentsOpen(v => !v)}>
                💬 Comments
              </button>
            )}

            {msg.messageId && (
              <CommentZone messageId={msg.messageId} open={commentsOpen} onClose={() => setCommentsOpen(false)} />
            )}

            {msg.chartData && <BotChart chartData={msg.chartData} />}

            {msg.suggestions?.length > 0 && (
              <div className="suggestions-section">
                <div className="suggestions-label">
                  <svg width="11" height="11" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                  </svg>
                  Suggested questions
                </div>
                <div className="suggestions-chips">
                  {msg.suggestions.map((s, i) => (
                    <button key={i} className="suggestion-chip" onClick={() => onSuggest(s)}>{s}</button>
                  ))}
                </div>
              </div>
            )}

            {msg.relatedComments?.length > 0 && (
              <div className="related-comments-section">
                <div className="related-comments-title">
                  <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M17 8h2a2 2 0 012 2v6a2 2 0 01-2 2h-2v4l-4-4H9a1.994 1.994 0 01-1.414-.586m0 0L11 14h4a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2v4l.586-.586z"/>
                  </svg>
                  Team comments on similar questions
                </div>
                {msg.relatedComments.map((item, i) => (
                  <div key={i} className="related-comment-block">
                    <div className="related-comment-q">"{item.question}"</div>
                    {item.comments?.map((c, j) => (
                      <div key={j} className="related-comment-entry">
                        <span className="related-comment-author">{c.author} : </span>
                        {c.content}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

/* ─────────── DeleteModal component ─────────── */
function DeleteModal({ sessionId, onConfirm, onCancel }) {
  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onCancel()}>
      <div className="modal-box">
        <h3>Delete conversation?</h3>
        <p>This action is irreversible. All messages will be lost.</p>
        <div className="modal-actions">
          <button className="btn-cancel" onClick={onCancel}>Cancel</button>
          <button className="btn-confirm-delete" onClick={() => onConfirm(sessionId)}>Delete</button>
        </div>
      </div>
    </div>
  )
}

/* ─────────── ShareModal component ─────────── */
function ShareModal({ sessionId, onClose }) {
  const [users,    setUsers]    = useState(null)
  const [search,   setSearch]   = useState('')
  const [selected, setSelected] = useState([])
  const [sending,  setSending]  = useState(false)

  useEffect(() => {
    chatbotAPI.getUsers()
      .then(r => setUsers(r.data?.users || []))
      .catch(() => setUsers([]))
  }, [])

  const filtered = users === null ? [] : search
    ? users.filter(u => (u.full_name + u.username).toLowerCase().includes(search.toLowerCase()))
    : users

  function toggle(id) {
    setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  async function doShare() {
    if (!selected.length) { alert('Select at least one user.'); return }
    setSending(true)
    try {
      const r = await chatbotAPI.shareWithUsers(sessionId, selected)
      onClose()
      showToast(`✓ Session shared with ${r.data?.shared_count || selected.length} user(s)`, 'green')
    } catch { alert('Network error.') }
    finally { setSending(false) }
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal-box share-modal-box">
        <h3 style={{ textAlign: 'left' }}>Share conversation</h3>
        <p style={{ textAlign: 'left' }}>Select colleagues to share this session with (read-only).</p>
        <input
          type="text"
          className="user-search-input"
          placeholder="Search a user..."
          value={search}
          onChange={e => setSearch(e.target.value)}
        />
        <div className="user-list">
          {users === null
            ? <div style={{ color: 'var(--text-dim)', fontSize: 12, padding: '12px 0', textAlign: 'center' }}>Loading…</div>
            : filtered.length === 0
            ? <div style={{ color: 'var(--text-dim)', fontSize: 12, padding: '8px', textAlign: 'center' }}>No users found.</div>
            : filtered.map(u => (
              <label key={u.id} className={`user-item${selected.includes(u.id) ? ' selected' : ''}`}>
                <input type="checkbox" checked={selected.includes(u.id)} onChange={() => toggle(u.id)} />
                <div className="user-item-info">
                  <div className="user-item-name">{u.full_name}</div>
                  <div className="user-item-sub">@{u.username}{u.role ? ` · ${u.role}` : ''}</div>
                </div>
              </label>
            ))
          }
        </div>
        <div className="modal-actions" style={{ marginTop: 14 }}>
          <button className="btn-cancel" onClick={onClose}>Cancel</button>
          <button className="btn-confirm-share" onClick={doShare} disabled={sending}>
            {sending ? 'Sending…' : 'Share'}
          </button>
        </div>
      </div>
    </div>
  )
}

/* ─────────── SessionItem component ─────────── */
function SessionItem({ session, isActive, onNavigate, onDelete, onShare }) {
  const [renaming, setRenaming] = useState(false)
  const [renameVal, setRenameVal] = useState(session.title || '')
  const inputRef = useRef(null)

  useEffect(() => {
    if (renaming) inputRef.current?.focus()
  }, [renaming])

  async function saveRename() {
    const newTitle = renameVal.trim()
    setRenaming(false)
    if (!newTitle || newTitle === session.title) return
    try {
      await chatbotAPI.renameSession(session.id, newTitle)
      session.title = newTitle
    } catch { /* silent */ }
  }

  return (
    <div className={`session-item${isActive ? ' active' : ''}`} onClick={() => !renaming && onNavigate(session.id)}>
      <div className="session-info">
        {renaming
          ? <input
              ref={inputRef}
              className="session-title-input"
              value={renameVal}
              onChange={e => setRenameVal(e.target.value)}
              onBlur={saveRename}
              onKeyDown={e => {
                if (e.key === 'Enter') { e.preventDefault(); inputRef.current?.blur() }
                if (e.key === 'Escape') { setRenaming(false) }
              }}
              onClick={e => e.stopPropagation()}
              maxLength={200}
            />
          : <div className="session-title">{trunc(session.title || 'Unnamed', 38)}</div>
        }
        <div className="session-date">{session.created_at || ''}</div>
      </div>
      <div className="session-actions">
        <button className="session-action-btn" title="Rename" onClick={e => { e.stopPropagation(); setRenaming(true); setRenameVal(session.title || '') }}>
          <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125"/>
          </svg>
        </button>
        <button className="session-action-btn" title="Share" onClick={e => { e.stopPropagation(); onShare(session.id) }}>
          <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"/>
          </svg>
        </button>
        <button className="session-action-btn delete" title="Delete" onClick={e => { e.stopPropagation(); onDelete(session.id) }}>
          <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0"/>
          </svg>
        </button>
      </div>
    </div>
  )
}

/* ─────────── Main Chatbot component ─────────── */
const SUGGESTIONS = [
  'Analyze EZZAOUIA field performance',
  'What are the top 5 producing wells?',
  'Analyze field WCT and GOR',
  'List all active wells with their status',
]

export default function Chatbot() {
  const { sessionId } = useParams()
  const navigate      = useNavigate()
  const { toggle: toggleTheme, isDark } = useTheme()
  const { user, logout } = useAuth()

  const effectiveSessionId = sessionId && sessionId !== 'new' ? parseInt(sessionId) : null

  const [sessions,       setSessions]       = useState([])
  const [messages,       setMessages]       = useState([])
  const [activeSession,  setActiveSession]  = useState(null)
  const [input,          setInput]          = useState('')
  const [sending,        setSending]        = useState(false)
  const [loadingSess,    setLoadingSess]    = useState(true)
  const [loadingMsgs,    setLoadingMsgs]    = useState(false)
  const [activeDocIds,   setActiveDocIds]   = useState([])
  const [activeDocNames, setActiveDocNames] = useState([])
  const [uploadStatus,   setUploadStatus]   = useState('')
  const [fileNotifs,     setFileNotifs]     = useState([])
  const [morningSugs,    setMorningSugs]    = useState(null)
  const [sharedWithMe,   setSharedWithMe]   = useState([])
  const [deleteModal,    setDeleteModal]    = useState(null)
  const [shareModal,     setShareModal]     = useState(null)

  const messagesEndRef = useRef(null)
  const abortRef       = useRef(null)
  const fileInputRef   = useRef(null)
  const textareaRef    = useRef(null)

  const initials = [user?.first_name?.[0], user?.last_name?.[0]].filter(Boolean).join('').toUpperCase()
    || user?.username?.[0]?.toUpperCase() || '?'
  const displayName = user
    ? (user.first_name && user.last_name ? `${user.first_name} ${user.last_name}` : user.username)
    : ''

  /* Load sessions */
  useEffect(() => {
    chatbotAPI.getSessions()
      .then(r => setSessions(r.data?.sessions || []))
      .catch(console.error)
      .finally(() => setLoadingSess(false))
  }, [])

  /* Load messages */
  useEffect(() => {
    if (!effectiveSessionId) {
      setMessages([]); setActiveSession(null); return
    }
    setLoadingMsgs(true)
    chatbotAPI.getMessages(effectiveSessionId)
      .then(r => {
        const msgs = (r.data?.messages || []).flatMap(m => [
          { id: `u-${m.id}`, type: 'user', question: m.question },
          { id: `b-${m.id}`, type: 'bot', answer: m.answer, duration: m.duration,
            createdAt: m.created_at, messageId: m.id, is_satisfied: m.is_satisfied ?? null },
        ])
        setMessages(msgs)
        setActiveSession({ id: effectiveSessionId, title: r.data?.title })
      })
      .catch(console.error)
      .finally(() => setLoadingMsgs(false))
  }, [effectiveSessionId])

  /* Auto-scroll */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  /* Morning suggestions */
  useEffect(() => {
    chatbotAPI.getSuggestions()
      .then(r => { if (r.data?.suggestions?.length) setMorningSugs(r.data) })
      .catch(() => {})
  }, [])

  /* Shared with me */
  useEffect(() => {
    chatbotAPI.getSharedWithMe()
      .then(r => setSharedWithMe(r.data?.shared_sessions || []))
      .catch(() => {})
  }, [])

  /* Pre-attach document from ?doc_id= query param (from Library "Ask" button) */
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const docId = params.get('doc_id')
    if (!docId || !/^\d+$/.test(docId)) return
    window.history.replaceState({}, '', window.location.pathname)
    fetch(`/chatbot/doc-info/?doc_id=${docId}`, { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        const doc = (data.docs || [])[0]
        if (doc) {
          setActiveDocIds([doc.id])
          setActiveDocNames([doc.name])
        }
      })
      .catch(() => {})
  }, [])

  /* Send message */
  const handleSend = useCallback(async (text) => {
    const question = (text || input).trim()
    if (!question || sending) return

    abortRef.current = new AbortController()
    setSending(true)
    if (!text) setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'

    const tempId = Date.now()
    setMessages(prev => [
      ...prev,
      { id: `u-${tempId}`, type: 'user', question },
      { id: `b-${tempId}`, type: 'bot', pending: true },
    ])

    try {
      const payload = { question, session_id: activeSession?.id || null }
      if (activeDocIds.length > 0) payload.doc_ids = activeDocIds
      if (activeDocNames.length > 0) payload.filename = activeDocNames[0]

      const r = await chatbotAPI.ask(payload)
      const data = r.data

      const rawAnswer =
        typeof data?.answer   === 'string' ? data.answer   :
        typeof data?.response === 'string' ? data.response :
        typeof data?.reponse  === 'string' ? data.reponse  : ''

      if (!activeSession && data.session_id) {
        const newSess = { id: data.session_id, title: question.slice(0, 60), created_at: 'Just now' }
        setActiveSession(newSess)
        setSessions(prev => [newSess, ...prev])
        navigate(`/chatbot/${data.session_id}`, { replace: true })
      }

      setMessages(prev => prev.map(m =>
        m.id === `b-${tempId}` ? {
          ...m, pending: false,
          answer: data.stopped ? null : (rawAnswer.trim() || 'No answer returned.'),
          stopped: data.stopped || false,
          error: data.error ? `Error: ${data.error}` : null,
          duration: data.duration,
          messageId: data.message_id,
          chartData: data.chart_data || null,
          suggestions: data.suggestions || [],
          relatedComments: data.related_comments || [],
        } : m
      ))
    } catch (e) {
      setMessages(prev => prev.map(m =>
        m.id === `b-${tempId}` ? {
          ...m, pending: false,
          stopped: e.name === 'AbortError',
          error: e.name === 'AbortError' ? null : (e.response?.data?.error || e.message),
          answer: e.name === 'AbortError' ? null : `Error: ${e.response?.data?.error || e.message}`,
        } : m
      ))
    } finally {
      setSending(false)
      abortRef.current = null
    }
  }, [input, sending, activeSession, activeDocIds, activeDocNames, navigate])

  function stopGeneration() {
    chatbotAPI.stopGeneration().catch(() => {})
    abortRef.current?.abort()
  }

  /* Delete session */
  async function confirmDelete(id) {
    try {
      await chatbotAPI.deleteSession(id)
      setSessions(prev => prev.filter(s => s.id !== id))
      setDeleteModal(null)
      if (activeSession?.id === id) navigate('/chatbot', { replace: true })
    } catch { alert('Delete failed.') }
  }

  /* File upload */
  async function handleFileUpload(e) {
    const files = Array.from(e.target.files)
    if (!files.length) return
    setUploadStatus(`Indexing ${files.length} file(s)...`)
    let success = 0, errors = 0
    for (const file of files) {
      try {
        const fd = new FormData()
        fd.append('file', file)
        const r = await chatbotAPI.upload(fd)
        const data = r.data
        if (data.error) { errors++; continue }
        if (!activeDocIds.includes(data.doc_id)) {
          setActiveDocIds(prev => [...prev, data.doc_id])
          setActiveDocNames(prev => [...prev, data.filename])
        }
        success++
      } catch { errors++ }
    }
    setUploadStatus('')
    const notif = `${success} file(s) indexed successfully.${errors > 0 ? ` ${errors} Error(s).` : ''} The chatbot now queries all active documents.`
    setFileNotifs(prev => [...prev, notif])
    e.target.value = ''
  }

  function removeDoc(index) {
    setActiveDocIds(prev => prev.filter((_, i) => i !== index))
    setActiveDocNames(prev => prev.filter((_, i) => i !== index))
  }

  const isAdmin = user?.role === 'admin'

  return (
    <div className="chatbot-page">

      {/* ── Sessions panel ── */}
      <div className="sessions-panel">
        <div className="sessions-top">
          <div className="sessions-brand">
            <img
              src="/static/img/logomaretap.png"
              alt="MARETAP"
              className="logo-img"
            />
            <div className="brand-text">EZZ<span>AOUIA</span> IA</div>
          </div>
          <button className="btn-new-session" onClick={() => navigate('/chatbot')}>
            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4.5v15m7.5-7.5h-15"/>
            </svg>
            New conversation
          </button>
        </div>

        <div className="sessions-list">
          {loadingSess ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-dim)', fontSize: 12 }}>Loading…</div>
          ) : sessions.length === 0 ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-dim)', fontSize: 12 }}>No conversations</div>
          ) : (
            sessions.map(s => (
              <SessionItem
                key={s.id}
                session={s}
                isActive={activeSession?.id === s.id}
                onNavigate={id => navigate(`/chatbot/${id}`)}
                onDelete={id => setDeleteModal(id)}
                onShare={id => setShareModal(id)}
              />
            ))
          )}

          {sharedWithMe.length > 0 && (
            <>
              <div className="shared-section-label">Shared with me</div>
              {sharedWithMe.map(s => (
                <a key={s.token} href={`/chatbot/shared/${s.token}/`} className="session-item shared-item">
                  <div className="session-info">
                    <div className="session-title">{trunc(s.title, 35)}</div>
                    <div className="session-date">From {s.shared_by} · {s.shared_at}</div>
                  </div>
                </a>
              ))}
            </>
          )}
        </div>

        <div className="sessions-footer">
          {isAdmin && (
            <Link to="/stats" className="btn-back" style={{ marginBottom: 10 }}>
              <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"/>
              </svg>
              View stats
            </Link>
          )}
          <Link to="/dashboard" className="btn-back">
            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18"/>
            </svg>
            Back to dashboard
          </Link>
        </div>

        <div className="sessions-bottom">
          <Link to="/profile" className="user-row">
            <div className="user-avatar-sm">{initials}</div>
            <div>
              <div className="user-name-sm">{displayName}</div>
              <div className="user-role-sm">{user?.department || user?.role || ''}</div>
            </div>
          </Link>
          <div className="user-actions">
            <Link to="/profile" className="btn-user-action">
              <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
              </svg>
              Profile
            </Link>
            <button className="btn-user-action" onClick={logout}>
              <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75"/>
              </svg>
              Logout
            </button>
          </div>
        </div>
      </div>

      {/* ── Chat main ── */}
      <div className="chat-main">

        {/* Topbar */}
        <div className="chat-topbar">
          <div className="topbar-left">
            <div className="ai-indicator">
              <div className="ai-dot" />
              <span className="ai-label">Assistant online</span>
            </div>
            <div>
              <div className="topbar-title">Expert Production EZZAOUIA</div>
              <div className="topbar-sub">
                {activeSession ? trunc(activeSession.title, 50) : 'EZZAOUIA Field · CPF Zarzis · MARETAP'}
              </div>
            </div>
          </div>
          <div className="topbar-right">
            <Link to="/bibliotheque" className="topbar-link">
              <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
              </svg>
              Library
            </Link>
           
            <button className="theme-toggle" onClick={toggleTheme} title="Toggle theme">
              {isDark ? (
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
                </svg>
              ) : (
                <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Messages area */}
        <div className="messages-area">
          {loadingMsgs ? (
            <div style={{ margin: 'auto', color: 'var(--text-dim)', fontSize: 13 }}>Loading conversation…</div>
          ) : messages.length === 0 ? (
            <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
              {morningSugs && (
                <div className="morning-suggestions-wrap" style={{ maxWidth: 560, margin: '0 auto 18px' }}>
                  <div className="morning-suggestions-title">{morningSugs.morning_suggestions_title || '☀️ Suggested this morning'}</div>
                  <div className="suggestions-grid">
                    {morningSugs.suggestions?.map((s, i) => (
                      <button key={i} className="suggestion-btn" onClick={() => handleSend(s.text || s)}>
                        {s.icon || ''} {s.text || s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <div className="welcome-wrap">
                <div className="welcome-icon">
                  <svg width="28" height="28" fill="none" stroke="#C9A84C" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1 1 .26 2.798-1.17 2.798H4.17c-1.43 0-2.17-1.798-1.17-2.798L4.4 15.3"/>
                  </svg>
                </div>
                <div className="welcome-title">Hello, {displayName || 'User'}</div>
                <div className="welcome-sub">
                  I am your expert assistant for oil production in the <strong>EZZAOUIA</strong> field.<br/>
                  I combine your SQL Server data with your technical documents for precise analysis.
                </div>
                <div className="suggestions-grid">
                  {SUGGESTIONS.map(s => (
                    <button key={s} className="suggestion-btn" onClick={() => handleSend(s)}>{s}</button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map(msg => (
                msg.type === 'user'
                  ? (
                    <div key={msg.id} className="msg-row user">
                      <div className="msg-avatar user">{initials}</div>
                      <div className="msg-content">
                        <div className="msg-bubble">{msg.question}</div>
                      </div>
                    </div>
                  ) : (
                    <BotMessage
                      key={msg.id}
                      msg={msg}
                      initials={initials}
                      onSuggest={handleSend}
                    />
                  )
              ))}
              {fileNotifs.map((n, i) => (
                <div key={i} className="file-notif">
                  <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                  </svg>
                  {n}
                </div>
              ))}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input area */}
        <div className="input-area">
          <div className="input-toolbar">
            <button className="toolbar-btn" onClick={() => fileInputRef.current?.click()}>
              <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M18.375 12.739l-7.693 7.693a4.5 4.5 0 01-6.364-6.364l10.94-10.94A3 3 0 1119.5 7.372L8.552 18.32m.009-.01l-.01.01m5.699-9.941l-7.81 7.81a1.5 1.5 0 002.112 2.13"/>
              </svg>
              Attach documents
            </button>
            <input
              ref={fileInputRef}
              type="file"
              style={{ display: 'none' }}
              accept=".pdf,.docx,.xlsx"
              multiple
              onChange={handleFileUpload}
            />
            {uploadStatus && <span className="upload-status" style={{ color: 'var(--text-muted)' }}>{uploadStatus}</span>}
            {activeDocNames.map((name, i) => (
              <div key={i} className={`doc-badge ${getDocExt(name)}`} title={name}>
                <span className="doc-badge-name">{name.length > 25 ? name.slice(0, 22) + '…' : name}</span>
                <span className="doc-remove" onClick={() => removeDoc(i)}>×</span>
              </div>
            ))}
            {activeDocIds.length > 1 && (
              <div className="doc-badge tcm">📁 TCM — {activeDocIds.length} active files</div>
            )}
            {activeDocIds.length > 0 && (
              <button className="btn-clear-all" onClick={() => { setActiveDocIds([]); setActiveDocNames([]) }}>
                ✕ Clear all
              </button>
            )}
          </div>

          <div className="input-row">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => {
                setInput(e.target.value)
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
              }}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
              }}
              placeholder="Ask your question about EZZAOUIA production..."
              rows={1}
            />
            {sending ? (
              <button className="btn-stop" onClick={stopGeneration} title="Stop">
                <svg width="16" height="16" fill="currentColor" viewBox="0 0 24 24">
                  <rect x="5" y="5" width="14" height="14" rx="2"/>
                </svg>
              </button>
            ) : (
              <button className="btn-send" onClick={() => handleSend()} disabled={!input.trim()}>
                <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5"/>
                </svg>
              </button>
            )}
          </div>
          <div className="input-hint">Enter to send · Shift+Enter for a new line · PDF/Word/Excel accepted · Multiple selection supported</div>
        </div>
      </div>

      {/* ── Delete modal ── */}
      {deleteModal && (
        <DeleteModal
          sessionId={deleteModal}
          onConfirm={confirmDelete}
          onCancel={() => setDeleteModal(null)}
        />
      )}

      {/* ── Share modal ── */}
      {shareModal && (
        <ShareModal
          sessionId={shareModal}
          onClose={() => setShareModal(null)}
        />
      )}
    </div>
  )
}
