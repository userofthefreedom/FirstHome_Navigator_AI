export type Profile = {
  name: string
  birth_year: number
  job_status: string
  annual_income: number
  asset: number
  debt: number
  monthly_saving: number
  is_homeless: boolean
  subscription_months: number
  special_conditions: string[]
  preferred_regions: string[]
  preferred_supply_types: string[]
  target_months: number
  desired_area_min_m2: number
  desired_area_max_m2: number
  desired_price_min: number
  desired_price_max: number
  max_down_payment: number
  monthly_payment_capacity: number
}

export type AuthUser = {
  is_authenticated: boolean
  id?: number
  username?: string
  email?: string
}

export type AuthSession = {
  user: AuthUser
  profile?: Profile
}

export type AuthCredentials = {
  username: string
  password: string
  email?: string
}

export type Notice = {
  id: number
  source_id?: string
  data_source?: string
  is_price_confirmed?: boolean
  source_meta?: Record<string, any>
  ownership_type?: string
  is_service_target?: boolean
  exclude_reason?: string
  official_document_status?: string
  analysis_summary?: AnalysisSummary
  document_count?: number
  unit_option_count?: number
  title: string
  provider: string
  region: string
  district: string
  supply_type: string
  housing_type: string
  area: string
  price: number
  contract_rate: number
  application_deadline: string
  winner_date: string
  contract_date: string
  move_in: string
  competition: string
  source_url: string
  tags: string[]
  required_documents: string[]
  cautions: string[]
}

export type AnalysisSummary = {
  stage: string
  label: string
  tone: 'success' | 'warning' | 'danger' | 'info' | 'muted' | string
  next_action: string
  is_mock: boolean
  source: string
  schema_version: string
  extraction_status: string
  document_status: string
  document_count: number
  unit_option_count: number
  latest_error: string
}

export type Favorite = {
  favorite_type: 'notice' | 'option' | 'product' | 'policy'
  object_id: number
  item?: Record<string, any> | null
}

export type HousingRecommendation = {
  notice_id: number
  source_id?: string
  data_source?: string
  is_price_confirmed?: boolean
  source_meta?: Record<string, any>
  ownership_type?: string
  is_service_target?: boolean
  exclude_reason?: string
  official_document_status?: string
  analysis_summary?: AnalysisSummary
  document_count?: number
  unit_option_count?: number
  title: string
  provider: string
  region: string
  district: string
  supply_type: string
  housing_type: string
  area: string
  price: number
  application_deadline: string
  winner_date: string
  contract_date: string
  move_in: string
  competition: string
  source_url: string
  total_score: number
  option_fit_score?: number
  best_option?: BestUnitOption | null
  top_options?: BestUnitOption[]
  score_detail: {
    eligibility: number
    funding: number
    location: number
    schedule: number
    policy_link: number
  }
  reasons: string[]
}

export type BestUnitOption = {
  option_id: number
  unit_type: string
  exclusive_area_m2: number
  floor_group: string
  option_type: string
  base_price: number
  loan_amount: number
  balcony_extension_price: number
  confidence: number
  source_page?: number | null
  down_payment: number
  middle_payment: number
  final_payment: number
  option_fit_score: number
  fit_reasons?: string[]
}

export type FundingPlan = {
  notice_id: number
  notice_title: string
  option_id?: number | null
  unit_type?: string
  exclusive_area_m2?: number
  floor_group?: string
  option_type?: string
  schedule_source?: string
  price: number
  down_payment: number
  middle_payment?: number
  final_payment?: number
  available_cash: number
  shortfall: number
  months_until_contract: number
  monthly_target: number
  timeline: Array<{ label: string; date: string; amount: number; payment_type?: string; evidence_text?: string }>
  notice: string
}

export type NoticeDocument = {
  id: number
  notice_id: number
  provider: string
  file_id: string
  file_name: string
  document_url: string
  source_url: string
  status: string
  error_message: string
  fetched_at: string
  analyzed_at: string
}

export type NoticeExtraction = {
  id: number
  notice_id: number
  document_id: number
  schema_version: string
  status: string
  confidence: number
  source: string
  option_count: number
  warnings: Record<string, string[]>
  evidence: ExtractionEvidence[]
  created_at: string
}

export type ExtractionEvidence = {
  id: number
  field_path: string
  page_no?: number | null
  source_text: string
  confidence: number
}

export type PaymentSchedule = {
  id: number
  label: string
  due_date: string
  amount: number
  payment_type: string
  sequence: number
  evidence_text: string
}

export type HousingUnitOption = {
  id: number
  notice_id: number
  document_id?: number | null
  extraction_id?: number | null
  extraction_schema_version?: string
  extraction_status?: string
  extraction_source?: string
  unit_type: string
  exclusive_area_m2: number
  floor_group: string
  option_type: string
  base_price: number
  loan_amount: number
  balcony_extension_price: number
  confidence: number
  source_page?: number | null
  source_text: string
  payment_schedules: PaymentSchedule[]
}

export type NoticeEligibilityChecklist = {
  id: number
  notice_id: number
  document_id?: number | null
  category: string
  title: string
  condition_text: string
  evidence_text: string
  confidence: number
}

export type NoticeDocumentStatus = {
  notice_id: number
  official_document_status: string
  analysis_summary: AnalysisSummary
  document_count: number
  unit_option_count: number
  analyzed_option_count: number
  documents: NoticeDocument[]
  latest_extraction?: NoticeExtraction | null
}

export type NoticeAnalyzeResponse = {
  notice_id: number
  official_document_status: string
  document: NoticeDocument
  extraction?: NoticeExtraction | null
  unit_options: HousingUnitOption[]
  message: string
}

export type FinancialProduct = {
  id: number
  data_source?: string
  name: string
  provider: string
  category: string
  rate: string
  limit: string
  period: string
  term_months?: number
  monthly_limit?: number
  protection_status?: boolean
  match_score?: number
  source_url: string
  reasons: string[]
}

export type Policy = {
  id: number
  data_source?: string
  name: string
  provider: string
  target: string
  benefit: string
  policy_category?: string
  regions?: string[]
  match_score?: number
  source_url: string
  reasons: string[]
}

export type CoachSummary = {
  source: string
  summary: string
  todo_this_week: string[]
  official_checklist: string[]
  warning: string
}

export type CoachChatResponse = {
  source: string
  notice_id: number
  notice_title: string
  option_id?: number | null
  reply: string
  suggested_actions: string[]
  context_refs?: Array<Record<string, any>>
}

export type Dashboard = {
  profile: Profile
  top_recommendations: HousingRecommendation[]
  notice_count: number
  message: string
}
