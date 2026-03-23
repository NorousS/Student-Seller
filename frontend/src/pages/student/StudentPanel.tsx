import { useState, useEffect, useRef, useMemo } from 'react'
import api from '../../api/client'
import { useAuth } from '../../store/AuthContext'
import type { StudentProfile, ContactRequest, ChatMessage } from '../../api/types'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  RadialLinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js'
import { Bar, Radar } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  RadialLinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
)

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
  experience_filter?: string | null
  estimated_salary: number | null
  confidence: number
  total_disciplines: number
  matched_disciplines: number
  skill_matches: SkillMatch[]
  formula_used?: string
}

interface StudentDiscipline {
  id: number
  name: string
  grade: number
}

type SortField = 'similarity' | 'avg_salary' | 'vacancy_count'
type SortDirection = 'asc' | 'desc'

function EvaluationTab() {
  const [specialty, setSpecialty] = useState('')
  const [experience, setExperience] = useState('Любой')
  const [topK, setTopK] = useState(5)
  const [formula, setFormula] = useState('baseline')
  const [availableFormulas, setAvailableFormulas] = useState<{name: string, description: string}[]>([])
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<EvaluationResult | null>(null)
  const [studentDisciplines, setStudentDisciplines] = useState<StudentDiscipline[]>([])
  const [excludedSkills, setExcludedSkills] = useState<Set<string>>(new Set())

  const [similarityThreshold, setSimilarityThreshold] = useState(0)
  const [minSimilarity, setMinSimilarity] = useState(0)
  const [minSalary, setMinSalary] = useState(0)
  const [minVacancyCount, setMinVacancyCount] = useState(0)
  const [sortField, setSortField] = useState<SortField>('similarity')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  const experienceMap: Record<string, string | null> = {
    'Любой': null,
    'Без опыта': 'noExperience',
    '1-3 года': 'between1And3',
    '3-6 лет': 'between3And6',
    '6+ лет': 'moreThan6'
  }

  const experienceLabelMap: Record<string, string> = {
    noExperience: 'Без опыта',
    between1And3: '1-3 года',
    between3And6: '3-6 лет',
    moreThan6: '6+ лет'
  }

  useEffect(() => {
    api.get('/profile/student/disciplines')
      .then(r => setStudentDisciplines(r.data || []))
      .catch(() => setStudentDisciplines([]))
    
    api.get('/profile/student/formulas')
      .then(r => setAvailableFormulas(r.data || []))
      .catch(() => setAvailableFormulas([]))
  }, [])

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
      params.set('formula', formula)
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

  const filteredAndSortedSkills = useMemo(() => {
    if (!result) return []

    let skills = result.skill_matches.filter(sm => {
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
  }, [result, minSimilarity, minSalary, minVacancyCount, sortField, sortDirection])

  const impactChartData = useMemo(() => {
    if (filteredAndSortedSkills.length === 0) return null

    const impactMap: Record<string, number> = {}
    filteredAndSortedSkills.forEach(sm => {
      if (sm.avg_salary) {
        const impact = sm.similarity * sm.avg_salary
        impactMap[sm.skill_name] = (impactMap[sm.skill_name] || 0) + impact
      }
    })

    const topImpact = Object.entries(impactMap)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 12)

    if (topImpact.length === 0) return null

    const colors = [
      '#58a6ff', '#bc8cff', '#3fb950', '#d29922', '#f85149',
      '#79c0ff', '#d2a8ff', '#56d364', '#e3b341', '#ff7b72',
      '#a5d6ff', '#e8d4ff'
    ]

    return {
      labels: topImpact.map(([name]) => name),
      datasets: [{
        label: 'Влияние на ЗП',
        data: topImpact.map(([, value]) => Math.round(value)),
        backgroundColor: colors.slice(0, topImpact.length),
        borderRadius: 6,
        borderSkipped: false,
      }]
    }
  }, [filteredAndSortedSkills])

  const impactChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    indexAxis: 'y' as const,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx: any) => `${Number(ctx.raw).toLocaleString('ru-RU')} ₽`
        },
      }
    },
    scales: {
      x: {
        beginAtZero: true,
        ticks: { callback: (value: any) => `${Math.round(Number(value) / 1000)}k` },
        grid: { color: '#21262d' }
      },
      y: { grid: { display: false } }
    }
  }

  const similarityRadarData = useMemo(() => {
    if (filteredAndSortedSkills.length === 0) return null

    const groups: Record<string, number[]> = {}
    filteredAndSortedSkills.forEach(sm => {
      if (!groups[sm.discipline]) groups[sm.discipline] = []
      groups[sm.discipline].push(sm.similarity)
    })

    const labels = Object.keys(groups)
    if (labels.length === 0) return null

    const data = labels.map(label => Math.max(...groups[label]))

    return {
      labels,
      datasets: [{
        label: 'Макс. сходство',
        data,
        backgroundColor: 'rgba(88,166,255,0.15)',
        borderColor: '#58a6ff',
        pointBackgroundColor: '#58a6ff',
        pointBorderColor: '#0d1117',
        pointBorderWidth: 2,
        borderWidth: 2,
      }]
    }
  }, [filteredAndSortedSkills])

  const similarityRadarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    scales: {
      r: {
        beginAtZero: true,
        max: 1,
        grid: { color: '#21262d' },
        angleLines: { color: '#21262d' },
        ticks: { backdropColor: 'transparent' }
      }
    },
    plugins: {
      legend: { display: false }
    },
  }

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle direction
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

  const getGradeClass = (grade: number | null) => {
    if (grade === 5) return 'g5'
    if (grade === 4) return 'g4'
    return 'g3'
  }

  const salaryText = result?.estimated_salary
    ? formatSalary(result.estimated_salary)
    : 'Н/Д'

  const selectedExperience = result?.experience_filter
    ? experienceLabelMap[result.experience_filter] || result.experience_filter
    : 'Любой'

  return (
    <>
      <div className="card">
        <h2 style={{ marginBottom: 16, fontSize: 28 }}>Выберите параметры оценки</h2>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, alignItems: 'flex-end' }}>
          <div className="form-group" style={{ flex: '1 1 210px', marginBottom: 0 }}>
            <label style={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>Специальность</label>
            <input
              type="text"
              value={specialty}
              onChange={e => setSpecialty(e.target.value)}
              placeholder="Например: Python developer"
            />
          </div>
          <div className="form-group" style={{ flex: '1 1 170px', marginBottom: 0 }}>
            <label style={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>Опыт работы</label>
            <select value={experience} onChange={e => setExperience(e.target.value)}>
              <option value="Любой">Любой</option>
              <option value="Без опыта">Без опыта</option>
              <option value="1-3 года">1-3 года</option>
              <option value="3-6 лет">3-6 лет</option>
              <option value="6+ лет">6+ лет</option>
            </select>
          </div>
          <div className="form-group" style={{ flex: '1 1 240px', marginBottom: 0 }}>
            <label style={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>Навыков на дисциплину: {topK}</label>
            <input
              type="range"
              min="1"
              max="20"
              value={topK}
              onChange={e => setTopK(+e.target.value)}
              style={{ width: '100%' }}
            />
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'var(--text-muted)' }}>
              <span>1</span>
              <span>20</span>
            </div>
          </div>
          <div className="form-group" style={{ flex: '1 1 190px', marginBottom: 0 }}>
            <label style={{ textTransform: 'uppercase', letterSpacing: 0.5 }}>Формула расчёта</label>
            <select value={formula} onChange={e => setFormula(e.target.value)} title={availableFormulas.find(f => f.name === formula)?.description || ''}>
              {availableFormulas.length > 0 ? availableFormulas.map(f => (
                <option key={f.name} value={f.name}>{f.name}</option>
              )) : (
                <>
                  <option value="baseline">baseline</option>
                  <option value="linear">linear</option>
                  <option value="quadratic">quadratic</option>
                  <option value="exponential">exponential</option>
                  <option value="tfidf">tfidf</option>
                  <option value="matrix">matrix</option>
                </>
              )}
            </select>
          </div>
          <button
            className="btn btn-primary"
            onClick={evaluate}
            disabled={loading || !specialty.trim()}
            style={{
              whiteSpace: 'nowrap',
              background: 'linear-gradient(135deg, #238636 0%, #2ea043 100%)',
              color: '#fff',
              border: 'none',
            }}
          >
            {loading ? 'Оценка...' : 'Оценить стоимость'}
          </button>
        </div>

        {studentDisciplines.length > 0 && (
          <div style={{ marginTop: 14 }}>
            <h3 style={{ marginBottom: 8 }}>Дисциплины студента:</h3>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              {studentDisciplines.map(d => (
                <span key={d.id} className="tag-badge">
                  {d.name}
                  <span className={`grade-badge ${getGradeClass(d.grade)}`}>{d.grade}</span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {loading && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div className="spinner" />
          <p style={{ marginTop: 16, color: 'var(--text-muted)' }}>Анализируем навыки...</p>
        </div>
      )}

      {result && !loading && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 16, marginBottom: 16 }}>
            <div className="card stat-card" style={{ marginBottom: 0 }}>
              <div className="value salary-value">{salaryText}</div>
              <div className="label">Оценочная зарплата</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                📌 {result.specialty} · {selectedExperience}
                {result.formula_used && <span> · <span style={{ color: '#58a6ff' }}>{result.formula_used}</span></span>}
              </div>
            </div>
            <div className="card stat-card" style={{ marginBottom: 0 }}>
              <div className={`value ${getConfidenceColor(result.confidence * 100) === 'badge-green' ? 'confidence-value' : ''}`}>
                {(result.confidence * 100).toFixed(1)}%
              </div>
              <div className="label">Уверенность оценки</div>
            </div>
            <div className="card stat-card" style={{ marginBottom: 0 }}>
              <div className="value">{result.total_disciplines}</div>
              <div className="label">Всего дисциплин</div>
            </div>
            <div className="card stat-card" style={{ marginBottom: 0 }}>
              <div className="value match-value">{result.matched_disciplines}</div>
              <div className="label">Совпало дисциплин</div>
            </div>
          </div>

          <div className="grid-2">
            <div className="card">
              <h2 style={{ marginBottom: 12 }}>Влияние навыков на стоимость</h2>
              <div className="chart-container">
                {impactChartData ? (
                  <Bar data={impactChartData} options={impactChartOptions} />
                ) : (
                  <p style={{ color: 'var(--text-muted)' }}>Недостаточно данных для графика</p>
                )}
              </div>
            </div>
            <div className="card">
              <h2 style={{ marginBottom: 12 }}>Сходство дисциплин с навыками</h2>
              <div className="chart-container">
                {similarityRadarData ? (
                  <Radar data={similarityRadarData} options={similarityRadarOptions} />
                ) : (
                  <p style={{ color: 'var(--text-muted)' }}>Недостаточно данных для графика</p>
                )}
              </div>
            </div>
          </div>

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

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 16 }}>
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
                  onChange={e => setMinSalary(Number(e.target.value) || 0)}
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
                  onChange={e => setMinVacancyCount(Number(e.target.value) || 0)}
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
                Сбросить фильтры
              </button>
              <span style={{ color: 'var(--text-muted)', alignSelf: 'center' }}>
                Показано: {filteredAndSortedSkills.length} / {result.skill_matches.length}
              </span>
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h2 style={{ margin: 0 }}>Детальная разбивка</h2>
              <button
                className="btn btn-primary"
                onClick={evaluate}
                disabled={loading}
                style={{
                  fontSize: 13,
                  background: 'linear-gradient(135deg, #238636 0%, #2ea043 100%)',
                  color: '#fff',
                  border: 'none',
                }}
              >
                🔄 Пересчитать
              </button>
            </div>

            {filteredAndSortedSkills.length === 0 ? (
              <p style={{ color: 'var(--text-muted)' }}>
                {result.skill_matches.length === 0 
                  ? 'Навыки не найдены' 
                  : 'Нет навыков, соответствующих фильтрам'}
              </p>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="tags-table">
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
                      <th>Исключить</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredAndSortedSkills.map((sm, idx) => {
                      const isExcluded = excludedSkills.has(`${sm.discipline}:${sm.skill_name}`)
                      const isLowVacancy = sm.vacancy_count < 3
                      const isBelowThreshold = sm.similarity < similarityThreshold
                      const shouldStrikethrough = isExcluded || isBelowThreshold

                      return (
                        <tr
                          key={idx}
                          className={isLowVacancy && !isExcluded ? 'filtered-tag' : undefined}
                          style={{
                            textDecoration: shouldStrikethrough ? 'line-through' : 'none',
                            backgroundColor: isExcluded
                              ? 'rgba(239, 68, 68, 0.1)'
                              : isBelowThreshold
                                ? 'rgba(156, 163, 175, 0.1)'
                                : 'transparent',
                            opacity: isBelowThreshold ? 0.6 : 1,
                            transition: 'all 0.2s ease',
                          }}
                        >
                          <td>
                            <span className="tag-badge">
                              {sm.discipline}
                            </span>
                            {isLowVacancy && <span className="warning-note"> (&lt; 3 вакансий)</span>}
                          </td>
                          <td>{sm.skill_name}</td>
                          <td>
                            <div className="tag-bar-bg">
                              <div className="tag-bar" style={{ width: `${Math.min(sm.similarity * 100, 100)}%` }} />
                            </div>
                            <span style={{
                              color: isBelowThreshold ? 'var(--text-muted)' : 'inherit',
                              fontWeight: isBelowThreshold ? 'normal' : 500
                            }}>
                              {(sm.similarity * 100).toFixed(1)}%
                              {isLowVacancy && <span className="warning-note"> (&lt; 3 вакансий)</span>}
                            </span>
                          </td>
                          <td>
                            {!isLowVacancy && sm.avg_salary ? formatSalary(sm.avg_salary) : (
                              <>
                                — <span className="warning-note">(&lt; 3 вакансий)</span>
                              </>
                            )}
                          </td>
                          <td>
                            {sm.vacancy_count}
                            {isLowVacancy && <span className="warning-note"> ⚠️ (&lt; 3 вакансий)</span>}
                          </td>
                          <td>
                            {sm.grade !== null && sm.grade !== undefined ? (
                              <>
                                <span className={`grade-badge ${getGradeClass(sm.grade)}`}>{sm.grade}</span>
                                <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                                  {' '}×{sm.grade_coeff ?? 1}
                                </span>
                                {isLowVacancy && <span className="warning-note"> (&lt; 3 вакансий)</span>}
                              </>
                            ) : '—'}
                          </td>
                          <td style={{ textAlign: 'center' }}>
                            <input
                              type="checkbox"
                              checked={isExcluded}
                              onChange={() => toggleExcluded(sm.discipline, sm.skill_name)}
                              style={{ cursor: 'pointer', width: 18, height: 18 }}
                            />
                            {isLowVacancy && <div className="warning-note">&lt; 3 вакансий</div>}
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
