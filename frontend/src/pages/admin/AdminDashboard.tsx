import { useState, useEffect, useMemo } from 'react'
import api from '../../api/client'
import type { EvaluationResponse, Student } from '../../api/types'

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

  // --- Edit/evaluate student state ---
  const [editingStudent, setEditingStudent] = useState<Student | null>(null)
  const [editForm, setEditForm] = useState({ full_name: '', group_name: '', disciplines: '' })
  const [savingEdit, setSavingEdit] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)
  const [evaluatingStudent, setEvaluatingStudent] = useState<Student | null>(null)
  const [evalForm, setEvalForm] = useState({ specialty: '', experience: '' })
  const [evaluating, setEvaluating] = useState(false)
  const [evalResult, setEvalResult] = useState<EvaluationResponse | null>(null)
  const [evalError, setEvalError] = useState<string | null>(null)

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

  const openEdit = (student: Student) => {
    setEditError(null)
    setEditForm({
      full_name: student.full_name,
      group_name: student.group_name || '',
      disciplines: student.disciplines.map(d => `${d.name}:${d.grade}`).join(', '),
    })
    setEditingStudent(student)
  }

  const parseDisciplines = () => editForm.disciplines
    .split(',')
    .map(item => {
      const [rawName, rawGrade] = item.trim().split(':')
      const grade = Number.parseInt(rawGrade ?? '5', 10)
      return {
        name: (rawName || '').trim(),
        grade: Number.isNaN(grade) ? 5 : Math.min(5, Math.max(3, grade)),
      }
    })
    .filter(item => item.name)

  const saveEdit = async () => {
    if (!editingStudent) return
    setSavingEdit(true)
    setEditError(null)
    try {
      await api.patch(`/admin/students/${editingStudent.id}`, {
        full_name: editForm.full_name || undefined,
        group_name: editForm.group_name || null,
      })
      await api.post(`/students/${editingStudent.id}/disciplines`, {
        disciplines: parseDisciplines(),
      }, { params: { replace: true } })
      setEditingStudent(null)
      await loadStudents()
    } catch (e: any) {
      setEditError(e.response?.data?.detail || 'Ошибка сохранения')
    } finally {
      setSavingEdit(false)
    }
  }

  const openEvaluate = (student: Student) => {
    setEvalForm({ specialty: '', experience: '' })
    setEvalResult(null)
    setEvalError(null)
    setEvaluatingStudent(student)
  }

  const runEvaluation = async () => {
    if (!evaluatingStudent) return
    setEvaluating(true)
    setEvalError(null)
    setEvalResult(null)
    try {
      const params: Record<string, string> = {}
      if (evalForm.specialty.trim()) params.specialty = evalForm.specialty.trim()
      if (evalForm.experience) params.experience = evalForm.experience
      const { data } = await api.post(`/students/${evaluatingStudent.id}/evaluate`, {}, { params })
      setEvalResult(data)
    } catch (e: any) {
      setEvalError(e.response?.data?.detail || 'Ошибка оценки')
    } finally {
      setEvaluating(false)
    }
  }

  const formatSalary = (salary: number | null) => (
    salary
      ? new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(salary)
      : '—'
  )

  return (
    <div className="container">
      <div className="tabs">
        <div className={`tab ${tab === 'students' ? 'active' : ''}`} onClick={() => setTab('students')} role="tab" tabIndex={0}>👩‍🎓 Студенты</div>
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
                <thead><tr><th>ID</th><th>ФИО</th><th>Группа</th><th>Дисциплины</th><th>Действия</th></tr></thead>
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
                      <td style={{ whiteSpace: 'nowrap' }}>
                        <button className="btn" style={{ marginRight: 6 }} onClick={() => openEdit(s)}>✏️ Редактировать</button>
                        <button className="btn" onClick={() => openEvaluate(s)}>Оценить</button>
                      </td>
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

      {editingStudent && (
        <div className="modal-overlay" onClick={() => setEditingStudent(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3 style={{ marginBottom: 16 }}>Редактировать студента #{editingStudent.id}</h3>
            <div className="form-group">
              <label>ФИО</label>
              <input value={editForm.full_name} onChange={e => setEditForm(prev => ({ ...prev, full_name: e.target.value }))} />
            </div>
            <div className="form-group">
              <label>Группа</label>
              <input value={editForm.group_name} onChange={e => setEditForm(prev => ({ ...prev, group_name: e.target.value }))} placeholder="ИВТ-21" />
            </div>
            <div className="form-group">
              <label>Дисциплины (формат: Название:оценка, ...)</label>
              <textarea
                rows={4}
                value={editForm.disciplines}
                onChange={e => setEditForm(prev => ({ ...prev, disciplines: e.target.value }))}
                placeholder="Python:5, SQL:4, Docker:3"
                style={{ width: '100%', fontFamily: 'inherit', fontSize: 14 }}
              />
              <small style={{ color: 'var(--text-muted)' }}>Разделяйте дисциплины запятыми. Оценка: 3, 4 или 5.</small>
            </div>
            {editError && <div className="alert-error" style={{ marginBottom: 12 }}>{editError}</div>}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
              <button className="btn" onClick={() => setEditingStudent(null)}>Отмена</button>
              <button className="btn btn-primary" onClick={saveEdit} disabled={savingEdit}>
                {savingEdit ? <span className="spinner" /> : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {evaluatingStudent && (
        <div className="modal-overlay" onClick={() => setEvaluatingStudent(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3 style={{ marginBottom: 16 }}>Оценка студента: {evaluatingStudent.full_name}</h3>
            <div className="grid-2">
              <div className="form-group">
                <label>Специальность (необязательно)</label>
                <input
                  value={evalForm.specialty}
                  onChange={e => setEvalForm(prev => ({ ...prev, specialty: e.target.value }))}
                  placeholder="Например: Python-разработчик"
                />
              </div>
              <div className="form-group">
                <label>Опыт</label>
                <select value={evalForm.experience} onChange={e => setEvalForm(prev => ({ ...prev, experience: e.target.value }))}>
                  <option value="">Любой</option>
                  <option value="noExperience">Без опыта</option>
                  <option value="between1And3">1-3 года</option>
                  <option value="between3And6">3-6 лет</option>
                  <option value="moreThan6">Более 6 лет</option>
                </select>
              </div>
            </div>
            <button className="btn btn-primary" onClick={runEvaluation} disabled={evaluating} style={{ marginBottom: 16 }}>
              {evaluating ? <span className="spinner" /> : 'Рассчитать'}
            </button>
            {evalError && <div className="alert-error" style={{ marginBottom: 12 }}>{evalError}</div>}
            {evalResult && (
              <div>
                <div className="grid-2" style={{ marginBottom: 16 }}>
                  <div className="card stat-card"><div className="value">{formatSalary(evalResult.estimated_salary)}</div><div className="label">Оценочная зарплата</div></div>
                  <div className="card stat-card"><div className="value">{Math.round(evalResult.confidence * 100)}%</div><div className="label">Уверенность</div></div>
                </div>
                <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>
                  Дисциплин: {evalResult.matched_disciplines} / {evalResult.total_disciplines}
                </div>
                {evalResult.skill_matches.slice(0, 8).map((match, index) => (
                  <div key={`${match.discipline}-${match.skill_name}-${index}`} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                    <span>{match.discipline} → <strong>{match.skill_name}</strong></span>
                    <span style={{ color: 'var(--text-muted)' }}>{Math.round(match.similarity * 100)}% {match.avg_salary ? `· ${formatSalary(match.avg_salary)}` : ''}</span>
                  </div>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 16 }}>
              <button className="btn" onClick={() => setEvaluatingStudent(null)}>Закрыть</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function TagsTab() {
  const [tags, setTags] = useState<any>(null)
  const [sortField, setSortField] = useState<'name' | 'count' | 'percent'>('count')
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc')

  useEffect(() => { api.get('/tags').then(r => setTags(r.data)).catch(() => {}) }, [])
  if (!tags) return <div className="card"><div className="spinner" /></div>

  const totalVacancies = tags.total_vacancies || 0
  const sortedTags = useMemo(() => {
    const list = [...(tags.tags || [])]
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
