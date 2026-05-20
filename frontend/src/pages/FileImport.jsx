import { useCallback, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../components/Layout/Layout'
import { ingestionAPI } from '../api/ingestion'

const ACCEPTED_EXTS = ['pdf', 'docx', 'xlsx']
const MAX_FILE_SIZE = 50 * 1024 * 1024  // 50 MB

function fileExt(name) {
  return name.split('.').pop().toLowerCase()
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function FileImport() {
  const [mode, setMode]           = useState('files')   // 'files' | 'folder'
  const [queue, setQueue]         = useState([])         // [{file, status:'pending'|'uploading'|'done'|'error', msg}]
  const [dragOver, setDragOver]   = useState(false)
  const [running, setRunning]     = useState(false)
  const [globalMsg, setGlobalMsg] = useState(null)

  const fileInputRef   = useRef(null)
  const folderInputRef = useRef(null)

  function buildQueue(fileList) {
    const valid = []
    const oversized = []
    for (const f of Array.from(fileList)) {
      if (!ACCEPTED_EXTS.includes(fileExt(f.name))) continue
      if (f.size > MAX_FILE_SIZE) { oversized.push(f.name); continue }
      valid.push({ file: f, status: 'pending', msg: '' })
    }
    setQueue(valid)
    if (oversized.length)
      setGlobalMsg({ type: 'error', text: `Fichier(s) trop volumineux (max 50 MB) : ${oversized.join(', ')}` })
    else
      setGlobalMsg(null)
  }

  function handleFilesChange(e) {
    buildQueue(e.target.files)
  }

  function handleFolderChange(e) {
    buildQueue(e.target.files)
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragOver(false)
    const items = e.dataTransfer.items
    if (items) {
      const files = []
      for (const item of items) {
        const f = item.getAsFile()
        if (f && ACCEPTED_EXTS.includes(fileExt(f.name))) files.push(f)
      }
      if (files.length) {
        setQueue(files.map(f => ({ file: f, status: 'pending', msg: '' })))
        setGlobalMsg(null)
      }
    }
  }

  // Poll /api-status/<id>/ until Celery finishes (success / error / rejected)
  const pollStatus = useCallback(async (fileId, idx) => {
    for (let n = 0; n < 30; n++) {
      await new Promise(r => setTimeout(r, 2000))
      try {
        const { data } = await ingestionAPI.getStatus(fileId)
        if (data.status === 'success') {
          setQueue(q => q.map((x, i) => i === idx ? { ...x, status: 'done', msg: 'Traité ✓' } : x))
          return 'success'
        }
        if (data.status === 'error') {
          setQueue(q => q.map((x, i) => i === idx ? { ...x, status: 'error', msg: data.error || 'Erreur de traitement' } : x))
          return 'error'
        }
        if (data.status === 'rejected') {
          setQueue(q => q.map((x, i) => i === idx ? { ...x, status: 'rejected', msg: data.reason || 'Non lié au pétrole/MARETAP' } : x))
          return 'rejected'
        }
        // 'pending' or 'processing' — continue
      } catch { /* network hiccup — keep polling */ }
    }
    setQueue(q => q.map((x, i) => i === idx ? { ...x, status: 'error', msg: 'Timeout — traitement trop long' } : x))
    return 'timeout'
  }, [])

  async function startUpload() {
    if (!queue.length || running) return
    setRunning(true)
    setGlobalMsg(null)

    // Phase 1 — upload all pending files sequentially
    const toProcess = []
    for (let i = 0; i < queue.length; i++) {
      const item = queue[i]
      if (item.status !== 'pending') continue

      setQueue(q => q.map((x, idx) => idx === i ? { ...x, status: 'uploading' } : x))
      try {
        const fd = new FormData()
        fd.append('file', item.file)
        const res = await ingestionAPI.upload(fd)
        const fileId = res.data?.file?.id
        if (fileId) {
          setQueue(q => q.map((x, idx) => idx === i ? { ...x, status: 'processing', msg: 'Indexation…' } : x))
          toProcess.push({ idx: i, fileId })
        } else {
          setQueue(q => q.map((x, idx) => idx === i ? { ...x, status: 'error', msg: 'Erreur : ID fichier manquant' } : x))
        }
      } catch (err) {
        const msg = err.response?.data?.error || 'Erreur upload'
        setQueue(q => q.map((x, idx) => idx === i ? { ...x, status: 'error', msg } : x))
      }
    }

    // Phase 2 — poll all uploaded files concurrently
    const results = await Promise.all(
      toProcess.map(({ idx, fileId }) => pollStatus(fileId, idx))
    )

    const success  = results.filter(s => s === 'success').length
    const rejected = results.filter(s => s === 'rejected').length
    const failed   = results.filter(s => s === 'error' || s === 'timeout').length

    setRunning(false)
    if (failed === 0 && rejected === 0)
      setGlobalMsg({ type: 'success', text: `${success} fichier(s) traité(s) avec succès.` })
    else
      setGlobalMsg({
        type: 'error',
        text: `${success} traité(s)${rejected ? `, ${rejected} rejeté(s) — document non lié au domaine pétrolier/MARETAP` : ''}${failed ? `, ${failed} erreur(s)` : ''}.`,
      })
  }

  function clearQueue() {
    setQueue([])
    setGlobalMsg(null)
    if (fileInputRef.current)   fileInputRef.current.value   = ''
    if (folderInputRef.current) folderInputRef.current.value = ''
  }

  const pendingCount = queue.filter(x => x.status === 'pending').length
  const doneCount    = queue.filter(x => x.status === 'done').length

  const statusColor = {
    pending:    'var(--text-dim)',
    uploading:  'var(--gold)',
    processing: 'var(--blue)',
    done:       'var(--green)',
    rejected:   'var(--red)',
    error:      'var(--red)',
  }
  const statusLabel = {
    pending:    '—',
    uploading:  '…',
    processing: '⟳',
    done:       '✓',
    rejected:   '⊘',
    error:      '✗',
  }

  return (
    <Layout
      title="Import de fichiers"
      breadcrumb="Importer des rapports techniques"
      rightNode={
        <Link to="/ingestion/list" style={{ fontSize: 12, color: 'var(--gold)', textDecoration: 'none' }}>
          Mes documents →
        </Link>
      }
    >
      {/* Global message */}
      {globalMsg && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '12px 16px', borderRadius: 8, fontSize: 13,
          marginBottom: 20, maxWidth: 620,
          background: globalMsg.type === 'error' ? 'rgba(224,85,85,0.08)' : 'rgba(77,170,122,0.08)',
          border: `1px solid ${globalMsg.type === 'error' ? 'rgba(224,85,85,0.25)' : 'rgba(77,170,122,0.25)'}`,
          color: globalMsg.type === 'error' ? 'var(--red)' : 'var(--green)',
        }}>
          {globalMsg.text}
        </div>
      )}

      {/* Section label */}
      <div style={{
        fontSize: 11, fontWeight: 600, color: 'var(--text-dim)',
        textTransform: 'uppercase', letterSpacing: 2, marginBottom: 20,
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        Import
        <span style={{ flex: 1, height: 1, background: 'var(--border)' }} />
      </div>

      {/* Card */}
      <div style={{
        background: 'var(--dark2)', border: '1px solid var(--border)',
        borderRadius: 10, padding: 36, maxWidth: 620,
      }}>
        <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 18, fontWeight: 600, color: 'var(--text)', marginBottom: 6 }}>
          Rapport technique
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 24, lineHeight: 1.6 }}>
          Importez vos rapports PDF, Word ou Excel. Les documents seront indexés automatiquement pour l'assistant IA.
        </div>

        {/* Mode toggle */}
        <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
          {[
            { key: 'files',  label: 'Fichiers' },
            { key: 'folder', label: 'Dossier' },
          ].map(({ key, label }) => (
            <button
              key={key}
              onClick={() => { setMode(key); clearQueue() }}
              style={{
                padding: '7px 18px', borderRadius: 6, fontSize: 13, cursor: 'pointer',
                fontFamily: 'Inter, sans-serif', fontWeight: 500,
                background: mode === key ? 'var(--gold)' : 'var(--dark3)',
                color:      mode === key ? '#050D18'     : 'var(--text-dim)',
                border:     mode === key ? 'none'        : '1px solid var(--border)',
                transition: 'all 0.15s',
              }}
            >
              {key === 'folder' && (
                <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  style={{ marginRight: 6, verticalAlign: 'middle' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                    d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/>
                </svg>
              )}
              {key === 'files' && (
                <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  style={{ marginRight: 6, verticalAlign: 'middle' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
              )}
              {label}
            </button>
          ))}
        </div>

        {/* Drop zone (shown only when queue is empty) */}
        {queue.length === 0 && (
          <div
            onClick={() => mode === 'folder' ? folderInputRef.current?.click() : fileInputRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            style={{
              border: `2px dashed ${dragOver ? 'var(--gold)' : 'rgba(201,168,76,0.2)'}`,
              borderRadius: 10, padding: '48px 32px', textAlign: 'center',
              color: 'var(--text-dim)', fontSize: 14, marginBottom: 20,
              cursor: 'pointer',
              background: dragOver ? 'rgba(201,168,76,0.08)' : 'rgba(201,168,76,0.02)',
              transition: 'all 0.2s',
            }}
          >
            <div style={{
              width: 52, height: 52, background: 'var(--gold-dim)',
              border: '1px solid var(--border)', borderRadius: 12,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px',
            }}>
              {mode === 'folder' ? (
                <svg width="24" height="24" fill="none" stroke="#C9A84C" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5"
                    d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V7z"/>
                </svg>
              ) : (
                <svg width="24" height="24" fill="none" stroke="#C9A84C" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5"
                    d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
                </svg>
              )}
            </div>

            <div style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 500 }}>
              {mode === 'folder' ? 'Cliquez pour sélectionner un dossier' : 'Glissez vos fichiers ici'}
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 16 }}>
              {mode === 'folder'
                ? 'Tous les fichiers PDF, Word et Excel du dossier seront importés'
                : 'ou cliquez pour parcourir'}
            </div>

            <span
              onClick={e => { e.stopPropagation(); mode === 'folder' ? folderInputRef.current?.click() : fileInputRef.current?.click() }}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 7,
                padding: '9px 20px', background: 'var(--gold-dim)',
                border: '1px solid var(--border)', color: 'var(--gold)',
                borderRadius: 6, cursor: 'pointer', fontSize: 13,
                fontFamily: 'Inter, sans-serif',
              }}
            >
              {mode === 'folder' ? 'Sélectionner un dossier' : 'Parcourir'}
            </span>

            {/* hidden inputs */}
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.xlsx"
              multiple
              style={{ display: 'none' }}
              onChange={handleFilesChange}
            />
            <input
              ref={folderInputRef}
              type="file"
              accept=".pdf,.docx,.xlsx"
              webkitdirectory=""
              directory=""
              multiple
              style={{ display: 'none' }}
              onChange={handleFolderChange}
            />
          </div>
        )}

        {/* File queue */}
        {queue.length > 0 && (
          <div style={{ marginBottom: 20 }}>
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              marginBottom: 10,
            }}>
              <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>
                {queue.length} fichier(s) — {doneCount} importé(s)
                {running && ` · traitement en cours…`}
              </div>
              {!running && (
                <button
                  onClick={clearQueue}
                  style={{
                    background: 'none', border: 'none', color: 'var(--text-dim)',
                    cursor: 'pointer', fontSize: 12, padding: '2px 6px',
                  }}
                >
                  Effacer
                </button>
              )}
            </div>

            <div style={{
              maxHeight: 260, overflowY: 'auto',
              border: '1px solid var(--border)', borderRadius: 8,
            }}>
              {queue.map((item, i) => (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '9px 14px',
                  borderBottom: i < queue.length - 1 ? '1px solid var(--border-soft)' : 'none',
                  background: item.status === 'uploading' ? 'rgba(201,168,76,0.04)' : 'transparent',
                }}>
                  {/* ext badge */}
                  <span style={{
                    fontSize: 10, fontWeight: 700, padding: '2px 6px',
                    borderRadius: 4, background: 'var(--dark3)',
                    color: 'var(--text-dim)', textTransform: 'uppercase', minWidth: 36, textAlign: 'center',
                  }}>
                    {fileExt(item.file.name)}
                  </span>

                  {/* name */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontSize: 13, color: 'var(--text)',
                      whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                    }}>
                      {item.file.name}
                    </div>
                    <div style={{
                      fontSize: 11,
                      color: (item.status === 'rejected' || item.status === 'error')
                        ? statusColor[item.status]
                        : 'var(--text-dim)',
                    }}>
                      {formatSize(item.file.size)}
                      {item.msg ? ` · ${item.msg}` : ''}
                    </div>
                  </div>

                  {/* status */}
                  <span style={{
                    fontSize: 13, fontWeight: 600, minWidth: 20, textAlign: 'center',
                    color: statusColor[item.status],
                    animation: item.status === 'uploading' ? 'pulse 1s infinite' : 'none',
                  }}>
                    {(item.status === 'uploading' || item.status === 'processing') ? (
                      <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                        style={{ animation: 'spin 1s linear infinite', color: statusColor[item.status] }}>
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                      </svg>
                    ) : statusLabel[item.status]}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Format pills */}
        <div style={{
          fontSize: 11, color: 'var(--text-dim)', marginBottom: 20,
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          Formats acceptés:
          {['PDF', 'Word .docx', 'Excel .xlsx'].map(f => (
            <span key={f} style={{
              padding: '3px 10px', background: 'var(--dark3)',
              border: '1px solid var(--border-soft)', borderRadius: 20,
              fontSize: 11, color: 'var(--text-dim)',
            }}>{f}</span>
          ))}
          <span style={{ marginLeft: 4 }}>— Max 50 MB</span>
        </div>

        {/* Submit */}
        <button
          onClick={startUpload}
          disabled={pendingCount === 0 || running}
          style={{
            width: '100%', padding: 13,
            background: (pendingCount === 0 || running) ? 'var(--dark4)' : 'var(--gold)',
            color:       (pendingCount === 0 || running) ? 'var(--text-dim)' : '#050D18',
            border: 'none', borderRadius: 8, fontSize: 14, fontWeight: 600,
            fontFamily: 'Rajdhani, sans-serif', letterSpacing: 0.5,
            cursor: (pendingCount === 0 || running) ? 'not-allowed' : 'pointer',
            transition: 'all 0.2s',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
          }}
        >
          {running ? (
            <>
              <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                style={{ animation: 'spin 1s linear infinite' }}>
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              Import en cours…
            </>
          ) : (
            <>
              <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                  d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
              </svg>
              {pendingCount > 0 ? `Importer ${pendingCount} fichier(s)` : 'Importer'}
            </>
          )}
        </button>
      </div>

      <style>{`
        @keyframes spin { from { transform: rotate(0deg) } to { transform: rotate(360deg) } }
      `}</style>
    </Layout>
  )
}
