import axios from 'axios';
const api = axios.create({
    baseURL: (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api').replace(/\/$/, ''),
    timeout: 10000,
    withCredentials: true,
});
function firstHomeClientId() {
    const storageKey = 'firsthome_client_id';
    const existingId = window.localStorage.getItem(storageKey);
    if (existingId)
        return existingId;
    const nextId = window.crypto?.randomUUID?.() ?? `firsthome-${Date.now()}-${Math.random().toString(16).slice(2)}`;
    window.localStorage.setItem(storageKey, nextId);
    return nextId;
}
function favoriteHeaders() {
    return { 'X-FirstHome-Client-Id': firstHomeClientId() };
}
export async function fetchAuthSession() {
    const response = await api.get('/auth/me');
    return response.data;
}
export async function registerToApi(credentials) {
    const response = await api.post('/auth/register', credentials, { headers: favoriteHeaders() });
    return response.data;
}
export async function loginToApi(credentials) {
    const response = await api.post('/auth/login', credentials, { headers: favoriteHeaders() });
    return response.data;
}
export async function logoutFromApi() {
    const response = await api.post('/auth/logout');
    return response.data;
}
export async function saveProfileToApi(profile) {
    const response = await api.put('/profile', profile);
    return response.data;
}
export async function fetchProfile() {
    const response = await api.get('/profile');
    return response.data;
}
export async function fetchDashboard() {
    const response = await api.get('/dashboard');
    return response.data;
}
export async function fetchNotices(params) {
    const response = await api.get('/notices', { params });
    return response.data;
}
export async function fetchNotice(noticeId) {
    const response = await api.get(`/notices/${noticeId}`);
    return response.data;
}
export async function fetchNoticeDocumentStatus(noticeId) {
    const response = await api.get(`/notices/${noticeId}/documents/status`);
    return response.data;
}
export async function analyzeNoticeDocument(noticeId) {
    const response = await api.post(`/notices/${noticeId}/documents/analyze`, undefined, { timeout: 90000 });
    return response.data;
}
export async function fetchNoticeUnitOptions(noticeId) {
    const response = await api.get(`/notices/${noticeId}/unit-options`);
    return response.data;
}
export async function fetchNoticeEligibilityChecklists(noticeId) {
    const response = await api.get(`/notices/${noticeId}/eligibility-checklists`);
    return response.data;
}
export async function fetchHousingRecommendations() {
    const response = await api.get('/recommendations/housing');
    return response.data;
}
export async function fetchFundingPlan(noticeId, optionId) {
    const response = await api.get(`/recommendations/funding/${noticeId}`, {
        params: optionId ? { option_id: optionId } : undefined,
    });
    return response.data;
}
export async function fetchProducts() {
    const response = await api.get('/recommendations/products');
    return response.data;
}
export async function fetchPolicies() {
    const response = await api.get('/recommendations/policies');
    return response.data;
}
export async function fetchCoachSummary(noticeId, profile) {
    const response = await api.post('/ai/coach-summary', { notice_id: noticeId, profile });
    return response.data;
}
export async function askCoachChat(noticeId, message, profile, optionId) {
    const response = await api.post('/ai/chat', { notice_id: noticeId, option_id: optionId, message, profile });
    return response.data;
}
export async function fetchFavorites() {
    const response = await api.get('/favorites', { headers: favoriteHeaders() });
    return response.data;
}
export async function addFavorite(favorite) {
    const response = await api.post('/favorites', favorite, { headers: favoriteHeaders() });
    return response.data;
}
export async function removeFavorite(favorite) {
    await api.delete('/favorites', { data: favorite, headers: favoriteHeaders() });
}
