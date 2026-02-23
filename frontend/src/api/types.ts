/** Общие типы для фронтенда */

export type UserRole = 'admin' | 'student' | 'employer'

export interface User {
  id: number
  email: string
  role: UserRole
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Discipline {
  id: number
  name: string
  grade: number
}

export interface Student {
  id: number
  full_name: string
  group_name: string | null
  disciplines: Discipline[]
}

export interface StudentProfile extends Student {
  about_me: string | null
  photo_url: string | null
}

export interface EmployerProfile {
  id: number
  user_id: number
  company_name: string | null
  position: string | null
}

export interface SkillMatch {
  discipline: string
  skill_name: string
  similarity: number
  avg_salary: number | null
  vacancy_count: number
  grade: number
  grade_coeff: number
  excluded: boolean
}

export interface AnonymizedStudent {
  student_id: number
  photo_url: string | null
  disciplines: Discipline[]
  estimated_salary: number | null
  confidence: number
  matched_disciplines: number
  total_disciplines: number
  skill_matches: SkillMatch[]
}

export interface AnonymizedStudentProfile {
  student_id: number
  photo_url: string | null
  disciplines: Discipline[]
  about_me: string | null
  contact_status: string | null
}

export interface ContactRequest {
  id: number
  employer_id: number
  student_id: number
  status: string
  created_at: string
  responded_at: string | null
  employer_company?: string | null
}

export interface ChatMessage {
  id: number
  sender_id: number
  text: string
  created_at: string
  is_read: boolean
}
