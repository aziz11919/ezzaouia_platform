import { useEffect, useMemo, useState } from 'react'
import Layout from '../components/Layout/Layout'
import KPICard from '../components/UI/KPICard'
import ModuleCard from '../components/UI/ModuleCard'
import TrendChart from '../components/Charts/TrendChart'
import Top5Chart from '../components/Charts/Top5Chart'
import { kpisAPI } from '../api/kpis'

const CURRENT_YEAR = new Date().getFullYear()
const YEARS = [CURRENT_YEAR, CURRENT_YEAR - 1, CURRENT_YEAR - 2]

function toMonthShort(label) {
  if (!label) return ''
  return String(label).slice(0, 3)
}

export default function Dashboard() {
  const [year, setYear] = useState(YEARS[0])
  const [loading, setLoading] = useState(true)
  const [summary, setSummary] = useState(null)
  const [trend, setTrend] = useState([])
  const [topProducers, setTopProducers] = useState([])

  useEffect(() => {
    let active = true
    async function load() {
      setLoading(true)
      try {
        const [summaryRes, trendRes, topRes] = await Promise.all([
          kpisAPI.getSummary(year),
          kpisAPI.getTrend(year),
          kpisAPI.getTopProducers(year),
        ])
        if (!active) return
        setSummary(summaryRes.data || {})
        setTrend(Array.isArray(trendRes.data) ? trendRes.data : [])
        setTopProducers(Array.isArray(topRes.data) ? topRes.data : [])
      } catch (error) {
        if (!active) return
        setSummary(null)
        setTrend([])
        setTopProducers([])
      } finally {
        if (active) setLoading(false)
      }
    }
    load()
    return () => { active = false }
  }, [year])

  const trendLabels = useMemo(() => trend.map((row) => toMonthShort(row.month_name)), [trend])
  const trendOil = useMemo(() => trend.map((row) => Number(row.total_oil || 0)), [trend])
  const trendBsw = useMemo(() => trend.map((row) => Number(row.avg_bsw || 0)), [trend])
  const topLabels = useMemo(() => topProducers.map((row) => row.well_code), [topProducers])
  const topBopd = useMemo(() => topProducers.map((row) => Number(row.avg_bopd || 0)), [topProducers])

  return (
    <Layout title="Overview" breadcrumb="EZZAOUIA Field - CPF Zarzis">
      <div className="year-selector">
        <span className="year-label">Annee</span>
        {YEARS.map((y) => (
          <button key={y} type="button" className={`year-btn${y === year ? ' active' : ''}`} onClick={() => setYear(y)}>
            {y}
          </button>
        ))}
        {summary?.last_date ? (
          <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-dim)' }}>
            Last data: {summary.last_date}
          </span>
        ) : null}
      </div>

      <div className="section-label">Production indicators - {year}</div>
      <div className="grid-kpi">
        <KPICard
          title="Average BOPD"
          value={(summary?.avg_bopd ?? 0).toLocaleString(undefined, { maximumFractionDigits: 1 })}
          unit="barrels / day"
          color="red"
          loading={loading}
          icon={
            <svg width="18" height="18" fill="none" stroke="#E05555" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
          }
        />
        <KPICard
          title="Average BSW"
          value={(summary?.avg_bsw ?? 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}
          unit="% water cut"
          color="gold"
          loading={loading}
          icon={
            <svg width="18" height="18" fill="none" stroke="#C9A84C" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5m.75-9l3-3 2.148 2.148A12.061 12.061 0 0116.5 7.605" />
            </svg>
          }
        />
        <KPICard
          title="Average GOR"
          value={(summary?.avg_gor ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          unit="SCF / STB"
          color="blue"
          loading={loading}
          icon={
            <svg width="18" height="18" fill="none" stroke="#4D8FCC" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.25 15a4.5 4.5 0 004.5 4.5H18a3.75 3.75 0 001.332-7.257 3 3 0 00-3.758-3.848 5.25 5.25 0 00-10.233 2.33A4.502 4.502 0 002.25 15z" />
            </svg>
          }
        />
        <KPICard
          title="Total oil"
          value={(summary?.total_oil ?? summary?.total_oil_stbd ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
          unit="STB"
          color="green"
          loading={loading}
          icon={
            <svg width="18" height="18" fill="none" stroke="#4DAA7A" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
            </svg>
          }
        />
      </div>

      <div className="section-label">Analytics - {year}</div>
      <div className="charts-grid">
        <div className="chart-card">
          <div className="chart-title">Tendance Mensuelle</div>
          {trend.length ? <TrendChart labels={trendLabels} oilData={trendOil} bswData={trendBsw} /> : <div className="chart-empty">No data for {year}</div>}
        </div>

        <div className="chart-card">
          <div className="chart-title" style={{ color: '#FFD700' }}>Top 5 Puits (BOPD)</div>
          {topProducers.length ? <Top5Chart labels={topLabels} data={topBopd} /> : <div className="chart-empty">No data for {year}</div>}
        </div>
      </div>

      <div className="section-label">Modules</div>
      <div className="modules-grid">
        <ModuleCard
          to="/chatbot"
          tone="mod-red"
          title="Chatbot IA"
          description="Posez des questions sur vos donnees en langage naturel."
          icon={
            <svg width="20" height="20" fill="none" stroke="#E05555" strokeWidth="1.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1 1 .26 2.798-1.17 2.798H4.17c-1.43 0-2.17-1.798-1.17-2.798L4.4 15.3" />
            </svg>
          }
        />
        <ModuleCard
          to="/ingestion/upload"
          tone="mod-blue"
          title="Import fichiers"
          description="Importez vos rapports PDF, Word et Excel."
          icon={
            <svg width="20" height="20" fill="none" stroke="#4D8FCC" strokeWidth="1.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
          }
        />
        <ModuleCard
          to="/reports"
          tone="mod-yellow"
          title="PDF Report"
          description="Generer des rapports PDF de production mensuelle."
          icon={
            <svg width="20" height="20" fill="none" stroke="#FFD700" strokeWidth="1.5" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2h-3.5a1 1 0 01-.8-.4l-1.4-1.9a1 1 0 00-.8-.4H8a2 2 0 00-2 2v15a2 2 0 002 2z" />
            </svg>
          }
        />
      </div>

      <div className="section-label">Top producers - {year}</div>
      <div className="table-card">
        <div className="table-header">
          <div className="table-title">Top 5 wells by cumulative oil</div>
          <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>Total gas: {(summary?.total_gas_mscf ?? 0).toLocaleString()} MSCF</div>
        </div>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Well</th>
              <th>Name</th>
              <th>Total oil (STB)</th>
              <th>Avg BOPD</th>
              <th>Avg BSW (%)</th>
            </tr>
          </thead>
          <tbody>
            {topProducers.length ? topProducers.map((well, index) => (
              <tr key={well.well_code || index}>
                <td style={{ color: 'var(--text-dim)' }}>{index + 1}</td>
                <td style={{ color: 'var(--text)', fontWeight: 600, fontFamily: 'Rajdhani, sans-serif' }}>{well.well_code}</td>
                <td>{well.well_name || '-'}</td>
                <td style={{ color: 'var(--green)' }}>{Number(well.total_oil || 0).toLocaleString()}</td>
                <td style={{ color: 'var(--red)' }}>{Number(well.avg_bopd || 0).toFixed(1)}</td>
                <td style={{ color: 'var(--gold)' }}>{Number(well.avg_bsw || 0).toFixed(2)}</td>
              </tr>
            )) : (
              <tr>
                <td colSpan={6} className="empty-row">No production data available for {year}.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </Layout>
  )
}
