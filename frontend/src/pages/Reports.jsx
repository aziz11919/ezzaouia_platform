import { useState } from 'react'
import Layout from '../components/Layout/Layout'

const months = [
  { value: 1, label: 'January' },
  { value: 2, label: 'February' },
  { value: 3, label: 'March' },
  { value: 4, label: 'April' },
  { value: 5, label: 'May' },
  { value: 6, label: 'June' },
  { value: 7, label: 'July' },
  { value: 8, label: 'August' },
  { value: 9, label: 'September' },
  { value: 10, label: 'October' },
  { value: 11, label: 'November' },
  { value: 12, label: 'December' },
]

export default function Reports() {
  const currentDate = new Date()
  const [month, setMonth] = useState(currentDate.getMonth() + 1)
  const [year, setYear] = useState(currentDate.getFullYear())
  const years = Array.from({ length: 11 }).map((_, i) => currentDate.getFullYear() - i)

  const reportUrl = `/reports/?download=1&month=${month}&year=${year}`

  return (
    <Layout title="Monthly PDF Report" breadcrumb="EZZAOUIA Field - CPF Zarzis">
      <div style={{ maxWidth: 520 }} className="page-panel">
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 18 }}>
          <img src="/static/img/logomaretap.png" alt="MARETAP" style={{ width: 46, height: 46, borderRadius: 8, background: '#fff', padding: 4 }} />
          <div>
            <div style={{ fontFamily: 'Rajdhani, sans-serif', fontSize: 22, fontWeight: 700, lineHeight: 1 }}>Monthly PDF Report</div>
            <div style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 4 }}>EZZAOUIA Field - CPF Zarzis</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Month</label>
            <select className="input-field" value={month} onChange={(e) => setMonth(Number(e.target.value))}>
              {months.map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 12, color: 'var(--text-muted)', marginBottom: 6 }}>Year</label>
            <select className="input-field" value={year} onChange={(e) => setYear(Number(e.target.value))}>
              {years.map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ marginTop: 18, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <a className="btn-primary" style={{ minWidth: 240, textDecoration: 'none', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }} href={reportUrl}>
            Generate PDF report
          </a>
          <a className="btn-secondary" style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }} href="/dashboard">
            Back to dashboard
          </a>
        </div>
      </div>
    </Layout>
  )
}
