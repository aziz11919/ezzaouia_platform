import { useState, useEffect } from 'react'
import { BarChart2, Settings, ExternalLink, RefreshCw } from 'lucide-react'
import Sidebar from '../components/Layout/Sidebar'
import Topbar  from '../components/Layout/Topbar'

const DEFAULT_REPORTS = [
  { id: 'production', name: 'Production Overview', file: 'EZZAOUIA_Production', desc: 'Indicateurs de production journalière et mensuelle' },
  { id: 'wells',      name: 'Well Performance',    file: 'EZZAOUIA_Wells',       desc: 'Performance individuelle des puits' },
  { id: 'budget',     name: 'Budget Analysis',     file: 'EZZAOUIA_Budget',      desc: 'Analyse budgétaire et coûts opérationnels' },
]

const LS_KEY = 'maretap_powerbi_server'

export default function PowerBI() {
  const [serverUrl,      setServerUrl]      = useState(() => localStorage.getItem(LS_KEY) || '')
  const [inputUrl,       setInputUrl]       = useState(() => localStorage.getItem(LS_KEY) || '')
  const [activeReport,   setActiveReport]   = useState(DEFAULT_REPORTS[0])
  const [showSettings,   setShowSettings]   = useState(!localStorage.getItem(LS_KEY))
  const [iframeKey,      setIframeKey]      = useState(0)

  const saveServer = () => {
    const url = inputUrl.trim().replace(/\/$/, '')
    localStorage.setItem(LS_KEY, url)
    setServerUrl(url)
    setShowSettings(false)
    setIframeKey(k => k + 1)
  }

  const reportUrl = serverUrl
    ? `${serverUrl}/powerbi/${activeReport.file}`
    : null

  return (
    <div className="flex h-screen bg-maretap-dark overflow-hidden">
      <Sidebar />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Topbar
          title="Power BI Dashboards"
          subtitle="Tableaux de bord analytiques MARETAP"
        />

        <main className="flex-1 flex flex-col overflow-hidden p-4 gap-4">

          {/* Report tabs + Settings */}
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-2">
              {DEFAULT_REPORTS.map(r => (
                <button
                  key={r.id}
                  onClick={() => { setActiveReport(r); setIframeKey(k => k + 1) }}
                  className={`px-4 py-2 text-xs font-rajdhani font-semibold uppercase tracking-wider rounded transition-colors ${
                    activeReport.id === r.id
                      ? 'bg-maretap-red text-white'
                      : 'bg-maretap-dark3 text-gray-400 hover:text-white border border-red-900/20'
                  }`}
                >
                  {r.name}
                </button>
              ))}
            </div>
            <div className="flex items-center gap-2">
              {serverUrl && (
                <button
                  onClick={() => setIframeKey(k => k + 1)}
                  className="p-2 text-gray-500 hover:text-white hover:bg-red-900/10 rounded-md transition-colors"
                  title="Actualiser"
                >
                  <RefreshCw size={15} />
                </button>
              )}
              <button
                onClick={() => setShowSettings(v => !v)}
                className={`flex items-center gap-2 px-3 py-2 text-xs rounded-md border transition-colors ${
                  showSettings
                    ? 'bg-red-900/20 border-red-700/30 text-red-400'
                    : 'bg-maretap-dark3 border-red-900/20 text-gray-400 hover:text-white'
                }`}
              >
                <Settings size={14} /> Configuration
              </button>
            </div>
          </div>

          {/* Settings panel */}
          {showSettings && (
            <div className="card">
              <h3 className="text-sm font-rajdhani font-semibold text-gray-300 uppercase tracking-wider mb-4">
                Configuration Power BI Report Server
              </h3>
              <p className="text-xs text-gray-500 mb-3">
                Entrez l'URL de votre Power BI Report Server (ex: <code className="text-gray-400">http://192.168.1.10/Reports</code>)
              </p>
              <div className="flex items-center gap-3">
                <input
                  type="text"
                  value={inputUrl}
                  onChange={e => setInputUrl(e.target.value)}
                  placeholder="http://localhost/Reports"
                  className="input-field flex-1"
                />
                <button onClick={saveServer} className="btn-primary shrink-0">
                  Sauvegarder
                </button>
              </div>
              {serverUrl && (
                <p className="text-xs text-green-400 mt-2">
                  Serveur configuré : <span className="text-gray-400">{serverUrl}</span>
                </p>
              )}
            </div>
          )}

          {/* Report frame or fallback */}
          <div className="flex-1 card overflow-hidden flex flex-col">
            {reportUrl
              ? (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <h4 className="text-sm font-rajdhani font-semibold text-white">{activeReport.name}</h4>
                      <p className="text-xs text-gray-500">{activeReport.desc}</p>
                    </div>
                    <a
                      href={reportUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-white transition-colors"
                    >
                      <ExternalLink size={13} /> Ouvrir dans un onglet
                    </a>
                  </div>
                  <iframe
                    key={iframeKey}
                    src={reportUrl}
                    className="flex-1 w-full rounded-md border border-red-900/10"
                    style={{ minHeight: '500px' }}
                    title={activeReport.name}
                    allowFullScreen
                  />
                </>
              )
              : (
                <div className="flex-1 flex flex-col items-center justify-center gap-6 text-center">
                  <BarChart2 size={48} className="text-gray-700" />
                  <div>
                    <h3 className="text-lg font-rajdhani font-semibold text-gray-400 mb-2">
                      Power BI Report Server non configuré
                    </h3>
                    <p className="text-gray-600 text-sm max-w-md">
                      Configurez l'URL de votre Report Server ci-dessus pour afficher les rapports directement dans la plateforme.
                    </p>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-3 w-full max-w-xl">
                    {DEFAULT_REPORTS.map(r => (
                      <div key={r.id} className="bg-maretap-dark3 border border-red-900/20 rounded-lg p-4 text-left">
                        <p className="text-sm text-gray-300 font-medium">{r.name}</p>
                        <p className="text-xs text-gray-600 mt-1">{r.desc}</p>
                        <span className="text-xs text-gray-700 font-mono mt-2 block">{r.file}.pbix</span>
                      </div>
                    ))}
                  </div>
                  <button
                    onClick={() => setShowSettings(true)}
                    className="btn-primary"
                  >
                    Configurer le Report Server
                  </button>
                </div>
              )
            }
          </div>

        </main>
      </div>
    </div>
  )
}
