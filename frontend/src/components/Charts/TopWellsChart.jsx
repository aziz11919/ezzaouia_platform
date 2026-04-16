import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Cell,
} from 'recharts'

const COLORS = ['#C0392B', '#E74C3C', '#D4AC0D', '#2E86C1', '#27AE60']

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-maretap-dark3 border border-red-900/20 rounded-md px-3 py-2 text-xs">
      <p className="text-gray-400 mb-1">{label}</p>
      <p className="text-white">BOPD: <strong>{payload[0]?.value?.toLocaleString()}</strong></p>
    </div>
  )
}

export default function TopWellsChart({ data = [], loading = false }) {
  if (loading) {
    return <div className="h-52 animate-pulse bg-maretap-dark3 rounded-lg" />
  }

  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} layout="vertical" margin={{ top: 5, right: 20, left: 20, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(192,57,43,0.08)" horizontal={false} />
        <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis type="category" dataKey="well_code" tick={{ fill: '#9ca3af', fontSize: 11 }} axisLine={false} tickLine={false} width={80} />
        <Tooltip content={<CustomTooltip />} />
        <Bar dataKey="avg_bopd" name="BOPD" radius={[0, 3, 3, 0]}>
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
