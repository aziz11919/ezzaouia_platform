import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useEffect } from 'react'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Chatbot from './pages/Chatbot'
import FileImport from './pages/FileImport'
import Library from './pages/Library'
import AuditLog from './pages/AuditLog'
import UserManagement from './pages/UserManagement'
import Profile from './pages/Profile'
import Reports from './pages/Reports'
import NotFound from './pages/NotFound'

function LoadingGate() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#050D18', color: '#C9A84C', fontFamily: 'Rajdhani, sans-serif', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
      Loading...
    </div>
  )
}

function RequireAuth({ children }) {
  const { user, loading } = useAuth()
  const location = useLocation()

  if (loading) return <LoadingGate />
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return children
}

function PublicOnly({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <LoadingGate />
  if (user) return <Navigate to="/dashboard" replace />
  return children
}

function LogoutPage() {
  const { logout } = useAuth()
  useEffect(() => {
    logout()
  }, [logout])
  return <LoadingGate />
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<PublicOnly><Login /></PublicOnly>} />
      <Route path="/accounts/login" element={<Navigate to="/login" replace />} />
      <Route path="/accounts/logout" element={<LogoutPage />} />

      <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
      <Route path="/chatbot" element={<RequireAuth><Chatbot /></RequireAuth>} />
      <Route path="/chatbot/new" element={<RequireAuth><Chatbot /></RequireAuth>} />
      <Route path="/chatbot/:sessionId" element={<RequireAuth><Chatbot /></RequireAuth>} />

      <Route path="/ingestion" element={<RequireAuth><FileImport /></RequireAuth>} />
      <Route path="/ingestion/upload" element={<RequireAuth><FileImport /></RequireAuth>} />
      <Route path="/ingestion/list" element={<RequireAuth><FileImport /></RequireAuth>} />

      <Route path="/bibliotheque" element={<RequireAuth><Library /></RequireAuth>} />
      <Route path="/audit/log" element={<RequireAuth><AuditLog /></RequireAuth>} />
      <Route path="/accounts/users" element={<RequireAuth><UserManagement /></RequireAuth>} />
      <Route path="/profile" element={<RequireAuth><Profile /></RequireAuth>} />
      <Route path="/accounts/profile" element={<Navigate to="/profile" replace />} />
      <Route path="/reports" element={<RequireAuth><Reports /></RequireAuth>} />

      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}
