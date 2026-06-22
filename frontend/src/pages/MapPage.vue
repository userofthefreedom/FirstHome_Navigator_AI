<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { Building2, ExternalLink, LocateFixed, MapPin, Navigation, Search, WalletCards } from 'lucide-vue-next';
import { fetchMapNotices, fetchPlaceRoute, searchPlaces } from '../api/firsthome';
import { formatMoney } from '../utils/format';
import { saveCurrentSelection } from '../utils/selectionState';

const KAKAO_JS_KEY = import.meta.env.VITE_KAKAO_MAP_JS_KEY ?? '';
const KAKAO_SCRIPT_ID = 'firsthome-kakao-map-sdk';
const DEFAULT_CENTER = { lat: 37.5012743, lng: 127.039585 };

const mapElement = ref(null);
const map = ref(null);
const markers = ref([]);
const routeLine = ref(null);
const routeMarkers = ref([]);
const userLocationMarker = ref(null);
const infoWindow = ref(null);
const mapReady = ref(false);
const mapError = ref('');
const mode = ref('notice');
const searchTerm = ref('');
const noticeRegion = ref('');
const noticeSupplyType = ref('');
const noticeDataType = ref('all');
const placeSido = ref('');
const placeSigungu = ref('');
const bankBrand = ref('');
const notices = ref([]);
const places = ref([]);
const selectedItem = ref(null);
const loading = ref(true);
const routeLoading = ref(false);
const routeMessage = ref('');
const locationMessage = ref('');
const error = ref('');

const REGION_GROUPS = {
  서울특별시: ['종로구', '중구', '용산구', '성동구', '광진구', '동대문구', '중랑구', '성북구', '강북구', '도봉구', '노원구', '은평구', '서대문구', '마포구', '양천구', '강서구', '구로구', '금천구', '영등포구', '동작구', '관악구', '서초구', '강남구', '송파구', '강동구'],
  부산광역시: ['중구', '서구', '동구', '영도구', '부산진구', '동래구', '남구', '북구', '해운대구', '사하구', '금정구', '강서구', '연제구', '수영구', '사상구', '기장군'],
  대구광역시: ['중구', '동구', '서구', '남구', '북구', '수성구', '달서구', '달성군', '군위군'],
  인천광역시: ['중구', '동구', '미추홀구', '연수구', '남동구', '부평구', '계양구', '서구', '강화군', '옹진군'],
  광주광역시: ['동구', '서구', '남구', '북구', '광산구'],
  대전광역시: ['동구', '중구', '서구', '유성구', '대덕구'],
  울산광역시: ['중구', '남구', '동구', '북구', '울주군'],
  세종특별자치시: ['세종시'],
  경기도: ['수원시', '성남시', '의정부시', '안양시', '부천시', '광명시', '평택시', '동두천시', '안산시', '고양시', '과천시', '구리시', '남양주시', '오산시', '시흥시', '군포시', '의왕시', '하남시', '용인시', '파주시', '이천시', '안성시', '김포시', '화성시', '광주시', '양주시', '포천시', '여주시', '연천군', '가평군', '양평군'],
  강원특별자치도: ['춘천시', '원주시', '강릉시', '동해시', '태백시', '속초시', '삼척시', '홍천군', '횡성군', '영월군', '평창군', '정선군', '철원군', '화천군', '양구군', '인제군', '고성군', '양양군'],
  충청북도: ['청주시', '충주시', '제천시', '보은군', '옥천군', '영동군', '증평군', '진천군', '괴산군', '음성군', '단양군'],
  충청남도: ['천안시', '공주시', '보령시', '아산시', '서산시', '논산시', '계룡시', '당진시', '금산군', '부여군', '서천군', '청양군', '홍성군', '예산군', '태안군'],
  전북특별자치도: ['전주시', '군산시', '익산시', '정읍시', '남원시', '김제시', '완주군', '진안군', '무주군', '장수군', '임실군', '순창군', '고창군', '부안군'],
  전라남도: ['목포시', '여수시', '순천시', '나주시', '광양시', '담양군', '곡성군', '구례군', '고흥군', '보성군', '화순군', '장흥군', '강진군', '해남군', '영암군', '무안군', '함평군', '영광군', '장성군', '완도군', '진도군', '신안군'],
  경상북도: ['포항시', '경주시', '김천시', '안동시', '구미시', '영주시', '영천시', '상주시', '문경시', '경산시', '의성군', '청송군', '영양군', '영덕군', '청도군', '고령군', '성주군', '칠곡군', '예천군', '봉화군', '울진군', '울릉군'],
  경상남도: ['창원시', '진주시', '통영시', '사천시', '김해시', '밀양시', '거제시', '양산시', '의령군', '함안군', '창녕군', '고성군', '남해군', '하동군', '산청군', '함양군', '거창군', '합천군'],
  제주특별자치도: ['제주시', '서귀포시'],
};

const bankBrandOptions = [
  { value: '', label: '전체 은행' },
  { value: 'kb', label: 'KB국민은행' },
  { value: 'shinhan', label: '신한은행' },
  { value: 'woori', label: '우리은행' },
  { value: 'hana', label: '하나은행' },
  { value: 'nh', label: 'NH농협은행' },
  { value: 'ibk', label: 'IBK기업은행' },
  { value: 'sc', label: 'SC제일은행' },
  { value: 'kdb', label: 'KDB산업은행' },
  { value: 'suhyup', label: '수협은행' },
  { value: 'saemaeul', label: '새마을금고' },
  { value: 'shinhyup', label: '신협' },
];

const modeMeta = {
  notice: { label: '청약', icon: MapPin },
  estate: { label: '부동산', icon: Building2 },
  bank: { label: '은행', icon: WalletCards },
};

const modeLabel = computed(() => modeMeta[mode.value]?.label ?? '지도');
const placeSidoOptions = computed(() => Object.keys(REGION_GROUPS));
const placeSigunguOptions = computed(() => placeSido.value ? REGION_GROUPS[placeSido.value] ?? [] : []);
const selectedPlaceRegion = computed(() => {
  if (!placeSido.value)
    return '';
  if (!placeSigungu.value)
    return placeSido.value;
  if (placeSido.value === '세종특별자치시')
    return placeSido.value;
  return `${placeSido.value} ${placeSigungu.value}`;
});
const noticeRegions = computed(() => uniqueOptions(notices.value.map((item) => item.map_region || item.region)));
const noticeSupplyTypes = computed(() => uniqueOptions(notices.value.map((item) => item.supply_type)));
const filteredNotices = computed(() => {
  const keyword = normalize(searchTerm.value);
  return notices.value.filter((item) => {
    const dataSource = String(item.data_source ?? '').toLowerCase();
    const isFixture = dataSource.includes('fixture') || Boolean(item.source_meta?.fixture_id);
    const matchesKeyword = !keyword || normalize([
      item.name,
      item.provider,
      item.region,
      item.map_region,
      item.district,
      item.supply_type,
    ].join(' ')).includes(keyword);
    const matchesRegion = !noticeRegion.value || (item.map_region || item.region) === noticeRegion.value;
    const matchesSupply = !noticeSupplyType.value || item.supply_type === noticeSupplyType.value;
    const matchesData = noticeDataType.value === 'all'
      || (noticeDataType.value === 'fixture' ? isFixture : !isFixture);
    return matchesKeyword && matchesRegion && matchesSupply && matchesData;
  });
});
const currentItems = computed(() => mode.value === 'notice' ? filteredNotices.value : places.value);

function uniqueOptions(values) {
  return [...new Set(values.filter(Boolean))].sort((a, b) => String(a).localeCompare(String(b), 'ko'));
}

function normalize(value) {
  return String(value ?? '').trim().toLowerCase();
}

function loadKakaoMapSdk() {
  if (!KAKAO_JS_KEY) {
    mapError.value = 'Kakao Map JavaScript 키가 없어 지도를 표시할 수 없습니다.';
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
    const response = await fetchMapNotices();
    notices.value = (response.items ?? []).map((item) => ({
      ...item,
      lat: item.location?.lat,
      lng: item.location?.lng,
      name: item.title,
      address: [item.region, item.district].filter(Boolean).join(' '),
    }));
    selectedItem.value = filteredNotices.value[0] ?? notices.value[0] ?? null;
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
  routeMessage.value = '';
  clearRoute();
  try {
    const placeQuery = searchTerm.value.trim() || selectedPlaceRegion.value;
    const response = await searchPlaces({
      type: mode.value,
      query: placeQuery,
      bank_brand: mode.value === 'bank' ? bankBrand.value : '',
      lat: DEFAULT_CENTER.lat,
      lng: DEFAULT_CENTER.lng,
      radius: placeQuery ? 20000 : 3000,
    });
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
  infoWindow.value?.close();

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
  routeMessage.value = '';
  clearRoute();
  if (!map.value || !window.kakao?.maps || !item.lat || !item.lng)
    return;
  const subtitle = item.address || item.road_address || item.provider || '';
  const content = `
    <div style="width:280px;padding:13px 14px;background:#ffffff;color:#0f172a;border:1px solid #cbd5e1;border-radius:10px;box-shadow:0 16px 36px rgba(15,23,42,.2);font-family:system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
      <div style="display:flex;align-items:flex-start;gap:10px;">
        <strong style="display:block;flex:1;min-width:0;color:#0f172a;font-size:14px;font-weight:800;line-height:1.35;">${escapeHtml(item.name)}</strong>
        <button type="button" onclick="window.__firsthomeMapRouteToSelected && window.__firsthomeMapRouteToSelected()" style="flex:0 0 auto;border:0;border-radius:999px;background:#10b981;color:#ffffff;padding:6px 9px;font-size:11px;font-weight:800;line-height:1;cursor:pointer;">길찾기</button>
      </div>
      <span style="display:block;margin-top:7px;color:#475569;font-size:12px;font-weight:600;line-height:1.45;">${escapeHtml(subtitle)}</span>
    </div>`;
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
  locationMessage.value = '현재 위치를 확인하고 있습니다.';
  navigator.geolocation.getCurrentPosition(
    (position) => {
      const { latitude, longitude, accuracy } = position.coords;
      if (!isReliableKoreaLocation(latitude, longitude, accuracy)) {
        locationMessage.value = '위치 정확도가 낮아 이동하지 않았습니다. 브라우저 위치 권한과 OS 위치 서비스를 확인한 뒤 다시 눌러주세요.';
        return;
      }
      const latLng = new window.kakao.maps.LatLng(latitude, longitude);
      userLocationMarker.value?.setMap(null);
      userLocationMarker.value = new window.kakao.maps.Marker({
        map: map.value,
        position: latLng,
        title: '현재 위치',
      });
      map.value.panTo(latLng);
      map.value.setLevel(4);
      locationMessage.value = accuracy ? `현재 위치로 이동했습니다. 정확도 약 ${Math.round(accuracy)}m` : '현재 위치로 이동했습니다.';
    },
    () => {
      locationMessage.value = '현재 위치를 가져오지 못했습니다. 브라우저 위치 권한을 확인해주세요.';
    },
    { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 },
  );
}

function isReliableKoreaLocation(lat, lng, accuracy) {
  const inKorea = lat >= 33 && lat <= 39 && lng >= 124 && lng <= 132;
  if (!inKorea)
    return false;
  if (accuracy && accuracy > 5000)
    return false;
  return true;
}

async function changeMode(nextMode) {
  mode.value = nextMode;
  selectedItem.value = null;
  routeMessage.value = '';
  clearRoute();
  if (nextMode === 'notice') {
    selectedItem.value = filteredNotices.value[0] ?? null;
  } else {
    await loadPlaces();
  }
  await nextTick();
  renderMarkers();
}

async function submitSearch() {
  if (mode.value === 'notice') {
    selectedItem.value = filteredNotices.value[0] ?? null;
    await nextTick();
    renderMarkers();
    return;
  }
  await loadPlaces();
  renderMarkers();
}

async function changePlaceSido() {
  placeSigungu.value = '';
  await submitSearch();
}

async function showRouteToSelected() {
  if (!selectedItem.value?.lat || !selectedItem.value?.lng || !map.value || !window.kakao?.maps)
    return;
  routeLoading.value = true;
  routeMessage.value = '';
  clearRoute();
  try {
    const response = await fetchPlaceRoute({ lat: selectedItem.value.lat, lng: selectedItem.value.lng });
    const drawn = drawRoute(response);
    routeMessage.value = response.message || (drawn ? '멀티캠퍼스 역삼에서 선택 위치까지의 경로를 지도에 표시했습니다.' : '실제 도로 경로를 표시할 수 없습니다.');
  } catch {
    routeMessage.value = '경로 정보를 불러오지 못했습니다.';
  } finally {
    routeLoading.value = false;
  }
}

function drawRoute(route) {
  if (route?.fallback)
    return false;
  const points = (route.polyline?.length ? route.polyline : [route.origin, route.destination])
    .filter((point) => point?.lat && point?.lng)
    .map((point) => new window.kakao.maps.LatLng(point.lat, point.lng));
  if (points.length < 2)
    return false;

  const bounds = new window.kakao.maps.LatLngBounds();
  points.forEach((point) => bounds.extend(point));
  routeLine.value = new window.kakao.maps.Polyline({
    map: map.value,
    path: points,
    strokeWeight: 6,
    strokeColor: '#10b981',
    strokeOpacity: 0.85,
    strokeStyle: 'solid',
  });
  routeMarkers.value = [
    new window.kakao.maps.Marker({ map: map.value, position: points[0], title: route.origin?.name || '멀티캠퍼스 역삼' }),
    new window.kakao.maps.Marker({ map: map.value, position: points[points.length - 1], title: selectedItem.value?.name || '목적지' }),
  ];
  map.value.setBounds(bounds, 64, 64, 64, 64);
  return true;
}

function clearRoute() {
  routeLine.value?.setMap(null);
  routeLine.value = null;
  routeMarkers.value.forEach((marker) => marker.setMap(null));
  routeMarkers.value = [];
}

watch([filteredNotices, noticeRegion, noticeSupplyType, noticeDataType], () => {
  if (mode.value !== 'notice')
    return;
  selectedItem.value = filteredNotices.value[0] ?? null;
  renderMarkers();
});

onMounted(async () => {
  window.__firsthomeMapRouteToSelected = () => {
    showRouteToSelected();
  };
  await loadNotices();
  try {
    await loadKakaoMapSdk();
    initializeMap();
  } catch {
    mapReady.value = false;
  }
});

onBeforeUnmount(() => {
  if (window.__firsthomeMapRouteToSelected)
    delete window.__firsthomeMapRouteToSelected;
  markers.value.forEach((marker) => marker.setMap(null));
  markers.value = [];
  userLocationMarker.value?.setMap(null);
  userLocationMarker.value = null;
  clearRoute();
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

      <div class="absolute left-4 top-4 z-10 w-[min(660px,calc(100%-2rem))] rounded-lg border border-white/10 bg-slate-950/95 p-3 shadow-2xl">
        <div class="flex flex-wrap gap-2">
          <button
            v-for="item in [{key:'notice',label:'청약'}, {key:'estate',label:'부동산'}, {key:'bank',label:'은행'}]"
            :key="item.key"
            type="button"
            class="h-10 rounded-lg px-4 text-sm font-black"
            :class="mode === item.key ? 'bg-emerald-400 text-slate-950' : 'bg-slate-800 text-slate-200'"
            @click="changeMode(item.key)"
          >
            {{ item.label }}
          </button>
          <button type="button" class="ml-auto flex h-10 w-10 items-center justify-center rounded-lg bg-slate-800 text-slate-200" @click="moveToCurrentLocation">
            <LocateFixed class="h-4 w-4" />
          </button>
        </div>

        <div class="mt-3 flex gap-2">
          <input
            v-model="searchTerm"
            class="h-10 min-w-0 flex-1 rounded-lg border border-white/10 bg-slate-900 px-3 text-sm font-bold text-white placeholder:text-slate-500"
            type="search"
            :placeholder="mode === 'notice' ? '청약명, 지역, 지구 검색' : `${modeLabel} 검색어 또는 지역`"
            @keydown.enter="submitSearch"
          />
          <button type="button" class="flex h-10 items-center gap-2 rounded-lg bg-emerald-500 px-4 text-sm font-black text-slate-950" @click="submitSearch">
            <Search class="h-4 w-4" /> 검색
          </button>
        </div>

        <div v-if="mode === 'notice'" class="mt-3 grid gap-2 sm:grid-cols-3">
          <select v-model="noticeRegion" class="h-9 rounded-lg border border-white/10 bg-slate-900 px-3 text-xs font-bold text-white" @change="submitSearch">
            <option value="">전체 지역</option>
            <option v-for="item in noticeRegions" :key="item" :value="item">{{ item }}</option>
          </select>
          <select v-model="noticeSupplyType" class="h-9 rounded-lg border border-white/10 bg-slate-900 px-3 text-xs font-bold text-white" @change="submitSearch">
            <option value="">전체 청약 유형</option>
            <option v-for="item in noticeSupplyTypes" :key="item" :value="item">{{ item }}</option>
          </select>
          <select v-model="noticeDataType" class="h-9 rounded-lg border border-white/10 bg-slate-900 px-3 text-xs font-bold text-white" @change="submitSearch">
            <option value="all">전체 데이터</option>
            <option value="real">실데이터</option>
            <option value="fixture">Fixture</option>
          </select>
        </div>

        <div v-if="mode !== 'notice'" class="mt-3 grid gap-2" :class="mode === 'bank' ? 'sm:grid-cols-3' : 'sm:grid-cols-2'">
          <select v-model="placeSido" class="h-9 rounded-lg border border-white/10 bg-slate-900 px-3 text-xs font-bold text-white" @change="changePlaceSido">
            <option value="">전체 시/도</option>
            <option v-for="item in placeSidoOptions" :key="item" :value="item">{{ item }}</option>
          </select>
          <select v-model="placeSigungu" class="h-9 rounded-lg border border-white/10 bg-slate-900 px-3 text-xs font-bold text-white" :disabled="!placeSido" @change="submitSearch">
            <option value="">전체 시/군/구</option>
            <option v-for="item in placeSigunguOptions" :key="item" :value="item">{{ item }}</option>
          </select>
          <select v-if="mode === 'bank'" v-model="bankBrand" class="h-9 rounded-lg border border-white/10 bg-slate-900 px-3 text-xs font-bold text-white" @change="submitSearch">
            <option v-for="item in bankBrandOptions" :key="item.value" :value="item.value">{{ item.label }}</option>
          </select>
        </div>

        <p v-if="locationMessage" class="mt-2 rounded-md bg-slate-900/80 px-3 py-2 text-xs font-bold text-slate-300">
          {{ locationMessage }}
        </p>
      </div>
    </section>

    <aside class="flex min-h-0 flex-col border-l border-white/10 bg-slate-950 p-4 text-white">
      <div class="shrink-0">
        <p class="inline-flex items-center gap-2 text-sm font-bold text-emerald-300">
          <MapPin class="h-4 w-4" /> {{ modeLabel }} 지도
        </p>
        <h1 class="mt-2 text-2xl font-black">{{ modeLabel }} 검색</h1>
        <p class="mt-2 text-sm text-slate-400">
          {{ mode === 'notice' ? `${currentItems.length}건의 공고를 지도에서 확인합니다.` : '지역명을 넣어 주변 은행과 부동산을 찾습니다.' }}
        </p>
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
            <p class="text-xs font-bold text-slate-400">접수 마감</p>
            <p class="font-black">{{ selectedItem.application_deadline }}</p>
          </div>
          <div class="rounded-lg bg-slate-900 p-3">
            <p class="text-xs font-bold text-slate-400">청약 유형</p>
            <p class="font-black">{{ selectedItem.supply_type || '확인 필요' }}</p>
          </div>
          <div class="rounded-lg bg-slate-900 p-3">
            <p class="text-xs font-bold text-slate-400">추천 점수</p>
            <p class="font-black">{{ selectedItem.total_score }}/{{ selectedItem.score_max }}</p>
          </div>
        </div>

        <p v-if="mode !== 'notice' && selectedItem.phone" class="mt-3 text-sm font-bold text-slate-300">{{ selectedItem.phone }}</p>
        <p v-if="mode !== 'notice' && selectedItem.distance" class="mt-1 text-xs font-bold text-emerald-300">멀티캠퍼스 역삼 기준 {{ selectedItem.distance }}m</p>

        <div class="mt-4 grid gap-2" :class="mode === 'notice' ? 'grid-cols-2' : 'grid-cols-1'">
          <RouterLink v-if="mode === 'notice'" :to="`/notices/${selectedItem.notice_id}`" class="rounded-lg bg-emerald-400 px-3 py-2 text-center text-sm font-black text-slate-950" @click="saveCurrentSelection(selectedItem.notice_id, selectedItem.best_option?.option_id)">
            공고 상세
          </RouterLink>
          <RouterLink v-if="mode === 'notice'" :to="`/funding/${selectedItem.notice_id}`" class="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-800 px-3 py-2 text-sm font-black text-white" @click="saveCurrentSelection(selectedItem.notice_id, selectedItem.best_option?.option_id)">
            <WalletCards class="h-4 w-4" /> 자금
          </RouterLink>
          <button type="button" class="inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-500 px-3 py-2 text-sm font-black text-slate-950" :class="mode === 'notice' ? 'col-span-2' : ''" :disabled="routeLoading" @click="showRouteToSelected">
            <Navigation class="h-4 w-4" /> {{ routeLoading ? '경로 확인 중' : '지도에 경로 표시' }}
          </button>
          <a v-if="mode !== 'notice' && selectedItem.place_url" :href="selectedItem.place_url" target="_blank" rel="noreferrer" class="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-800 px-3 py-2 text-sm font-black text-white">
            카카오맵 장소 보기 <ExternalLink class="h-4 w-4" />
          </a>
        </div>
        <p v-if="routeMessage" class="mt-3 rounded-lg bg-slate-900 p-3 text-xs font-bold text-slate-300">{{ routeMessage }}</p>
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
