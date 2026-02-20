import { useState, useEffect, useRef } from 'react'
import api from '../../api/client'
import { useAuth } from '../../store/AuthContext'
import type { StudentProfile, ContactRequest, ChatMessage } from '../../api/types'

export default function StudentPanel() {
  const [tab, setTab] = useState<'profile' | 'skills' | 'requests' | 'chat'>('profile')
  return (
    <div className="container">
      <div className="tabs">
        <div className={`tab ${tab === 'profile' ? 'active' : ''}`} onClick={() => setTab('profile')} role="tab" tabIndex={0}>👤 Профиль</div>
        <div className={`tab ${tab === 'skills' ? 'active' : ''}`} onClick={() => setTab('skills')} role="tab" tabIndex={0}>📚 Навыки</div>
        <div className={`tab ${tab === 'requests' ? 'active' : ''}`} onClick={() => setTab('requests')} role="tab" tabIndex={0}>📩 Запросы</div>
        <div className={`tab ${tab === 'chat' ? 'active' : ''}`} onClick={() => setTab('chat')} role="tab" tabIndex={0}>💬 Чат</div>
      </div>
      {tab === 'profile' && <ProfileTab />}
      {tab === 'skills' && <SkillsTab />}
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
        <thead><tr><th>Дисциплина</th><th>Оценка</th></tr></thead>
        <tbody>
          {disciplines.map(d => (
            <tr key={d.id}>
              <td>{d.name}</td>
              <td><span className={`badge ${d.grade === 5 ? 'badge-green' : d.grade === 4 ? 'badge-yellow' : 'badge-red'}`}>{d.grade}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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
