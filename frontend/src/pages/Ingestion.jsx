import { useState, useEffect, useRef, useCallback } from 'react'
import { Upload, FileText, CheckCircle, AlertCircle, Clock, RefreshCw, X } from 'lucide-react'
import Sidebar from '../components/Layout/Sidebar'
import Topbar  from '../components/Layout/Topbar'
import Badge   from '../components/UI/Badge'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import { ingestionAPI } from '../api/ingestion'

const STATUS_MAP = {
  success:    { variant: 'success', label: 'Traité',     icon: CheckCircle },
  processing: { variant: 'warning', label: 'En cours',   icon: RefreshCw   },
  pending:    { variant: 'info',    label: 'En attente', icon: Clock       },
  error:      { variant: 'error',   label: 'Erreur',     icon: AlertCircle },
}

const EXT_COLORS = { pdf: 'text-red-400', docx: 'text-blue-400', xlsx: 'text-green-400' }

export default function Ingestion() {
  const [files,    setFiles]    = useState([])
  const [loading,  setLoading]  = useState(true)
  const [dragging, setDragging] = useState(false)
  const [uploads,  setUploads]  = useState([])
  const fileInputRef = useRef(null)

  const loadFiles = useCallback(async () => {
    setLoading(true)
    try {
      const r = await ingestionAPI.getRecentFiles()
      setFiles(r.data?.files || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadFiles() }, [loadFiles])

  const handleUpload = async (fileList) => {
    const allowed = ['pdf', 'docx', 'xlsx']
    for (const file of Array.from(fileList)) {
      const ext = file.name.split('.').pop().toLowerCase()
      if (!allowed.includes(ext)) continue

      const id = Date.now() + Math.random()
      setUploads(prev => [...prev, { id, name: file.name, status: 'uploading' }])

      try {
        const fd = new FormData()
        fd.append('file', file)
        await ingestionAPI.upload(fd)
        setUploads(prev => prev.map(u => u.id === id ? { ...u, status: 'done' } : u))
        loadFiles()
      } catch (err) {
        setUploads(prev => prev.map(u =>
          u.id === id ? { ...u, status: 'error', error: err.response?.data?.error || 'Erreur' } : u
        ))
      }
    }
  }

  return (
    <div className="flex h-screen bg-maretap-dark overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Topbar title="Import fichiers" subtitle="PDF, Word, Excel — max 50 MB" onRefresh={loadFiles} loading={loading} />

        <main className="flex-1 overflow-y-auto p-6 space-y-6">

          {/* Drop zone */}
          <div
            className={`border-2 border-dashed rounded-xl p-12 text-center transition-colors cursor-pointer ${
              dragging ? 'border-maretap-red bg-red-900/10' : 'border-red-900/20 hover:border-red-700/40 hover:bg-red-900/5'
            }`}
            onClick={() => fileInputRef.current?.click()}
            onDragOver={e => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => { e.preventDefault(); setDragging(false); handleUpload(e.dataTransfer.files) }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.xlsx"
              multiple
              className="hidden"
              onChange={e => handleUpload(e.target.files)}
            />
            <Upload size={36} className={`mx-auto mb-4 ${dragging ? 'text-maretap-red' : 'text-gray-600'}`} />
            <p className="text-gray-300 font-rajdhani text-lg">
              Glissez vos fichiers ici ou <span className="text-maretap-red">cliquez pour sélectionner</span>
            </p>
            <p className="text-gray-600 text-sm mt-2">PDF, Word (.docx), Excel (.xlsx) — Max 50 MB</p>
          </div>

          {/* Active uploads */}
          {uploads.filter(u => u.status !== 'done').length > 0 && (
            <div className="card space-y-2">
              <h3 className="text-sm font-rajdhani font-semibold text-gray-300 uppercase tracking-wider mb-3">
                Imports en cours
              </h3>
              {uploads.filter(u => u.status !== 'done').map(u => (
                <div key={u.id} className="flex items-center gap-3 py-2">
                  {u.status === 'uploading'
                    ? <RefreshCw size={14} className="text-yellow-400 animate-spin" />
                    : <AlertCircle size={14} className="text-red-400" />
                  }
                  <span className="text-sm text-gray-300 flex-1 truncate">{u.name}</span>
                  {u.error && <span className="text-xs text-red-400">{u.error}</span>}
                  <button onClick={() => setUploads(prev => prev.filter(x => x.id !== u.id))}>
                    <X size={14} className="text-gray-600 hover:text-gray-400" />
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* File list */}
          <div className="card">
            <h3 className="text-sm font-rajdhani font-semibold text-gray-300 uppercase tracking-wider mb-4">
              Fichiers importés (10 derniers)
            </h3>

            {loading
              ? <div className="flex justify-center p-8"><LoadingSpinner text="Chargement..." /></div>
              : files.length === 0
                ? (
                  <div className="text-center py-12">
                    <FileText size={32} className="mx-auto text-gray-700 mb-3" />
                    <p className="text-gray-500 text-sm">Aucun fichier importé</p>
                  </div>
                )
                : (
                  <div className="space-y-0">
                    {files.map(f => {
                      const s = STATUS_MAP[f.status] || STATUS_MAP.pending
                      const StatusIcon = s.icon
                      return (
                        <div key={f.id} className="flex items-center gap-4 py-3 border-b border-red-900/10 last:border-0 hover:bg-red-900/5 -mx-2 px-2 rounded transition-colors">
                          <FileText size={18} className={EXT_COLORS[f.file_type] || 'text-gray-500'} />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-gray-200 truncate">{f.original_name}</p>
                            <p className="text-xs text-gray-600 mt-0.5">{f.created_at}</p>
                          </div>
                          <span className="text-xs uppercase text-gray-600 bg-maretap-dark3 px-1.5 py-0.5 rounded font-mono">
                            {f.file_type}
                          </span>
                          <div className="flex items-center gap-1.5">
                            <StatusIcon size={13} className={
                              f.status === 'success' ? 'text-green-400' :
                              f.status === 'error'   ? 'text-red-400'   : 'text-yellow-400'
                            } />
                            <Badge variant={s.variant}>{s.label}</Badge>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                )
            }
          </div>

        </main>
      </div>
    </div>
  )
}
