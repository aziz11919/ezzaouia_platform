import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../components/Layout/Layout'
import { libraryAPI } from '../api/library'

const WELLS = ['EZZ1', 'EZZ2', 'EZZ4', 'EZZ5', 'EZZ6', 'EZZ7', 'EZZ8', 'EZZ9', 'EZZ10', 'EZZ11', 'EZZ12', 'EZZ14', 'EZZ15', 'EZZ16', 'EZZ17', 'EZZ18']

export default function Library() {
  const [query, setQuery] = useState('')
  const [fileType, setFileType] = useState('')
  const [year, setYear] = useState('')
  const [well, setWell] = useState('')
  const [documents, setDocuments] = useState([])
  const [stats, setStats] = useState({ total: 0, pdf: 0, docx: 0, xlsx: 0, total_size_human: '0 B' })
  const [availableYears, setAvailableYears] = useState([])

  async function load() {
    try {
      const res = await libraryAPI.list({ q: query, type: fileType, year, well })
      setDocuments(res.data?.results || [])
      setStats(res.data?.stats || { total: 0, pdf: 0, docx: 0, xlsx: 0, total_size_human: '0 B' })
      setAvailableYears(res.data?.available_years || [])
    } catch {
      setDocuments([])
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function deleteDocument(id, name) {
    const ok = window.confirm(`Delete '${name}' and remove its vector index?`)
    if (!ok) return
    try {
      await libraryAPI.remove(id)
      await load()
    } catch {
      window.alert('Delete failed.')
    }
  }

  return (
    <Layout
      title="Document library"
      breadcrumb={`${stats.total} documents indexed`}
      rightNode={
        <>
          <Link to="/ingestion/upload" className="btn-primary" style={{ textDecoration: 'none' }}>Import</Link>
          <Link to="/chatbot" className="btn-secondary" style={{ textDecoration: 'none' }}>AI Assistant</Link>
        </>
      }
    >
      <div className="grid-kpi" style={{ marginBottom: 18 }}>
        <div className="page-panel"><div className="kpi-label">Total indexed</div><div className="kpi-value v-gold" style={{ marginBottom: 0, fontSize: 26 }}>{stats.total}</div></div>
        <div className="page-panel"><div className="kpi-label">PDF reports</div><div className="kpi-value v-red" style={{ marginBottom: 0, fontSize: 26 }}>{stats.pdf}</div></div>
        <div className="page-panel"><div className="kpi-label">Word documents</div><div className="kpi-value v-blue" style={{ marginBottom: 0, fontSize: 26 }}>{stats.docx}</div></div>
        <div className="page-panel"><div className="kpi-label">Excel files</div><div className="kpi-value v-green" style={{ marginBottom: 0, fontSize: 26 }}>{stats.xlsx}</div></div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '230px 1fr', gap: 20 }}>
        <aside className="page-panel" style={{ height: 'fit-content' }}>
          <div className="section-label" style={{ marginBottom: 12 }}>Filters</div>
          <div style={{ marginBottom: 10 }}>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Search</label>
            <input className="input-field" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="File name..." />
          </div>
          <div style={{ marginBottom: 10 }}>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Type</label>
            <select className="input-field" value={fileType} onChange={(e) => setFileType(e.target.value)}>
              <option value="">All types</option>
              <option value="pdf">PDF</option>
              <option value="docx">DOCX</option>
              <option value="xlsx">XLSX</option>
            </select>
          </div>
          <div style={{ marginBottom: 10 }}>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Year</label>
            <select className="input-field" value={year} onChange={(e) => setYear(e.target.value)}>
              <option value="">All years</option>
              {availableYears.map((y) => <option key={y} value={y}>{y}</option>)}
            </select>
          </div>
          <div style={{ marginBottom: 12 }}>
            <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>Well</label>
            <select className="input-field" value={well} onChange={(e) => setWell(e.target.value)}>
              <option value="">All wells</option>
              {WELLS.map((w) => <option key={w} value={w}>{w}</option>)}
            </select>
          </div>
          <button className="btn-primary" style={{ width: '100%', marginBottom: 8 }} onClick={load}>Apply</button>
          <button
            className="btn-secondary"
            style={{ width: '100%' }}
            onClick={() => {
              setQuery('')
              setFileType('')
              setYear('')
              setWell('')
              setTimeout(load, 0)
            }}
          >
            Reset
          </button>
        </aside>

        <div>
          <div className="section-label">Documents</div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0,1fr))', gap: 12 }}>
            {documents.map((doc) => (
              <div key={doc.id} className="page-panel" style={{ padding: 16 }}>
                <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start', marginBottom: 10 }}>
                  <div className={`module-icon ${doc.file_type === 'pdf' ? 'i-red' : doc.file_type === 'docx' ? 'i-blue' : 'i-green'}`} style={{ width: 38, height: 38, fontFamily: 'Rajdhani, sans-serif', fontWeight: 700 }}>
                    {(doc.file_type || '').toUpperCase()}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--text)', lineHeight: 1.4 }}>{doc.original_name}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 3 }}>{doc.created_at}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>Size: {doc.file_size_human || '-'}</div>
                  </div>
                </div>
                <span className="badge badge-success">Indexed</span>
                <div style={{ display: 'flex', gap: 6, marginTop: 10 }}>
                  <Link to={`/chatbot?doc_id=${doc.id}`} className="btn-secondary" style={{ flex: 1, textDecoration: 'none', textAlign: 'center' }}>Ask</Link>
                  {doc.can_delete ? (
                    <button className="btn-danger" style={{ flex: 1 }} onClick={() => deleteDocument(doc.id, doc.original_name)}>Delete</button>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
          {!documents.length ? <div className="empty-row">No document found.</div> : null}
        </div>
      </div>

      <div className="page-panel" style={{ marginTop: 20, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
        <div>Indexed documents <strong style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 18, marginLeft: 6 }}>{stats.total}</strong></div>
        <div>PDF <strong style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 18, marginLeft: 6 }}>{stats.pdf}</strong></div>
        <div>DOCX <strong style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 18, marginLeft: 6 }}>{stats.docx}</strong></div>
        <div>XLSX <strong style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 18, marginLeft: 6 }}>{stats.xlsx}</strong></div>
        <div>Total size <strong style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 18, marginLeft: 6 }}>{stats.total_size_human}</strong></div>
      </div>
    </Layout>
  )
}
