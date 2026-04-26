import { Link } from 'react-router-dom'

export default function ModuleCard({ to, title, description, icon, tone = 'mod-red' }) {
  return (
    <Link to={to} className={`module-card ${tone}`}>
      <div className="module-icon">{icon}</div>
      <div className="module-title">{title}</div>
      <div className="module-desc">{description}</div>
    </Link>
  )
}
