import { X } from 'lucide-react'

const styles = {
  error:   'bg-red-900/30 border-red-700/50 text-red-300',
  success: 'bg-green-900/30 border-green-700/50 text-green-300',
  warning: 'bg-yellow-900/30 border-yellow-700/50 text-yellow-300',
  info:    'bg-blue-900/30 border-blue-700/50 text-blue-300',
}

export default function AlertBanner({ type = 'error', message, onClose }) {
  if (!message) return null
  return (
    <div className={`flex items-center justify-between gap-3 px-4 py-3 rounded-md border text-sm ${styles[type]}`}>
      <span>{message}</span>
      {onClose && (
        <button onClick={onClose} className="shrink-0 opacity-70 hover:opacity-100 transition-opacity">
          <X size={16} />
        </button>
      )}
    </div>
  )
}
