import DarkModeToggle from '../UI/DarkModeToggle'

function formatDate() {
  return new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

export default function Header({ title, breadcrumb, rightNode }) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="page-title">{title}</div>
        {breadcrumb && (
          <div className="breadcrumb">
            <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
            <span>{breadcrumb}</span>
          </div>
        )}
      </div>

      <div className="topbar-right">
        {rightNode}
        <div className="topbar-date">{formatDate()}</div>
        <DarkModeToggle />
      </div>
    </header>
  )
}
