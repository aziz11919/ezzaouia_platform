import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../components/Layout/Layout'
import { ingestionAPI } from '../api/ingestion'

export default function FileImport() {
  const [selectedFile, setSelectedFile] = useState(null)
  const [dragOver,     setDragOver]     = useState(false)
  const [loading,      setLoading]      = useState(false)
  const [message,      setMessage]      = useState(null)
  const fileInputRef = useRef(null)

  function onFileChange(file) {
    if (!file) return
    setSelectedFile(file)
  }

  async function onSubmit(e) {
    e.preventDefault()
    if (!selectedFile || loading) return
    setLoading(true)
    setMessage(null)
    try {
      const fd = new FormData()
      fd.append('file', selectedFile)
      await ingestionAPI.upload(fd)
      setMessage({ type: 'success', text: `File '${selectedFile.name}' imported successfully. Processing in background.` })
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (err) {
      setMessage({ type: 'error', text: err.response?.data?.error || 'Upload failed.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout
      title="File import"
      breadcrumb="Import a technical report"
      rightNode={
        <Link
          to="/ingestion/list"
          style={{ fontSize: 12, color: 'var(--gold)', textDecoration: 'none' }}
        >
          View my documents →
        </Link>
      }
    >
      {/* Alert */}
      {message && (
        <div
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            padding: '12px 16px', borderRadius: 8, fontSize: 13,
            marginBottom: 20, maxWidth: 580,
            background: message.type === 'error'
              ? 'rgba(224,85,85,0.08)' : 'rgba(77,170,122,0.08)',
            border: `1px solid ${message.type === 'error'
              ? 'rgba(224,85,85,0.25)' : 'rgba(77,170,122,0.25)'}`,
            color: message.type === 'error' ? 'var(--red)' : 'var(--green)',
          }}
        >
          {message.type === 'error' ? (
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/>
            </svg>
          ) : (
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
          )}
          {message.text}
        </div>
      )}

      {/* Section label */}
      <div style={{
        fontSize: 11, fontWeight: 600, color: 'var(--text-dim)',
        textTransform: 'uppercase', letterSpacing: 2, marginBottom: 20,
        display: 'flex', alignItems: 'center', gap: 12,
      }}>
        Import a report
        <span style={{ flex: 1, height: 1, background: 'var(--border)' }} />
      </div>

      {/* Upload card */}
      <div style={{
        background: 'var(--dark2)',
        border: '1px solid var(--border)',
        borderRadius: 10,
        padding: 36,
        maxWidth: 580,
      }}>
        <div style={{
          fontFamily: 'Rajdhani, sans-serif',
          fontSize: 18, fontWeight: 600, color: 'var(--text)', marginBottom: 6,
        }}>
          Technical report
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 28, lineHeight: 1.6 }}>
          Import your PDF, Word, or Excel reports. The document will be extracted and indexed automatically
          in the vector database for the AI Assistant.
        </div>

        <form onSubmit={onSubmit} id="uploadForm">
          {/* Drop zone */}
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={e => {
              e.preventDefault()
              setDragOver(false)
              if (e.dataTransfer.files?.[0]) onFileChange(e.dataTransfer.files[0])
            }}
            style={{
              border: `2px dashed ${dragOver ? 'var(--gold)' : 'rgba(201,168,76,0.2)'}`,
              borderRadius: 10,
              padding: '48px 32px',
              textAlign: 'center',
              color: 'var(--text-dim)',
              fontSize: 14,
              marginBottom: 20,
              cursor: 'pointer',
              background: dragOver ? 'rgba(201,168,76,0.08)' : 'rgba(201,168,76,0.02)',
              transition: 'all 0.2s',
            }}
          >
            {/* Drop icon */}
            <div style={{
              width: 52, height: 52,
              background: 'var(--gold-dim)',
              border: '1px solid var(--border)',
              borderRadius: 12,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px',
            }}>
              <svg width="24" height="24" fill="none" stroke="#C9A84C" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
              </svg>
            </div>

            <div style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 500 }}>
              Drag your file here
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 16 }}>
              or click to browse
            </div>

            {/* Browse button */}
            <label
              onClick={e => e.stopPropagation()}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 7,
                padding: '9px 20px',
                background: 'var(--gold-dim)',
                border: '1px solid var(--border)',
                color: 'var(--gold)',
                borderRadius: 6,
                cursor: 'pointer',
                fontSize: 13,
                fontFamily: 'Inter, sans-serif',
                transition: 'all 0.15s',
              }}
            >
              <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H6.75a9.06 9.06 0 011.5.124m7.5 10.376h3.375c.621 0 1.125-.504 1.125-1.125V11.25c0-4.46-3.243-8.161-7.5-8.876a9.06 9.06 0 00-1.5-.124H9.375c-.621 0-1.125.504-1.125 1.125v3.5m7.5 10.375H9.375a1.125 1.125 0 01-1.125-1.125v-9.25m12 6.625v-1.875a3.375 3.375 0 00-3.375-3.375h-1.5a1.125 1.125 0 01-1.125-1.125v-1.5a3.375 3.375 0 00-3.375-3.375H9.75"/>
              </svg>
              Browse
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.xlsx"
                style={{ display: 'none' }}
                onChange={e => onFileChange(e.target.files?.[0])}
              />
            </label>

            {/* Selected file indicator */}
            {selectedFile && (
              <div style={{
                display: 'flex', alignItems: 'center', gap: 10,
                marginTop: 14, padding: '10px 14px',
                background: 'rgba(77,170,122,0.06)',
                border: '1px solid rgba(77,170,122,0.2)',
                borderRadius: 7, fontSize: 13, color: 'var(--green)',
              }}>
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span>{selectedFile.name}</span>
              </div>
            )}
          </div>

          {/* Format pills */}
          <div style={{
            fontSize: 11, color: 'var(--text-dim)',
            marginBottom: 20,
            display: 'flex', alignItems: 'center', gap: 10,
          }}>
            Accepted formats:
            {['PDF', 'Word .docx', 'Excel .xlsx'].map(f => (
              <span key={f} style={{
                padding: '3px 10px',
                background: 'var(--dark3)',
                border: '1px solid var(--border-soft)',
                borderRadius: 20, fontSize: 11, color: 'var(--text-dim)',
              }}>{f}</span>
            ))}
            <span style={{ marginLeft: 4 }}>— Max 50 MB</span>
          </div>

          {/* Submit button */}
          <button
            type="submit"
            disabled={!selectedFile || loading}
            style={{
              width: '100%',
              padding: 13,
              background: (!selectedFile || loading) ? 'var(--dark4)' : 'var(--gold)',
              color: (!selectedFile || loading) ? 'var(--text-dim)' : '#050D18',
              border: 'none',
              borderRadius: 8,
              fontSize: 14,
              fontWeight: 600,
              fontFamily: 'Rajdhani, sans-serif',
              letterSpacing: 0.5,
              cursor: (!selectedFile || loading) ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
            }}
          >
            {loading ? (
              <>
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24"
                  style={{ animation: 'spin 1s linear infinite' }}>
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                Processing...
              </>
            ) : (
              <>
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/>
                </svg>
                Start import
              </>
            )}
          </button>
        </form>
      </div>

      <style>{`@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}`}</style>
    </Layout>
  )
}
