import { Bell, RefreshCw } from 'lucide-react'
import { useAuth } from '../../contexts/AuthContext'

export default function Topbar({ title, subtitle, onRefresh, loading = false }) {
  const { user } = useAuth()

  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-red-900/20 bg-maretap-dark2/50 backdrop-blur-sm">
      <div>
        <h1 className="text-lg font-rajdhani font-semibold text-white tracking-wider uppercase">
          {title}
        </h1>
        {subtitle && <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-3">
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={loading}
            className="p-2 text-gray-500 hover:text-white hover:bg-red-900/10 rounded-md transition-colors disabled:opacity-40"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
        )}
        <button className="p-2 text-gray-500 hover:text-white hover:bg-red-900/10 rounded-md transition-colors relative">
          <Bell size={16} />
        </button>
        <div className="h-6 w-px bg-red-900/20" />
        <span className="text-sm text-gray-400 hidden sm:block">
          {user?.first_name ? `${user.first_name} ${user.last_name || ''}`.trim() : user?.username}
        </span>
      </div>
    </header>
  )
}
