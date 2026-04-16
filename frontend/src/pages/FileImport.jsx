import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../components/Layout/Layout'
import { ingestionAPI } from '../api/ingestion'

function statusClass(status) {
  if (status === 'success') return 'badge badge-success'
  if (status === 'error') return 'badge badge-error'
  if (status === 'processing') return 'badge badge-processing'
  return 'badge badge-pending'
}

export default function FileImport() {
  const [files, setFiles] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState(null)
  const fileInputRef = useRef(null)

  async function loadFiles() {
    try {
      const res = await ingestionAPI.getRecentFiles()
      setFiles(res.data?.files || [])
    } catch {
      setFiles([])
    }
  }

  useEffect(() => {
    loadFiles()
  }, [])

  function onFileChange(file) {
    if (!file) return
    setSelectedFile(file)
  }

  async function onSubmit(event) {
    event.preventDefault()
    if (!selectedFile) return
    setLoading(true)
    setMessage(null)
    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      await ingestionAPI.upload(formData)
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
      setMessage({ type: 'success', text: `File '${selectedFile.name}' uploaded.` })
      await loadFiles()
    } catch (error) {
      setMessage({ type: 'error', text: error.response?.data?.error || 'Upload failed.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout
      title="File import"
      breadcrumb="Import a technical report"
      rightNode={<Link to="/ingestion/list" style={{ fontSize: 12, color: 'var(--gold)', textDecoration: 'none' }}>View my documents {'->'}</Link>}
    >
      {message ? (
        <div className={`alert ${message.type === 'error' ? 'alert-error' : 'alert-success'}`}>
          {message.text}
        </div>
      ) : null}

      <div className="section-label">Import a report</div>
      <div className="page-panel" style={{ maxWidth: 580 }}>
        <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 18, fontWeight: 600, color: 'var(--text)', marginBottom: 6 }}>
          Technical report
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 28, lineHeight: 1.6 }}>
          Import your PDF, Word, or Excel reports. The document will be indexed automatically for the AI Assistant.
        </div>

        <form onSubmit={onSubmit}>
          <div
            onClick={() => fileInputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault()
              setDragOver(false)
              onFileChange(e.dataTransfer.files?.[0])
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
            <div style={{ width: 52, height: 52, background: 'var(--gold-dim)', border: '1px solid var(--border)', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px' }}>
              <svg width="24" height="24" fill="none" stroke="#C9A84C" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>
            <div style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 8, fontWeight: 500 }}>Drag your file here</div>
            <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 16 }}>or click to browse</div>
            <div className="btn-secondary" style={{ display: 'inline-flex' }}>Browse</div>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.xlsx"
              style={{ display: 'none' }}
              onChange={(e) => onFileChange(e.target.files?.[0])}
            />
            {selectedFile ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 14, padding: '10px 14px', background: 'rgba(77,170,122,0.06)', border: '1px solid rgba(77,170,122,0.2)', borderRadius: 7, fontSize: 13, color: 'var(--green)' }}>
                <span>{selectedFile.name}</span>
              </div>
            ) : null}
          </div>

          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 10 }}>
            Accepted formats:
            <span style={{ padding: '3px 10px', background: 'var(--dark3)', border: '1px solid var(--border-soft)', borderRadius: 20 }}>PDF</span>
            <span style={{ padding: '3px 10px', background: 'var(--dark3)', border: '1px solid var(--border-soft)', borderRadius: 20 }}>Word .docx</span>
            <span style={{ padding: '3px 10px', background: 'var(--dark3)', border: '1px solid var(--border-soft)', borderRadius: 20 }}>Excel .xlsx</span>
          </div>

          <button type="submit" className="btn-primary" style={{ width: '100%', height: 46 }} disabled={!selectedFile || loading}>
            {loading ? 'Processing...' : 'Start import'}
          </button>
        </form>
      </div>

      <div style={{ marginTop: 28 }}>
        <div className="section-label">Imported files</div>
        <div className="table-card">
          <table>
            <thead>
              <tr>
                <th>File</th>
                <th>Type</th>
                <th>Status</th>
                <th>Import date</th>
              </tr>
            </thead>
            <tbody>
              {files.length ? files.map((file) => (
                <tr key={file.id}>
                  <td style={{ color: 'var(--text)' }}>{file.original_name}</td>
                  <td>{String(file.file_type || '').toUpperCase()}</td>
                  <td><span className={statusClass(file.status)}>{file.status}</span></td>
                  <td>{file.created_at}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={4} className="empty-row">No imported file.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  )
}
