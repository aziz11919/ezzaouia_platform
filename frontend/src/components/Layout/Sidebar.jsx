import { Link, NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

const sections = [
  {
    label: 'Dashboard',
    items: [
      {
        to: '/dashboard',
        label: 'Overview',
        badge: 'Home',
        roles: ['admin', 'ingenieur', 'direction'],
        icon: (
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
          </svg>
        ),
      },
    ],
  },
  {
    label: 'Modules',
    items: [
      {
        to: '/chatbot',
        label: 'AI Assistant',
        roles: ['admin', 'ingenieur', 'direction'],
        icon: (
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1 1 .26 2.798-1.17 2.798H4.17c-1.43 0-2.17-1.798-1.17-2.798L4.4 15.3" />
          </svg>
        ),
      },
      {
        to: '/ingestion/upload',
        label: 'File Import',
        roles: ['admin', 'ingenieur', 'direction'],
        icon: (
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
        ),
      },
      {
        to: '/bibliotheque',
        label: 'Library',
        roles: ['admin', 'ingenieur', 'direction'],
        icon: (
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        ),
      },
      {
        to: '/reports',
        label: 'PDF Report',
        roles: ['admin', 'ingenieur', 'direction'],
        icon: (
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 10v6m0 0l-3-3m3 3l3-3M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2h-3.5a1 1 0 01-.8-.4l-1.4-1.9a1 1 0 00-.8-.4H8a2 2 0 00-2 2v15a2 2 0 002 2z" />
          </svg>
        ),
      },
      {
        to: '/powerbi',
        label: 'Power BI',
        roles: ['admin', 'ingenieur', 'direction'],
        icon: (
          <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
          </svg>
        ),
      },
    ],
  },
]

const adminSection = {
  label: 'Administration',
  items: [
    {
      to: '/audit/log',
      label: 'Audit Log',
      badge: 'Audit',
      roles: ['admin', 'direction'],
      icon: (
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h7l5 5v11a2 2 0 01-2 2z" />
        </svg>
      ),
    },
    {
      to: '/accounts/users',
      label: 'User Management',
      badge: 'Admin',
      roles: ['admin'],
      icon: (
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
        </svg>
      ),
    },
    {
      to: '/stats',
      label: 'Chatbot Stats',
      badge: 'Admin',
      roles: ['admin'],
      icon: (
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
        </svg>
      ),
    },
  ],
}

export default function Sidebar() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const role = user?.role || ''
  const initials = [user?.first_name?.[0], user?.last_name?.[0]].filter(Boolean).join('').toUpperCase() || user?.username?.[0]?.toUpperCase() || '?'

  const isActive = (target) => {
    if (target === '/dashboard') return location.pathname === '/dashboard' || location.pathname === '/'
    return location.pathname === target || location.pathname.startsWith(`${target}/`)
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="logo-row">
          <img
            src="/static/img/logomaretap.png"
            alt="MARETAP"
            style={{ width: 42, height: 42, filter: 'drop-shadow(0 0 8px rgba(201,40,40,0.25))' }}
            onError={(e) => { e.currentTarget.style.display = 'none' }}
          />
          <div>
            <div className="logo-company">MARETAP S.A.</div>
            <div className="logo-name">EZZ<span>AOUIA</span></div>
          </div>
        </div>
        <div className="logo-tagline">Smart Production Platform</div>
      </div>

      <div className="system-status">
        <span className="status-dot" />
        <span className="status-text">System online</span>
      </div>

      <nav className="sidebar-nav">
        {sections.map((section) => {
          const items = section.items.filter((item) => item.roles.includes(role))
          if (!items.length) return null
          return (
            <div key={section.label}>
              <div className="nav-section">{section.label}</div>
              {items.map((item) => (
                <NavLink key={item.to} to={item.to} className={`sidebar-item${isActive(item.to) ? ' active' : ''}`}>
                  {item.icon}
                  <span>{item.label}</span>
                  {item.badge ? <span className="nav-badge">{item.badge}</span> : null}
                </NavLink>
              ))}
            </div>
          )
        })}

        {adminSection.items.some((item) => item.roles.includes(role)) && (
          <div>
            <div className="nav-section">{adminSection.label}</div>
            {adminSection.items.filter((item) => item.roles.includes(role)).map((item) => (
              <NavLink key={item.to} to={item.to} className={`sidebar-item${isActive(item.to) ? ' active' : ''}`}>
                {item.icon}
                <span>{item.label}</span>
                {item.badge ? <span className="nav-badge">{item.badge}</span> : null}
              </NavLink>
            ))}
          </div>
        )}
      </nav>

      <div className="sidebar-user">
        <Link to="/profile" style={{ textDecoration: 'none' }}>
          <div className="user-info" style={{ marginBottom: 10 }}>
            <div className="user-avatar">{initials}</div>
            <div>
              <div className="user-name">{user?.first_name || user?.username}</div>
              <div className="user-role">{user?.department || role}</div>
              <span className={`role-badge role-${role}`}>{role}</span>
            </div>
          </div>
        </Link>

        <div className="user-actions">
          <Link to="/profile" className="btn-soft">
            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
            Profile
          </Link>
          <button type="button" className="btn-soft btn-soft-danger" onClick={logout}>
            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75" />
            </svg>
            Logout
          </button>
        </div>
      </div>
    </aside>
  )
}
