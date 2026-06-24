<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { fetchMarketAssets, fetchMarketSummary } from '../api/firsthome';
import { formatMoney } from '../utils/format';

const asset = ref('estate_apt_trade_avg');
const start = ref('');
const end = ref('');
const rows = ref([]);
const summary = ref([]);
const latest = ref({});
const assetMeta = ref({ label: '부동산 거래', unit: '만원' });
const marketStats = ref([]);
const error = ref('');
const loading = ref(false);
const estateProvince = ref('');
const estateRegion = ref('');
const estateRegionOptions = ref([]);

const chartOptions = [
  { value: 'estate_apt_trade_avg', label: '부동산 거래' },
  { value: 'base_rate', label: '기준금리' },
  { value: 'usd_krw', label: '원/달러' },
  { value: 'kospi', label: 'KOSPI' },
  { value: 'kosdaq', label: 'KOSDAQ' },
  { value: 'gold', label: '금' },
  { value: 'silver', label: '은' },
];

const watchedAssets = ['usd_krw', 'jpy_krw', 'eur_krw', 'cnh_krw', 'gbp_krw', 'kosdaq'];
const estateProvinceLabels = {
  11: '서울',
  26: '부산',
  27: '대구',
  28: '인천',
  29: '광주',
  30: '대전',
  31: '울산',
  36: '세종',
  41: '경기',
  43: '충북',
  44: '충남',
  46: '전남',
  47: '경북',
  48: '경남',
  50: '제주',
  51: '강원',
  52: '전북',
};

const summaryByAsset = computed(() => Object.fromEntries(summary.value.map((card) => [card.asset, card])));
const statsByAsset = computed(() => Object.fromEntries(marketStats.value.map((card) => [card.asset, card])));
const estateCard = computed(() => summaryByAsset.value.estate_apt_trade_avg ?? emptyCard('estate_apt_trade_avg', '부동산 거래'));
const baseRateCard = computed(() => summaryByAsset.value.base_rate ?? emptyCard('base_rate', '기준금리'));
const usdCard = computed(() => summaryByAsset.value.usd_krw ?? emptyCard('usd_krw', '원/달러 환율'));
const kospiCard = computed(() => summaryByAsset.value.kospi ?? emptyCard('kospi', 'KOSPI'));
const exchangeCards = computed(() => [
  { label: 'USD', row: latest.value.usd_krw, fallback: usdCard.value },
  { label: 'JPY(100)', row: latest.value.jpy_krw },
  { label: 'EUR', row: latest.value.eur_krw },
  { label: 'CNH', row: latest.value.cnh_krw },
  { label: 'GBP', row: latest.value.gbp_krw },
]);
const kosdaqLatest = computed(() => latest.value.kosdaq);
const metals = computed(() => [
  {
    asset: 'gold',
    label: '금 가격',
    value: summaryByAsset.value.gold?.value ?? '수집 필요',
    description: summaryByAsset.value.gold?.description ?? 'KRX 금시장 기준',
  },
  {
    asset: 'silver',
    label: '은 가격',
    value: summaryByAsset.value.silver?.value ?? '수집 필요',
    description: summaryByAsset.value.silver?.description ?? 'Metals.dev 현물 기준',
  },
]);
const estatePriceManwon = computed(() => parseLocalizedNumber(estateCard.value.value));
const estateDisplayValue = computed(() => estatePriceManwon.value ? formatMoney(estatePriceManwon.value * 10000) : estateCard.value.value);
const estimatedDeposit = computed(() => Math.round(estatePriceManwon.value * 0.1));
const monthlySavingTarget = computed(() => Math.round(estimatedDeposit.value / 24));
const indexCards = computed(() => [
  {
    asset: 'kospi',
    label: 'KOSPI',
    value: kospiCard.value.value,
    caption: `전일 대비 ${changeLabel(kospiCard.value.change_rate)}`,
  },
  {
    asset: 'kosdaq',
    label: 'KOSDAQ',
    value: kosdaqLatest.value ? formatValue(kosdaqLatest.value.price, kosdaqLatest.value.unit) : '수집 필요',
    caption: kosdaqLatest.value ? `전일 대비 ${changeLabel(kosdaqLatest.value.change_rate)}` : '데이터 수집 후 표시됩니다.',
  },
]);
const estateRegionGroups = computed(() => {
  const groups = new Map();
  for (const option of estateRegionOptions.value) {
    const code = String(option.code || '');
    if (!code)
      continue;
    const prefix = code.slice(0, 2);
    const label = estateProvinceLabels[prefix] || option.name.split(' ')[0] || prefix;
    if (!groups.has(prefix)) {
      groups.set(prefix, { label, prefix, districts: [] });
    }
    groups.get(prefix).districts.push({
      code,
      name: districtLabel(option.name, label),
    });
  }
  return [...groups.values()]
    .map((group) => ({
      ...group,
      districts: group.districts.sort((a, b) => a.name.localeCompare(b.name, 'ko')),
    }))
    .sort((a, b) => a.label.localeCompare(b.label, 'ko'));
});
const selectedEstateGroup = computed(() => estateRegionGroups.value.find((group) => group.prefix === estateProvince.value));
const estateDistricts = computed(() => selectedEstateGroup.value?.districts ?? []);
const isEstateAsset = computed(() => asset.value === 'estate_apt_trade_avg');
const uniqueValueCount = computed(() => new Set(rows.value.map((row) => Number(row.price || 0))).size);
const hasTrend = computed(() => rows.value.length >= 2 && uniqueValueCount.value >= 2);
const isFlatTrend = computed(() => rows.value.length >= 2 && uniqueValueCount.value === 1);
const chartStatus = computed(() => {
  if (!rows.value.length) return '수집된 데이터가 없습니다.';
  if (rows.value.length === 1) return '현재 선택 조건은 관측값 1건만 있어 추세선 대신 최신값을 강조합니다.';
  if (isFlatTrend.value) return '선택 기간 동안 값이 변하지 않아 수평선으로 표시됩니다.';
  return `${rows.value.length}개 관측값으로 추세를 표시합니다.`;
});
const decisionCards = computed(() => {
  return [
    { label: '예상 계약금', value: estimatedDeposit.value ? formatMoney(estimatedDeposit.value * 10000) : '계산 필요', caption: '평균 실거래가 10% 기준' },
    { label: '월 저축 기준', value: monthlySavingTarget.value ? formatMoney(monthlySavingTarget.value * 10000) : '계산 필요', caption: '24개월 분할 준비 기준' },
    { label: '원/달러', value: usdCard.value.value, caption: '수입 물가와 금리 부담 신호' },
    { label: 'KOSDAQ', value: kosdaqLatest.value ? formatValue(kosdaqLatest.value.price, kosdaqLatest.value.unit) : '수집 필요', caption: kosdaqLatest.value ? `전일 대비 ${changeLabel(kosdaqLatest.value.change_rate)}` : '보조 시장 심리 지표' },
  ];
});

const chartValues = computed(() => rows.value.map((row) => Number(row.price || 0)));
const chartMin = computed(() => chartValues.value.length ? Math.min(...chartValues.value) : 0);
const chartMax = computed(() => chartValues.value.length ? Math.max(...chartValues.value) : 0);
const chartRange = computed(() => Math.max(1, chartMax.value - chartMin.value));
const chartPadding = computed(() => Math.max(chartRange.value * 0.18, Math.abs(chartMax.value || 1) * 0.015));
const chartMinBound = computed(() => Math.max(0, chartMin.value - chartPadding.value));
const chartMaxBound = computed(() => chartMax.value + chartPadding.value);
const chartMid = computed(() => chartValues.value.length ? (chartMinBound.value + chartMaxBound.value) / 2 : 0);
const points = computed(() => {
  if (!rows.value.length)
    return '';
  return rows.value.map((row, index) => {
    const { x, y } = pointForRow(row, index);
    return `${x},${y}`;
  }).join(' ');
});
const highPoint = computed(() => extremumPoint('max'));
const lowPoint = computed(() => extremumPoint('min'));
const latestPoint = computed(() => {
  if (!latestRow.value || !rows.value.length) return null;
  return {
    ...pointForRow(latestRow.value, rows.value.length - 1),
    row: latestRow.value,
    value: formatValue(latestRow.value.price, latestRow.value.unit || assetMeta.value.unit),
  };
});
const yAxisTicks = computed(() => [
  { label: formatValue(chartMaxBound.value, assetMeta.value.unit), position: 8 },
  { label: formatValue(chartMid.value, assetMeta.value.unit), position: 50 },
  { label: formatValue(chartMinBound.value, assetMeta.value.unit), position: 92 },
]);
const xAxisTicks = computed(() => {
  if (!rows.value.length) return [];
  const middleIndex = Math.floor((rows.value.length - 1) / 2);
  return [
    { label: formatShortDate(rows.value[0].date), position: 0 },
    { label: formatShortDate(rows.value[middleIndex].date), position: 50 },
    { label: formatShortDate(rows.value.at(-1).date), position: 100 },
  ];
});

const latestRow = computed(() => rows.value.at(-1));
const latestValue = computed(() => latestRow.value ? formatValue(latestRow.value.price, assetMeta.value.unit) : '수집 필요');

async function load() {
  if (start.value && end.value && start.value > end.value) {
    error.value = '시작일은 종료일보다 늦을 수 없습니다.';
    rows.value = [];
    return;
  }
  loading.value = true;
  error.value = '';
  try {
    const assetParams = { asset: asset.value, start: start.value, end: end.value };
    if (isEstateAsset.value) {
      if (estateRegion.value) {
        assetParams.region = estateRegion.value;
      } else if (estateProvince.value) {
        assetParams.region_prefix = estateProvince.value;
      }
    }
    const [assetResponse, summaryResponse, ...latestResponses] = await Promise.all([
      fetchMarketAssets(assetParams),
      fetchMarketSummary(),
      ...watchedAssets.map((item) => fetchMarketAssets({ asset: item })),
    ]);
    if (Array.isArray(assetResponse.regions)) {
      estateRegionOptions.value = assetResponse.regions;
    }
    rows.value = assetResponse.items ?? [];
    syncDateRangeToRows();
    assetMeta.value = {
      label: assetResponse.label ?? selectedAssetLabel(asset.value),
      unit: assetResponse.unit ?? '',
      detail: assetResponse.detail ?? '',
      source: assetResponse.source ?? '',
    };
    summary.value = summaryResponse.cards ?? [];
    marketStats.value = summaryResponse.stats ?? [];
    latest.value = Object.fromEntries(watchedAssets.map((item, index) => [item, latestResponses[index]?.items?.at(-1) ?? null]));
  } catch (event) {
    error.value = event?.response?.data?.detail ?? '시장 데이터를 불러오지 못했습니다.';
  } finally {
    loading.value = false;
  }
}

function selectedAssetLabel(value) {
  return chartOptions.find((item) => item.value === value)?.label ?? value;
}

function districtLabel(name, provinceLabel) {
  const text = String(name || '').trim();
  if (!text)
    return '지역';
  if (text.startsWith(`${provinceLabel} `))
    return text.slice(provinceLabel.length + 1).trim() || text;
  if (text.startsWith(provinceLabel))
    return text.slice(provinceLabel.length).trim() || text;
  return text;
}

function emptyCard(assetName, label) {
  return { asset: assetName, label, value: '수집 필요', description: '데이터 수집 후 표시됩니다.', change_rate: 0 };
}

function formatValue(value, unit = '') {
  const numericValue = Number(value || 0);
  if (unit === '%')
    return `${numericValue.toFixed(2)}${unit}`;
  if (unit === '만원')
    return formatMoney(numericValue * 10000);
  if (unit === 'USD/toz' || unit === 'pt')
    return `${numericValue.toLocaleString(undefined, { maximumFractionDigits: 2 })}${unit}`;
  return `${Math.round(numericValue).toLocaleString()}${unit}`;
}

function parseLocalizedNumber(value) {
  const match = String(value || '').replace(/,/g, '').match(/\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : 0;
}

function formatShortDate(value) {
  if (!value) return '';
  const [year, month, day] = value.split('-');
  return `${year.slice(2)}.${month}.${day}`;
}

function changeLabel(value) {
  const numericValue = Number(value || 0);
  if (!numericValue)
    return '변동 없음';
  return `${numericValue > 0 ? '+' : ''}${numericValue.toFixed(2)}%`;
}

function pointForRow(row, index) {
  const span = Math.max(1, chartMaxBound.value - chartMinBound.value);
  return {
    x: rows.value.length === 1 ? 50 : (index / (rows.value.length - 1)) * 100,
    y: uniqueValueCount.value === 1 ? 50 : 92 - ((Number(row.price || 0) - chartMinBound.value) / span) * 84,
  };
}

function chartDotStyle(point) {
  if (!point) return {};
  return {
    left: `${point.x}%`,
    top: `${point.y}%`,
    transform: 'translate(-50%, -50%)',
  };
}

function chartBadgeStyle(point, side = 'above') {
  if (!point) return {};
  const top = badgeTop(point, side);
  return {
    left: `${badgeLeft(point)}%`,
    top: `${top}%`,
    transform: 'translate(-50%, -50%)',
  };
}

function chartConnector(point, side = 'above') {
  if (!point) return {};
  return {
    x: badgeLeft(point),
    y: badgeTop(point, side),
  };
}

function badgeLeft(point) {
  return Math.min(86, Math.max(14, point.x));
}

function badgeTop(point, side) {
  const offset = side === 'above' ? -18 : 18;
  return Math.min(88, Math.max(8, point.y + offset));
}

function latestValueBadgeStyle(point) {
  if (!point) return {};
  const shouldPlaceBelow = point.y < 18;
  const offset = shouldPlaceBelow ? 10 : -10;
  return {
    left: '1rem',
    top: `${Math.min(88, Math.max(12, point.y + offset))}%`,
    transform: 'translateY(-50%)',
  };
}

function extremumPoint(type) {
  if (!rows.value.length) return null;
  const target = type === 'max' ? chartMax.value : chartMin.value;
  const index = rows.value.findIndex((row) => Number(row.price || 0) === target);
  if (index < 0) return null;
  const row = rows.value[index];
  return {
    ...pointForRow(row, index),
    row,
    value: formatValue(row.price, row.unit || assetMeta.value.unit),
    label: type === 'max' ? '최고' : '최저',
  };
}

function syncDateRangeToRows() {
  if (!rows.value.length) return;
  start.value = rows.value[0].date;
  end.value = rows.value.at(-1).date;
}

function applyKnownRange(assetName = asset.value) {
  const stat = statsByAsset.value[assetName];
  if (!stat?.first || !stat?.last) return;
  start.value = stat.first;
  end.value = stat.last;
}

function selectAsset(assetName) {
  asset.value = assetName;
  applyKnownRange(assetName);
  load();
}

onMounted(load);

watch(asset, (nextAsset) => {
  applyKnownRange(nextAsset);
});

watch(estateProvince, () => {
  estateRegion.value = '';
});
</script>

<template>
  <div class="space-y-5">
    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <p class="text-sm font-bold text-blue-700">청약 시장 지표</p>
      <h1 class="mt-1 text-3xl font-black text-slate-950">경제 NOW</h1>
      <p class="mt-2 text-sm leading-6 text-slate-500">청약 판단에 직접 닿는 부동산 거래, 금리, 환율, 국내 지수를 먼저 확인합니다.</p>
    </section>

    <section class="grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.75fr)]">
      <div class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <p class="text-sm font-bold text-blue-700">주거 시장 핵심</p>
        <div class="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 class="text-3xl font-black text-slate-950">{{ estateDisplayValue }}</h2>
            <p class="mt-2 text-sm leading-6 text-slate-500">{{ estateCard.description }}</p>
          </div>
          <button type="button" class="h-11 rounded-lg bg-blue-600 px-5 text-sm font-black text-white" @click="selectAsset('estate_apt_trade_avg')">
            거래 추이 보기
          </button>
        </div>
        <div class="mt-5 grid gap-3 sm:grid-cols-3">
          <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold text-slate-500">기준금리</p>
            <p class="mt-2 text-xl font-black text-slate-950">{{ baseRateCard.value }}</p>
            <p class="mt-1 text-xs text-slate-500">{{ baseRateCard.description }}</p>
          </div>
          <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold text-slate-500">원/달러</p>
            <p class="mt-2 text-xl font-black text-slate-950">{{ usdCard.value }}</p>
            <p class="mt-1 text-xs text-slate-500">{{ usdCard.description }}</p>
          </div>
          <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-bold text-slate-500">KOSPI</p>
            <p class="mt-2 text-xl font-black text-slate-950">{{ kospiCard.value }}</p>
            <p class="mt-1 text-xs text-slate-500">{{ changeLabel(kospiCard.change_rate) }}</p>
          </div>
        </div>
        <div class="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div v-for="item in decisionCards" :key="item.label" class="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
            <p class="text-xs font-bold text-slate-500">{{ item.label }}</p>
            <p class="mt-1 text-lg font-black text-slate-950">{{ item.value }}</p>
            <p class="mt-1 truncate text-xs font-semibold text-slate-500">{{ item.caption }}</p>
          </div>
        </div>
      </div>

      <aside class="flex h-full flex-col rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-lg font-black text-slate-950">환율 상세</h2>
        <p class="mt-1 text-sm text-slate-500">수입 물가와 금리 환경을 함께 보기 위한 보조 지표입니다.</p>
        <div class="mt-4 grid flex-1 grid-rows-5 gap-2">
          <div v-for="item in exchangeCards" :key="item.label" class="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4">
            <p class="text-sm font-bold text-slate-500">{{ item.label }}</p>
            <p class="text-base font-black text-slate-950">{{ item.row ? formatValue(item.row.price, item.row.unit) : item.fallback?.value ?? '수집 필요' }}</p>
          </div>
        </div>
      </aside>
    </section>

    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h2 class="text-lg font-black text-slate-950">{{ assetMeta.label }} 추이</h2>
          <p class="mt-1 text-sm text-slate-500">운영자가 수집한 DB 기준입니다. 최신값은 {{ latestValue }}입니다.</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <select v-model="asset" class="h-10 rounded-lg border border-slate-200 px-3 text-sm font-bold">
            <option v-for="option in chartOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
          </select>
          <select v-if="isEstateAsset" v-model="estateProvince" class="h-10 rounded-lg border border-slate-200 px-3 text-sm font-bold">
            <option value="">전국</option>
            <option v-for="group in estateRegionGroups" :key="group.prefix" :value="group.prefix">{{ group.label }}</option>
          </select>
          <select v-if="isEstateAsset && estateDistricts.length > 1" v-model="estateRegion" class="h-10 rounded-lg border border-slate-200 px-3 text-sm font-bold" :disabled="!estateProvince">
            <option value="">전체 시군구</option>
            <option v-for="district in estateDistricts" :key="district.code" :value="district.code">{{ district.name }}</option>
          </select>
          <input v-model="start" class="h-10 rounded-lg border border-slate-200 px-3 text-sm font-bold" type="date" />
          <input v-model="end" class="h-10 rounded-lg border border-slate-200 px-3 text-sm font-bold" type="date" />
          <button type="button" :disabled="loading" class="h-10 rounded-lg bg-blue-600 px-4 text-sm font-black text-white disabled:opacity-60" @click="load">
            {{ loading ? '조회 중' : '조회' }}
          </button>
        </div>
      </div>

      <p v-if="error" class="mt-4 rounded-lg bg-amber-50 p-3 text-sm font-bold text-amber-800">{{ error }}</p>
      <p v-else-if="assetMeta.detail && !rows.length" class="mt-4 rounded-lg bg-slate-50 p-3 text-sm font-bold text-slate-600">{{ assetMeta.detail }}</p>

      <div class="mt-5 rounded-lg bg-slate-950 p-5">
        <div v-if="rows.length" class="grid h-[420px] grid-cols-[112px_minmax(0,1fr)] grid-rows-[minmax(0,1fr)_34px] gap-x-3">
          <div class="flex flex-col justify-between py-2 text-right text-xs font-bold text-slate-400">
            <span v-for="tick in yAxisTicks" :key="tick.position">{{ tick.label }}</span>
          </div>
          <div class="relative min-w-0">
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" class="h-full w-full overflow-visible">
              <line x1="0" y1="92" x2="100" y2="92" stroke="#334155" stroke-width="0.8" vector-effect="non-scaling-stroke" />
              <line x1="0" y1="50" x2="100" y2="50" stroke="#1e293b" stroke-width="0.6" stroke-dasharray="3 3" vector-effect="non-scaling-stroke" />
              <line x1="0" y1="8" x2="100" y2="8" stroke="#1e293b" stroke-width="0.6" stroke-dasharray="3 3" vector-effect="non-scaling-stroke" />
              <line
                v-if="latestPoint"
                x1="0"
                :x2="latestPoint.x"
                :y1="latestPoint.y"
                :y2="latestPoint.y"
                stroke="#fb7185"
                stroke-width="1"
                stroke-dasharray="2 5"
                vector-effect="non-scaling-stroke"
              />
              <polyline v-if="points" :points="points" fill="none" stroke="#2dd4bf" stroke-width="2.5" vector-effect="non-scaling-stroke" />
              <line
                v-if="highPoint"
                :x1="highPoint.x"
                :y1="highPoint.y"
                :x2="chartConnector(highPoint, 'above').x"
                :y2="chartConnector(highPoint, 'above').y"
                stroke="#38bdf8"
                stroke-width="1"
                vector-effect="non-scaling-stroke"
              />
              <line
                v-if="lowPoint"
                :x1="lowPoint.x"
                :y1="lowPoint.y"
                :x2="chartConnector(lowPoint, 'below').x"
                :y2="chartConnector(lowPoint, 'below').y"
                stroke="#f59e0b"
                stroke-width="1"
                vector-effect="non-scaling-stroke"
              />
            </svg>
            <span
              v-if="highPoint"
              class="pointer-events-none absolute h-2 w-2 rounded-full bg-sky-300 shadow-[0_0_0_3px_rgba(15,23,42,0.9),0_0_12px_rgba(56,189,248,0.55)]"
              :style="chartDotStyle(highPoint)"
            ></span>
            <span
              v-if="lowPoint"
              class="pointer-events-none absolute h-2 w-2 rounded-full bg-amber-300 shadow-[0_0_0_3px_rgba(15,23,42,0.9),0_0_12px_rgba(245,158,11,0.5)]"
              :style="chartDotStyle(lowPoint)"
            ></span>
            <span
              v-if="latestPoint"
              class="economy-current-dot pointer-events-none absolute h-2.5 w-2.5 rounded-full"
              :style="chartDotStyle(latestPoint)"
            ></span>
            <div
              v-if="highPoint"
              class="pointer-events-none absolute z-20 whitespace-nowrap rounded-full border border-sky-300/40 bg-slate-950/95 px-3 py-1.5 text-xs font-black text-sky-100 shadow-lg shadow-sky-950/30"
              :style="chartBadgeStyle(highPoint, 'above')"
            >
              <span class="mr-1 inline-block h-2 w-2 rounded-full bg-sky-300"></span>
              최고 {{ highPoint.value }}
            </div>
            <div
              v-if="lowPoint"
              class="pointer-events-none absolute z-20 whitespace-nowrap rounded-full border border-amber-300/40 bg-slate-950/95 px-3 py-1.5 text-xs font-black text-amber-100 shadow-lg shadow-amber-950/30"
              :style="chartBadgeStyle(lowPoint, 'below')"
            >
              <span class="mr-1 inline-block h-2 w-2 rounded-full bg-amber-300"></span>
              최저 {{ lowPoint.value }}
            </div>
            <div
              v-if="latestPoint"
              class="economy-current-badge pointer-events-none absolute z-10 rounded-md px-2.5 py-1 text-xs font-black leading-tight"
              :style="latestValueBadgeStyle(latestPoint)"
            >
              <span class="economy-current-badge-label block">현재</span>
              <span class="economy-current-badge-value block">{{ latestPoint.value }}</span>
            </div>
            <div v-if="!hasTrend" class="absolute inset-x-4 top-4 max-w-xl rounded-lg border border-slate-700 bg-slate-900/90 p-4">
              <p class="text-sm font-black text-white">{{ chartStatus }}</p>
              <p class="mt-2 text-sm font-semibold text-slate-300">
                최신값 {{ latestValue }} · {{ rows.length }}건 · {{ assetMeta.source || 'database' }}
              </p>
            </div>
          </div>
          <div></div>
          <div class="relative text-xs font-bold text-slate-400">
            <span
              v-for="tick in xAxisTicks"
              :key="`${tick.position}-${tick.label}`"
              class="absolute top-2"
              :style="{ left: `${tick.position}%`, transform: tick.position === 0 ? 'translateX(0)' : tick.position === 100 ? 'translateX(-100%)' : 'translateX(-50%)' }"
            >
              {{ tick.label }}
            </span>
          </div>
        </div>
        <div v-else class="flex h-[420px] items-center justify-center rounded-lg border border-slate-800 bg-slate-950 text-center">
          <div class="max-w-md">
            <p class="text-base font-black text-white">선택한 조건의 수집 데이터가 없습니다.</p>
            <p class="mt-2 text-sm font-semibold text-slate-400">
              부동산 거래는 현재 수집된 지역만 필터에 표시되며, 추가 지역은 수집 후 그래프로 확인할 수 있습니다.
            </p>
          </div>
        </div>
        <div class="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800 pt-3 text-xs font-bold text-slate-400">
          <span>{{ chartStatus }}</span>
          <div class="flex flex-wrap items-center gap-2">
            <span>기간 {{ start || '-' }} ~ {{ end || '-' }}</span>
          </div>
        </div>
      </div>
    </section>

    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div class="flex items-center justify-between gap-3">
        <div>
          <h2 class="text-lg font-black text-slate-950">보조 원자재 지표</h2>
          <p class="mt-1 text-sm text-slate-500">금과 은은 청약 판단의 주 지표가 아니므로 참고값으로만 표시합니다.</p>
        </div>
      </div>
      <div class="mt-4 grid gap-3 md:grid-cols-2">
        <button v-for="item in metals" :key="item.asset" type="button" class="rounded-lg border border-slate-200 bg-slate-50 p-4 text-left transition hover:bg-blue-50" @click="selectAsset(item.asset)">
          <p class="text-sm font-bold text-slate-500">{{ item.label }}</p>
          <p class="mt-2 text-2xl font-black text-slate-950">{{ item.value }}</p>
          <p class="mt-1 text-xs text-slate-500">{{ item.description }}</p>
        </button>
      </div>
    </section>
  </div>
</template>
