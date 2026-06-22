<script setup>
import { computed, onMounted, ref } from 'vue';
import { fetchMarketAssets, fetchMarketSummary } from '../api/firsthome';

const today = new Date();
const twoYearsAgo = new Date(today);
twoYearsAgo.setFullYear(today.getFullYear() - 2);

const asset = ref('estate_apt_trade_avg');
const start = ref(twoYearsAgo.toISOString().slice(0, 10));
const end = ref(today.toISOString().slice(0, 10));
const rows = ref([]);
const summary = ref([]);
const latest = ref({});
const assetMeta = ref({ label: '부동산 거래', unit: '만원' });
const error = ref('');
const loading = ref(false);

const chartOptions = [
  { value: 'estate_apt_trade_avg', label: '부동산 거래' },
  { value: 'base_rate', label: '기준금리' },
  { value: 'usd_krw', label: '원/달러' },
  { value: 'kospi', label: 'KOSPI' },
  { value: 'kosdaq', label: 'KOSDAQ' },
  { value: 'gold', label: '금' },
  { value: 'silver', label: '은' },
];

const watchedAssets = ['usd_krw', 'jpy_krw', 'eur_krw', 'cnh_krw', 'kosdaq'];

const summaryByAsset = computed(() => Object.fromEntries(summary.value.map((card) => [card.asset, card])));
const estateCard = computed(() => summaryByAsset.value.estate_apt_trade_avg ?? emptyCard('estate_apt_trade_avg', '부동산 거래'));
const baseRateCard = computed(() => summaryByAsset.value.base_rate ?? emptyCard('base_rate', '기준금리'));
const usdCard = computed(() => summaryByAsset.value.usd_krw ?? emptyCard('usd_krw', '원/달러 환율'));
const kospiCard = computed(() => summaryByAsset.value.kospi ?? emptyCard('kospi', 'KOSPI'));
const metals = computed(() => [
  summaryByAsset.value.gold ?? emptyCard('gold', '금 가격'),
  summaryByAsset.value.silver ?? emptyCard('silver', '은 가격'),
]);
const exchangeCards = computed(() => [
  { label: 'USD', row: latest.value.usd_krw, fallback: usdCard.value },
  { label: 'JPY(100)', row: latest.value.jpy_krw },
  { label: 'EUR', row: latest.value.eur_krw },
  { label: 'CNH', row: latest.value.cnh_krw },
]);
const kosdaqLatest = computed(() => latest.value.kosdaq);

const points = computed(() => {
  if (!rows.value.length)
    return '';
  const values = rows.value.map((row) => Number(row.price || 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = Math.max(1, max - min);
  return rows.value.map((row, index) => {
    const x = rows.value.length === 1 ? 50 : (index / (rows.value.length - 1)) * 100;
    const y = 88 - ((Number(row.price || 0) - min) / span) * 74;
    return `${x},${y}`;
  }).join(' ');
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
    const [assetResponse, summaryResponse, ...latestResponses] = await Promise.all([
      fetchMarketAssets({ asset: asset.value, start: start.value, end: end.value }),
      fetchMarketSummary(),
      ...watchedAssets.map((item) => fetchMarketAssets({ asset: item })),
    ]);
    rows.value = assetResponse.items ?? [];
    assetMeta.value = {
      label: assetResponse.label ?? selectedAssetLabel(asset.value),
      unit: assetResponse.unit ?? '',
      detail: assetResponse.detail ?? '',
      source: assetResponse.source ?? '',
    };
    summary.value = summaryResponse.cards ?? [];
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

function emptyCard(assetName, label) {
  return { asset: assetName, label, value: '수집 필요', description: '데이터 수집 후 표시됩니다.', change_rate: 0 };
}

function formatValue(value, unit = '') {
  const numericValue = Number(value || 0);
  if (unit === '%')
    return `${numericValue.toFixed(2)}${unit}`;
  if (unit === 'USD/toz' || unit === 'pt')
    return `${numericValue.toLocaleString(undefined, { maximumFractionDigits: 2 })}${unit}`;
  return `${Math.round(numericValue).toLocaleString()}${unit}`;
}

function changeLabel(value) {
  const numericValue = Number(value || 0);
  if (!numericValue)
    return '변동 없음';
  return `${numericValue > 0 ? '+' : ''}${numericValue.toFixed(2)}%`;
}

onMounted(load);
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
            <h2 class="text-3xl font-black text-slate-950">{{ estateCard.value }}</h2>
            <p class="mt-2 text-sm leading-6 text-slate-500">{{ estateCard.description }}</p>
          </div>
          <button type="button" class="h-11 rounded-lg bg-blue-600 px-5 text-sm font-black text-white" @click="asset = 'estate_apt_trade_avg'; load()">
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
      </div>

      <aside class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-lg font-black text-slate-950">환율 상세</h2>
        <p class="mt-1 text-sm text-slate-500">수입 물가와 금리 환경을 함께 보기 위한 보조 지표입니다.</p>
        <div class="mt-4 grid gap-2">
          <div v-for="item in exchangeCards" :key="item.label" class="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
            <p class="text-sm font-bold text-slate-500">{{ item.label }}</p>
            <p class="text-base font-black text-slate-950">{{ item.row ? formatValue(item.row.price, item.row.unit) : item.fallback?.value ?? '수집 필요' }}</p>
          </div>
        </div>
        <div class="mt-4 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3">
          <div class="flex items-center justify-between gap-3">
            <p class="text-sm font-bold text-slate-500">KOSDAQ</p>
            <p class="text-base font-black text-slate-950">{{ kosdaqLatest ? formatValue(kosdaqLatest.price, kosdaqLatest.unit) : '수집 필요' }}</p>
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
          <input v-model="start" class="h-10 rounded-lg border border-slate-200 px-3 text-sm font-bold" type="date" />
          <input v-model="end" class="h-10 rounded-lg border border-slate-200 px-3 text-sm font-bold" type="date" />
          <button type="button" :disabled="loading" class="h-10 rounded-lg bg-blue-600 px-4 text-sm font-black text-white disabled:opacity-60" @click="load">
            {{ loading ? '조회 중' : '조회' }}
          </button>
        </div>
      </div>

      <p v-if="error" class="mt-4 rounded-lg bg-amber-50 p-3 text-sm font-bold text-amber-800">{{ error }}</p>
      <p v-else-if="assetMeta.detail && !rows.length" class="mt-4 rounded-lg bg-slate-50 p-3 text-sm font-bold text-slate-600">{{ assetMeta.detail }}</p>

      <div class="mt-5 aspect-[16/6] rounded-lg bg-slate-950 p-5">
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" class="h-full w-full">
          <line x1="0" y1="88" x2="100" y2="88" stroke="#334155" stroke-width="0.8" vector-effect="non-scaling-stroke" />
          <polyline v-if="points" :points="points" fill="none" stroke="#2dd4bf" stroke-width="2.5" vector-effect="non-scaling-stroke" />
          <circle v-if="rows.length === 1" cx="50" cy="50" r="2.5" fill="#2dd4bf" vector-effect="non-scaling-stroke" />
        </svg>
      </div>
      <div class="mt-4 grid gap-2 text-xs font-bold text-slate-500 sm:grid-cols-3">
        <span v-for="row in rows.slice(-3)" :key="row.date" class="rounded-md bg-slate-50 px-3 py-2">{{ row.date }} · {{ formatValue(row.price, row.unit || assetMeta.unit) }}</span>
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
        <button v-for="item in metals" :key="item.asset" type="button" class="rounded-lg border border-slate-200 bg-slate-50 p-4 text-left transition hover:bg-blue-50" @click="asset = item.asset; load()">
          <p class="text-sm font-bold text-slate-500">{{ item.label }}</p>
          <p class="mt-2 text-2xl font-black text-slate-950">{{ item.value }}</p>
          <p class="mt-1 text-xs text-slate-500">{{ item.description }}</p>
        </button>
      </div>
    </section>
  </div>
</template>
