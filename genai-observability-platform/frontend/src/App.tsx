import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Traces from './pages/Traces'
import TraceDetail from './pages/TraceDetail'
import Agents from './pages/Agents'
import AgentDetail from './pages/AgentDetail'
import Alerts from './pages/Alerts'
import Settings from './pages/Settings'
import Query from './pages/Query'
import Remediation from './pages/Remediation'
import Integrations from './pages/Integrations'
import Login from './pages/Login'
import { useAuthStore } from './store'

// Protected route wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  const location = useLocation()

  // For demo purposes, allow access without authentication
  // In production, uncomment the redirect
  // if (!isAuthenticated) {
  //   return <Navigate to="/login" state={{ from: location }} replace />
  // }

  return <>{children}</>
}

function App() {
  const location = useLocation()

  // Don't wrap login page in Layout
  if (location.pathname === '/login') {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
      </Routes>
    )
  }

  return (
    <Layout>
      <Routes>
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/query"
          element={
            <ProtectedRoute>
              <Query />
            </ProtectedRoute>
          }
        />
        <Route
          path="/traces"
          element={
            <ProtectedRoute>
              <Traces />
            </ProtectedRoute>
          }
        />
        <Route
          path="/traces/:traceId"
          element={
            <ProtectedRoute>
              <TraceDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/agents"
          element={
            <ProtectedRoute>
              <Agents />
            </ProtectedRoute>
          }
        />
        <Route
          path="/agents/:agentId"
          element={
            <ProtectedRoute>
              <AgentDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/alerts"
          element={
            <ProtectedRoute>
              <Alerts />
            </ProtectedRoute>
          }
        />
        <Route
          path="/remediation"
          element={
            <ProtectedRoute>
              <Remediation />
            </ProtectedRoute>
          }
        />
        <Route
          path="/integrations"
          element={
            <ProtectedRoute>
              <Integrations />
            </ProtectedRoute>
          }
        />
        <Route
          path="/settings"
          element={
            <ProtectedRoute>
              <Settings />
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Layout>
  )
}

export default App
