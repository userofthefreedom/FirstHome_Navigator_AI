import axios from 'axios'
import type {
  CoachSummary,
  Dashboard,
  Favorite,
  FinancialProduct,
  FundingPlan,
  HousingRecommendation,
  Notice,
  Policy,
  Profile,
} from '../types/firsthome'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api',
  timeout: 3000,
  withCredentials: true,
})

export async function saveProfileToApi(profile: Profile) {
  const response = await api.put<Profile>('/profile', profile)
  return response.data
}

export async function fetchProfile() {
  const response = await api.get<Profile>('/profile')
  return response.data
}

export async function fetchDashboard() {
  const response = await api.get<Dashboard>('/dashboard')
  return response.data
}

export async function fetchNotices() {
  const response = await api.get<Notice[]>('/notices')
  return response.data
}

export async function fetchNotice(noticeId: number) {
  const response = await api.get<Notice>(`/notices/${noticeId}`)
  return response.data
}

export async function fetchHousingRecommendations() {
  const response = await api.get<HousingRecommendation[]>('/recommendations/housing')
  return response.data
}

export async function fetchFundingPlan(noticeId: number) {
  const response = await api.get<FundingPlan>(`/recommendations/funding/${noticeId}`)
  return response.data
}

export async function fetchProducts() {
  const response = await api.get<FinancialProduct[]>('/recommendations/products')
  return response.data
}

export async function fetchPolicies() {
  const response = await api.get<Policy[]>('/recommendations/policies')
  return response.data
}

export async function fetchCoachSummary(noticeId: number, profile: Profile) {
  const response = await api.post<CoachSummary>('/ai/coach-summary', { notice_id: noticeId, profile })
  return response.data
}

export async function fetchFavorites() {
  const response = await api.get<Favorite[]>('/favorites')
  return response.data
}

export async function addFavorite(favorite: Favorite) {
  const response = await api.post<Favorite>('/favorites', favorite)
  return response.data
}

export async function removeFavorite(favorite: Favorite) {
  await api.delete('/favorites', { data: favorite })
}
