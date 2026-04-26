import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Chart, registerables } from 'chart.js'
import { useTheme } from '../contexts/ThemeContext'
import { useAuth } from '../contexts/AuthContext'
import { chatbotAPI } from '../api/chatbot'
import './Stats.css'

Chart.register(...registerables)

/* ─────────── DailyChart ─────────── */
function DailyChart({ labels, values }) {
  const canvasRef = useRef(null)
  const chartRef  = useRef(null)
  const { isDark } = useTheme()

  useEffect(() => {
    if (!canvasRef.current) return
    const axisColor = isDark ? '#7F93AE' : '#4A5568'
    const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)'
    if (chartRef.current) chartRef.current.destroy()
    chartRef.current = new Chart(canvasRef.current, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: 'Questions',
          data: values,
          borderColor: '#C0392B',
          backgroundColor: 'rgba(192,57,43,0.18)',
          fill: true,
          tension: 0.3,
          borderWidth: 2,
          pointRadius: 2,
        }],
      },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: axisColor } } },
        scales: {
          x: { ticks: { color: axisColor, maxRotation: 45, minRotation: 45 }, grid: { color: gridColor } },
          y: { ticks: { color: axisColor, precision: 0 }, grid: { color: gridColor } },
        },
      },
    })
    return () => chartRef.current?.destroy()
  }, [labels, values, isDark])

  return <canvas ref={canvasRef} style={{ width: '100%', height: '100%' }} />
}

/* ─────────── PeakChart ─────────── */
function PeakChart({ labels, values }) {
  const canvasRef = useRef(null)
  const chartRef  = useRef(null)
  const { isDark } = useTheme()

  useEffect(() => {
    if (!canvasRef.current) return
    const axisColor = isDark ? '#7F93AE' : '#4A5568'
    const gridColor = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.08)'
    if (chartRef.current) chartRef.current.destroy()
    chartRef.current = new Chart(canvasRef.current, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Questions',
          data: values,
          backgroundColor: 'rgba(192,57,43,0.7)',
          borderColor: '#C0392B',
          borderWidth: 1,
        }],
      },
      options: {
        maintainAspectRatio: false,
        plugins: { legend: { labels: { color: axisColor } } },
        scales: {
          x: { ticks: { color: axisColor, maxRotation: 90, minRotation: 90 }, grid: { color: gridColor } },
          y: { ticks: { color: axisColor, precision: 0 }, grid: { color: gridColor } },
        },
      },
    })
    return () => chartRef.current?.destroy()
  }, [labels, values, isDark])

  return <canvas ref={canvasRef} style={{ width: '100%', height: '100%' }} />
}

/* ─────────── Main Stats page ─────────── */
export default function Stats() {
  const { toggle: toggleTheme, isDark } = useTheme()
  const { user, logout } = useAuth()
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState('')
  const [date,    setDate]    = useState('')

  useEffect(() => {
    setDate(new Date().toLocaleDateString('en-US', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }))
    chatbotAPI.getStats()
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.error || 'Failed to load stats'))
      .finally(() => setLoading(false))
  }, [])

  const initials = [user?.first_name?.[0], user?.last_name?.[0]].filter(Boolean).join('').toUpperCase()
    || user?.username?.[0]?.toUpperCase() || '?'
  const displayName = user
    ? (user.first_name && user.last_name ? `${user.first_name} ${user.last_name}` : user.username)
    : ''

  return (
    <div className="stats-page">

      {/* ── Sidebar ── */}
      <div className="stats-sidebar">
        <div className="stats-sidebar-logo">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
            <img
              src="/static/img/logomaretap.png"
              alt="MARETAP"
              className="stats-logo-img"
            />
            <div>
              <div className="stats-logo-company">MARETAP S.A.</div>
              <div className="stats-logo-name">EZZ<span>AOUIA</span></div>
            </div>
          </div>
          <div className="stats-logo-tagline">Smart Production Platform</div>
        </div>

        <nav className="stats-sidebar-nav">
          <div className="stats-nav-section">Dashboard</div>
          <Link to="/dashboard" className="stats-nav-item">
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"/>
            </svg>
            Overview
          </Link>

          <div className="stats-nav-section">Modules</div>
          <Link to="/chatbot" className="stats-nav-item">
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1 1 .26 2.798-1.17 2.798H4.17c-1.43 0-2.17-1.798-1.17-2.798L4.4 15.3"/>
            </svg>
            AI Assistant
          </Link>
          <Link to="/audit/log" className="stats-nav-item">
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h7l5 5v11a2 2 0 01-2 2z"/>
            </svg>
            Audit log
          </Link>

          <div className="stats-nav-section">Administration</div>
          <Link to="/stats" className="stats-nav-item active">
            <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"/>
            </svg>
            Chatbot stats
            <span className="stats-nav-badge">Admin</span>
          </Link>
        </nav>

        <div className="stats-sidebar-user">
          <div className="stats-user-info">
            <div className="stats-user-avatar">{initials}</div>
            <div>
              <div className="stats-user-name">{displayName}</div>
              <div className="stats-user-role">{user?.role || ''}</div>
            </div>
          </div>
          <button className="stats-btn-logout" onClick={logout}>
            <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15M12 9l-3 3m0 0l3 3m-3-3h12.75"/>
            </svg>
            Logout
          </button>
        </div>
      </div>

      {/* ── Main ── */}
      <div className="stats-main">
        <div className="stats-topbar">
          <div className="stats-topbar-left">
            <div className="stats-page-title">Chatbot usage statistics</div>
            <div className="stats-breadcrumb">
              <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8.25 4.5l7.5 7.5-7.5 7.5"/>
              </svg>
              <span>Admin analytics - last 30 days</span>
            </div>
          </div>
          <div className="stats-topbar-right">
            <div className="stats-topbar-date">{date}</div>
            <button className="stats-theme-toggle" onClick={toggleTheme} title="Toggle theme">
              {isDark ? (
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364-6.364l-.707.707M6.343 17.657l-.707.707M17.657 17.657l-.707-.707M6.343 6.343l-.707-.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"/>
                </svg>
              ) : (
                <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"/>
                </svg>
              )}
            </button>
          </div>
        </div>

        <div className="stats-content">
          {loading ? (
            <div className="stats-loading">Loading…</div>
          ) : error ? (
            <div className="stats-error">{error}</div>
          ) : data ? (
            <>
              {/* KPI grid */}
              <div className="stats-section-label">Main KPIs</div>
              <div className="stats-kpi-grid">
                <div className="stats-kpi-card">
                  <div className="stats-kpi-title">Questions today</div>
                  <div className="stats-kpi-value">{data.questions_today}</div>
                  <div className="stats-kpi-sub">Chatbot messages today</div>
                </div>
                <div className="stats-kpi-card">
                  <div className="stats-kpi-title">This week</div>
                  <div className="stats-kpi-value">{data.questions_week}</div>
                  <div className="stats-kpi-sub">Last 7 days</div>
                </div>
                <div className="stats-kpi-card">
                  <div className="stats-kpi-title">Average time</div>
                  <div className="stats-kpi-value">{Number(data.avg_duration).toFixed(2)}s</div>
                  <div className="stats-kpi-sub">30-day average</div>
                </div>
                <div className="stats-kpi-card">
                  <div className="stats-kpi-title">Satisfaction rate</div>
                  <div className="stats-kpi-value">{Number(data.satisfaction_rate).toFixed(1)}%</div>
                  <div className="stats-kpi-sub">Across {data.evaluated_count} rated responses</div>
                </div>
              </div>

              {/* Meta pills */}
              <div className="stats-meta-row">
                <div className="stats-meta-pill">
                  <span>Questions (30 days)</span>
                  <strong>{data.questions_month}</strong>
                </div>
                <div className="stats-meta-pill">
                  <span>Max time (30 days)</span>
                  <strong>{Number(data.max_duration).toFixed(2)}s</strong>
                </div>
                <div className="stats-meta-pill">
                  <span>"Out-of-scope" responses</span>
                  <strong>{data.unanswered}</strong>
                </div>
              </div>

              {/* Charts row */}
              <div className="stats-cards-grid">
                <div className="stats-card">
                  <div className="stats-card-header">
                    <div>
                      <div className="stats-card-title">Questions per day</div>
                      <div className="stats-card-sub">30-day trend</div>
                    </div>
                  </div>
                  <div className="stats-card-body">
                    <div className="stats-chart-wrap">
                      <DailyChart labels={data.questions_per_day_labels} values={data.questions_per_day_values} />
                    </div>
                  </div>
                </div>
                <div className="stats-card">
                  <div className="stats-card-header">
                    <div>
                      <div className="stats-card-title">Peak hours</div>
                      <div className="stats-card-sub">Question distribution by hour</div>
                    </div>
                  </div>
                  <div className="stats-card-body">
                    <div className="stats-chart-wrap">
                      <PeakChart labels={data.peak_hours_labels} values={data.peak_hours_values} />
                    </div>
                  </div>
                </div>
              </div>

              {/* Tables row */}
              <div className="stats-cards-grid">
                <div className="stats-card">
                  <div className="stats-card-header">
                    <div className="stats-card-title">Top 5 Users</div>
                  </div>
                  <div className="stats-card-body" style={{ padding: 0 }}>
                    <table className="stats-table">
                      <thead>
                        <tr>
                          <th>User</th>
                          <th>Login</th>
                          <th>Total questions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.top_users?.length ? data.top_users.map((row, i) => (
                          <tr key={i}>
                            <td>{row.name}</td>
                            <td className="stats-muted">{row.username}</td>
                            <td>{row.total}</td>
                          </tr>
                        )) : (
                          <tr><td colSpan={3} className="stats-empty">No data available.</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="stats-card">
                  <div className="stats-card-header">
                    <div className="stats-card-title">10 latest unsatisfactory questions</div>
                  </div>
                  <div className="stats-card-body" style={{ padding: 0 }}>
                    <table className="stats-table">
                      <thead>
                        <tr>
                          <th>Date</th>
                          <th>User</th>
                          <th>Question</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.latest_unsatisfied?.length ? data.latest_unsatisfied.map((msg, i) => (
                          <tr key={i}>
                            <td className="stats-muted">{msg.date}</td>
                            <td>{msg.user}</td>
                            <td>{msg.question}</td>
                            <td><span className="stats-score-badge">Unsatisfied</span></td>
                          </tr>
                        )) : (
                          <tr><td colSpan={4} className="stats-empty">No question marked as unsatisfactory.</td></tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}
