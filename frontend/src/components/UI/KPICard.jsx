export default function KPICard({ title, value, unit, icon, color = 'gold', loading = false }) {
  const cardColor = {
    red: 'kpi-red',
    gold: 'kpi-gold',
    blue: 'kpi-blue',
    green: 'kpi-green',
  }[color] || 'kpi-gold'

  const valueColor = {
    red: 'v-red',
    gold: 'v-gold',
    blue: 'v-blue',
    green: 'v-green',
  }[color] || 'v-gold'

  const iconColor = {
    red: 'i-red',
    gold: 'i-gold',
    blue: 'i-blue',
    green: 'i-green',
  }[color] || 'i-gold'

  return (
    <div className={`kpi-card ${cardColor}`}>
      <div className={`kpi-icon ${iconColor}`}>{icon}</div>
      <div className="kpi-label">{title}</div>
      <div className={`kpi-value ${valueColor} ${loading ? 'kpi-loading' : ''}`}>{loading ? '...' : value}</div>
      <div className="kpi-unit">{unit}</div>
    </div>
  )
}
