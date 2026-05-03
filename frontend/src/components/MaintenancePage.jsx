import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { maintenanceAPI } from '../api/maintenance'

export default function MaintenancePage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState({ active: true, message: '', estimated_end: null })

  const formattedEnd = useMemo(() => {
    if (!status.estimated_end) return null
    try {
      return new Intl.DateTimeFormat('fr-FR', {
        dateStyle: 'full',
        timeStyle: 'short',
      }).format(new Date(status.estimated_end))
    } catch {
      return null
    }
  }, [status.estimated_end])

  useEffect(() => {
    let mounted = true

    const checkStatus = async () => {
      try {
        const res = await maintenanceAPI.status()
        if (!mounted) return
        const next = {
          active: Boolean(res.data?.active),
          message: res.data?.message || '',
          estimated_end: res.data?.estimated_end || null,
        }
        setStatus(next)

        if (!next.active) {
          navigate('/', { replace: true })
        }
      } catch {
        if (!mounted) return
      }
    }

    checkStatus()
    const id = window.setInterval(checkStatus, 30000)

    return () => {
      mounted = false
      window.clearInterval(id)
    }
  }, [navigate])

  return (
    <div style={{
      minHeight: '100vh',
      background: 'radial-gradient(circle at 20% 20%, rgba(201,168,76,0.15), transparent 50%), linear-gradient(160deg, #050D18 0%, #0D1A2A 60%, #111E2F 100%)',
      color: '#E8EDF5',
      display: 'grid',
      placeItems: 'center',
      padding: 24,
    }}>
      <div style={{ maxWidth: 760, width: '100%', background: 'rgba(7,16,27,0.88)', border: '1px solid rgba(201,168,76,0.24)', borderRadius: 16, padding: '42px 32px', boxShadow: '0 20px 80px rgba(0,0,0,0.4)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 18, marginBottom: 20 }}>
          <div style={{ width: 68, height: 68, borderRadius: 16, background: 'rgba(201,168,76,0.12)', display: 'grid', placeItems: 'center', border: '1px solid rgba(201,168,76,0.3)' }}>
            <svg width="38" height="38" fill="none" stroke="#C9A84C" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" d="M10.5 6.75A3.75 3.75 0 1014.25 10.5a3.75 3.75 0 00-3.75-3.75z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.7" d="M10.5 2.25v2.5m0 11.5v2.5m8.25-8.25h-2.5m-11.5 0h-2.5m12.193 5.807l-1.768-1.768M7.575 7.575L5.807 5.807m8.636 0l-1.768 1.768M7.575 13.425l-1.768 1.768" />
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 11, color: '#C9A84C', letterSpacing: 2, textTransform: 'uppercase', marginBottom: 8 }}>MARETAP S.A.</div>
            <h1 style={{ margin: 0, fontFamily: 'Rajdhani, sans-serif', fontSize: 44, lineHeight: 1 }}>EZZAOUIA Maintenance</h1>
          </div>
        </div>

        <p style={{ color: '#CBD5E3', fontSize: 17, lineHeight: 1.7, marginBottom: 20 }}>
          {status.message || 'La plateforme est en cours de maintenance. Merci de reessayer dans quelques instants.'}
        </p>

        {formattedEnd ? (
          <div style={{ background: 'rgba(14,30,50,0.9)', border: '1px solid rgba(77,143,204,0.3)', borderRadius: 10, padding: '12px 14px', color: '#8FC0FF', marginBottom: 22 }}>
            Fin estimee: {formattedEnd}
          </div>
        ) : null}

        <div style={{ fontSize: 12, color: '#9BA8BB', letterSpacing: 0.4 }}>
          Cette page se met a jour automatiquement toutes les 30 secondes.
        </div>
      </div>
    </div>
  )
}
