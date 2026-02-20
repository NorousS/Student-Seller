import { useState, useEffect } from 'react'
import api from '../../api/client'
import type { Student } from '../../api/types'

export default function AdminDashboard() {
  const [tab, setTab] = useState<'students' | 'parse' | 'tags'>('students')
  const [students, setStudents] = useState<Student[]>([])
  const [loading, setLoading] = useState(false)

  // --- Create student state ---
  const [newName, setNewName] = useState('')
  const [newGroup, setNewGroup] = useState('')
  const [newDiscs, setNewDiscs] = useState('')

  // --- Parse state ---
  const [query, setQuery] = useState('python')
  const [count, setCount] = useState(20)
  const [parseResult, setParseResult] = useState<any>(null)
  const [parsing, setParsing] = useState(false)

  const loadStudents = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/students/')
      setStudents(data)
    } catch { /* ignore */ }
    setLoading(false)
  }

  useEffect(() => { loadStudents() }, [])

  const createStudent = async () => {
    if (!newName.trim()) return
    const disciplines = newDiscs.trim()
      ? newDiscs.split(',').map(d => ({ name: d.trim(), grade: 5 }))
      : []
    await api.post('/students/', { full_name: newName, group_name: newGroup || null, disciplines })
    setNewName(''); setNewGroup(''); setNewDiscs('')
    loadStudents()
  }

  const parseVacancies = async () => {
    setParsing(true)
    try {
      const { data } = await api.post('/parse', { query, count })
      setParseResult(data)
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Ошибка парсинга')
    }
    setParsing(false)
  }

  return (
    <div className="container">
      <div className="tabs">
        <div className={`tab ${tab === 'students' ? 'active' : ''}`} onClick={() => setTab('students')}>👩‍🎓 Студенты</div>
        <div className={`tab ${tab === 'parse' ? 'active' : ''}`} onClick={() => setTab('parse')}>🔍 Парсинг</div>
        <div className={`tab ${tab === 'tags' ? 'active' : ''}`} onClick={() => setTab('tags')}>🏷️ Теги</div>
      </div>

      {/* === Students tab === */}
      {tab === 'students' && (
        <>
          <div className="card">
            <h3 style={{ marginBottom: 16 }}>Создать студента</h3>
            <div className="grid-2">
              <div className="form-group">
                <label>ФИО</label>
                <input value={newName} onChange={e => setNewName(e.target.value)} placeholder="Иванов Иван" />
              </div>
              <div className="form-group">
                <label>Группа</label>
                <input value={newGroup} onChange={e => setNewGroup(e.target.value)} placeholder="ИВТ-21" />
              </div>
            </div>
            <div className="form-group">
              <label>Дисциплины (через запятую)</label>
              <input value={newDiscs} onChange={e => setNewDiscs(e.target.value)} placeholder="Python, SQL, Docker" />
            </div>
            <button className="btn btn-primary" onClick={createStudent}>Создать</button>
          </div>

          <div className="card">
            <h3 style={{ marginBottom: 16 }}>Список студентов ({students.length})</h3>
            {loading ? <div className="spinner" /> : (
              <table>
                <thead><tr><th>ID</th><th>ФИО</th><th>Группа</th><th>Дисциплины</th></tr></thead>
                <tbody>
                  {students.map(s => (
                    <tr key={s.id}>
                      <td>{s.id}</td>
                      <td>{s.full_name}</td>
                      <td>{s.group_name || '—'}</td>
                      <td>{s.disciplines.map(d => (
                        <span key={d.id} className={`badge ${d.grade === 5 ? 'badge-green' : d.grade === 4 ? 'badge-yellow' : 'badge-red'}`} style={{ marginRight: 4 }}>
                          {d.name} ({d.grade})
                        </span>
                      ))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}

      {/* === Parse tab === */}
      {tab === 'parse' && (
        <div className="card">
          <h3 style={{ marginBottom: 16 }}>Парсинг вакансий с hh.ru</h3>
          <div className="grid-2">
            <div className="form-group">
              <label>Поисковый запрос</label>
              <input value={query} onChange={e => setQuery(e.target.value)} />
            </div>
            <div className="form-group">
              <label>Количество (1-100)</label>
              <input type="number" min={1} max={100} value={count} onChange={e => setCount(+e.target.value)} />
            </div>
          </div>
          <button className="btn btn-primary" onClick={parseVacancies} disabled={parsing}>
            {parsing ? <span className="spinner" /> : '🚀 Парсить'}
          </button>

          {parseResult && (
            <div style={{ marginTop: 24 }}>
              <div className="grid-2">
                <div className="card stat-card">
                  <div className="value">{parseResult.total_parsed}</div>
                  <div className="label">Вакансий спарсено</div>
                </div>
                <div className="card stat-card">
                  <div className="value">{parseResult.average_salary ? `₽${Math.round(parseResult.average_salary).toLocaleString()}` : '—'}</div>
                  <div className="label">Средняя зарплата</div>
                </div>
              </div>
              {parseResult.tags?.length > 0 && (
                <table>
                  <thead><tr><th>Навык</th><th>Кол-во</th></tr></thead>
                  <tbody>
                    {parseResult.tags.slice(0, 20).map((t: any) => (
                      <tr key={t.name}><td>{t.name}</td><td>{t.count}</td></tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      )}

      {/* === Tags tab === */}
      {tab === 'tags' && <TagsTab />}
    </div>
  )
}

function TagsTab() {
  const [tags, setTags] = useState<any>(null)
  useEffect(() => { api.get('/tags').then(r => setTags(r.data)).catch(() => {}) }, [])
  if (!tags) return <div className="card"><div className="spinner" /></div>
  return (
    <div className="card">
      <h3 style={{ marginBottom: 16 }}>Навыки и теги</h3>
      <div className="grid-2" style={{ marginBottom: 16 }}>
        <div className="card stat-card"><div className="value">{tags.total_vacancies || 0}</div><div className="label">Вакансий</div></div>
        <div className="card stat-card"><div className="value">{tags.tags?.length || 0}</div><div className="label">Тегов</div></div>
      </div>
      <table>
        <thead><tr><th>Навык</th><th>Вакансий</th><th>%</th></tr></thead>
        <tbody>
          {(tags.tags || []).slice(0, 30).map((t: any) => (
            <tr key={t.name}><td>{t.name}</td><td>{t.count}</td><td>{tags.total_vacancies ? ((t.count / tags.total_vacancies) * 100).toFixed(1) : 0}%</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
