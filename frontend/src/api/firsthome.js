import axios from 'axios';
function normalizeApiBaseUrl(value) {
    const fallback = '/api';
    const raw = (value || fallback).replace(/\/$/, '');
    return raw.endsWith('/api') ? raw : `${raw}/api`;
}
const api = axios.create({
    baseURL: normalizeApiBaseUrl(import.meta.env.VITE_API_BASE_URL),
    timeout: 10000,
    withCredentials: true,
    headers: {
        'ngrok-skip-browser-warning': 'true',
    },
});
const GET_CACHE_TTL_MS = 60 * 1000;
const getCache = new Map();
const pendingGetRequests = new Map();

function stableParams(params) {
    if (!params)
        return '';
    return JSON.stringify(
        Object.entries(params)
            .filter(([, value]) => value !== undefined && value !== null && value !== '')
            .sort(([left], [right]) => left.localeCompare(right)),
    );
}

function getCacheKey(url, config = {}) {
    return `${url}?${stableParams(config.params)}`;
}

async function cachedGet(url, config = {}, options = {}) {
    const ttl = options.ttl ?? GET_CACHE_TTL_MS;
    const key = getCacheKey(url, config);
    const now = Date.now();
    const cached = getCache.get(key);
    if (cached && cached.expiresAt > now)
        return cached.data;
    if (pendingGetRequests.has(key))
        return pendingGetRequests.get(key);
    const request = api
        .get(url, config)
        .then((response) => {
            getCache.set(key, { data: response.data, expiresAt: Date.now() + ttl });
            pendingGetRequests.delete(key);
            return response.data;
        })
        .catch((error) => {
            pendingGetRequests.delete(key);
            throw error;
        });
    pendingGetRequests.set(key, request);
    return request;
}

export function clearFirstHomeApiCache() {
    getCache.clear();
    pendingGetRequests.clear();
}

function invalidateFirstHomeApiCache() {
    clearFirstHomeApiCache();
}

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
    return cachedGet('/auth/me');
}
export async function registerToApi(credentials) {
    const response = await api.post('/auth/register', credentials, { headers: favoriteHeaders() });
    invalidateFirstHomeApiCache();
    return response.data;
}
export async function loginToApi(credentials) {
    const response = await api.post('/auth/login', credentials, { headers: favoriteHeaders() });
    invalidateFirstHomeApiCache();
    return response.data;
}
export async function logoutFromApi() {
    const response = await api.post('/auth/logout');
    invalidateFirstHomeApiCache();
    return response.data;
}
export async function saveProfileToApi(profile) {
    const response = await api.put('/profile', profile);
    invalidateFirstHomeApiCache();
    return response.data;
}
export async function fetchProfile() {
    return cachedGet('/profile');
}
export async function fetchAccountState() {
    return cachedGet('/account-state');
}
export async function saveAccountStateToApi(accountState) {
    const response = await api.put('/account-state', accountState);
    invalidateFirstHomeApiCache();
    return response.data;
}
export async function fetchDashboard() {
    return cachedGet('/dashboard');
}
export async function fetchNotices(params) {
    return cachedGet('/notices', { params });
}
export async function fetchMapNotices(params) {
    return cachedGet('/notices/map', { params });
}
export async function fetchNotice(noticeId) {
    return cachedGet(`/notices/${noticeId}`);
}
export async function fetchNoticeDocumentStatus(noticeId) {
    return cachedGet(`/notices/${noticeId}/documents/status`);
}
export async function analyzeNoticeDocument(noticeId) {
    const response = await api.post(`/notices/${noticeId}/documents/analyze`, undefined, { timeout: 90000 });
    invalidateFirstHomeApiCache();
    return response.data;
}
export async function fetchNoticeUnitOptions(noticeId) {
    return cachedGet(`/notices/${noticeId}/unit-options`);
}
export async function fetchNoticeEligibilityChecklists(noticeId) {
    return cachedGet(`/notices/${noticeId}/eligibility-checklists`);
}
export async function fetchHousingRecommendations() {
    return cachedGet('/recommendations/housing');
}
export async function fetchFundingPlan(noticeId, optionId) {
    return cachedGet(`/recommendations/funding/${noticeId}`, {
        params: optionId ? { option_id: optionId } : undefined,
    });
}
export async function fetchProducts() {
    return cachedGet('/recommendations/products');
}
export async function fetchFinancialProducts(params) {
    return cachedGet('/products', { params });
}
export async function fetchFinancialProduct(productId) {
    return cachedGet(`/products/${productId}`);
}
export async function joinFinancialProduct(productId, optionId, memo = '') {
    const response = await api.post(`/products/${productId}/join`, { option_id: optionId, memo });
    invalidateFirstHomeApiCache();
    return response.data;
}
export async function fetchJoinedProducts() {
    return cachedGet('/products/joined');
}
export async function fetchMarketAssets(params) {
    return cachedGet('/market/assets', { params });
}
export async function fetchMarketSummary() {
    return cachedGet('/market/summary');
}
export async function fetchDefaultVideos() {
    return cachedGet('/videos/default');
}
export async function searchVideos(query) {
    return cachedGet('/videos/search', { params: { q: query } });
}
export async function fetchAgoraPosts(params) {
    return cachedGet('/agora/posts', { params });
}
export async function createAgoraPost(payload) {
    const response = await api.post('/agora/posts', payload);
    invalidateFirstHomeApiCache();
    return response.data;
}
export async function updateAgoraPost(postId, payload) {
    const response = await api.put(`/agora/posts/${postId}`, payload);
    invalidateFirstHomeApiCache();
    return response.data;
}
export async function deleteAgoraPost(postId) {
    await api.delete(`/agora/posts/${postId}`);
    invalidateFirstHomeApiCache();
}
export async function createAgoraComment(postId, payload) {
    const response = await api.post(`/agora/posts/${postId}/comments`, payload);
    invalidateFirstHomeApiCache();
    return response.data;
}
export async function updateAgoraComment(commentId, payload) {
    const response = await api.put(`/agora/comments/${commentId}`, payload);
    invalidateFirstHomeApiCache();
    return response.data;
}
export async function deleteAgoraComment(commentId) {
    await api.delete(`/agora/comments/${commentId}`);
    invalidateFirstHomeApiCache();
}
export async function searchPlaces(params) {
    return cachedGet('/places/search', { params });
}
export async function fetchPlaceRoute(params) {
    return cachedGet('/places/route', { params });
}
export async function fetchLoanProducts() {
    return cachedGet('/recommendations/loans');
}
export async function fetchPolicies() {
    return cachedGet('/recommendations/policies');
}
export async function fetchCoachSummary(noticeId, profile, optionId) {
    const response = await api.post('/ai/coach-summary', { notice_id: noticeId, option_id: optionId, profile }, { timeout: 90000 });
    return response.data;
}
export async function askCoachChat(noticeId, message, profile, optionId, pageContext = {}) {
    const response = await api.post('/ai/chat', { notice_id: noticeId, option_id: optionId, message, profile, page_context: pageContext });
    return response.data;
}
export async function fetchFavorites() {
    return cachedGet('/favorites', { headers: favoriteHeaders() });
}
export async function addFavorite(favorite) {
    const response = await api.post('/favorites', favorite, { headers: favoriteHeaders() });
    invalidateFirstHomeApiCache();
    return response.data;
}
export async function removeFavorite(favorite) {
    await api.delete('/favorites', { data: favorite, headers: favoriteHeaders() });
    invalidateFirstHomeApiCache();
}
