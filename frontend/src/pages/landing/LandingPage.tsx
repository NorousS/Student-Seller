import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api/client'
import type { TopStudentCard } from '../../api/types'

export default function LandingPage() {
  const [cards, setCards] = useState<TopStudentCard[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/landing/top-students')
      .then(r => setCards(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const formatSalary = (salary: number | null) => {
    if (!salary) return 'По запросу'
    return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(salary)
  }

  return (
    <div className="container" style={{ maxWidth: 1200, margin: '0 auto', padding: '40px 20px' }}>
      {/* Hero section */}
      <div style={{ textAlign: 'center', marginBottom: 48 }}>
        <h1 style={{ fontSize: 36, marginBottom: 16 }}>Найдите лучших выпускников</h1>
        <p style={{ fontSize: 18, color: 'var(--text-muted)', maxWidth: 600, margin: '0 auto' }}>
          Платформа оценки студентов на основе ИИ. Быстрый доступ к лучшим кандидатам с реальными компетенциями.
        </p>
      </div>

      {/* Top students cards */}
      <h2 style={{ marginBottom: 24, textAlign: 'center' }}>Топ-5 кандидатов</h2>
      {loading ? (
        <div style={{ textAlign: 'center' }}><div className="spinner" /></div>
      ) : cards.length === 0 ? (
        <p style={{ textAlign: 'center', color: 'var(--text-muted)' }}>Пока нет профилей студентов</p>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 20, marginBottom: 48 }}>
          {cards.map(card => (
            <div key={card.student_id} className="card" style={{ textAlign: 'center', padding: 24 }}>
              <div style={{ width: 80, height: 80, borderRadius: '50%', background: 'var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 16px', overflow: 'hidden' }}>
                {card.photo_url ? (
                  <img src={card.photo_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                ) : (
                  <span style={{ fontSize: 32 }}>👤</span>
                )}
              </div>
              <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--green)', marginBottom: 8 }}>
                {formatSalary(card.estimated_salary)}
              </div>
              <p style={{ fontSize: 14, color: 'var(--text-muted)', marginBottom: 16, minHeight: 40 }}>
                {card.competency_summary}
              </p>
              <button
                className="btn btn-primary"
                style={{ width: '100%' }}
                onClick={() => navigate('/login')}
              >
                📩 Пригласить
              </button>
            </div>
          ))}
        </div>
      )}

      {/* CTA */}
      <div style={{ textAlign: 'center', padding: '32px 0' }}>
        <button className="btn btn-primary" style={{ fontSize: 16, padding: '12px 32px' }} onClick={() => navigate('/register')}>
          Зарегистрироваться как работодатель
        </button>
      </div>
    </div>
  )
}
