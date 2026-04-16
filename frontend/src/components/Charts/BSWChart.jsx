import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis,
  CartesianGrid, Tooltip,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-maretap-dark3 border border-red-900/20 rounded-md px-3 py-2 text-xs">
      <p className="text-gray-400 mb-1">{label}</p>
      <p className="text-yellow-400">BSW: <strong>{payload[0]?.value?.toFixed(1)}%</strong></p>
    </div>
  )
}

export default function BSWChart({ data = [], loading = false }) {
  if (loading) {
    return <div className="h-40 animate-pulse bg-maretap-dark3 rounded-lg" />
  }

  return (
    <ResponsiveContainer width="100%" height={160}>
      <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
        <defs>
          <linearGradient id="bswGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#D4AC0D" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#D4AC0D" stopOpacity={0}   />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(192,57,43,0.08)" />
        <XAxis dataKey="label" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
        <Tooltip content={<CustomTooltip />} />
        <Area type="monotone" dataKey="bsw_avg" stroke="#D4AC0D" strokeWidth={2} fill="url(#bswGrad)" />
      </AreaChart>
    </ResponsiveContainer>
  )
}
