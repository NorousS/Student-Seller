import { useState, useEffect, useMemo } from 'react'
import api from '../../api/client'
import type { AdminEmployer, Student } from '../../api/types'

export default function AdminDashboard() {
  const [tab, setTab] = useState<'students' | 'employers' | 'parse' | 'tags'>('students')
  const [students, setStudents] = useState<Student[]>([])
  const [employers, setEmployers] = useState<AdminEmployer[]>([])
  const [loading, setLoading] = useState(false)
  const [employersLoading, setEmployersLoading] = useState(false)
  const [updatingEmployerId, setUpdatingEmployerId] = useState<number | null>(null)

  // --- Create student state ---
  const [newName, setNewName] = useState('')
  const [newGroup, setNewGroup] = useState('')
  const [newDiscs, setNewDiscs] = useState('')

  // --- Parse state ---
  const [query, setQuery] = useState('python')
  const [count, setCount] = useState(20)
  const [parseResult, setParseResult] = useState<any>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [parsing, setParsing] = useState(false)

  const loadStudents = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/students/')
      setStudents(data)
    } catch { /* ignore */ }
    setLoading(false)
  }

  const loadEmployers = async () => {
    setEmployersLoading(true)
    try {
      const { data } = await api.get('/admin/employers')
      setEmployers(data)
    } catch { /* ignore */ }
    setEmployersLoading(false)
  }

  useEffect(() => {
    loadStudents()
    loadEmployers()
  }, [])

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
    setParseError(null)
    try {
      const { data } = await api.post('/parse', { query, count })
      setParseResult(data)
    } catch (e: any) {
      const detail = e.response?.data?.detail
      if (typeof detail === 'object' && detail !== null) {
        const parts = [
          detail.message || 'Ошибка парсинга HH',
          detail.status_code ? `HTTP ${detail.status_code}` : null,
          detail.error_type ? `type: ${detail.error_type}` : null,
          detail.request_id ? `request_id: ${detail.request_id}` : null,
        ].filter(Boolean)
        setParseError(parts.join(' | '))
      } else {
        setParseError(detail || 'Ошибка парсинга')
      }
    }
    setParsing(false)
  }

  const toggleEmployerPartnership = async (employer: AdminEmployer) => {
    const nextStatus = employer.partnership_status === 'partner' ? 'non_partner' : 'partner'
    setUpdatingEmployerId(employer.employer_user_id)
    try {
      await api.patch(`/admin/partnership/employer/${employer.employer_user_id}`, {
        partnership_status: nextStatus,
      })
      setEmployers(prev => prev.map(item => (
        item.employer_user_id === employer.employer_user_id
          ? { ...item, partnership_status: nextStatus }
          : item
      )))
    } finally {
      setUpdatingEmployerId(null)
    }
  }

  return (
    <div className="container">
      <div className="tabs">
        <div className={`tab ${tab === 'students' ? 'active' : ''}`} onClick={() => setTab('students')} role="tab" tabIndex={0}>👩‍🎓 Студенты</div>
        <div className={`tab ${tab === 'employers' ? 'active' : ''}`} onClick={() => setTab('employers')} role="tab" tabIndex={0}>🏢 Работодатели</div>
        <div className={`tab ${tab === 'parse' ? 'active' : ''}`} onClick={() => setTab('parse')} role="tab" tabIndex={0}>🔍 Парсинг</div>
        <div className={`tab ${tab === 'tags' ? 'active' : ''}`} onClick={() => setTab('tags')} role="tab" tabIndex={0}>🏷️ Теги</div>
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

      {/* === Employers tab === */}
      {tab === 'employers' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center', marginBottom: 16 }}>
            <h3>Работодатели ({employers.length})</h3>
            <button className="btn" onClick={loadEmployers} disabled={employersLoading}>
              {employersLoading ? <span className="spinner" /> : 'Обновить'}
            </button>
          </div>
          {employersLoading ? <div className="spinner" /> : (
            <table>
              <thead>
                <tr>
                  <th>Email</th>
                  <th>Компания</th>
                  <th>Должность</th>
                  <th>Статус</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {employers.map(employer => (
                  <tr key={employer.employer_user_id}>
                    <td>{employer.email}</td>
                    <td>{employer.company_name || '—'}</td>
                    <td>{employer.position || '—'}</td>
                    <td>
                      <span className={`badge ${employer.partnership_status === 'partner' ? 'badge-green' : 'badge-yellow'}`}>
                        {employer.partnership_status === 'partner' ? 'Партнер' : 'Не партнер'}
                      </span>
                    </td>
                    <td>
                      <button
                        className={`btn ${employer.partnership_status === 'partner' ? '' : 'btn-primary'}`}
                        onClick={() => toggleEmployerPartnership(employer)}
                        disabled={updatingEmployerId === employer.employer_user_id}
                      >
                        {updatingEmployerId === employer.employer_user_id
                          ? <span className="spinner" />
                          : employer.partnership_status === 'partner'
                          ? 'Снять статус'
                          : 'Сделать партнером'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
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

          {parseError && (
            <div className="alert-error" style={{ marginTop: 16 }}>
              {parseError}
            </div>
          )}

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
  const [sortField, setSortField] = useState<'name' | 'count' | 'percent'>('count')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')

  useEffect(() => { api.get('/tags').then(r => setTags(r.data)).catch(() => {}) }, [])
  const totalVacancies = tags?.total_vacancies || 0
  const sortedTags = useMemo(() => {
    const list = [...(tags?.tags || [])]
    return list.sort((a: any, b: any) => {
      let cmp = 0
      if (sortField === 'name') cmp = String(a.name).localeCompare(String(b.name), 'ru')
      if (sortField === 'count') cmp = Number(a.count || 0) - Number(b.count || 0)
      if (sortField === 'percent') {
        const pctA = totalVacancies > 0 ? (Number(a.count || 0) / totalVacancies) * 100 : 0
        const pctB = totalVacancies > 0 ? (Number(b.count || 0) / totalVacancies) * 100 : 0
        cmp = pctA - pctB
      }
      return sortDirection === 'asc' ? cmp : -cmp
    })
  }, [tags, sortField, sortDirection, totalVacancies])

  if (!tags) return <div className="card"><div className="spinner" /></div>

  const setSort = (field: 'name' | 'count' | 'percent') => {
    if (sortField === field) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDirection(field === 'name' ? 'asc' : 'desc')
    }
  }

  const sortIcon = (field: 'name' | 'count' | 'percent') => (
    sortField !== field ? '↕️' : sortDirection === 'asc' ? '↑' : '↓'
  )

  return (
    <div className="card">
      <h3 style={{ marginBottom: 16 }}>Навыки и теги</h3>
      <div className="grid-2" style={{ marginBottom: 16 }}>
        <div className="card stat-card"><div className="value">{totalVacancies}</div><div className="label">Вакансий</div></div>
        <div className="card stat-card"><div className="value">{tags.tags?.length || 0}</div><div className="label">Тегов</div></div>
      </div>
      <table className="tags-table">
        <thead>
          <tr>
            <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => setSort('name')}>
              Навык {sortIcon('name')}
            </th>
            <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => setSort('count')}>
              Вакансий {sortIcon('count')}
            </th>
            <th style={{ cursor: 'pointer', userSelect: 'none' }} onClick={() => setSort('percent')}>
              % {sortIcon('percent')}
            </th>
          </tr>
        </thead>
        <tbody>
          {sortedTags.slice(0, 100).map((t: any) => {
            const pct = totalVacancies ? (t.count / totalVacancies) * 100 : 0
            return (
              <tr key={t.name} className={t.count <= 1 ? 'filtered-tag' : undefined}>
                <td><span className="tag-badge">{t.name}</span></td>
                <td>{t.count}</td>
                <td>
                  <div className="tag-bar-bg"><div className="tag-bar" style={{ width: `${Math.min(100, pct)}%` }} /></div>
                  {pct.toFixed(1)}%
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}
