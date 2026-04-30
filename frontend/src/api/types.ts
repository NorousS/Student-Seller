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
  category: string | null
}

export interface DisciplineGroup {
  group_name: string
  disciplines: Discipline[]
  total_count: number
  avg_grade: number
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
  contact_info?: string | null
  about_company?: string | null
  website_url?: string | null
  partnership_status: 'partner' | 'non_partner'
}

export interface AdminEmployer {
  employer_user_id: number
  profile_id: number
  email: string
  company_name: string | null
  position: string | null
  partnership_status: 'partner' | 'non_partner'
  created_at: string
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
  discipline_groups: DisciplineGroup[]
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
  discipline_groups: DisciplineGroup[]
  about_me: string | null
  contact_status: string | null
  partnership_status: string | null
  work_ready_date: string | null
  competence_blocks: CompetenceBlock[]
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

export interface TopStudentCard {
  student_id: number
  photo_url: string | null
  estimated_salary: number | null
  competency_summary: string
}

export interface PaywallOption {
  id: string
  title: string
  description: string
  action_url: string
}

export interface CompetenceBlock {
  block_name: string
  avg_grade: number
  market_value: number | null
  strong_points: number
  top_tags: string[]
  achievements_summary: string
}

export interface FactorBreakdown {
  factor_name: string
  contribution: number
}

export interface EvaluationResponse {
  student_id: number
  student_name: string
  specialty: string
  experience_filter: string | null
  top_k: number
  excluded_skills: string[]
  estimated_salary: number | null
  confidence: number
  total_disciplines: number
  matched_disciplines: number
  skill_matches: SkillMatch[]
}

export interface InviteResponse {
  status: 'invite_created' | 'paywall_required'
  reason?: string
  message?: string
  contact_request?: any
}
