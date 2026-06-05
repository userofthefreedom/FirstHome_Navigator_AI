<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import {
    Building2,
    ChevronRight,
    Crosshair,
    ExternalLink,
    LocateFixed,
    MapPin,
    RotateCcw,
    Search,
    SlidersHorizontal,
    WalletCards,
} from 'lucide-vue-next';
import { fetchMapNotices } from '../api/firsthome';
import { analysisBadgeClass, analysisSummary } from '../utils/analysisStatus';
import { formatMoney } from '../utils/format';
import { saveCurrentSelection } from '../utils/selectionState';

const KAKAO_JS_KEY = import.meta.env.VITE_KAKAO_MAP_JS_KEY ?? '';
const KAKAO_SCRIPT_ID = 'firsthome-kakao-map-sdk';
const DEFAULT_CENTER = { lat: 36.35, lng: 127.85 };
const DEFAULT_LEVEL = 11;
const REGION_LEVEL = 8;
const NOTICE_LEVEL = 4;
const PAGE_SIZE = 8;
const SOUTH_KOREA_BOUNDS = {
    sw: { lat: 32.9, lng: 124.6 },
    ne: { lat: 38.25, lng: 131.0 },
};
const REGION_CENTERS = {
    서울: { lat: 37.566826, lng: 126.978656 },
    부산: { lat: 35.179554, lng: 129.075642 },
    대구: { lat: 35.871435, lng: 128.601445 },
    인천: { lat: 37.456256, lng: 126.705206 },
    광주: { lat: 35.159545, lng: 126.852601 },
    대전: { lat: 36.350412, lng: 127.384548 },
    울산: { lat: 35.538377, lng: 129.31136 },
    울산광역시: { lat: 35.538377, lng: 129.31136 },
    세종: { lat: 36.480132, lng: 127.289021 },
    경기: { lat: 37.4138, lng: 127.5183 },
    '경기 남부': { lat: 37.263573, lng: 127.028601 },
    '경기 북부': { lat: 37.738098, lng: 127.033682 },
    강원: { lat: 37.885621, lng: 127.72997 },
    강원도: { lat: 37.885621, lng: 127.72997 },
    충북: { lat: 36.63568, lng: 127.491384 },
    충청북도: { lat: 36.63568, lng: 127.491384 },
    충남: { lat: 36.658829, lng: 126.672849 },
    충청남도: { lat: 36.658829, lng: 126.672849 },
    전북: { lat: 35.824224, lng: 127.147953 },
    전라북도: { lat: 35.824224, lng: 127.147953 },
    전남: { lat: 34.816095, lng: 126.462924 },
    전라남도: { lat: 34.816095, lng: 126.462924 },
    경북: { lat: 36.576032, lng: 128.505599 },
    경상북도: { lat: 36.576032, lng: 128.505599 },
    경남: { lat: 35.238294, lng: 128.692397 },
    경상남도: { lat: 35.238294, lng: 128.692397 },
    제주: { lat: 33.499621, lng: 126.531188 },
    제주특별자치도: { lat: 33.499621, lng: 126.531188 },
};

const mapElement = ref(null);
const map = ref(null);
const markers = ref([]);
const infoWindow = ref(null);
const items = ref([]);
const selectedNotice = ref(null);
const loading = ref(true);
const error = ref('');
const mapReady = ref(false);
const mapError = ref('');
const searchTerm = ref('');
const selectedRegion = ref('all');
const selectedSupply = ref('all');
const selectedSource = ref('all');
const currentPage = ref(1);

const filteredItems = computed(() => {
    const keyword = searchTerm.value.trim().toLowerCase();
    return items.value.filter((item) => {
        if (selectedRegion.value !== 'all' && mapRegion(item) !== selectedRegion.value)
            return false;
        if (selectedSupply.value !== 'all' && item.supply_type !== selectedSupply.value)
            return false;
        if (selectedSource.value !== 'all' && sourceGroup(item) !== selectedSource.value)
            return false;
        if (!keyword)
            return true;
        return [item.title, item.region, mapRegion(item), item.district, item.provider, item.supply_type]
            .filter(Boolean)
            .some((value) => String(value).toLowerCase().includes(keyword));
    });
});

const regions = computed(() => uniqueValues(items.value.map((item) => mapRegion(item))));
const supplyTypes = computed(() => uniqueValues(items.value.map((item) => item.supply_type)));
const fixtureCount = computed(() => items.value.filter((item) => sourceGroup(item) === 'fixture').length);
const realCount = computed(() => Math.max(0, items.value.length - fixtureCount.value));
const totalPages = computed(() => Math.max(1, Math.ceil(filteredItems.value.length / PAGE_SIZE)));
const displayRangeStart = computed(() => (filteredItems.value.length ? (currentPage.value - 1) * PAGE_SIZE + 1 : 0));
const displayRangeEnd = computed(() => Math.min(currentPage.value * PAGE_SIZE, filteredItems.value.length));
const pagedItems = computed(() => {
    const start = (currentPage.value - 1) * PAGE_SIZE;
    return filteredItems.value.slice(start, start + PAGE_SIZE);
});
const pageButtons = computed(() => {
    const pages = [];
    const total = totalPages.value;
    const start = Math.max(1, Math.min(currentPage.value - 2, total - 4));
    const end = Math.min(total, start + 4);
    for (let page = start; page <= end; page += 1)
        pages.push(page);
    return pages;
});
const selectedAnalysis = computed(() => {
    if (!selectedNotice.value)
        return null;
    return analysisSummary(selectedNotice.value.analysis_summary, selectedNotice.value.official_document_status);
});

function uniqueValues(values) {
    return Array.from(new Set(values.filter(Boolean))).sort((a, b) => a.localeCompare(b, 'ko'));
}

function sourceGroup(item) {
    return String(item?.data_source ?? '').toLowerCase().includes('fixture') ? 'fixture' : 'real';
}

function mapRegion(item) {
    return item?.map_region || item?.region || '전국';
}

function priceLabel(price) {
    return Number(price || 0) > 0 ? formatMoney(price) : '공고문 확인 필요';
}

function locationQualityLabel(quality) {
    if (quality === 'exact' || quality === 'kakao_rest')
        return '좌표 확인';
    if (quality === 'district')
        return '지구 기준';
    if (quality === 'fixture')
        return 'Fixture';
    return '지역 기준';
}

function selectedOptionId(item) {
    return item?.best_option?.option_id ?? null;
}

function fundingRoute(item) {
    const optionId = selectedOptionId(item);
    return optionId ? `/funding/${item.notice_id}?option_id=${optionId}` : `/funding/${item.notice_id}`;
}

function coachRoute(item) {
    const optionId = selectedOptionId(item);
    return optionId ? `/ai-coach/${item.notice_id}?option_id=${optionId}` : `/ai-coach/${item.notice_id}`;
}

function kakaoSearchUrl(item) {
    const query = item?.location?.label || `${item?.region ?? ''} ${item?.district ?? ''}`;
    return `https://map.kakao.com/link/search/${encodeURIComponent(query)}`;
}

function selectNotice(item, { pan = false, persist = true, marker = null } = {}) {
    selectedNotice.value = item;
    if (persist)
        saveCurrentSelection(item.notice_id, selectedOptionId(item));
    if (pan && map.value && window.kakao?.maps) {
        const position = new window.kakao.maps.LatLng(item.location.lat, item.location.lng);
        map.value.panTo(position);
        if (map.value.getLevel() > NOTICE_LEVEL)
            map.value.setLevel(NOTICE_LEVEL);
    }
    openInfoWindow(item, marker);
}

async function loadMapData() {
    loading.value = true;
    error.value = '';
    try {
        const response = await fetchMapNotices({ ownership_type: 'public_sale' });
        items.value = response.items ?? [];
        selectedNotice.value = items.value[0] ?? null;
    }
    catch {
        items.value = [];
        selectedNotice.value = null;
        error.value = '지도 공고 데이터를 불러오지 못했습니다. Django 서버와 마이그레이션 상태를 확인하세요.';
    }
    finally {
        loading.value = false;
    }
}

function loadKakaoMapSdk() {
    if (!KAKAO_JS_KEY) {
        mapError.value = '카카오 지도 JavaScript 키가 없습니다. frontend/.env에 VITE_KAKAO_MAP_JS_KEY를 추가하세요.';
        return Promise.reject(new Error('missing kakao map key'));
    }
    if (window.kakao?.maps) {
        return new Promise((resolve) => window.kakao.maps.load(resolve));
    }
    const existingScript = document.getElementById(KAKAO_SCRIPT_ID);
    if (existingScript) {
        return new Promise((resolve, reject) => {
            existingScript.addEventListener('load', () => window.kakao.maps.load(resolve), { once: true });
            existingScript.addEventListener('error', reject, { once: true });
        });
    }
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.id = KAKAO_SCRIPT_ID;
        script.async = true;
        script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(KAKAO_JS_KEY)}&libraries=services&autoload=false`;
        script.onload = () => window.kakao.maps.load(resolve);
        script.onerror = () => reject(new Error('failed to load kakao maps sdk'));
        document.head.appendChild(script);
    });
}

function initializeMap() {
    if (!mapElement.value || !window.kakao?.maps)
        return;
    const center = new window.kakao.maps.LatLng(DEFAULT_CENTER.lat, DEFAULT_CENTER.lng);
    map.value = new window.kakao.maps.Map(mapElement.value, {
        center,
        level: DEFAULT_LEVEL,
    });
    map.value.addControl(new window.kakao.maps.ZoomControl(), window.kakao.maps.ControlPosition.RIGHT);
    infoWindow.value = new window.kakao.maps.InfoWindow({ zIndex: 10 });
    mapReady.value = true;
    renderMarkers();
}

function renderMarkers() {
    if (!map.value || !window.kakao?.maps)
        return;
    map.value.relayout();
    markers.value.forEach((marker) => marker.setMap(null));
    markers.value = [];
    infoWindow.value?.close();

    const bounds = new window.kakao.maps.LatLngBounds();
    filteredItems.value.forEach((item) => {
        const position = new window.kakao.maps.LatLng(item.location.lat, item.location.lng);
        const marker = new window.kakao.maps.Marker({
            map: map.value,
            position,
            title: item.title,
        });
        window.kakao.maps.event.addListener(marker, 'click', () => {
            selectNotice(item, { persist: true, marker });
        });
        markers.value.push(marker);
        bounds.extend(position);
    });

    if (filteredItems.value.length === 0) {
        centerKoreaMap();
    }
    else if (selectedRegion.value !== 'all') {
        const center = regionCenter(selectedRegion.value) ?? filteredItems.value[0].location;
        map.value.setCenter(new window.kakao.maps.LatLng(center.lat, center.lng));
        map.value.setLevel(REGION_LEVEL);
    }
    else if (!searchTerm.value.trim() && selectedSupply.value === 'all' && selectedSource.value === 'all') {
        centerKoreaMap();
    }
    else if (filteredItems.value.length > 1) {
        map.value.setBounds(bounds, 48, 48, 48, 48);
        if (map.value.getLevel() > DEFAULT_LEVEL)
            map.value.setLevel(DEFAULT_LEVEL);
    }
    else if (filteredItems.value.length === 1) {
        const only = filteredItems.value[0];
        map.value.setCenter(new window.kakao.maps.LatLng(only.location.lat, only.location.lng));
        map.value.setLevel(NOTICE_LEVEL);
    }
}

function centerKoreaMap() {
    if (!map.value || !window.kakao?.maps)
        return;
    const bounds = new window.kakao.maps.LatLngBounds();
    bounds.extend(new window.kakao.maps.LatLng(SOUTH_KOREA_BOUNDS.sw.lat, SOUTH_KOREA_BOUNDS.sw.lng));
    bounds.extend(new window.kakao.maps.LatLng(SOUTH_KOREA_BOUNDS.ne.lat, SOUTH_KOREA_BOUNDS.ne.lng));
    map.value.setBounds(bounds, 24, 24, 24, 24);
    if (map.value.getLevel() > DEFAULT_LEVEL)
        map.value.setLevel(DEFAULT_LEVEL);
    map.value.setCenter(new window.kakao.maps.LatLng(DEFAULT_CENTER.lat, DEFAULT_CENTER.lng));
}

function regionCenter(region) {
    if (REGION_CENTERS[region])
        return REGION_CENTERS[region];
    if (region.includes('경기') && region.includes('북'))
        return REGION_CENTERS['경기 북부'];
    if (region.includes('경기'))
        return REGION_CENTERS['경기 남부'];
    return Object.entries(REGION_CENTERS).find(([key]) => key && region.includes(key))?.[1] ?? null;
}

function openInfoWindow(item, marker = null) {
    if (!map.value || !infoWindow.value || !window.kakao?.maps)
        return;
    const content = `
        <div style="width:240px;padding:12px 14px;background:#0f172a;color:#e5edf5;border:1px solid #2dd4bf;border-radius:8px;font-family:system-ui,-apple-system,sans-serif;">
            <div style="font-size:12px;color:#5eead4;font-weight:800;">${mapRegion(item)} · ${item.supply_type}</div>
            <div style="margin-top:4px;font-size:14px;font-weight:900;line-height:1.35;">${escapeHtml(item.title)}</div>
            <div style="margin-top:8px;display:flex;justify-content:space-between;font-size:12px;color:#a8b3c3;">
                <span>${priceLabel(item.price)}</span>
                <strong style="color:#ffffff;">${item.total_score}/${item.score_max}점</strong>
            </div>
        </div>
    `;
    infoWindow.value.setContent(content);
    if (marker) {
        infoWindow.value.open(map.value, marker);
    }
    else {
        const position = new window.kakao.maps.LatLng(item.location.lat, item.location.lng);
        infoWindow.value.setPosition(position);
        infoWindow.value.open(map.value);
    }
}

function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function resetMapBounds() {
    if (selectedRegion.value === 'all' && !searchTerm.value.trim() && selectedSupply.value === 'all' && selectedSource.value === 'all') {
        centerKoreaMap();
        return;
    }
    renderMarkers();
}

function moveToCurrentLocation() {
    if (!navigator.geolocation || !map.value || !window.kakao?.maps)
        return;
    navigator.geolocation.getCurrentPosition((position) => {
        map.value.panTo(new window.kakao.maps.LatLng(position.coords.latitude, position.coords.longitude));
        map.value.setLevel(NOTICE_LEVEL);
    });
}

function goToPage(page) {
    currentPage.value = Math.min(Math.max(1, page), totalPages.value);
}

watch([searchTerm, selectedRegion, selectedSupply, selectedSource], () => {
    currentPage.value = 1;
});

watch(filteredItems, async () => {
    await nextTick();
    if (currentPage.value > totalPages.value)
        currentPage.value = totalPages.value;
    if (!filteredItems.value.length) {
        selectedNotice.value = null;
        renderMarkers();
        return;
    }
    if (filteredItems.value.length && !filteredItems.value.some((item) => item.notice_id === selectedNotice.value?.notice_id)) {
        selectedNotice.value = filteredItems.value[0];
    }
    renderMarkers();
});

onMounted(async () => {
    await loadMapData();
    try {
        await loadKakaoMapSdk();
        initializeMap();
    }
    catch {
        if (!mapError.value)
            mapError.value = '카카오 지도를 불러오지 못했습니다. JavaScript 키와 허용 도메인을 확인하세요.';
    }
});

onBeforeUnmount(() => {
    markers.value.forEach((marker) => marker.setMap(null));
    markers.value = [];
    infoWindow.value?.close();
});
</script>

<template>
  <div class="-m-4 flex h-[calc(100vh-4rem)] flex-col overflow-hidden bg-[#071015] sm:-m-6">
    <section class="shrink-0 border-b border-slate-200 bg-slate-950 px-4 py-4 sm:px-6">
      <div class="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p class="inline-flex items-center gap-2 text-sm font-bold text-emerald-300">
            <MapPin class="h-4 w-4" />
            청약 지도
          </p>
          <h1 class="mt-2 text-3xl font-black text-white">지도에서 공고를 직접 고르기</h1>
          <p class="mt-2 text-sm text-slate-400">
            활성화된 소유형 공공분양 공고를 카카오 지도 위에 표시합니다. 마커를 선택하면 상세, 자금 로드맵, AI 코치로 이어집니다.
          </p>
        </div>

        <div class="grid gap-2 sm:grid-cols-3 xl:w-[520px]">
          <div class="rounded-lg border border-slate-200 bg-slate-900 px-4 py-3">
            <p class="text-xs font-bold text-slate-400">지도 공고</p>
            <p class="mt-1 text-xl font-black text-white">{{ filteredItems.length }}건</p>
          </div>
          <div class="rounded-lg border border-slate-200 bg-slate-900 px-4 py-3">
            <p class="text-xs font-bold text-slate-400">실제 데이터</p>
            <p class="mt-1 text-xl font-black text-white">{{ realCount }}건</p>
          </div>
          <div class="rounded-lg border border-slate-200 bg-slate-900 px-4 py-3">
            <p class="text-xs font-bold text-slate-400">Fixture 보강</p>
            <p class="mt-1 text-xl font-black text-white">{{ fixtureCount }}건</p>
          </div>
        </div>
      </div>
    </section>

    <section class="grid min-h-0 flex-1 overflow-hidden xl:grid-cols-[minmax(0,1fr)_420px]">
      <div class="relative min-h-0 overflow-hidden">
        <div ref="mapElement" class="absolute inset-0 bg-slate-900" />

        <div class="absolute left-4 top-4 z-10 flex w-[min(560px,calc(100%-2rem))] flex-col gap-3">
          <div class="rounded-lg border border-slate-200 bg-slate-950/92 p-3 shadow-2xl backdrop-blur">
            <div class="flex items-center gap-2">
              <Search class="h-4 w-4 text-slate-400" />
              <input
                v-model="searchTerm"
                class="h-10 min-w-0 flex-1 rounded-lg border border-slate-200 bg-slate-900 px-3 text-sm font-semibold text-white outline-none transition placeholder:text-slate-500 focus:border-emerald-400"
                type="search"
                placeholder="청약명, 지역, 지구 검색"
              />
              <button
                type="button"
                class="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-slate-900 text-slate-300 transition hover:text-white"
                title="현재 위치"
                @click="moveToCurrentLocation"
              >
                <LocateFixed class="h-4 w-4" />
              </button>
              <button
                type="button"
                class="flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-slate-900 text-slate-300 transition hover:text-white"
                title="전체 보기"
                @click="resetMapBounds"
              >
                <Crosshair class="h-4 w-4" />
              </button>
            </div>

            <div class="mt-3 flex flex-wrap gap-2 text-xs font-bold">
              <select v-model="selectedRegion" class="h-9 rounded-lg border border-slate-200 bg-slate-900 px-3 text-slate-100 outline-none">
                <option value="all">전체 지역</option>
                <option v-for="region in regions" :key="region" :value="region">{{ region }}</option>
              </select>
              <select v-model="selectedSupply" class="h-9 rounded-lg border border-slate-200 bg-slate-900 px-3 text-slate-100 outline-none">
                <option value="all">전체 공급유형</option>
                <option v-for="supplyType in supplyTypes" :key="supplyType" :value="supplyType">{{ supplyType }}</option>
              </select>
              <select v-model="selectedSource" class="h-9 rounded-lg border border-slate-200 bg-slate-900 px-3 text-slate-100 outline-none">
                <option value="all">전체 데이터</option>
                <option value="real">실제 데이터</option>
                <option value="fixture">Fixture</option>
              </select>
            </div>
          </div>
        </div>

        <div v-if="loading" class="absolute inset-0 z-20 flex items-center justify-center bg-slate-950/70">
          <div class="rounded-lg border border-slate-200 bg-slate-950 px-5 py-4 text-sm font-bold text-white shadow-2xl">
            지도 공고를 불러오는 중입니다.
          </div>
        </div>

        <div v-if="error || mapError" class="absolute bottom-4 left-4 right-4 z-20 rounded-lg border border-amber-500/30 bg-amber-950/90 p-4 text-sm font-bold text-amber-100 shadow-2xl">
          {{ error || mapError }}
        </div>

        <div v-if="mapReady && !filteredItems.length && !loading" class="absolute left-4 top-36 z-20 max-w-[min(520px,calc(100%-2rem))] rounded-lg border border-amber-400/50 bg-slate-950/95 p-4 text-sm font-bold text-slate-100 shadow-2xl backdrop-blur">
          <p class="text-amber-200">조건에 맞는 지도 공고가 없습니다.</p>
          <p class="mt-1 text-xs font-semibold leading-5 text-slate-400">
            지역, 공급유형, 데이터 필터를 넓혀 다시 확인해보세요.
          </p>
        </div>
      </div>

      <aside class="flex min-h-0 flex-col overflow-hidden border-l border-slate-200 bg-slate-950 p-4 sm:p-5">
        <div class="flex shrink-0 items-center justify-between gap-3">
          <p class="inline-flex items-center gap-2 text-sm font-bold text-emerald-300">
            <SlidersHorizontal class="h-4 w-4" />
            선택한 공고
          </p>
          <button
            type="button"
            class="inline-flex h-9 items-center gap-2 rounded-lg border border-slate-200 bg-slate-900 px-3 text-xs font-bold text-slate-200 transition hover:text-white"
            @click="resetMapBounds"
          >
            <RotateCcw class="h-4 w-4" />
            전체 보기
          </button>
        </div>

        <div v-if="selectedNotice" class="mt-4 shrink-0 rounded-lg border border-emerald-400/60 bg-emerald-950/30 p-4">
          <div class="flex items-start justify-between gap-3">
            <div>
              <div class="flex flex-wrap gap-2">
                <span class="rounded-md bg-emerald-400/15 px-2 py-1 text-xs font-black text-emerald-200">{{ selectedNotice.supply_type }}</span>
                <span v-if="sourceGroup(selectedNotice) === 'fixture'" class="rounded-md bg-slate-100 px-2 py-1 text-xs font-black text-slate-700">Fixture</span>
                <span class="rounded-md bg-slate-800 px-2 py-1 text-xs font-black text-slate-200">
                  {{ locationQualityLabel(selectedNotice.location.quality) }}
                </span>
              </div>
              <h2 class="mt-3 text-xl font-black leading-tight text-white">{{ selectedNotice.title }}</h2>
              <p class="mt-2 text-sm text-slate-400">{{ selectedNotice.provider }} · {{ mapRegion(selectedNotice) }} · {{ selectedNotice.district }}</p>
            </div>
            <div class="shrink-0 rounded-lg bg-slate-900 px-3 py-2 text-right">
              <p class="text-xs font-bold text-slate-400">추천 점수</p>
              <p class="text-xl font-black text-white">{{ selectedNotice.total_score }}/{{ selectedNotice.score_max }}</p>
            </div>
          </div>

          <div class="mt-4 grid grid-cols-2 gap-2">
            <div class="rounded-lg bg-slate-900 p-3">
              <p class="text-xs font-bold text-slate-400">예상 분양가</p>
              <p class="mt-1 text-lg font-black text-white">{{ priceLabel(selectedNotice.price) }}</p>
            </div>
            <div class="rounded-lg bg-slate-900 p-3">
              <p class="text-xs font-bold text-slate-400">접수 마감</p>
              <p class="mt-1 text-lg font-black text-white">{{ selectedNotice.application_deadline }}</p>
            </div>
            <div class="rounded-lg bg-slate-900 p-3">
              <p class="text-xs font-bold text-slate-400">주택형 옵션</p>
              <p class="mt-1 text-lg font-black text-white">{{ selectedNotice.unit_option_count }}개</p>
            </div>
            <div class="rounded-lg bg-slate-900 p-3">
              <p class="text-xs font-bold text-slate-400">공식 분석</p>
              <p class="mt-1">
                <span class="rounded-md px-2 py-1 text-xs font-black" :class="analysisBadgeClass(selectedAnalysis)">
                  {{ selectedAnalysis?.label }}
                </span>
              </p>
            </div>
          </div>

          <div v-if="selectedNotice.best_option" class="mt-3 rounded-lg border border-slate-200 bg-slate-900 p-3">
            <p class="text-xs font-bold text-emerald-300">대표 주택형</p>
            <p class="mt-1 text-lg font-black text-white">
              {{ selectedNotice.best_option.unit_type }} · {{ selectedNotice.best_option.floor_group }}
            </p>
            <p class="mt-1 text-sm text-slate-400">{{ priceLabel(selectedNotice.best_option.base_price) }}</p>
          </div>

          <div class="mt-4 grid grid-cols-2 gap-2">
            <RouterLink
              :to="`/notices/${selectedNotice.notice_id}`"
              class="col-span-2 inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-emerald-500 text-sm font-black text-slate-950 transition hover:bg-emerald-300"
              @click="saveCurrentSelection(selectedNotice.notice_id, selectedOptionId(selectedNotice))"
            >
              공고 상세와 옵션 보기
              <ChevronRight class="h-4 w-4" />
            </RouterLink>
            <RouterLink
              :to="fundingRoute(selectedNotice)"
              class="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-900 text-sm font-black text-white transition hover:bg-slate-800"
              @click="saveCurrentSelection(selectedNotice.notice_id, selectedOptionId(selectedNotice))"
            >
              <WalletCards class="h-4 w-4" />
              자금 로드맵
            </RouterLink>
            <RouterLink
              :to="coachRoute(selectedNotice)"
              class="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-900 text-sm font-black text-white transition hover:bg-slate-800"
              @click="saveCurrentSelection(selectedNotice.notice_id, selectedOptionId(selectedNotice))"
            >
              AI 코칭 받기
            </RouterLink>
            <a
              :href="kakaoSearchUrl(selectedNotice)"
              target="_blank"
              rel="noreferrer"
              class="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-slate-900 text-sm font-black text-white transition hover:bg-slate-800"
            >
              카카오맵에서 검색
              <ExternalLink class="h-4 w-4" />
            </a>
          </div>
        </div>

        <div v-else class="mt-4 rounded-lg border border-slate-200 bg-slate-900 p-4 text-sm font-bold text-slate-300">
          지도 마커나 목록에서 공고를 선택하세요.
        </div>

        <div class="mt-4 flex min-h-0 flex-1 flex-col">
          <div class="flex shrink-0 items-end justify-between gap-3">
            <div>
              <h3 class="text-sm font-black text-white">지도 공고 목록</h3>
              <p class="mt-1 text-xs font-bold text-slate-400">
                {{ filteredItems.length }}건 중 {{ displayRangeStart }}-{{ displayRangeEnd }}건
              </p>
            </div>
            <span class="rounded-md bg-slate-900 px-2 py-1 text-xs font-black text-slate-300">
              {{ currentPage }}/{{ totalPages }}
            </span>
          </div>

          <div class="mt-3 min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
            <button
              v-for="item in pagedItems"
              :key="item.notice_id"
              type="button"
              class="w-full rounded-lg border p-3 text-left transition"
              :class="selectedNotice?.notice_id === item.notice_id ? 'border-emerald-400 bg-emerald-950/35' : 'border-slate-200 bg-slate-900 hover:border-emerald-400/60'"
              @click="selectNotice(item, { pan: true })"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <p class="truncate text-xs font-black text-emerald-300">{{ mapRegion(item) }} · {{ item.supply_type }}</p>
                  <p class="mt-1 line-clamp-2 text-sm font-black leading-5 text-white">{{ item.title }}</p>
                  <p class="mt-1 truncate text-xs text-slate-400">{{ item.district }}</p>
                </div>
                <span class="shrink-0 rounded-md bg-slate-950 px-2 py-1 text-xs font-black text-white">
                  {{ item.total_score }}점
                </span>
              </div>
            </button>
          </div>

          <div v-if="totalPages > 1" class="mt-3 flex shrink-0 items-center justify-center gap-1 border-t border-slate-200 pt-3">
            <button
              type="button"
              class="h-8 rounded-md px-2 text-xs font-black text-slate-300 transition hover:bg-slate-800 disabled:opacity-35"
              :disabled="currentPage === 1"
              @click="goToPage(currentPage - 1)"
            >
              이전
            </button>
            <button
              v-for="page in pageButtons"
              :key="page"
              type="button"
              class="flex h-8 min-w-8 items-center justify-center rounded-md px-2 text-xs font-black transition"
              :class="page === currentPage ? 'bg-emerald-400 text-slate-950' : 'text-slate-300 hover:bg-slate-800'"
              @click="goToPage(page)"
            >
              {{ page }}
            </button>
            <button
              type="button"
              class="h-8 rounded-md px-2 text-xs font-black text-slate-300 transition hover:bg-slate-800 disabled:opacity-35"
              :disabled="currentPage === totalPages"
              @click="goToPage(currentPage + 1)"
            >
              다음
            </button>
          </div>
        </div>

        <div class="mt-4 shrink-0 rounded-lg border border-slate-200 bg-slate-900 p-3 text-xs leading-5 text-slate-400">
          <p class="flex items-center gap-2 font-black text-slate-100">
            <Building2 class="h-4 w-4 text-emerald-300" />
            위치 정확도
          </p>
          <p class="mt-2">
            정확 좌표가 없는 공고는 지구명 또는 지역 중심 좌표로 임시 표시합니다. Kakao REST 지오코딩을 실행하면 실제 주소 기반 좌표로 보강할 수 있습니다.
          </p>
        </div>
      </aside>
    </section>
  </div>
</template>
