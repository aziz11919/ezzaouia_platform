const variants = {
  success: 'bg-green-900/30 text-green-400 border border-green-700/30',
  error:   'bg-red-900/30 text-red-400 border border-red-700/30',
  warning: 'bg-yellow-900/30 text-yellow-400 border border-yellow-700/30',
  info:    'bg-blue-900/30 text-blue-400 border border-blue-700/30',
  default: 'bg-gray-800 text-gray-300 border border-gray-700/30',
}

export default function Badge({ children, variant = 'default', className = '' }) {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${variants[variant]} ${className}`}>
      {children}
    </span>
  )
}
