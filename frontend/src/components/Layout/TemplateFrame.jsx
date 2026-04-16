import { useEffect, useState } from 'react'
import { useLocation, useParams } from 'react-router-dom'

function toRelativePath(path) {
  return path.startsWith('/') ? path : `/${path}`
}

export default function TemplateFrame({ targetPath }) {
  const params = useParams()
  const location = useLocation()
  const [loaded, setLoaded] = useState(false)

  let resolvedPath
  if (typeof targetPath === 'function') {
    resolvedPath = targetPath(params)
  } else if (targetPath) {
    resolvedPath = targetPath
  } else {
    resolvedPath = `${location.pathname}${location.search || ''}`
  }
  const iframeSrc = toRelativePath(resolvedPath)

  useEffect(() => {
    setLoaded(false)
  }, [iframeSrc])

  return (
    <div style={{ width: '100%', height: '100vh', position: 'relative', background: '#050D18' }}>
      {!loaded && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#C9A84C',
            fontFamily: 'Rajdhani, sans-serif',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            zIndex: 1,
          }}
        >
          Loading Template...
        </div>
      )}
      <iframe
        key={iframeSrc}
        src={iframeSrc}
        title={`template-${resolvedPath}`}
        onLoad={() => setLoaded(true)}
        style={{
          width: '100%',
          height: '100%',
          border: 'none',
          display: 'block',
          background: '#050D18',
        }}
      />
    </div>
  )
}
