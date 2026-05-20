import axios from 'axios'
import type {
  AuthCredentials,
  AuthSession,
  CoachChatResponse,
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
  baseURL: (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api').replace(/\/$/, ''),
  timeout: 10000,
  withCredentials: true,
})

function firstHomeClientId() {
  const storageKey = 'firsthome_client_id'
  const existingId = window.localStorage.getItem(storageKey)
  if (existingId) return existingId

  const nextId = window.crypto?.randomUUID?.() ?? `firsthome-${Date.now()}-${Math.random().toString(16).slice(2)}`
  window.localStorage.setItem(storageKey, nextId)
  return nextId
}

function favoriteHeaders() {
  return { 'X-FirstHome-Client-Id': firstHomeClientId() }
}

export async function fetchAuthSession() {
  const response = await api.get<AuthSession>('/auth/me')
  return response.data
}

export async function registerToApi(credentials: AuthCredentials) {
  const response = await api.post<AuthSession>('/auth/register', credentials, { headers: favoriteHeaders() })
  return response.data
}

export async function loginToApi(credentials: AuthCredentials) {
  const response = await api.post<AuthSession>('/auth/login', credentials, { headers: favoriteHeaders() })
  return response.data
}

export async function logoutFromApi() {
  const response = await api.post<AuthSession>('/auth/logout')
  return response.data
}

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

export async function askCoachChat(noticeId: number, message: string, profile: Profile) {
  const response = await api.post<CoachChatResponse>('/ai/chat', { notice_id: noticeId, message, profile })
  return response.data
}

export async function fetchFavorites() {
  const response = await api.get<Favorite[]>('/favorites', { headers: favoriteHeaders() })
  return response.data
}

export async function addFavorite(favorite: Favorite) {
  const response = await api.post<Favorite>('/favorites', favorite, { headers: favoriteHeaders() })
  return response.data
}

export async function removeFavorite(favorite: Favorite) {
  await api.delete('/favorites', { data: favorite, headers: favoriteHeaders() })
}
