import { useState, useEffect, useRef } from 'react'
import api from '../../api/client'
import { useAuth } from '../../store/AuthContext'
import type { AnonymizedStudent, AnonymizedStudentProfile, ContactRequest, ChatMessage } from '../../api/types'

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

function SearchTab() {
  const [jobTitle, setJobTitle] = useState('')
  const [results, setResults] = useState<AnonymizedStudent[]>([])
  const [searching, setSearching] = useState(false)
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [profile, setProfile] = useState<AnonymizedStudentProfile | null>(null)

  const search = async () => {
    if (!jobTitle.trim()) return
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
  }

  const requestContact = async (studentId: number) => {
    try {
      await api.post(`/employer/students/${studentId}/request-contact`)
      openProfile(studentId)
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка')
    }
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
              <thead><tr><th>ID</th><th>Salary</th><th>Confidence</th><th></th></tr></thead>
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

  const load = () => api.get('/employer/profile').then(r => { setProfile(r.data); setCompany(r.data.company_name || ''); setPosition(r.data.position || '') })
  useEffect(() => { load() }, [])

  const save = async () => {
    await api.put('/employer/profile', { company_name: company, position })
    load()
  }

  if (!profile) return <div className="card"><div className="spinner" /></div>

  return (
    <div className="card">
      <h3 style={{ marginBottom: 16 }}>Профиль компании</h3>
      <div className="form-group">
        <label>Название компании</label>
        <input value={company} onChange={e => setCompany(e.target.value)} />
      </div>
      <div className="form-group">
        <label>Должность</label>
        <input value={position} onChange={e => setPosition(e.target.value)} />
      </div>
      <button className="btn btn-primary" onClick={save}>Сохранить</button>
    </div>
  )
}
