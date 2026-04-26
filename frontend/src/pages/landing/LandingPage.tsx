import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api from '../../api/client'
import type { TopStudentCard } from '../../api/types'

const skillGroups = [
  {
    title: 'Программирование',
    items: ['Python', 'Java', 'Алгоритмы и структуры данных'],
    tone: 'blue',
  },
  {
    title: 'Иностранные языки',
    items: ['Английский', 'Немецкий'],
    tone: 'green',
  },
  {
    title: 'Soft skills',
    items: ['Soft skills в IT', 'Lean менеджмент', 'Управление IT проектами'],
    tone: 'rose',
  },
  {
    title: 'Точные науки',
    items: ['Линал', 'Матан', 'Матстат', 'Физика'],
    tone: 'amber',
  },
]

const audiences = [
  {
    title: 'Работодателю',
    label: 'shortlist',
    text: 'Видите сильные группы навыков, рыночную оценку и детализацию только там, где она нужна для решения.',
  },
  {
    title: 'Студенту',
    label: 'profile',
    text: 'Собираете профиль из дисциплин, оценок и готовности к работе, а платформа переводит это на язык вакансий.',
  },
  {
    title: 'Вузу',
    label: 'partner',
    text: 'Управляете партнёрами, показываете качество подготовки и даёте компаниям понятный вход в подбор.',
  },
]

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
    if (!salary) return 'Оценка после расчёта'
    return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(salary)
  }

  return (
    <div className="landing-page">
      <header className="landing-header">
        <button className="landing-logo" onClick={() => navigate('/')}>
          KAI Talent Match
        </button>
        <nav className="landing-header-nav">
          <button className="landing-link-button" onClick={() => navigate('/login')}>Войти</button>
          <button className="landing-primary-button" onClick={() => navigate('/register')}>Зарегистрироваться</button>
        </nav>
      </header>

      <section className="landing-hero">
        <div className="landing-product-scene" aria-hidden="true">
          <div className="product-shell">
            <div className="product-toolbar">
              <span />
              <span />
              <span />
              <strong>Поиск: Junior Python</strong>
            </div>
            <div className="product-layout">
              <aside className="product-sidebar">
                <span className="product-nav active">Кандидаты</span>
                <span className="product-nav">Группы навыков</span>
                <span className="product-nav">Партнёры</span>
              </aside>
              <main className="product-main">
                <div className="product-student-row">
                  <div>
                    <strong>Студент #128</strong>
                    <small>готов к стажировке с июня</small>
                  </div>
                  <b>86%</b>
                </div>
                <div className="product-groups-preview">
                  {skillGroups.map(group => (
                    <div key={group.title} className={`product-group ${group.tone}`}>
                      <span>{group.title}</span>
                      <strong>{group.items.length}</strong>
                    </div>
                  ))}
                </div>
                <div className="product-chart">
                  <span style={{ height: '72%' }} />
                  <span style={{ height: '48%' }} />
                  <span style={{ height: '88%' }} />
                  <span style={{ height: '61%' }} />
                  <span style={{ height: '76%' }} />
                </div>
                <div className="product-table">
                  <span>Python</span><b>5</b>
                  <span>Английский</span><b>4</b>
                  <span>Матан</span><b>5</b>
                </div>
              </main>
            </div>
          </div>
        </div>

        <div className="landing-hero-copy">
          <p className="landing-eyebrow">ИИ-подбор студентов по реальным требованиям рынка</p>
          <h1>Найдите лучших выпускников</h1>
          <p className="landing-hero-subtitle">
            Платформа связывает дисциплины, оценки и вакансии hh.ru: работодатель видит понятные группы навыков, вуз управляет партнёрским доступом, студент показывает сильные стороны без лишнего шума.
          </p>
          <div className="landing-hero-actions">
            <button className="landing-primary-button large" onClick={() => navigate('/register')}>
              Начать подбор
            </button>
            <button className="landing-secondary-button large" onClick={() => navigate('/login')}>
              Войти в платформу
            </button>
          </div>
        </div>
      </section>

      <section className="landing-proof-strip" aria-label="Ключевые возможности">
        <span><strong>4</strong> группы навыков вместо россыпи предметов</span>
        <span><strong>HH</strong> диагностика парсинга с понятными ошибками</span>
        <span><strong>Partner</strong> доступ без paywall для аффилированных компаний</span>
      </section>

      <section className="landing-section landing-audiences">
        <div className="landing-section-heading">
          <p className="landing-eyebrow">Одна платформа, три рабочих сценария</p>
          <h2>Кому это полезно</h2>
        </div>
        <div className="landing-audience-grid">
          {audiences.map(item => (
            <article key={item.title} className="landing-audience-panel">
              <span>{item.label}</span>
              <h3>{item.title}</h3>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="landing-section landing-skill-preview">
        <div className="landing-section-heading">
          <p className="landing-eyebrow">Группы навыков в профиле работодателя</p>
          <h2>Работодатель видит картину, а не ведомость</h2>
        </div>
        <div className="landing-skill-layout">
          <div className="landing-skill-copy">
            <p>
              Дисциплины остаются внутри расчёта оценки и зарплаты, но в профиле кандидата собираются в четыре понятных блока. Наведение или фокус раскрывает конкретные предметы.
            </p>
            <button className="landing-secondary-button" onClick={() => navigate('/register')}>
              Посмотреть как работодатель
            </button>
          </div>
          <div className="landing-skill-groups">
            {skillGroups.map(group => (
              <div key={group.title} className={`landing-skill-group ${group.tone}`} tabIndex={0}>
                <div>
                  <h3>{group.title}</h3>
                  <span>{group.items.length} дисциплины</span>
                </div>
                <ul>
                  {group.items.map(item => <li key={item}>{item}</li>)}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="landing-section">
        <div className="landing-section-heading">
          <p className="landing-eyebrow">Анонимный топ кандидатов</p>
          <h2>Топ-5 кандидатов</h2>
        </div>
        {loading ? (
          <div className="landing-loading"><div className="spinner" /></div>
        ) : cards.length === 0 ? (
          <div className="landing-empty-state">
            <p>Пока нет профилей студентов</p>
            <span>После загрузки профилей здесь появятся анонимные карточки для быстрого старта подбора.</span>
          </div>
        ) : (
          <div className="landing-students-grid">
            {cards.map(card => (
              <article key={card.student_id} className="landing-student-card card">
                <div className="landing-student-avatar">
                  {card.photo_url ? (
                    <img src={card.photo_url} alt="" />
                  ) : (
                    <span>#{card.student_id}</span>
                  )}
                </div>
                <div className="landing-student-salary">
                  {formatSalary(card.estimated_salary)}
                </div>
                <p>{card.competency_summary || 'Профиль готовится к оценке'}</p>
                <button className="landing-primary-button" onClick={() => navigate('/login')}>
                  Пригласить
                </button>
              </article>
            ))}
          </div>
        )}
      </section>

      <section className="landing-partner-cta">
        <div>
          <p className="landing-eyebrow">Paywall и партнёрство</p>
          <h2>Аффилированные работодатели получают полный сценарий</h2>
          <p>
            Администратор может выдать компании статус партнёра: приглашения проходят без paywall, а контакты и полный профиль открываются после принятия студентом.
          </p>
        </div>
        <div className="landing-cta-actions">
          <button className="landing-primary-button large" onClick={() => navigate('/register')}>Подключить компанию</button>
          <Link to="/login">Уже есть аккаунт</Link>
        </div>
      </section>
    </div>
  )
}
