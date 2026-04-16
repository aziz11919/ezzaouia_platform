import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Layout from '../components/Layout/Layout'
import { libraryAPI } from '../api/library'
import './Library.css'

const PAGE_SIZE = 12

export default function Library() {
  const [query,          setQuery]          = useState('')
  const [fileType,       setFileType]       = useState('')
  const [year,           setYear]           = useState('')
  const [well,           setWell]           = useState('')
  const [uploadedBy,     setUploadedBy]     = useState('')
  const [documents,      setDocuments]      = useState([])
  const [stats,          setStats]          = useState({ total: 0, pdf: 0, docx: 0, xlsx: 0, total_size_human: '0 B' })
  const [availableYears, setAvailableYears] = useState([])
  const [availableWells, setAvailableWells] = useState([])
  const [uploaders,      setUploaders]      = useState([])
  const [page,           setPage]           = useState(1)
  const [deleteModal,    setDeleteModal]    = useState({ open: false, id: null, name: '' })

  async function load(params = {}) {
    try {
      const res = await libraryAPI.list({
        q:           params.q           ?? query,
        type:        params.type        ?? fileType,
        year:        params.year        ?? year,
        well:        params.well        ?? well,
        uploaded_by: params.uploaded_by ?? uploadedBy,
      })
      setDocuments(res.data?.results || [])
      setStats(res.data?.stats || { total: 0, pdf: 0, docx: 0, xlsx: 0, total_size_human: '0 B' })
      setAvailableYears(res.data?.available_years || [])
      setAvailableWells(res.data?.wells || [])
      setUploaders(res.data?.uploaders || [])
      setPage(1)
    } catch {
      setDocuments([])
    }
  }

  useEffect(() => { load() }, [])

  function handleApply(e) {
    e?.preventDefault()
    load()
  }

  function handleReset() {
    setQuery(''); setFileType(''); setYear(''); setWell(''); setUploadedBy('')
    load({ q: '', type: '', year: '', well: '', uploaded_by: '' })
  }

  async function doDelete() {
    const { id, name } = deleteModal
    try {
      await libraryAPI.remove(id)
      setDocuments(prev => prev.filter(d => d.id !== id))
      setStats(prev => ({
        ...prev,
        total: Math.max(0, prev.total - 1),
        [prev.pdf && name ? 'pdf' : 'total']: prev.total - 1,
      }))
      setDeleteModal({ open: false, id: null, name: '' })
      load()
    } catch {
      setDeleteModal({ open: false, id: null, name: '' })
      alert('Delete failed.')
    }
  }

  /* Pagination */
  const totalPages = Math.max(1, Math.ceil(documents.length / PAGE_SIZE))
  const pageDocs   = documents.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE)

  return (
    <Layout
      title="Document library"
      breadcrumb={`${stats.total} document${stats.total !== 1 ? 's' : ''} indexed`}
      rightNode={
        <>
          <Link to="/ingestion/upload" className="btn-primary" style={{ textDecoration: 'none' }}>
            <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 4v16m8-8H4"/>
            </svg>
            Import
          </Link>
          <Link to="/chatbot" className="btn-secondary" style={{ textDecoration: 'none' }}>
            <svg width="13" height="13" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1 1 .26 2.798-1.17 2.798H4.17c-1.43 0-2.17-1.798-1.17-2.798L4.4 15.3"/>
            </svg>
            AI Assistant
          </Link>
        </>
      }
    >
      {/* ── Stats bar ── */}
      <div className="lib-stats-bar">
        <div className="lib-stat-card">
          <div className="lib-stat-icon total">
            <svg width="18" height="18" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
            </svg>
          </div>
          <div>
            <div className="lib-stat-num">{stats.total}</div>
            <div className="lib-stat-label">Total indexed</div>
          </div>
        </div>

        <div className="lib-stat-card">
          <div className="lib-stat-icon pdf">PDF</div>
          <div>
            <div className="lib-stat-num">{stats.pdf}</div>
            <div className="lib-stat-label">PDF reports</div>
          </div>
        </div>

        <div className="lib-stat-card">
          <div className="lib-stat-icon docx">DOC</div>
          <div>
            <div className="lib-stat-num">{stats.docx}</div>
            <div className="lib-stat-label">Word documents</div>
          </div>
        </div>

        <div className="lib-stat-card">
          <div className="lib-stat-icon xlsx">XLS</div>
          <div>
            <div className="lib-stat-num">{stats.xlsx}</div>
            <div className="lib-stat-label">Excel files</div>
          </div>
        </div>

        <div className="lib-stat-card">
          <div className="lib-stat-icon size">#</div>
          <div>
            <div className="lib-stat-num">{stats.total_size_human}</div>
            <div className="lib-stat-label">Total size</div>
          </div>
        </div>
      </div>

      {/* ── Page layout: filters + docs ── */}
      <div className="lib-page-layout">

        {/* Filters sidebar */}
        <aside className="lib-sidebar-filters">
          <form onSubmit={handleApply}>
            <div className="lib-filter-card">
              <div className="lib-filter-title">Search</div>
              <div className="lib-filter-group">
                <input
                  type="text"
                  className="lib-filter-input"
                  placeholder="File name..."
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                />
              </div>
            </div>

            <div className="lib-filter-card">
              <div className="lib-filter-title">Filters</div>

              <div className="lib-filter-group">
                <label className="lib-filter-label">File type</label>
                <select className="lib-filter-select" value={fileType} onChange={e => setFileType(e.target.value)}>
                  <option value="">All types</option>
                  <option value="pdf">PDF</option>
                  <option value="docx">Word (DOCX)</option>
                  <option value="xlsx">Excel (XLSX)</option>
                </select>
              </div>

              <div className="lib-filter-group">
                <label className="lib-filter-label">Import year</label>
                <select className="lib-filter-select" value={year} onChange={e => setYear(e.target.value)}>
                  <option value="">All years</option>
                  {availableYears.map(y => (
                    <option key={y} value={y}>{y}</option>
                  ))}
                </select>
              </div>

              <div className="lib-filter-group">
                <label className="lib-filter-label">Associated well</label>
                <select className="lib-filter-select" value={well} onChange={e => setWell(e.target.value)}>
                  <option value="">All wells</option>
                  {availableWells.map(w => (
                    <option key={w} value={w}>{w}</option>
                  ))}
                </select>
              </div>

              <div className="lib-filter-group">
                <label className="lib-filter-label">Uploaded by</label>
                <select className="lib-filter-select" value={uploadedBy} onChange={e => setUploadedBy(e.target.value)}>
                  <option value="">All users</option>
                  {uploaders.map(u => (
                    <option key={u} value={u}>{u}</option>
                  ))}
                </select>
              </div>

              <button type="submit" className="lib-filter-btn">Apply</button>
              <button type="button" className="lib-filter-reset" onClick={handleReset}>Reset</button>
            </div>
          </form>
        </aside>

        {/* Documents area */}
        <div className="lib-docs-area">

          {/* Search bar */}
          <div className="lib-search-wrap">
            <svg className="lib-search-icon" width="15" height="15" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
            <input
              type="text"
              className="lib-search-input"
              placeholder="Search a document..."
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && load()}
            />
          </div>

          <div className="lib-results-info">
            {documents.length === 0
              ? 'No document found'
              : `${documents.length} document${documents.length !== 1 ? 's' : ''} — page ${page} / ${totalPages}`
            }
          </div>

          {pageDocs.length > 0 ? (
            <>
              <div className="lib-doc-grid">
                {pageDocs.map(doc => (
                  <div className="lib-doc-card" key={doc.id}>
                    <div className="lib-doc-header">
                      <div className={`lib-doc-icon ${doc.file_type || 'pdf'}`}>
                        {(doc.file_type || 'pdf').toUpperCase()}
                      </div>
                      <div className="lib-doc-meta">
                        <div className="lib-doc-name" title={doc.original_name}>{doc.original_name}</div>
                        <div className="lib-doc-date">
                          {doc.created_at}
                          {doc.uploaded_by ? ` · ${doc.uploaded_by}` : ''}
                        </div>
                        <div className="lib-doc-size">Size: {doc.file_size_human || '-'}</div>
                      </div>
                    </div>

                    <span className="lib-doc-badge">
                      <svg width="8" height="8" fill="currentColor" viewBox="0 0 8 8">
                        <circle cx="4" cy="4" r="3"/>
                      </svg>
                      Indexed
                    </span>

                    <div className="lib-doc-actions">
                      <Link
                        to={`/chatbot?doc_id=${doc.id}`}
                        className="lib-doc-btn lib-doc-btn-chat"
                      >
                        <svg width="11" height="11" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1 1 .26 2.798-1.17 2.798H4.17c-1.43 0-2.17-1.798-1.17-2.798L4.4 15.3"/>
                        </svg>
                        Ask
                      </Link>
                      {doc.can_delete && (
                        <button
                          className="lib-doc-btn lib-doc-btn-del"
                          onClick={() => setDeleteModal({ open: true, id: doc.id, name: doc.original_name })}
                        >
                          <svg width="11" height="11" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                          </svg>
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="lib-pagination">
                  <button
                    className={`lib-page-btn${page === 1 ? ' disabled' : ''}`}
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >←</button>
                  {Array.from({ length: totalPages }, (_, i) => i + 1)
                    .filter(n => Math.abs(n - page) <= 2)
                    .map(n => (
                      <button
                        key={n}
                        className={`lib-page-btn${n === page ? ' current' : ''}`}
                        onClick={() => setPage(n)}
                      >{n}</button>
                    ))
                  }
                  <button
                    className={`lib-page-btn${page === totalPages ? ' disabled' : ''}`}
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >→</button>
                </div>
              )}
            </>
          ) : (
            <div className="lib-empty-state">
              <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"/>
              </svg>
              <div className="lib-empty-title">No document found</div>
              <div className="lib-empty-sub">
                Adjust your filters or{' '}
                <Link to="/ingestion/upload" style={{ color: 'var(--gold)' }}>import a document</Link>
              </div>
            </div>
          )}

          {/* Bottom summary */}
          <div className="lib-bottom-summary">
            <div className="lib-summary-item">Indexed documents<strong>{stats.total}</strong></div>
            <div className="lib-summary-item">PDF<strong>{stats.pdf}</strong></div>
            <div className="lib-summary-item">DOCX<strong>{stats.docx}</strong></div>
            <div className="lib-summary-item">XLSX<strong>{stats.xlsx}</strong></div>
            <div className="lib-summary-item">Total size<strong>{stats.total_size_human}</strong></div>
          </div>

        </div>{/* /lib-docs-area */}
      </div>{/* /lib-page-layout */}

      {/* ── Delete confirmation modal ── */}
      <div
        className={`lib-modal-overlay${deleteModal.open ? ' open' : ''}`}
        onClick={e => { if (e.target === e.currentTarget) setDeleteModal({ open: false, id: null, name: '' }) }}
      >
        <div className="lib-modal">
          <div className="lib-modal-title">Delete document</div>
          <div className="lib-modal-body">
            Delete &quot;{deleteModal.name}&quot; and remove its ChromaDB index?
          </div>
          <div className="lib-modal-actions">
            <button className="lib-btn-cancel" onClick={() => setDeleteModal({ open: false, id: null, name: '' })}>
              Cancel
            </button>
            <button className="lib-btn-delete" onClick={doDelete}>
              Delete
            </button>
          </div>
        </div>
      </div>

    </Layout>
  )
}
