import { Routes, Route, Navigate, Link } from 'react-router-dom'
import { useAuth } from './store/AuthContext'
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import StudentPanel from './pages/student/StudentPanel'
import EmployerPanel from './pages/employer/EmployerPanel'

// Note: /admin is served as static HTML by the backend (app/static/admin.html)
// It is NOT part of the React SPA

function Header() {
  const { user, logout } = useAuth()
  if (!user) return null
  return (
    <header className="header">
      <h1>🎓 HH.ru Student Evaluator</h1>
      <nav>
        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          {user.email} <span className="badge badge-blue">{user.role}</span>
        </span>
        <button onClick={logout}>Выйти</button>
      </nav>
    </header>
  )
}

function ProtectedRoute({ children, roles }: { children: React.ReactNode; roles?: string[] }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="container"><div className="spinner" /></div>
  if (!user) return <Navigate to="/login" replace />
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />
  return <>{children}</>
}

function HomeRedirect() {
  const { user, loading } = useAuth()
  if (loading) return <div className="container"><div className="spinner" /></div>
  if (!user) return <Navigate to="/login" replace />
  if (user.role === 'admin') return <Navigate to="/admin" replace />
  if (user.role === 'student') return <Navigate to="/student" replace />
  if (user.role === 'employer') return <Navigate to="/employer" replace />
  return <Navigate to="/login" replace />
}

export default function App() {
  return (
    <>
      <Header />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/" element={<HomeRedirect />} />
        <Route path="/student/*" element={<ProtectedRoute roles={['student']}><StudentPanel /></ProtectedRoute>} />
        <Route path="/employer/*" element={<ProtectedRoute roles={['employer']}><EmployerPanel /></ProtectedRoute>} />
      </Routes>
    </>
  )
}
