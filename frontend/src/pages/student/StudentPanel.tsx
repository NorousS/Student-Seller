import { useState, useEffect, useRef } from 'react'
import api from '../../api/client'
import { useAuth } from '../../store/AuthContext'
import type { StudentProfile, ContactRequest, ChatMessage } from '../../api/types'

export default function StudentPanel() {
  const [tab, setTab] = useState<'profile' | 'skills' | 'evaluation' | 'requests' | 'chat'>('profile')
  return (
    <div className="container">
      <div className="tabs">
        <div className={`tab ${tab === 'profile' ? 'active' : ''}`} onClick={() => setTab('profile')} role="tab" tabIndex={0}>👤 Профиль</div>
        <div className={`tab ${tab === 'skills' ? 'active' : ''}`} onClick={() => setTab('skills')} role="tab" tabIndex={0}>📚 Навыки</div>
        <div className={`tab ${tab === 'evaluation' ? 'active' : ''}`} onClick={() => setTab('evaluation')} role="tab" tabIndex={0}>💰 Оценка</div>
        <div className={`tab ${tab === 'requests' ? 'active' : ''}`} onClick={() => setTab('requests')} role="tab" tabIndex={0}>📩 Запросы</div>
        <div className={`tab ${tab === 'chat' ? 'active' : ''}`} onClick={() => setTab('chat')} role="tab" tabIndex={0}>💬 Чат</div>
      </div>
      {tab === 'profile' && <ProfileTab />}
      {tab === 'skills' && <SkillsTab />}
      {tab === 'evaluation' && <EvaluationTab />}
      {tab === 'requests' && <RequestsTab />}
      {tab === 'chat' && <ChatTab />}
    </div>
  )
}

function ProfileTab() {
  const [profile, setProfile] = useState<any>(null)
  const [aboutMe, setAboutMe] = useState('')
  const [saving, setSaving] = useState(false)

  const load = () => api.get('/profile/student/').then(r => { setProfile(r.data); setAboutMe(r.data.about_me || '') })
  useEffect(() => { load() }, [])

  const save = async () => {
    setSaving(true)
    await api.put('/profile/student/', null, { params: { about_me: aboutMe } })
    await load()
    setSaving(false)
  }

  const uploadPhoto = async (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    await api.post('/profile/student/photo', fd)
    load()
  }

  if (!profile) return <div className="card"><div className="spinner" /></div>

  return (
    <>
      <div className="card">
        <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ width: 120, height: 120, borderRadius: 12, background: 'var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', marginBottom: 8 }}>
              {profile.photo_url
                ? <img src={profile.photo_url} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                : <span style={{ fontSize: 48 }}>👤</span>}
            </div>
            <label className="btn" style={{ fontSize: 12 }}>
              📷 Загрузить
              <input type="file" accept="image/jpeg,image/png" hidden onChange={e => e.target.files?.[0] && uploadPhoto(e.target.files[0])} />
            </label>
          </div>
          <div style={{ flex: 1 }}>
            <h2>{profile.full_name}</h2>
            <p style={{ color: 'var(--text-muted)' }}>{profile.group_name || 'Группа не указана'}</p>
          </div>
        </div>
      </div>
      <div className="card">
        <h3 style={{ marginBottom: 12 }}>О себе</h3>
        <textarea rows={4} value={aboutMe} onChange={e => setAboutMe(e.target.value)} placeholder="Расскажите о себе..." />
        <button className="btn btn-primary" style={{ marginTop: 12 }} onClick={save} disabled={saving}>
          {saving ? 'Сохранение...' : 'Сохранить'}
        </button>
      </div>
    </>
  )
}

function SkillsTab() {
  const [disciplines, setDisciplines] = useState<any[]>([])
  const [newName, setNewName] = useState('')
  const [newGrade, setNewGrade] = useState(5)

  const load = () => api.get('/profile/student/disciplines').then(r => setDisciplines(r.data))
  useEffect(() => { load() }, [])

  const addSkill = async () => {
    if (!newName.trim()) return
    await api.post('/profile/student/disciplines', { disciplines: [{ name: newName, grade: newGrade }] })
    setNewName('')
    load()
  }

  const deleteSkill = async (id: number) => {
    if (!confirm('Удалить дисциплину?')) return
    await api.delete(`/profile/student/disciplines/${id}`)
    load()
  }

  const updateGrade = async (name: string, grade: number) => {
    await api.post('/profile/student/disciplines', { disciplines: [{ name, grade }] })
    load()
  }

  return (
    <div className="card">
      <h3 style={{ marginBottom: 16 }}>Мои навыки</h3>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Название дисциплины" style={{ flex: 1 }} />
        <select value={newGrade} onChange={e => setNewGrade(+e.target.value)} style={{ width: 80 }}>
          <option value={5}>5</option>
          <option value={4}>4</option>
          <option value={3}>3</option>
        </select>
        <button className="btn btn-primary" onClick={addSkill}>Добавить</button>
      </div>
      <table>
        <thead><tr><th>Дисциплина</th><th>Оценка</th><th></th></tr></thead>
        <tbody>
          {disciplines.map(d => (
            <tr key={d.id}>
              <td>{d.name}</td>
              <td>
                <select
                  value={d.grade}
                  onChange={e => updateGrade(d.name, +e.target.value)}
                  style={{ padding: '2px 6px', borderRadius: 4, border: '1px solid var(--border)' }}
                >
                  <option value={5}>5</option>
                  <option value={4}>4</option>
                  <option value={3}>3</option>
                </select>
              </td>
              <td>
                <button
                  onClick={() => deleteSkill(d.id)}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--red)', fontSize: 16 }}
                  title="Удалить"
                >
                  🗑️
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

interface SkillMatch {
  discipline: string
  skill_name: string
  similarity: number
  avg_salary: number | null
  vacancy_count: number
  grade: number | null
  grade_coeff: number | null
  excluded: boolean
}

interface EvaluationResult {
  student_id: number
  student_name: string
  specialty: string
  estimated_salary: number
  confidence: number
  total_disciplines: number
  matched_disciplines: number
  skill_matches: SkillMatch[]
}

function EvaluationTab() {
  const [specialty, setSpecialty] = useState('')
  const [experience, setExperience] = useState('Любой')
  const [topK, setTopK] = useState(5)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<EvaluationResult | null>(null)
  const [excludedSkills, setExcludedSkills] = useState<Set<string>>(new Set())

  const experienceMap: Record<string, string | null> = {
    'Любой': null,
    'Без опыта': 'noExperience',
    '1-3 года': 'between1And3',
    '3-6 лет': 'between3And6',
    '6+ лет': 'moreThan6'
  }

  const evaluate = async () => {
    if (!specialty.trim()) {
      alert('Введите специальность')
      return
    }

    setLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('specialty', specialty)
      const expValue = experienceMap[experience]
      if (expValue) params.set('experience', expValue)
      params.set('top_k', String(topK))
      excludedSkills.forEach(s => {
        const skillName = s.substring(s.indexOf(':') + 1)
        params.append('excluded_skills', skillName)
      })

      const { data } = await api.post(`/profile/student/evaluate?${params.toString()}`)
      setResult(data)
      
      // Update excluded skills from result
      const newExcluded = new Set<string>()
      data.skill_matches.forEach((sm: SkillMatch) => {
        if (sm.excluded) {
          newExcluded.add(`${sm.discipline}:${sm.skill_name}`)
        }
      })
      setExcludedSkills(newExcluded)
    } catch (err: any) {
      alert(`Ошибка: ${err.response?.data?.detail || err.message}`)
    } finally {
      setLoading(false)
    }
  }

  const toggleExcluded = (discipline: string, skillName: string) => {
    const key = `${discipline}:${skillName}`
    const newExcluded = new Set(excludedSkills)
    if (newExcluded.has(key)) {
      newExcluded.delete(key)
    } else {
      newExcluded.add(key)
    }
    setExcludedSkills(newExcluded)
  }

  const formatSalary = (salary: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB',
      maximumFractionDigits: 0
    }).format(salary)
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence > 70) return 'badge-green'
    if (confidence > 40) return 'badge-yellow'
    return 'badge-red'
  }

  return (
    <>
      <div className="card">
        <h3 style={{ marginBottom: 16 }}>Параметры оценки</h3>
        
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 6, fontWeight: 500 }}>Специальность *</label>
          <input
            type="text"
            value={specialty}
            onChange={e => setSpecialty(e.target.value)}
            placeholder="Например: Python разработчик"
            style={{ width: '100%' }}
          />
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 6, fontWeight: 500 }}>Опыт работы</label>
          <select
            value={experience}
            onChange={e => setExperience(e.target.value)}
            style={{ width: '100%' }}
          >
            <option value="Любой">Любой</option>
            <option value="Без опыта">Без опыта</option>
            <option value="1-3 года">1-3 года</option>
            <option value="3-6 лет">3-6 лет</option>
            <option value="6+ лет">6+ лет</option>
          </select>
        </div>

        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', marginBottom: 6, fontWeight: 500 }}>
            Кол-во навыков на дисциплину: {topK}
          </label>
          <input
            type="range"
            min="1"
            max="20"
            value={topK}
            onChange={e => setTopK(+e.target.value)}
            style={{ width: '100%' }}
          />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)' }}>
            <span>1</span>
            <span>20</span>
          </div>
        </div>

        <button
          className="btn btn-primary"
          onClick={evaluate}
          disabled={loading || !specialty.trim()}
          style={{ width: '100%' }}
        >
          {loading ? 'Оценка...' : '💰 Оценить стоимость'}
        </button>
      </div>

      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div className="spinner" />
          <p style={{ marginTop: 16, color: 'var(--text-muted)' }}>Анализируем навыки...</p>
        </div>
      )}

      {result && !loading && (
        <>
          <div className="grid-2">
            <div className="card">
              <h4 style={{ marginBottom: 8, color: 'var(--text-muted)', fontSize: 14 }}>Оценочная зарплата</h4>
              <div style={{ fontSize: 32, fontWeight: 700, color: 'var(--primary)' }}>
                {formatSalary(result.estimated_salary)}
              </div>
            </div>

            <div className="card">
              <h4 style={{ marginBottom: 8, color: 'var(--text-muted)', fontSize: 14 }}>Уверенность оценки</h4>
              <div style={{ fontSize: 32, fontWeight: 700 }}>
                <span className={`badge ${getConfidenceColor(result.confidence * 100)}`} style={{ fontSize: 24, padding: '8px 16px' }}>
                  {(result.confidence * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>

          <div className="grid-2">
            <div className="card">
              <h4 style={{ marginBottom: 8, color: 'var(--text-muted)', fontSize: 14 }}>Всего дисциплин</h4>
              <div style={{ fontSize: 28, fontWeight: 600 }}>{result.total_disciplines}</div>
            </div>

            <div className="card">
              <h4 style={{ marginBottom: 8, color: 'var(--text-muted)', fontSize: 14 }}>Совпало дисциплин</h4>
              <div style={{ fontSize: 28, fontWeight: 600, color: 'var(--success)' }}>{result.matched_disciplines}</div>
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3>Детализация по навыкам</h3>
              <button
                className="btn btn-primary"
                onClick={evaluate}
                disabled={loading}
                style={{ fontSize: 14 }}
              >
                🔄 Пересчитать
              </button>
            </div>

            {result.skill_matches.length === 0 ? (
              <p style={{ color: 'var(--text-muted)' }}>Навыки не найдены</p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table>
                  <thead>
                    <tr>
                      <th>Дисциплина</th>
                      <th>Навык hh.ru</th>
                      <th>Сходство</th>
                      <th>Ср. ЗП</th>
                      <th>Вакансий</th>
                      <th>Оценка</th>
                      <th>Исключить</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.skill_matches.map((sm, idx) => {
                      const isExcluded = excludedSkills.has(`${sm.discipline}:${sm.skill_name}`)
                      return (
                        <tr
                          key={idx}
                          style={{
                            textDecoration: isExcluded ? 'line-through' : 'none',
                            backgroundColor: isExcluded ? 'rgba(239, 68, 68, 0.1)' : 'transparent'
                          }}
                        >
                          <td>{sm.discipline}</td>
                          <td>{sm.skill_name}</td>
                          <td>{(sm.similarity * 100).toFixed(1)}%</td>
                          <td>{sm.avg_salary ? formatSalary(sm.avg_salary) : '—'}</td>
                          <td>{sm.vacancy_count}</td>
                          <td>
                            {sm.grade !== null && sm.grade !== undefined ? (
                              <span className={`badge ${sm.grade === 5 ? 'badge-green' : sm.grade === 4 ? 'badge-yellow' : 'badge-red'}`}>
                                {sm.grade}
                              </span>
                            ) : '—'}
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            <input
                              type="checkbox"
                              checked={isExcluded}
                              onChange={() => toggleExcluded(sm.discipline, sm.skill_name)}
                              style={{ cursor: 'pointer', width: 18, height: 18 }}
                            />
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
  const load = () => api.get('/profile/student/contact-requests').then(r => setRequests(r.data))
  useEffect(() => { load() }, [])

  const respond = async (id: number, accept: boolean) => {
    await api.post(`/profile/student/contact-requests/${id}/respond`, { accept })
    load()
  }

  return (
    <div className="card">
      <h3 style={{ marginBottom: 16 }}>Запросы на контакт</h3>
      {requests.length === 0 ? <p style={{ color: 'var(--text-muted)' }}>Нет запросов</p> : (
        <table>
          <thead><tr><th>Компания</th><th>Статус</th><th>Дата</th><th>Действия</th></tr></thead>
          <tbody>
            {requests.map(r => (
              <tr key={r.id}>
                <td>{r.employer_company || `Работодатель #${r.employer_id}`}</td>
                <td><span className={`badge ${r.status === 'accepted' ? 'badge-green' : r.status === 'rejected' ? 'badge-red' : 'badge-yellow'}`}>{r.status}</span></td>
                <td style={{ fontSize: 13 }}>{new Date(r.created_at).toLocaleDateString('ru')}</td>
                <td>
                  {r.status === 'pending' && (
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-success" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => respond(r.id, true)}>✅ Принять</button>
                      <button className="btn btn-danger" style={{ fontSize: 12, padding: '4px 10px' }} onClick={() => respond(r.id, false)}>❌ Отклонить</button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function ChatTab() {
  const { user } = useAuth()
  const [requests, setRequests] = useState<ContactRequest[]>([])
  const [activeChat, setActiveChat] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [text, setText] = useState('')
  const wsRef = useRef<WebSocket | null>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.get('/profile/student/contact-requests').then(r => setRequests(r.data.filter((cr: ContactRequest) => cr.status === 'accepted')))
  }, [])

  const openChat = async (crId: number) => {
    setActiveChat(crId)
    const { data } = await api.get(`/chat/${crId}/messages`)
    setMessages(data)

    // WebSocket
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
              💬 {r.employer_company || `Работодатель #${r.employer_id}`}
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
