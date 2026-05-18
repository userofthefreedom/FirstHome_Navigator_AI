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
}

export type Notice = {
  id: number
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

export type HousingRecommendation = {
  notice_id: number
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
  score_detail: {
    eligibility: number
    funding: number
    location: number
    schedule: number
    policy_link: number
  }
  reasons: string[]
}

export type FundingPlan = {
  notice_id: number
  notice_title: string
  price: number
  down_payment: number
  available_cash: number
  shortfall: number
  months_until_contract: number
  monthly_target: number
  timeline: Array<{ label: string; date: string; amount: number }>
}

export type FinancialProduct = {
  id: number
  name: string
  provider: string
  category: string
  rate: string
  limit: string
  period: string
  source_url: string
  reasons: string[]
}

export type Policy = {
  id: number
  name: string
  provider: string
  target: string
  benefit: string
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

export type Dashboard = {
  profile: Profile
  top_recommendations: HousingRecommendation[]
  notice_count: number
  message: string
}
