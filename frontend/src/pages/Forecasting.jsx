import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine, Area, ComposedChart,
} from 'recharts'
import Layout from '../components/Layout/Layout'
import { forecastingAPI } from '../api/forecasting'

// ─── Constants ────────────────────────────────────────────────────────────────

const KPI_OPTIONS = [
  { value: 'oil',       label: 'Oil (BOPD)' },
  { value: 'gas',       label: 'Gas (MSCF)' },
  { value: 'water',     label: 'Water (BWPD)' },
  { value: 'bsw',       label: 'BSW (%)' },
  { value: 'gor',       label: 'GOR (SCF/STB)' },
  { value: 'prodhours', label: 'Prod Hours' },
]

const PERIOD_OPTIONS = [12, 24, 36, 60]

const MODE_OPTIONS = [
  { value: 'field',     label: 'Field Total' },
  { value: 'well',      label: 'By Well' },
  { value: 'all_wells', label: 'All Wells' },
]

const TODAY = new Date().toISOString().slice(0, 10)

const QUARTER_COLORS = { 1: '#4D8FCC', 2: '#4DAA7A', 3: '#C9A84C', 4: '#E05555' }

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(n, d = 0) {
  if (n == null) return '-'
  return Number(n).toLocaleString(undefined, { maximumFractionDigits: d })
}

function buildChartData(result) {
  if (!result || !result.models) return []

  const map = {}

  // Historical
  const historical = result.models.prophet?.historical || []
  for (const pt of historical) {
    map[pt.date] = { date: pt.date, historical: pt.value }
  }

  // Prophet forecast + confidence band
  for (const pt of result.models.prophet?.forecast || []) {
    map[pt.date] = {
      ...map[pt.date],
      date: pt.date,
      prophet: pt.yhat,
      prophet_lower: pt.yhat_lower,
      prophet_upper: pt.yhat_upper,
    }
  }

  // SARIMA
  for (const pt of result.models.sarima?.forecast || []) {
    if (map[pt.date]) map[pt.date].sarima = pt.yhat
    else map[pt.date] = { date: pt.date, sarima: pt.yhat }
  }

  // ARIMA
  for (const pt of result.models.arima?.forecast || []) {
    if (map[pt.date]) map[pt.date].arima = pt.yhat
    else map[pt.date] = { date: pt.date, arima: pt.yhat }
  }

  // Holt-Winters
  for (const pt of result.models.holt_winters?.forecast || []) {
    if (map[pt.date]) map[pt.date].hw = pt.yhat
    else map[pt.date] = { date: pt.date, hw: pt.yhat }
  }

  return Object.values(map).sort((a, b) => a.date.localeCompare(b.date))
}

function buildQuarterlyData(result) {
  if (!result?.models?.prophet?.quarterly) return []
  return result.models.prophet.quarterly.map((q) => ({
    label: `${q.year} Q${q.quarter}`,
    year: q.year,
    quarter: q.quarter,
    value: Math.round(q.yhat || 0),
  }))
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function StatCard({ title, children, accent }) {
  return (
    <div style={{
      background: 'var(--surface)',
      border: `1px solid ${accent || 'var(--border)'}`,
      borderRadius: 8,
      padding: '16px 20px',
      minWidth: 220,
      flex: 1,
    }}>
      <div style={{ fontSize: 11, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function StationarityCard({ data }) {
  if (!data) return null
  const ok = data.is_stationary
  return (
    <StatCard title="Stationarity (ADF Test)" accent={ok ? 'var(--green)' : 'var(--gold)'}>
      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
        <div>
          <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>ADF Statistic</div>
          <div style={{ color: 'var(--text)', fontFamily: 'Rajdhani, sans-serif', fontSize: 18 }}>{data.adf_stat ?? '-'}</div>
        </div>
        <div>
          <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>p-value</div>
          <div style={{ color: 'var(--text)', fontFamily: 'Rajdhani, sans-serif', fontSize: 18 }}>{data.p_value ?? '-'}</div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{
            background: ok ? 'rgba(77,170,122,0.15)' : 'rgba(201,168,76,0.15)',
            color: ok ? 'var(--green)' : 'var(--gold)',
            border: `1px solid ${ok ? 'var(--green)' : 'var(--gold)'}`,
            borderRadius: 4,
            padding: '4px 10px',
            fontSize: 12,
            fontWeight: 700,
          }}>
            {ok ? 'Stationary' : 'Non-stationary'}
          </span>
        </div>
      </div>
      {data.critical_values && (
        <div style={{ marginTop: 8, fontSize: 11, color: 'var(--text-dim)' }}>
          Critical: 1%={data.critical_values['1%']} · 5%={data.critical_values['5%']} · 10%={data.critical_values['10%']}
        </div>
      )}
    </StatCard>
  )
}

function SeasonalityCard({ data }) {
  if (!data) return null
  const detected = data.detected
  const accentColor = detected ? 'var(--blue)' : 'var(--border)'

  return (
    <StatCard title="Seasonality Detection" accent={accentColor}>
      {/* Status badge + interpretation */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12, flexWrap: 'wrap' }}>
        <span style={{
          background: detected ? 'rgba(77,143,204,0.15)' : 'rgba(100,100,120,0.1)',
          color: detected ? 'var(--blue)' : 'var(--text-dim)',
          border: `1px solid ${detected ? 'var(--blue)' : 'var(--border)'}`,
          borderRadius: 4,
          padding: '3px 10px',
          fontSize: 12,
          fontWeight: 700,
        }}>
          {detected ? 'Seasonal' : 'Not seasonal'}
        </span>
        {data.interpretation && (
          <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>{data.interpretation}</span>
        )}
        {data.reason && (
          <span style={{ fontSize: 12, color: 'var(--text-dim)' }}>{data.reason}</span>
        )}
      </div>

      {/* Metrics row */}
      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
        {data.strength != null && (
          <div>
            <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>Strength</div>
            <div style={{ color: 'var(--text)', fontFamily: 'Rajdhani, sans-serif', fontSize: 18 }}>
              {(data.strength * 100).toFixed(1)}%
            </div>
          </div>
        )}
        {data.acf_lag12 != null && (
          <div>
            <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>ACF lag-12</div>
            <div style={{ color: 'var(--text)', fontFamily: 'Rajdhani, sans-serif', fontSize: 18 }}>
              {data.acf_lag12.toFixed(2)}
            </div>
          </div>
        )}
        {data.trend_direction && (
          <div>
            <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>Trend</div>
            <div style={{
              color: data.trend_direction === 'increasing' ? 'var(--green)' : 'var(--red)',
              fontFamily: 'Rajdhani, sans-serif',
              fontSize: 16,
              fontWeight: 700,
              textTransform: 'capitalize',
            }}>
              {data.trend_direction === 'increasing' ? '↑' : '↓'} {data.trend_direction}
            </div>
          </div>
        )}
      </div>

      {/* Peak / low months */}
      {(data.peak_month_name || data.low_month_name) && (
        <div style={{ display: 'flex', gap: 16, marginTop: 10, flexWrap: 'wrap' }}>
          {data.peak_month_name && (
            <div>
              <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>Peak month</div>
              <div style={{ color: 'var(--green)', fontSize: 13, fontWeight: 600 }}>
                ↑ {data.peak_month_name}
              </div>
            </div>
          )}
          {data.low_month_name && (
            <div>
              <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>Low month</div>
              <div style={{ color: 'var(--red)', fontSize: 13, fontWeight: 600 }}>
                ↓ {data.low_month_name}
              </div>
            </div>
          )}
        </div>
      )}
    </StatCard>
  )
}

function ModelComparisonTable({ comparison, bestModel }) {
  if (!comparison?.length) return null
  return (
    <div className="table-card">
      <div className="table-header">
        <div className="table-title">Model Comparison</div>
        <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>Lower MAPE = better fit</div>
      </div>
      <table>
        <thead>
          <tr>
            <th>Model</th>
            <th>MAE</th>
            <th>RMSE</th>
            <th>MAPE (%)</th>
            <th>Rank</th>
          </tr>
        </thead>
        <tbody>
          {comparison.map((row) => (
            <tr key={row.model} style={row.is_best ? { background: 'rgba(201,168,76,0.08)' } : {}}>
              <td style={{ fontWeight: row.is_best ? 700 : 400, color: row.is_best ? 'var(--gold)' : 'var(--text)' }}>
                {row.model}
              </td>
              <td>{fmt(row.mae, 1)}</td>
              <td>{fmt(row.rmse, 1)}</td>
              <td style={{ color: row.is_best ? 'var(--gold)' : 'var(--text)' }}>{fmt(row.mape, 2)}</td>
              <td>
                {row.is_best && (
                  <span style={{
                    background: 'rgba(201,168,76,0.15)',
                    color: 'var(--gold)',
                    border: '1px solid var(--gold)',
                    borderRadius: 4,
                    padding: '2px 8px',
                    fontSize: 11,
                    fontWeight: 700,
                  }}>
                    BEST
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function ForecastMainChart({ chartData, visibleModels, kpi }) {
  const kpiUnit = KPI_OPTIONS.find((k) => k.value === kpi)?.label || kpi

  return (
    <ResponsiveContainer width="100%" height={380}>
      <ComposedChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
        <XAxis
          dataKey="date"
          tickFormatter={(d) => d?.slice(0, 7)}
          tick={{ fill: 'var(--text-dim)', fontSize: 10 }}
          interval={Math.max(1, Math.floor(chartData.length / 12)) - 1}
        />
        <YAxis tick={{ fill: 'var(--text-dim)', fontSize: 10 }} width={60} />
        <Tooltip
          contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }}
          labelStyle={{ color: 'var(--text-dim)' }}
          formatter={(value, name) => [fmt(value, 1), name]}
        />
        <Legend wrapperStyle={{ fontSize: 12, color: 'var(--text-dim)' }} />
        <ReferenceLine x={TODAY} stroke="rgba(255,255,255,0.25)" strokeDasharray="4 2" label={{ value: 'Today', fill: 'var(--text-dim)', fontSize: 10 }} />

        {/* Confidence band (Prophet) */}
        {visibleModels.prophet && (
          <Area
            dataKey="prophet_upper"
            fill="rgba(230,130,50,0.12)"
            stroke="none"
            name="Prophet CI"
            legendType="none"
          />
        )}
        {visibleModels.prophet && (
          <Area
            dataKey="prophet_lower"
            fill="rgba(20,20,30,1)"
            stroke="none"
            name="Prophet CI lower"
            legendType="none"
          />
        )}

        <Line dataKey="historical" name="Historical" stroke="#4D8FCC" strokeWidth={2} dot={false} connectNulls />
        {visibleModels.prophet && (
          <Line dataKey="prophet" name="Prophet" stroke="#E08230" strokeWidth={2} dot={false} connectNulls strokeDasharray="0" />
        )}
        {visibleModels.sarima && (
          <Line dataKey="sarima" name="SARIMA" stroke="#E05555" strokeWidth={1.5} dot={false} strokeDasharray="5 3" connectNulls />
        )}
        {visibleModels.arima && (
          <Line dataKey="arima" name="ARIMA" stroke="#4DAA7A" strokeWidth={1.5} dot={false} strokeDasharray="5 3" connectNulls />
        )}
        {visibleModels.holt_winters && (
          <Line dataKey="hw" name="Holt-Winters" stroke="#A07FD0" strokeWidth={1.5} dot={false} strokeDasharray="5 3" connectNulls />
        )}
      </ComposedChart>
    </ResponsiveContainer>
  )
}

function QuarterlyBarChart({ data }) {
  if (!data?.length) return null
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
        <XAxis dataKey="label" tick={{ fill: 'var(--text-dim)', fontSize: 10 }} />
        <YAxis tick={{ fill: 'var(--text-dim)', fontSize: 10 }} width={60} />
        <Tooltip
          contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }}
          formatter={(v) => [fmt(v, 0), 'Production']}
        />
        <Bar dataKey="value" name="Production">
          {data.map((entry, i) => (
            <rect key={i} fill={QUARTER_COLORS[entry.quarter] || '#4D8FCC'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function WellRankingChart({ wells }) {
  if (!wells?.length) return null
  const top10 = wells.slice(0, 10)
  const barData = top10.map((w) => ({
    name: w.well_code,
    value: Math.round(w.forecast_2030 || 0),
    trend: w.trend,
  }))

  return (
    <ResponsiveContainer width="100%" height={Math.max(200, top10.length * 36)}>
      <BarChart data={barData} layout="vertical" margin={{ top: 5, right: 40, left: 60, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
        <XAxis type="number" tick={{ fill: 'var(--text-dim)', fontSize: 10 }} />
        <YAxis type="category" dataKey="name" tick={{ fill: 'var(--text)', fontSize: 12, fontFamily: 'Rajdhani, sans-serif' }} width={55} />
        <Tooltip
          contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, fontSize: 12 }}
          formatter={(v) => [fmt(v, 0), 'Forecast 2030']}
        />
        <Bar dataKey="value" name="2030 Forecast" radius={[0, 4, 4, 0]}>
          {barData.map((entry, i) => (
            <rect key={i} fill={entry.trend === 'increasing' ? '#4DAA7A' : '#E05555'} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function Forecasting() {
  const [kpi, setKpi] = useState('oil')
  const [mode, setMode] = useState('field')
  const [wellKey, setWellKey] = useState('')
  const [periods, setPeriods] = useState(60)
  const [wells, setWells] = useState([])
  const [result, setResult] = useState(null)
  const [allWellsResult, setAllWellsResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [visibleModels, setVisibleModels] = useState({ prophet: true, sarima: true, arima: true, holt_winters: true })

  // Fetch well list on mount
  useEffect(() => {
    forecastingAPI.getWellList()
      .then((res) => setWells(res.data?.wells || []))
      .catch(() => {})
  }, [])

  const runForecast = useCallback(async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    setAllWellsResult(null)

    try {
      if (mode === 'all_wells') {
        const res = await forecastingAPI.getAllWells(kpi)
        setAllWellsResult(res.data)
      } else if (mode === 'well') {
        if (!wellKey) { setError('Please select a well.'); setLoading(false); return }
        const res = await forecastingAPI.getWell(wellKey, kpi, periods)
        if (res.data?.error) setError(res.data.error)
        else setResult(res.data)
      } else {
        const res = await forecastingAPI.getField(kpi, periods)
        if (res.data?.error) setError(res.data.error)
        else setResult(res.data)
      }
    } catch (err) {
      setError('API request failed. Check that the backend is running and models are installed.')
    } finally {
      setLoading(false)
    }
  }, [kpi, mode, wellKey, periods])

  const chartData = useMemo(() => buildChartData(result), [result])
  const quarterlyData = useMemo(() => buildQuarterlyData(result), [result])

  const toggleModel = (m) => setVisibleModels((prev) => ({ ...prev, [m]: !prev[m] }))

  return (
    <Layout title="Production Forecasting" breadcrumb="EZZAOUIA Field — Time Series Forecast">

      {/* ── Controls ─────────────────────────────────────────────── */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end', marginBottom: 24 }}>
        {/* KPI */}
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>KPI</div>
          <select
            value={kpi}
            onChange={(e) => setKpi(e.target.value)}
            style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 6, padding: '6px 10px', fontSize: 13 }}
          >
            {KPI_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        {/* Mode */}
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Mode</div>
          <div style={{ display: 'flex', gap: 0, borderRadius: 6, overflow: 'hidden', border: '1px solid var(--border)' }}>
            {MODE_OPTIONS.map((o) => (
              <button
                key={o.value}
                type="button"
                onClick={() => setMode(o.value)}
                style={{
                  background: mode === o.value ? 'var(--red)' : 'var(--surface)',
                  color: mode === o.value ? '#fff' : 'var(--text-dim)',
                  border: 'none',
                  padding: '6px 14px',
                  fontSize: 12,
                  cursor: 'pointer',
                  fontFamily: 'Rajdhani, sans-serif',
                  letterSpacing: '0.04em',
                }}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>

        {/* Well selector */}
        {mode === 'well' && (
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Well</div>
            <select
              value={wellKey}
              onChange={(e) => setWellKey(e.target.value)}
              style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', borderRadius: 6, padding: '6px 10px', fontSize: 13, minWidth: 180 }}
            >
              <option value="">— select —</option>
              {wells.map((w) => (
                <option key={w.well_key} value={w.well_key}>{w.well_code} — {w.libelle}</option>
              ))}
            </select>
          </div>
        )}

        {/* Periods */}
        {mode !== 'all_wells' && (
          <div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Forecast horizon</div>
            <div style={{ display: 'flex', gap: 0, borderRadius: 6, overflow: 'hidden', border: '1px solid var(--border)' }}>
              {PERIOD_OPTIONS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPeriods(p)}
                  style={{
                    background: periods === p ? 'rgba(77,143,204,0.3)' : 'var(--surface)',
                    color: periods === p ? 'var(--blue)' : 'var(--text-dim)',
                    border: 'none',
                    padding: '6px 12px',
                    fontSize: 12,
                    cursor: 'pointer',
                    fontFamily: 'Rajdhani, sans-serif',
                  }}
                >
                  {p}m
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Run button */}
        <button
          type="button"
          onClick={runForecast}
          disabled={loading}
          style={{
            background: loading ? 'rgba(201,40,40,0.4)' : 'var(--red)',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            padding: '8px 22px',
            fontSize: 13,
            fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
            fontFamily: 'Rajdhani, sans-serif',
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
            alignSelf: 'flex-end',
          }}
        >
          {loading ? 'Running…' : 'Run Forecast'}
        </button>
      </div>

      {/* ── Loading state ─────────────────────────────────────────── */}
      {loading && (
        <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--text-dim)' }}>
          <div style={{ fontSize: 32, marginBottom: 12 }}>⏳</div>
          <div style={{ fontSize: 14, color: 'var(--text)', marginBottom: 6 }}>Running forecasting models…</div>
          <div style={{ fontSize: 12 }}>
            {mode === 'all_wells'
              ? 'Processing all active wells — this may take 2-5 minutes.'
              : 'Running 4 models (Prophet, SARIMA, ARIMA, Holt-Winters) — typically 30-60 seconds.'}
          </div>
        </div>
      )}

      {/* ── Error state ───────────────────────────────────────────── */}
      {!loading && error && (
        <div style={{
          background: 'rgba(224,85,85,0.1)',
          border: '1px solid var(--red)',
          borderRadius: 8,
          padding: '16px 20px',
          color: 'var(--red)',
          fontSize: 13,
          marginBottom: 24,
        }}>
          {error}
        </div>
      )}

      {/* ── All Wells mode ────────────────────────────────────────── */}
      {!loading && allWellsResult && mode === 'all_wells' && (
        <>
          <div className="section-label">Well Ranking by 2030 Forecast ({allWellsResult.kpi?.toUpperCase()})</div>
          <div className="chart-card" style={{ marginBottom: 24 }}>
            <div className="chart-title">Top 10 Wells — Projected 2030 Production</div>
            <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 12 }}>
              Green = increasing trend · Red = declining trend
            </div>
            <WellRankingChart wells={allWellsResult.wells} />
          </div>

          <div className="table-card">
            <div className="table-header">
              <div className="table-title">All Wells — Prophet Forecast Summary</div>
            </div>
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Well</th>
                  <th>Name</th>
                  <th>MAE</th>
                  <th>MAPE (%)</th>
                  <th>Trend</th>
                  <th>2030 Forecast</th>
                </tr>
              </thead>
              <tbody>
                {allWellsResult.wells?.map((w, i) => (
                  <tr key={w.well_key}>
                    <td style={{ color: 'var(--text-dim)' }}>{i + 1}</td>
                    <td style={{ fontWeight: 600, fontFamily: 'Rajdhani, sans-serif', color: 'var(--text)' }}>{w.well_code}</td>
                    <td>{w.well_name}</td>
                    <td>{fmt(w.metrics?.mae, 1)}</td>
                    <td>{fmt(w.metrics?.mape, 2)}</td>
                    <td style={{ color: w.trend === 'increasing' ? 'var(--green)' : 'var(--red)', fontWeight: 700 }}>
                      {w.trend === 'increasing' ? '↑ Rising' : '↓ Declining'}
                    </td>
                    <td style={{ color: 'var(--gold)' }}>{fmt(w.forecast_2030, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ── Single forecast result ────────────────────────────────── */}
      {!loading && result && mode !== 'all_wells' && (
        <>
          {/* Data analysis cards */}
          <div className="section-label">Data Analysis</div>
          <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
            <StationarityCard data={result.stationarity} />
            <SeasonalityCard data={result.seasonality} />
            <StatCard title="Dataset">
              <div style={{ color: 'var(--text)', fontFamily: 'Rajdhani, sans-serif', fontSize: 22 }}>{result.data_points}</div>
              <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>monthly observations</div>
              <div style={{ color: 'var(--text-dim)', fontSize: 11, marginTop: 4 }}>
                {result.date_range?.start?.slice(0, 7)} → {result.date_range?.end?.slice(0, 7)}
              </div>
            </StatCard>
            {result.best_model && (
              <StatCard title="Best Model" accent="var(--gold)">
                <div style={{ color: 'var(--gold)', fontFamily: 'Rajdhani, sans-serif', fontSize: 22, textTransform: 'uppercase' }}>
                  {result.models[result.best_model]?.model}
                </div>
                <div style={{ color: 'var(--text-dim)', fontSize: 11 }}>
                  MAPE: {result.models[result.best_model]?.metrics?.mape}%
                </div>
              </StatCard>
            )}
          </div>

          {/* Model toggles */}
          <div style={{ display: 'flex', gap: 8, marginBottom: 16, flexWrap: 'wrap' }}>
            {[
              { key: 'prophet',      label: 'Prophet',      color: '#E08230' },
              { key: 'sarima',       label: 'SARIMA',       color: '#E05555' },
              { key: 'arima',        label: 'ARIMA',        color: '#4DAA7A' },
              { key: 'holt_winters', label: 'Holt-Winters', color: '#A07FD0' },
            ].filter((m) => result.models[m.key]).map((m) => (
              <button
                key={m.key}
                type="button"
                onClick={() => toggleModel(m.key)}
                style={{
                  background: visibleModels[m.key] ? `${m.color}22` : 'var(--surface)',
                  border: `1px solid ${visibleModels[m.key] ? m.color : 'var(--border)'}`,
                  color: visibleModels[m.key] ? m.color : 'var(--text-dim)',
                  borderRadius: 20,
                  padding: '4px 14px',
                  fontSize: 12,
                  cursor: 'pointer',
                  fontFamily: 'Rajdhani, sans-serif',
                  transition: 'all 0.15s',
                }}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Main forecast chart */}
          <div className="section-label">Forecast Chart — {KPI_OPTIONS.find((k) => k.value === kpi)?.label}</div>
          <div className="chart-card" style={{ marginBottom: 24 }}>
            <ForecastMainChart chartData={chartData} visibleModels={visibleModels} kpi={kpi} />
          </div>

          {/* Model comparison table */}
          <div className="section-label">Model Comparison</div>
          <ModelComparisonTable comparison={result.comparison} bestModel={result.best_model} />

          {/* Quarterly bar chart — Prophet */}
          {quarterlyData.length > 0 && (
            <>
              <div className="section-label" style={{ marginTop: 24 }}>Quarterly Forecast — Prophet (2026–2030)</div>
              <div className="chart-card">
                <div className="chart-title">Seasonal Production Pattern by Quarter</div>
                <div style={{ display: 'flex', gap: 16, marginBottom: 8, fontSize: 11, color: 'var(--text-dim)' }}>
                  {[1, 2, 3, 4].map((q) => (
                    <span key={q} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ display: 'inline-block', width: 10, height: 10, borderRadius: 2, background: QUARTER_COLORS[q] }} />
                      Q{q}
                    </span>
                  ))}
                </div>
                <QuarterlyBarChart data={quarterlyData} />
              </div>
            </>
          )}
        </>
      )}

      {/* ── Empty state ───────────────────────────────────────────── */}
      {!loading && !result && !allWellsResult && !error && (
        <div style={{ textAlign: 'center', padding: '80px 20px', color: 'var(--text-dim)' }}>
          <div style={{ fontSize: 48, marginBottom: 16, opacity: 0.3 }}>📈</div>
          <div style={{ fontSize: 14 }}>Select a KPI and mode, then click <strong style={{ color: 'var(--text)' }}>Run Forecast</strong></div>
        </div>
      )}

    </Layout>
  )
}
