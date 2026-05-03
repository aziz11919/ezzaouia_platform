import { useEffect, useMemo, useState } from 'react'
import { Navigate } from 'react-router-dom'
import Layout from '../../components/Layout/Layout'
import { useAuth } from '../../contexts/AuthContext'
import { maintenanceAPI } from '../../api/maintenance'

export default function MaintenanceAdminPage() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [message, setMessage] = useState('')
  const [estimatedEnd, setEstimatedEnd] = useState('')
  const [active, setActive] = useState(false)
  const [error, setError] = useState('')

  const isAdmin = user?.role === 'admin'

  const formattedEnd = useMemo(() => {
    if (!estimatedEnd) return ''
    try {
      return new Intl.DateTimeFormat('fr-FR', {
        dateStyle: 'full',
        timeStyle: 'short',
      }).format(new Date(estimatedEnd))
    } catch {
      return ''
    }
  }, [estimatedEnd])

  const toDateTimeLocalValue = (value) => {
    if (!value) return ''
    const date = new Date(value)
    const offsetMs = date.getTimezoneOffset() * 60000
    return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16)
  }

  useEffect(() => {
    let mounted = true

    const load = async () => {
      try {
        const res = await maintenanceAPI.status()
        if (!mounted) return
        setActive(Boolean(res.data?.active))
        setMessage(res.data?.message || '')
        setEstimatedEnd(res.data?.estimated_end || '')
      } catch {
        if (!mounted) return
        setError('Impossible de charger le statut de maintenance.')
      } finally {
        if (mounted) setLoading(false)
      }
    }

    load()
    return () => {
      mounted = false
    }
  }, [])

  const onApply = async () => {
    setError('')
    if (active) {
      const ok = window.confirm('Attention : les utilisateurs connectes seront rediriges vers la page de maintenance.')
      if (!ok) return
    }

    try {
      const payload = {
        active,
        message,
        estimated_end: estimatedEnd || null,
      }
      const res = await maintenanceAPI.toggle(payload)
      setActive(Boolean(res.data?.active))
      setMessage(res.data?.message || '')
      setEstimatedEnd(res.data?.estimated_end || '')
    } catch (err) {
      setError(err.response?.data?.detail || 'Echec de la mise a jour du mode maintenance.')
    }
  }

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <Layout
      title="Maintenance"
      breadcrumb="Administration - Controle de disponibilite"
    >
      <div className="page-panel" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
          <span style={{
            display: 'inline-flex',
            alignItems: 'center',
            padding: '4px 10px',
            borderRadius: 16,
            background: active ? 'rgba(224,85,85,0.14)' : 'rgba(77,170,122,0.14)',
            color: active ? '#E05555' : '#4DAA7A',
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: 1,
            textTransform: 'uppercase',
          }}>
            {active ? 'Actif' : 'Inactif'}
          </span>
          <span style={{ color: '#9BA8BB', fontSize: 13 }}>Statut actuel du mode maintenance</span>
        </div>

        {loading ? <div style={{ color: '#9BA8BB', marginBottom: 10 }}>Chargement...</div> : null}

        <label style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 18 }}>
          <input type="checkbox" checked={active} onChange={(e) => setActive(e.target.checked)} />
          <span>Activer le mode maintenance</span>
        </label>

        <div style={{ marginBottom: 14 }}>
          <label style={{ display: 'block', marginBottom: 8, color: '#9BA8BB', fontSize: 12 }}>Message de maintenance</label>
          <textarea
            className="input-field"
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="Message affiche aux utilisateurs"
          />
        </div>

        <div style={{ marginBottom: 14 }}>
          <label style={{ display: 'block', marginBottom: 8, color: '#9BA8BB', fontSize: 12 }}>Fin estimee</label>
          <input
            className="input-field"
            type="datetime-local"
            value={toDateTimeLocalValue(estimatedEnd)}
            onChange={(e) => setEstimatedEnd(e.target.value)}
          />
          {formattedEnd ? <div style={{ marginTop: 8, fontSize: 12, color: '#C9A84C' }}>Affichage: {formattedEnd}</div> : null}
        </div>

        {error ? <div className="alert alert-error" style={{ marginBottom: 12 }}>{error}</div> : null}

        <button className="btn-primary" onClick={onApply}>Appliquer</button>
      </div>
    </Layout>
  )
}
