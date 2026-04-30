import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../../api/client'
import type { AnonymizedStudent, DisciplineGroup, TopStudentCard } from '../../api/types'

export default function LandingPage() {
  const [cards, setCards] = useState<TopStudentCard[]>([])
  const [results, setResults] = useState<AnonymizedStudent[]>([])
  const [loading, setLoading] = useState(true)
  const [searching, setSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [jobTitle, setJobTitle] = useState('')
  const [experience, setExperience] = useState('')
  const [searchError, setSearchError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/landing/top-students')
      .then(r => setCards(r.data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const formatSalary = (salary: number | null) => {
    if (!salary) return 'Оценка скоро'
    return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(salary)
  }

  const searchStudents = async () => {
    if (!jobTitle.trim()) {
      setSearchError('Введите должность или роль')
      return
    }
    setSearching(true)
    setSearchError(null)
    try {
      const { data } = await api.post('/landing/search-students', {
        job_title: jobTitle.trim(),
        experience: experience || null,
        top_k: 5,
      })
      setResults(data)
      setHasSearched(true)
    } catch (e: any) {
      setSearchError(e.response?.data?.detail || 'Ошибка поиска')
    } finally {
      setSearching(false)
    }
  }

  const displayedCards: Array<TopStudentCard | AnonymizedStudent> = hasSearched ? results : cards
  const title = hasSearched ? `Топ-10 под запрос: ${jobTitle}` : 'Топ-10 кандидатов'

  return (
    <div>
      {/* Header */}
      <header className="landing-header">
        <span className="landing-header-logo">🎓 HH Evaluator</span>
        <nav className="landing-header-nav">
          <button className="btn btn-outline" onClick={() => navigate('/login')}>Войти</button>
          <button className="btn btn-primary" onClick={() => navigate('/register')}>Зарегистрироваться</button>
        </nav>
      </header>

      {/* Hero */}
      <section className="landing-hero">
        <h1>Найдите лучших выпускников с помощью ИИ</h1>
        <p className="landing-hero-subtitle">
          Платформа оценки студентов на основе искусственного интеллекта. Сопоставляем учебные дисциплины с реальными требованиями рынка труда и рассчитываем потенциальную зарплату.
        </p>
        <div className="landing-hero-actions">
          <button className="btn btn-outline btn-lg" onClick={() => navigate('/login')}>Войти</button>
          <button className="btn btn-primary btn-lg" onClick={() => navigate('/register')}>Начать бесплатно</button>
        </div>
        <div className="landing-search">
          <input
            value={jobTitle}
            onChange={e => setJobTitle(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && searchStudents()}
            placeholder="Кого ищете? Например: Python разработчик"
          />
          <select value={experience} onChange={e => setExperience(e.target.value)} aria-label="Опыт">
            <option value="">Любой опыт</option>
            <option value="noExperience">Без опыта</option>
            <option value="between1And3">1-3 года</option>
            <option value="between3And6">3-6 лет</option>
            <option value="moreThan6">6+ лет</option>
          </select>
          <button className="btn btn-primary btn-lg" onClick={searchStudents} disabled={searching}>
            {searching ? <span className="spinner" /> : 'Найти студента'}
          </button>
        </div>
        {searchError && <div className="landing-search-error">{searchError}</div>}
      </section>

      {/* Features */}
      <section className="landing-section">
        <h2 className="landing-section-title">Почему наша платформа?</h2>
        <div className="landing-features-grid">
          <div className="landing-feature-card">
            <span className="landing-feature-icon">🤖</span>
            <h3>ИИ-оценка навыков</h3>
            <p>Семантический анализ дисциплин и сопоставление с реальными требованиями рынка труда</p>
          </div>
          <div className="landing-feature-card">
            <span className="landing-feature-icon">📊</span>
            <h3>Данные с hh.ru</h3>
            <p>Актуальные вакансии и зарплаты на основе парсинга крупнейшей площадки</p>
          </div>
          <div className="landing-feature-card">
            <span className="landing-feature-icon">🔒</span>
            <h3>Анонимный подбор</h3>
            <p>Работодатели видят компетенции, а не личные данные — до момента приглашения</p>
          </div>
          <div className="landing-feature-card">
            <span className="landing-feature-icon">⚡</span>
            <h3>Быстрый доступ</h3>
            <p>От регистрации до первого кандидата — менее 5 минут</p>
          </div>
        </div>
      </section>

      {/* Top Students */}
      <section className="landing-section">
        <h2 className="landing-section-title">{title}</h2>
        {loading && !hasSearched ? (
          <div style={{ textAlign: 'center' }}><div className="spinner" /></div>
        ) : displayedCards.length === 0 ? (
          <div className="landing-student-card" style={{ maxWidth: 480, margin: '0 auto' }}>
            <p style={{ color: 'var(--text-muted)', fontSize: 16 }}>
              {hasSearched ? 'Под этот запрос пока нет подходящих кандидатов' : 'Скоро здесь появятся лучшие кандидаты'}
            </p>
          </div>
        ) : (
          <div className="landing-students-grid">
            {displayedCards.map(card => (
              <div key={card.student_id} className="landing-student-card">
                <div className="landing-student-avatar">
                  {card.photo_url ? (
                    <img src={card.photo_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                  ) : (
                    <span style={{ fontSize: 32 }}>👤</span>
                  )}
                </div>
                <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--green)', marginBottom: 8 }}>
                  {formatSalary(card.estimated_salary)}
                </div>
                {'confidence' in card && (
                  <div style={{ marginBottom: 10 }}>
                    <span className={`badge ${card.confidence > 0.5 ? 'badge-green' : 'badge-yellow'}`}>
                      {(card.confidence * 100).toFixed(0)}% совпадение
                    </span>
                  </div>
                )}
                <LandingGroupBadges groups={card.discipline_groups} />
                <button className="btn btn-primary" style={{ width: '100%' }} onClick={() => navigate('/login')}>
                  📩 Пригласить
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* CTA Footer */}
      <section className="landing-section">
        <div className="landing-cta">
          <h2 style={{ fontSize: 28, marginBottom: 16 }}>Готовы найти лучших кандидатов?</h2>
          <p style={{ color: 'var(--text-muted)', marginBottom: 24, fontSize: 16 }}>
            Зарегистрируйтесь и получите доступ к ИИ-оценке студентов
          </p>
          <button className="btn btn-primary btn-lg" onClick={() => navigate('/register')}>
            Зарегистрироваться бесплатно
          </button>
          <p style={{ marginTop: 16, fontSize: 14, color: 'var(--text-muted)' }}>
            Уже есть аккаунт? <Link to="/login">Войти</Link>
          </p>
        </div>
      </section>
    </div>
  )
}

function LandingGroupBadges({ groups }: { groups?: DisciplineGroup[] }) {
  if (!groups?.length) return null
  return (
    <div className="landing-group-badges">
      {groups.slice(0, 4).map(group => (
        <div key={group.key} className={`landing-group-pill ${groupColorClass(group.key)}`} tabIndex={0}>
          <div className="landing-group-pill-head">
            <span>{group.label}</span>
            <strong>{group.count}</strong>
          </div>
          <div className="landing-group-details">
            {group.disciplines.map(discipline => (
              <span key={discipline.id} className={`discipline-pill g${discipline.grade}`}>
                {discipline.name} <strong>{discipline.grade}</strong>
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function groupColorClass(key: string) {
  return `skill-group-${key.toLowerCase().replace(/_/g, '-')}`
}
