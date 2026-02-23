import { useState, useEffect, useRef, useMemo } from 'react'
import api from '../../api/client'
import { useAuth } from '../../store/AuthContext'
import type { AnonymizedStudent, AnonymizedStudentProfile, ContactRequest, ChatMessage, SkillMatch } from '../../api/types'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { Bar } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
  Tooltip,
  Legend
)

export default function EmployerPanel() {
  const [tab, setTab] = useState<'search' | 'requests' | 'chat' | 'profile'>('search')
  return (
    <div className="container">
      <div className="tabs">
        <div className={`tab ${tab === 'search' ? 'active' : ''}`} onClick={() => setTab('search')} role="tab" tabIndex={0}>🔍 Поиск</div>
        <div className={`tab ${tab === 'requests' ? 'active' : ''}`} onClick={() => setTab('requests')} role="tab" tabIndex={0}>📩 Запросы</div>
        <div className={`tab ${tab === 'chat' ? 'active' : ''}`} onClick={() => setTab('chat')} role="tab" tabIndex={0}>💬 Чат</div>
        <div className={`tab ${tab === 'profile' ? 'active' : ''}`} onClick={() => setTab('profile')} role="tab" tabIndex={0}>🏢 Профиль</div>
      </div>
      {tab === 'search' && <SearchTab />}
      {tab === 'requests' && <RequestsTab />}
      {tab === 'chat' && <EmployerChatTab />}
      {tab === 'profile' && <ProfileTab />}
    </div>
  )
}

type SortField = 'similarity' | 'avg_salary' | 'vacancy_count'
type SortDirection = 'asc' | 'desc'

function SearchTab() {
  const [jobTitle, setJobTitle] = useState('')
  const [results, setResults] = useState<AnonymizedStudent[]>([])
  const [searching, setSearching] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [profile, setProfile] = useState<AnonymizedStudentProfile | null>(null)
  const [selectedStudent, setSelectedStudent] = useState<AnonymizedStudent | null>(null)

  // Фильтры навыков
  const [similarityThreshold, setSimilarityThreshold] = useState(0)
  const [minSimilarity, setMinSimilarity] = useState(0)
  const [minSalary, setMinSalary] = useState(0)
  const [minVacancyCount, setMinVacancyCount] = useState(0)
  
  // Сортировка
  const [sortField, setSortField] = useState<SortField>('similarity')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  const search = async () => {
    if (!jobTitle.trim()) return
    setSelectedId(null)
    setProfile(null)
    setSelectedStudent(null)
    setSimilarityThreshold(0)
    setMinSimilarity(0)
    setMinSalary(0)
    setMinVacancyCount(0)
    setSearching(true)
    try {
      const { data } = await api.post('/employer/search', { job_title: jobTitle })
      setResults(data)
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка поиска')
    }
    setSearching(false)
  }

  const openProfile = async (studentId: number) => {
    setSelectedId(studentId)
    const { data } = await api.get(`/employer/students/${studentId}/profile`)
    setProfile(data)
    
    // Найдем полные данные студента из результатов поиска
    const student = results.find(r => r.student_id === studentId)
    setSelectedStudent(student || null)
  }

  const requestContact = async (studentId: number) => {
    try {
      await api.post(`/employer/students/${studentId}/request-contact`)
      openProfile(studentId)
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка')
    }
  }

  // Фильтрация и сортировка навыков
  const filteredAndSortedSkills = useMemo(() => {
    if (!selectedStudent || !selectedStudent.skill_matches) return []
    
    let skills = selectedStudent.skill_matches.filter(sm => {
      if (sm.similarity < minSimilarity) return false
      if (minSalary > 0 && (sm.avg_salary === null || sm.avg_salary < minSalary)) return false
      if (minVacancyCount > 0 && sm.vacancy_count < minVacancyCount) return false
      return true
    })

    skills = [...skills].sort((a, b) => {
      let compareValue = 0
      
      if (sortField === 'similarity') {
        compareValue = a.similarity - b.similarity
      } else if (sortField === 'avg_salary') {
        const salaryA = a.avg_salary ?? 0
        const salaryB = b.avg_salary ?? 0
        compareValue = salaryA - salaryB
      } else if (sortField === 'vacancy_count') {
        compareValue = a.vacancy_count - b.vacancy_count
      }
      
      return sortDirection === 'asc' ? compareValue : -compareValue
    })

    return skills
  }, [selectedStudent, minSimilarity, minSalary, minVacancyCount, sortField, sortDirection])

  // Данные для диаграммы
  const chartData = useMemo(() => {
    if (!selectedStudent || !selectedStudent.skill_matches || filteredAndSortedSkills.length === 0) return null

    const topSkills = [...filteredAndSortedSkills]
      .sort((a, b) => b.similarity - a.similarity)
      .slice(0, 10)

    return {
      labels: topSkills.map(sm => sm.skill_name.length > 20 
        ? sm.skill_name.substring(0, 20) + '...' 
        : sm.skill_name),
      datasets: [
        {
          label: 'Сходство (%)',
          data: topSkills.map(sm => sm.similarity * 100),
          backgroundColor: 'rgba(99, 102, 241, 0.7)',
          borderColor: 'rgba(99, 102, 241, 1)',
          borderWidth: 1,
        },
      ],
    }
  }, [selectedStudent, filteredAndSortedSkills])

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: true,
        text: 'Топ-10 навыков по сходству',
        font: {
          size: 16,
          weight: 'bold' as const,
        },
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            return `${context.parsed.y.toFixed(1)}%`
          }
        }
      }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100,
        ticks: {
          callback: function(value: any) {
            return value + '%'
          }
        }
      },
    },
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection('desc')
    }
  }

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return '↕️'
    return sortDirection === 'asc' ? '↑' : '↓'
  }

  const formatSalary = (salary: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0
    }).format(salary)
  }

  return (
    <>
      <div className="card">
        <h3 style={{ marginBottom: 16 }}>Поиск студентов по должности</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <input value={jobTitle} onChange={e => setJobTitle(e.target.value)} placeholder="Например: Python разработчик" onKeyDown={e => e.key === 'Enter' && search()} style={{ flex: 1 }} />
          <button className="btn btn-primary" onClick={search} disabled={searching}>
            {searching ? <span className="spinner" /> : '🔍 Найти'}
          </button>
        </div>
      </div>

      <div className="grid-2">
        {/* Results list */}
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Результаты ({results.length})</h3>
          {results.length === 0 ? <p style={{ color: 'var(--text-muted)' }}>Введите должность и нажмите «Найти»</p> : (
            <table>
              <thead><tr><th>ID</th><th>ЗП</th><th>Уверенность</th><th></th></tr></thead>
              <tbody>
                {results.map(r => (
                  <tr key={r.student_id} style={{ cursor: 'pointer', background: selectedId === r.student_id ? 'rgba(88,166,255,0.1)' : undefined }} onClick={() => openProfile(r.student_id)}>
                    <td>#{r.student_id}</td>
                    <td style={{ color: 'var(--green)' }}>{r.estimated_salary ? `₽${Math.round(r.estimated_salary).toLocaleString()}` : '—'}</td>
                    <td><span className={`badge ${r.confidence > 0.5 ? 'badge-green' : 'badge-yellow'}`}>{(r.confidence * 100).toFixed(0)}%</span></td>
                    <td>{r.disciplines.length} дисц.</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Student profile */}
        <div className="card">
          {profile ? (
            <>
              <div style={{ display: 'flex', gap: 16, marginBottom: 16 }}>
                <div style={{ width: 80, height: 80, borderRadius: 8, background: 'var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                  {profile.photo_url ? <img src={profile.photo_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} /> : <span style={{ fontSize: 32 }}>👤</span>}
                </div>
                <div>
                  <h3>Студент #{profile.student_id}</h3>
                  <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                    Статус: <span className={`badge ${profile.contact_status === 'accepted' ? 'badge-green' : profile.contact_status === 'pending' ? 'badge-yellow' : profile.contact_status ? 'badge-red' : 'badge-blue'}`}>
                      {profile.contact_status || 'нет запроса'}
                    </span>
                  </p>
                </div>
              </div>

              <h4 style={{ marginBottom: 8 }}>Дисциплины</h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 16 }}>
                {profile.disciplines.map(d => (
                  <span key={d.id} className={`badge ${d.grade === 5 ? 'badge-green' : d.grade === 4 ? 'badge-yellow' : 'badge-red'}`}>{d.name} ({d.grade})</span>
                ))}
              </div>

              {profile.about_me && (
                <div style={{ marginBottom: 16 }}>
                  <h4 style={{ marginBottom: 8 }}>О студенте</h4>
                  <p style={{ fontSize: 14 }}>{profile.about_me}</p>
                </div>
              )}

              {!profile.contact_status && (
                <button className="btn btn-primary" onClick={() => requestContact(profile.student_id)}>📩 Запросить контакт</button>
              )}
            </>
          ) : <p style={{ color: 'var(--text-muted)' }}>Выберите студента из списка</p>}
        </div>
      </div>

      {/* Детализация навыков - новый блок */}
      {selectedStudent && selectedStudent.skill_matches && selectedStudent.skill_matches.length > 0 && (
        <>
          {/* Диаграмма навыков */}
          {chartData && (
            <div className="card">
              <div style={{ height: 300 }}>
                <Bar data={chartData} options={chartOptions} />
              </div>
            </div>
          )}

          {/* Фильтры и порог сходства */}
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>Фильтры и порог сходства</h3>
            
            <div style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', marginBottom: 6, fontWeight: 500 }}>
                Порог сходства: {(similarityThreshold * 100).toFixed(0)}%
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={similarityThreshold}
                onChange={e => setSimilarityThreshold(+e.target.value)}
                style={{ width: '100%' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                <span>0%</span>
                <span>100%</span>
              </div>
              <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 8 }}>
                Навыки ниже порога будут вычеркнуты
              </p>
            </div>

            <div className="grid-2" style={{ marginBottom: 16 }}>
              <div>
                <label style={{ display: 'block', marginBottom: 6, fontWeight: 500 }}>
                  Мин. сходство (%)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  value={Math.round(minSimilarity * 100)}
                  onChange={e => {
                    const value = Number(e.target.value) || 0
                    setMinSimilarity(Math.max(0, Math.min(1, value / 100)))
                  }}
                  placeholder="0"
                  style={{ width: '100%' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: 6, fontWeight: 500 }}>
                  Мин. зарплата (₽)
                </label>
                <input
                  type="number"
                  min="0"
                  step="10000"
                  value={minSalary}
                  onChange={e => setMinSalary(+e.target.value)}
                  placeholder="0"
                  style={{ width: '100%' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: 6, fontWeight: 500 }}>
                  Мин. кол-во вакансий
                </label>
                <input
                  type="number"
                  min="0"
                  value={minVacancyCount}
                  onChange={e => setMinVacancyCount(+e.target.value)}
                  placeholder="0"
                  style={{ width: '100%' }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: 8, fontSize: 13 }}>
              <button
                className="btn"
                onClick={() => {
                  setSimilarityThreshold(0)
                  setMinSimilarity(0)
                  setMinSalary(0)
                  setMinVacancyCount(0)
                }}
                style={{ fontSize: 13 }}
              >
                🔄 Сбросить фильтры
              </button>
              <span style={{ color: 'var(--text-muted)', alignSelf: 'center' }}>
                Показано: {filteredAndSortedSkills.length} / {selectedStudent.skill_matches.length}
              </span>
            </div>
          </div>

          {/* Таблица навыков */}
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3>Детализация по навыкам</h3>
            </div>

            {filteredAndSortedSkills.length === 0 ? (
              <p style={{ color: 'var(--text-muted)' }}>
                {selectedStudent.skill_matches.length === 0 
                  ? 'Навыки не найдены' 
                  : 'Нет навыков, соответствующих фильтрам'}
              </p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table>
                  <thead>
                    <tr>
                      <th>Дисциплина</th>
                      <th>Навык hh.ru</th>
                      <th 
                        style={{ cursor: 'pointer', userSelect: 'none' }} 
                        onClick={() => handleSort('similarity')}
                        title="Нажмите для сортировки"
                      >
                        Сходство {getSortIcon('similarity')}
                      </th>
                      <th 
                        style={{ cursor: 'pointer', userSelect: 'none' }} 
                        onClick={() => handleSort('avg_salary')}
                        title="Нажмите для сортировки"
                      >
                        Ср. ЗП {getSortIcon('avg_salary')}
                      </th>
                      <th 
                        style={{ cursor: 'pointer', userSelect: 'none' }} 
                        onClick={() => handleSort('vacancy_count')}
                        title="Нажмите для сортировки"
                      >
                        Вакансий {getSortIcon('vacancy_count')}
                      </th>
                      <th>Оценка</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAndSortedSkills.map((sm, idx) => {
                      const isBelowThreshold = sm.similarity < similarityThreshold
                      
                      return (
                        <tr
                          key={idx}
                          style={{
                            textDecoration: isBelowThreshold ? 'line-through' : 'none',
                            backgroundColor: isBelowThreshold ? 'rgba(156, 163, 175, 0.1)' : 'transparent',
                            opacity: isBelowThreshold ? 0.6 : 1,
                            transition: 'all 0.2s ease',
                          }}
                        >
                          <td>{sm.discipline}</td>
                          <td>{sm.skill_name}</td>
                          <td>
                            <span style={{ 
                              color: isBelowThreshold ? 'var(--text-muted)' : 'inherit',
                              fontWeight: isBelowThreshold ? 'normal' : 500
                            }}>
                              {(sm.similarity * 100).toFixed(1)}%
                            </span>
                          </td>
                          <td style={{ color: sm.avg_salary ? 'var(--green)' : 'var(--text-muted)' }}>
                            {sm.avg_salary ? formatSalary(sm.avg_salary) : '—'}
                          </td>
                          <td>{sm.vacancy_count}</td>
                          <td>
                            {sm.grade !== null ? (
                              <span className={`badge ${sm.grade === 5 ? 'badge-green' : sm.grade === 4 ? 'badge-yellow' : 'badge-red'}`}>
                                {sm.grade}
                              </span>
                            ) : '—'}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </>
  )
}

function RequestsTab() {
  const [requests, setRequests] = useState<ContactRequest[]>([])
  useEffect(() => { api.get('/employer/contact-requests').then(r => setRequests(r.data)) }, [])

  return (
    <div className="card">
      <h3 style={{ marginBottom: 16 }}>Мои запросы</h3>
      {requests.length === 0 ? <p style={{ color: 'var(--text-muted)' }}>Нет запросов</p> : (
        <table>
          <thead><tr><th>Студент</th><th>Статус</th><th>Дата</th></tr></thead>
          <tbody>
            {requests.map(r => (
              <tr key={r.id}>
                <td>Студент #{r.student_id}</td>
                <td><span className={`badge ${r.status === 'accepted' ? 'badge-green' : r.status === 'rejected' ? 'badge-red' : 'badge-yellow'}`}>{r.status}</span></td>
                <td style={{ fontSize: 13 }}>{new Date(r.created_at).toLocaleDateString('ru')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function EmployerChatTab() {
  const { user } = useAuth()
  const [requests, setRequests] = useState<ContactRequest[]>([])
  const [activeChat, setActiveChat] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [text, setText] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.get('/employer/contact-requests').then(r => setRequests(r.data.filter((cr: ContactRequest) => cr.status === 'accepted')))
  }, [])

  const openChat = async (crId: number) => {
    setActiveChat(crId)
    const { data } = await api.get(`/chat/${crId}/messages`)
    setMessages(data)

    wsRef.current?.close()
    const token = localStorage.getItem('access_token')
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${proto}//${window.location.host}/ws/chat/${crId}?token=${token}`)
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      setMessages(prev => [...prev, msg])
    }
    wsRef.current = ws
  }

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])
  useEffect(() => () => { wsRef.current?.close() }, [])

  const send = () => {
    if (!text.trim() || !wsRef.current) return
    wsRef.current.send(JSON.stringify({ text }))
    setText('')
  }

  return (
    <div className="grid-2">
      <div className="card">
        <h3 style={{ marginBottom: 12 }}>Чаты</h3>
        {requests.length === 0 ? <p style={{ color: 'var(--text-muted)' }}>Нет принятых запросов</p> :
          requests.map(r => (
            <div key={r.id} className="btn" style={{ width: '100%', marginBottom: 8, justifyContent: 'flex-start' }} onClick={() => openChat(r.id)}>
              💬 Студент #{r.student_id}
            </div>
          ))}
      </div>
      <div className="card">
        {activeChat ? (
          <>
            <div className="chat-messages">
              {messages.map(m => (
                <div key={m.id} className={`chat-msg ${m.sender_id === user?.id ? 'mine' : 'theirs'}`}>
                  {m.text}
                </div>
              ))}
              <div ref={chatEndRef} />
            </div>
            <div className="chat-input">
              <input value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} placeholder="Сообщение..." />
              <button className="btn btn-primary" onClick={send}>→</button>
            </div>
          </>
        ) : <p style={{ color: 'var(--text-muted)' }}>Выберите чат</p>}
      </div>
    </div>
  )
}

function ProfileTab() {
  const [profile, setProfile] = useState<any>(null)
  const [company, setCompany] = useState('')
  const [position, setPosition] = useState('')
  const [contactInfo, setContactInfo] = useState('')
  const [aboutCompany, setAboutCompany] = useState('')
  const [websiteUrl, setWebsiteUrl] = useState('')

  const load = () => api.get('/employer/profile').then(r => {
    setProfile(r.data)
    setCompany(r.data.company_name || '')
    setPosition(r.data.position || '')
    setContactInfo(r.data.contact_info || '')
    setAboutCompany(r.data.about_company || '')
    setWebsiteUrl(r.data.website_url || '')
  })
  useEffect(() => { load() }, [])

  const save = async () => {
    await api.put('/employer/profile', {
      company_name: company,
      position,
      contact_info: contactInfo,
      about_company: aboutCompany,
      website_url: websiteUrl
    })
    load()
  }

  if (!profile) return <div className="card"><div className="spinner" /></div>

  return (
    <div className="card">
      <h3 style={{ marginBottom: 16 }}>Профиль компании</h3>
      <div className="form-group">
        <label>Название компании</label>
        <input value={company} onChange={e => setCompany(e.target.value)} name="organization" autoComplete="organization" />
      </div>
      <div className="form-group">
        <label>Должность</label>
        <input value={position} onChange={e => setPosition(e.target.value)} name="organization-title" autoComplete="organization-title" />
      </div>
      <div className="form-group">
        <label>Контакты</label>
        <textarea value={contactInfo} onChange={e => setContactInfo(e.target.value)} placeholder="Телефон, email, Telegram..." rows={3} style={{ width: '100%', resize: 'vertical' }} />
      </div>
      <div className="form-group">
        <label>О компании</label>
        <textarea value={aboutCompany} onChange={e => setAboutCompany(e.target.value)} placeholder="Расскажите о вашей компании..." rows={4} style={{ width: '100%', resize: 'vertical' }} />
      </div>
      <div className="form-group">
        <label>Сайт компании</label>
        <input value={websiteUrl} onChange={e => setWebsiteUrl(e.target.value)} placeholder="https://example.com" type="url" autoComplete="url" />
      </div>
      <button className="btn btn-primary" onClick={save}>Сохранить</button>
    </div>
  )
}
