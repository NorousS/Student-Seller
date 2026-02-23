import { useState, FormEvent } from 'react'
import { useAuth } from '../../store/AuthContext'
import { Link, Navigate } from 'react-router-dom'

export default function RegisterPage() {
  const { register, user } = useAuth()
  const [role, setRole] = useState<string>('student')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [groupName, setGroupName] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [error, setError] = useState('')

  if (user) return <Navigate to="/" replace />

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const body: Record<string, string> = { email, password, role }
      if (role === 'student') { body.full_name = fullName; body.group_name = groupName }
      if (role === 'employer') { body.company_name = companyName }
      await register(body)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка регистрации')
    }
  }

  return (
    <div className="container" style={{ maxWidth: 420, marginTop: 60 }}>
      <div className="card">
        <h2 style={{ marginBottom: 24, textAlign: 'center' }}>🎓 Регистрация</h2>
        {error && <div style={{ color: 'var(--red)', marginBottom: 12, fontSize: 14 }}>{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Роль</label>
            <select value={role} onChange={e => setRole(e.target.value)}>
              <option value="student">Студент</option>
              <option value="employer">Работодатель</option>
            </select>
          </div>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required autoComplete="email" />
          </div>
          <div className="form-group">
            <label>Пароль (мин. 6 символов)</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={6} autoComplete="new-password" />
          </div>

          {role === 'student' && (
            <>
              <div className="form-group">
                <label>ФИО</label>
                <input value={fullName} onChange={e => setFullName(e.target.value)} required autoComplete="name" />
              </div>
              <div className="form-group">
                <label>Группа</label>
                <input value={groupName} onChange={e => setGroupName(e.target.value)} />
              </div>
            </>
          )}

          {role === 'employer' && (
            <div className="form-group">
              <label>Название компании</label>
              <input value={companyName} onChange={e => setCompanyName(e.target.value)} name="organization" autoComplete="organization" />
            </div>
          )}

          <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Зарегистрироваться</button>
        </form>
        <p style={{ textAlign: 'center', marginTop: 16, fontSize: 14, color: 'var(--text-muted)' }}>
          Уже есть аккаунт? <Link to="/login">Войти</Link>
        </p>
      </div>
    </div>
  )
}
