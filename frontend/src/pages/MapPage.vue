<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { Building2, ExternalLink, LocateFixed, MapPin, Search, WalletCards } from 'lucide-vue-next';
import { fetchMapNotices, searchPlaces } from '../api/firsthome';
import { formatMoney } from '../utils/format';
import { saveCurrentSelection } from '../utils/selectionState';

const KAKAO_JS_KEY = import.meta.env.VITE_KAKAO_MAP_JS_KEY ?? '';
const KAKAO_SCRIPT_ID = 'firsthome-kakao-map-sdk';
const DEFAULT_CENTER = { lat: 37.5012743, lng: 127.039585 };

const mapElement = ref(null);
const map = ref(null);
const markers = ref([]);
const infoWindow = ref(null);
const mapReady = ref(false);
const mapError = ref('');
const mode = ref('notice');
const searchTerm = ref('');
const notices = ref([]);
const places = ref([]);
const selectedItem = ref(null);
const loading = ref(true);
const error = ref('');

const currentItems = computed(() => mode.value === 'notice' ? notices.value : places.value);
const modeLabel = computed(() => ({ notice: '청약', bank: '은행', estate: '부동산' }[mode.value]));

function loadKakaoMapSdk() {
  if (!KAKAO_JS_KEY) {
    mapError.value = 'Kakao Map JavaScript 키가 없어 목록 모드로 표시합니다.';
    return Promise.reject(new Error('missing kakao key'));
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
    script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(KAKAO_JS_KEY)}&autoload=false`;
    script.onload = () => window.kakao.maps.load(resolve);
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

function initializeMap() {
  if (!mapElement.value || !window.kakao?.maps)
    return;
  map.value = new window.kakao.maps.Map(mapElement.value, {
    center: new window.kakao.maps.LatLng(DEFAULT_CENTER.lat, DEFAULT_CENTER.lng),
    level: 6,
  });
  infoWindow.value = new window.kakao.maps.InfoWindow({ zIndex: 10 });
  mapReady.value = true;
  renderMarkers();
}

async function loadNotices() {
  loading.value = true;
  error.value = '';
  try {
    const response = await fetchMapNotices({ ownership_type: 'public_sale' });
    notices.value = (response.items ?? []).map((item) => ({
      ...item,
      lat: item.location?.lat,
      lng: item.location?.lng,
      name: item.title,
      address: [item.region, item.district].filter(Boolean).join(' '),
    }));
    selectedItem.value = notices.value[0] ?? null;
  } catch {
    error.value = '청약 지도 데이터를 불러오지 못했습니다.';
  } finally {
    loading.value = false;
  }
}

async function loadPlaces() {
  if (mode.value === 'notice')
    return;
  loading.value = true;
  error.value = '';
  try {
    const response = await searchPlaces({ type: mode.value, query: searchTerm.value, lat: DEFAULT_CENTER.lat, lng: DEFAULT_CENTER.lng });
    places.value = response.items ?? [];
    selectedItem.value = places.value[0] ?? null;
  } catch {
    error.value = '장소 검색 결과를 불러오지 못했습니다.';
  } finally {
    loading.value = false;
  }
}

function renderMarkers() {
  if (!map.value || !window.kakao?.maps)
    return;
  markers.value.forEach((marker) => marker.setMap(null));
  markers.value = [];
  const bounds = new window.kakao.maps.LatLngBounds();
  currentItems.value.forEach((item) => {
    if (!item.lat || !item.lng)
      return;
    const position = new window.kakao.maps.LatLng(item.lat, item.lng);
    const marker = new window.kakao.maps.Marker({ map: map.value, position, title: item.name });
    window.kakao.maps.event.addListener(marker, 'click', () => selectItem(item, marker));
    markers.value.push(marker);
    bounds.extend(position);
  });
  if (markers.value.length > 1) {
    map.value.setBounds(bounds, 48, 48, 48, 48);
  } else if (markers.value.length === 1) {
    map.value.setCenter(markers.value[0].getPosition());
    map.value.setLevel(4);
  }
}

function selectItem(item, marker = null) {
  selectedItem.value = item;
  if (!map.value || !window.kakao?.maps || !item.lat || !item.lng)
    return;
  const content = `<div style="width:220px;padding:12px;font-family:system-ui,sans-serif"><b>${escapeHtml(item.name)}</b><br><span>${escapeHtml(item.address || item.road_address || '')}</span></div>`;
  infoWindow.value?.setContent(content);
  if (marker) {
    infoWindow.value?.open(map.value, marker);
  } else {
    infoWindow.value?.setPosition(new window.kakao.maps.LatLng(item.lat, item.lng));
    infoWindow.value?.open(map.value);
  }
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[char]));
}

function moveToCurrentLocation() {
  if (!navigator.geolocation || !map.value || !window.kakao?.maps)
    return;
  navigator.geolocation.getCurrentPosition((position) => {
    map.value.panTo(new window.kakao.maps.LatLng(position.coords.latitude, position.coords.longitude));
    map.value.setLevel(4);
  });
}

async function changeMode(nextMode) {
  mode.value = nextMode;
  selectedItem.value = null;
  if (nextMode === 'notice') {
    selectedItem.value = notices.value[0] ?? null;
  } else {
    await loadPlaces();
  }
  await nextTick();
  renderMarkers();
}

async function submitSearch() {
  if (mode.value === 'notice')
    return;
  await loadPlaces();
  renderMarkers();
}

watch(currentItems, () => {
  renderMarkers();
});

onMounted(async () => {
  await loadNotices();
  try {
    await loadKakaoMapSdk();
    initializeMap();
  } catch {
    mapReady.value = false;
  }
});

onBeforeUnmount(() => {
  markers.value.forEach((marker) => marker.setMap(null));
  markers.value = [];
  infoWindow.value?.close();
});
</script>

<template>
  <div class="-m-4 grid h-[calc(100vh-4rem)] overflow-hidden bg-slate-950 sm:-m-6 xl:grid-cols-[minmax(0,1fr)_420px]">
    <section class="relative min-h-0">
      <div ref="mapElement" class="absolute inset-0 bg-slate-900" />
      <div v-if="!mapReady" class="absolute inset-0 flex items-center justify-center bg-slate-900 text-sm font-bold text-slate-300">
        {{ mapError || '지도 로딩 중입니다.' }}
      </div>
      <div class="absolute left-4 top-4 z-10 w-[min(620px,calc(100%-2rem))] rounded-lg border border-white/10 bg-slate-950/95 p-3 shadow-2xl">
        <div class="flex flex-wrap gap-2">
          <button v-for="item in [{key:'notice',label:'청약'}, {key:'estate',label:'부동산'}, {key:'bank',label:'은행'}]" :key="item.key" type="button" class="h-10 rounded-lg px-4 text-sm font-black" :class="mode === item.key ? 'bg-emerald-400 text-slate-950' : 'bg-slate-800 text-slate-200'" @click="changeMode(item.key)">
            {{ item.label }}
          </button>
          <button type="button" class="ml-auto flex h-10 w-10 items-center justify-center rounded-lg bg-slate-800 text-slate-200" @click="moveToCurrentLocation">
            <LocateFixed class="h-4 w-4" />
          </button>
        </div>
        <div v-if="mode !== 'notice'" class="mt-3 flex gap-2">
          <input v-model="searchTerm" class="h-10 min-w-0 flex-1 rounded-lg border border-white/10 bg-slate-900 px-3 text-sm font-bold text-white" type="search" :placeholder="`${modeLabel} 검색어`" @keydown.enter="submitSearch" />
          <button type="button" class="flex h-10 items-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-black text-white" @click="submitSearch">
            <Search class="h-4 w-4" /> 검색
          </button>
        </div>
      </div>
    </section>

    <aside class="flex min-h-0 flex-col border-l border-white/10 bg-slate-950 p-4 text-white">
      <div class="shrink-0">
        <p class="inline-flex items-center gap-2 text-sm font-bold text-emerald-300">
          <MapPin class="h-4 w-4" /> {{ modeLabel }} 지도
        </p>
        <h1 class="mt-2 text-2xl font-black">{{ modeLabel }} 탐색</h1>
        <p class="mt-2 text-sm text-slate-400">청약 공고는 기존 흐름을 유지하고, 은행/부동산은 Kakao Local 기반 주변 검색을 사용합니다.</p>
      </div>

      <p v-if="error" class="mt-4 rounded-lg bg-amber-900/50 p-3 text-sm font-bold text-amber-100">{{ error }}</p>
      <div v-if="selectedItem" class="mt-4 rounded-lg border border-emerald-400/50 bg-emerald-950/30 p-4">
        <p class="text-xs font-black text-emerald-200">{{ modeLabel }}</p>
        <h2 class="mt-2 text-xl font-black">{{ selectedItem.name }}</h2>
        <p class="mt-2 text-sm text-slate-300">{{ selectedItem.address || selectedItem.road_address }}</p>
        <div v-if="mode === 'notice'" class="mt-4 grid grid-cols-2 gap-2">
          <div class="rounded-lg bg-slate-900 p-3">
            <p class="text-xs font-bold text-slate-400">분양가</p>
            <p class="font-black">{{ formatMoney(selectedItem.price || 0) }}</p>
          </div>
          <div class="rounded-lg bg-slate-900 p-3">
            <p class="text-xs font-bold text-slate-400">마감</p>
            <p class="font-black">{{ selectedItem.application_deadline }}</p>
          </div>
        </div>
        <div class="mt-4 grid gap-2" :class="mode === 'notice' ? 'grid-cols-2' : 'grid-cols-1'">
          <RouterLink v-if="mode === 'notice'" :to="`/notices/${selectedItem.notice_id}`" class="rounded-lg bg-emerald-400 px-3 py-2 text-center text-sm font-black text-slate-950" @click="saveCurrentSelection(selectedItem.notice_id, selectedItem.best_option?.option_id)">
            공고 상세
          </RouterLink>
          <RouterLink v-if="mode === 'notice'" :to="`/funding/${selectedItem.notice_id}`" class="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-800 px-3 py-2 text-sm font-black text-white" @click="saveCurrentSelection(selectedItem.notice_id, selectedItem.best_option?.option_id)">
            <WalletCards class="h-4 w-4" /> 자금
          </RouterLink>
          <a v-if="mode !== 'notice'" :href="selectedItem.direction_url" target="_blank" rel="noreferrer" class="inline-flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-3 py-2 text-sm font-black text-white">
            길찾기 <ExternalLink class="h-4 w-4" />
          </a>
        </div>
      </div>

      <div class="mt-4 min-h-0 flex-1 space-y-2 overflow-y-auto">
        <button v-for="item in currentItems" :key="item.id || item.notice_id" type="button" class="w-full rounded-lg border border-white/10 bg-slate-900 p-3 text-left transition hover:border-emerald-400/70" @click="selectItem(item)">
          <p class="line-clamp-2 text-sm font-black">{{ item.name }}</p>
          <p class="mt-1 text-xs text-slate-400">{{ item.address || item.road_address }}</p>
          <p v-if="item.distance" class="mt-1 text-xs font-bold text-emerald-300">{{ item.distance }}m</p>
        </button>
        <p v-if="!loading && !currentItems.length" class="rounded-lg bg-slate-900 p-4 text-sm font-bold text-slate-400">
          표시할 항목이 없습니다.
        </p>
      </div>
    </aside>
  </div>
</template>
