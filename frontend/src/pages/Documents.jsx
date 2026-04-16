import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { FileText, MessageSquare, Search, Filter } from 'lucide-react'
import Sidebar from '../components/Layout/Sidebar'
import Topbar  from '../components/Layout/Topbar'
import Badge   from '../components/UI/Badge'
import LoadingSpinner from '../components/UI/LoadingSpinner'
import { ingestionAPI } from '../api/ingestion'
import { useAuth } from '../contexts/AuthContext'

const EXT_COLORS = { pdf: 'text-red-400', docx: 'text-blue-400', xlsx: 'text-green-400' }
const STATUS_MAP = {
  success:    { variant: 'success', label: 'Indexé'    },
  processing: { variant: 'warning', label: 'En cours'  },
  pending:    { variant: 'info',    label: 'En attente' },
  error:      { variant: 'error',   label: 'Erreur'    },
}

export default function Documents() {
  const { user } = useAuth()
  const [files,   setFiles]   = useState([])
  const [loading, setLoading] = useState(true)
  const [search,  setSearch]  = useState('')
  const [filter,  setFilter]  = useState('all')

  const load = useCallback(async () => {
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

  useEffect(() => { load() }, [load])

  const filtered = files.filter(f => {
    const matchSearch = f.original_name.toLowerCase().includes(search.toLowerCase())
    const matchFilter = filter === 'all' || f.status === filter
    return matchSearch && matchFilter
  })

  return (
    <div className="flex h-screen bg-maretap-dark overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Topbar title="Documents" subtitle="Base documentaire MARETAP" onRefresh={load} loading={loading} />

        <main className="flex-1 overflow-y-auto p-6 space-y-5">

          {/* Search + Filter */}
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-sm">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-600" />
              <input
                type="text"
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Rechercher un document..."
                className="input-field pl-9 py-2 text-xs"
              />
            </div>
            <div className="flex items-center gap-1.5">
              <Filter size={14} className="text-gray-600" />
              {['all','success','processing','error'].map(s => (
                <button
                  key={s}
                  onClick={() => setFilter(s)}
                  className={`px-3 py-1.5 text-xs rounded font-rajdhani font-semibold transition-colors ${
                    filter === s
                      ? 'bg-maretap-red text-white'
                      : 'bg-maretap-dark3 text-gray-500 hover:text-white border border-red-900/20'
                  }`}
                >
                  {s === 'all' ? 'Tous' : STATUS_MAP[s]?.label || s}
                </button>
              ))}
            </div>
          </div>

          {/* Files grid */}
          {loading
            ? <div className="flex justify-center p-12"><LoadingSpinner text="Chargement des documents..." /></div>
            : filtered.length === 0
              ? (
                <div className="text-center py-16">
                  <FileText size={40} className="mx-auto text-gray-700 mb-4" />
                  <p className="text-gray-500">Aucun document trouvé</p>
                  {user?.role !== 'direction' && (
                    <Link to="/ingestion" className="mt-3 inline-flex items-center gap-2 text-sm text-maretap-red hover:text-red-400 transition-colors">
                      Importer des documents →
                    </Link>
                  )}
                </div>
              )
              : (
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {filtered.map(f => {
                    const s = STATUS_MAP[f.status] || STATUS_MAP.pending
                    return (
                      <div key={f.id} className="card hover:border-red-700/30 transition-colors group">
                        <div className="flex items-start justify-between mb-3">
                          <FileText size={20} className={EXT_COLORS[f.file_type] || 'text-gray-500'} />
                          <Badge variant={s.variant}>{s.label}</Badge>
                        </div>
                        <h4 className="text-sm text-gray-200 font-medium truncate mb-1" title={f.original_name}>
                          {f.original_name}
                        </h4>
                        <p className="text-xs text-gray-600">{f.created_at}</p>
                        {f.status === 'success' && user?.role !== 'direction' && (
                          <Link
                            to={`/chatbot?doc_id=${f.id}`}
                            className="mt-3 flex items-center gap-1.5 text-xs text-maretap-red hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                          >
                            <MessageSquare size={12} />
                            Interroger ce document
                          </Link>
                        )}
                      </div>
                    )
                  })}
                </div>
              )
          }

        </main>
      </div>
    </div>
  )
}
