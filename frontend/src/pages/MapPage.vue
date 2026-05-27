<script setup>
import { computed, onMounted, ref } from 'vue';
import { ChevronRight, FileSearch, ListChecks, MapPin } from 'lucide-vue-next';
import { fetchNotices } from '../api/firsthome';
import { analysisBadgeClass, analysisSummary } from '../utils/analysisStatus';
import { formatMoney } from '../utils/format';
const notices = ref([]);
const selectedRegion = ref('서울');
const loading = ref(true);
const error = ref('');
const regionCounts = computed(() => {
    return notices.value.reduce((acc, notice) => {
        const region = notice.region || '전국';
        acc[region] = (acc[region] ?? 0) + 1;
        return acc;
    }, {});
});
const markers = computed(() => [
    { region: '서울', x: 49, y: 37, count: regionCounts.value['서울'] ?? 0 },
    { region: '인천', x: 39, y: 39, count: regionCounts.value['인천'] ?? 0 },
    { region: '경기 남부', x: 53, y: 48, count: regionCounts.value['경기 남부'] ?? regionCounts.value['경기'] ?? 0 },
    { region: '경기 북부', x: 51, y: 28, count: regionCounts.value['경기 북부'] ?? 0 },
    { region: '부산', x: 76, y: 76, count: regionCounts.value['부산'] ?? 0 },
]);
const selectedNotices = computed(() => {
    return notices.value.filter((notice) => notice.region === selectedRegion.value);
});
const analyzedCount = computed(() => {
    return selectedNotices.value.filter((notice) => ['verified', 'needs_review'].includes(analysisSummary(notice.analysis_summary, notice.official_document_status).stage)).length;
});
function priceLabel(price) {
    return price > 0 ? formatMoney(price) : '공고문 확인 필요';
}
async function loadNotices() {
    loading.value = true;
    error.value = '';
    try {
        notices.value = await fetchNotices({ ownership_type: 'public_sale' });
        const firstRegion = markers.value.find((marker) => marker.count > 0)?.region;
        if (firstRegion)
            selectedRegion.value = firstRegion;
    }
    catch {
        notices.value = [];
        error.value = '공고 목록을 불러오지 못했습니다. Django 서버가 실행 중인지 확인하세요.';
    }
    finally {
        loading.value = false;
    }
}
onMounted(loadNotices);
</script>

<template>
  <div class="grid min-h-[640px] gap-4 lg:grid-cols-[minmax(0,1fr)_380px]">
    <section class="relative min-h-[560px] overflow-hidden rounded-lg border border-slate-200 bg-slate-950 shadow-sm">
      <div class="absolute inset-0 bg-[linear-gradient(135deg,#0b1117,#152331)]" />

      <svg class="absolute inset-0 h-full w-full" viewBox="0 0 1000 720" preserveAspectRatio="none" aria-hidden="true">
        <path d="M116 118 C240 70 338 90 438 152 C532 210 640 206 760 154 C862 110 940 126 990 180 L990 720 L0 720 L0 174 C28 148 68 132 116 118Z" fill="#162936" />
        <path d="M182 458 C270 344 384 294 498 330 C606 364 686 310 760 246 C838 178 924 190 1000 254 L1000 720 L114 720 C116 624 132 528 182 458Z" fill="#11242f" />
        <path d="M0 252 C118 226 230 254 324 340 C418 426 520 434 638 372 C770 304 884 324 1000 408" fill="none" stroke="#30515d" stroke-width="22" stroke-linecap="round" opacity="0.55" />
        <path d="M82 612 C214 520 308 482 422 502 C542 522 628 474 720 372 C794 290 874 248 1000 230" fill="none" stroke="#254653" stroke-width="12" stroke-linecap="round" opacity="0.7" />
        <path d="M192 80 C232 196 280 304 380 390 C488 484 560 564 612 720" fill="none" stroke="#3ee0b8" stroke-width="7" stroke-linecap="round" opacity="0.56" />
        <path d="M514 0 C500 114 506 232 558 330 C610 428 702 506 830 604" fill="none" stroke="#f5c86a" stroke-width="6" stroke-linecap="round" opacity="0.42" />
        <path d="M0 404 C118 388 224 394 310 430 C404 470 490 470 594 430 C734 376 850 380 1000 446" fill="none" stroke="#6f8090" stroke-width="5" stroke-dasharray="12 18" opacity="0.4" />
      </svg>

      <div class="absolute left-5 top-5 rounded-lg border border-white/10 bg-slate-950/80 px-4 py-3 text-white shadow-lg backdrop-blur">
        <p class="text-xs font-semibold text-emerald-200">소유형 공공분양 지도</p>
        <p class="mt-1 text-2xl font-bold">{{ notices.length }}건</p>
      </div>

      <div class="absolute inset-0">
        <button
          v-for="marker in markers"
          :key="marker.region"
          type="button"
          class="absolute -translate-x-1/2 -translate-y-1/2 rounded-lg border px-3 py-2 text-left text-white shadow-lg backdrop-blur transition"
          :class="selectedRegion === marker.region ? 'border-emerald-300 bg-blue-600' : 'border-white/15 bg-slate-950/85 hover:bg-blue-600'"
          :style="{ left: `${marker.x}%`, top: `${marker.y}%` }"
          @click="selectedRegion = marker.region"
        >
          <span class="flex items-center gap-2 text-sm font-bold">
            <MapPin class="h-4 w-4 text-emerald-300" />
            {{ marker.region }}
          </span>
          <span class="mt-1 block text-xs text-slate-200">{{ marker.count }}건</span>
        </button>
      </div>
    </section>

    <aside class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div class="flex items-start justify-between gap-3">
        <div>
          <p class="inline-flex items-center gap-2 text-sm font-semibold text-blue-700">
            <ListChecks class="h-4 w-4" />
            지역별 소유형 공고
          </p>
          <h1 class="mt-1 text-2xl font-bold text-slate-950">{{ selectedRegion }}</h1>
        </div>
        <span class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">
          분석 완료 {{ analyzedCount }}건
        </span>
      </div>

      <p class="mt-2 text-sm text-slate-500">
        지도 숫자는 임대형 공고를 제외한 소유형 공공분양만 계산하며, 상세 화면에서 주택형 옵션과 공식 분석 상태를 이어서 확인합니다.
      </p>

      <div v-if="loading" class="mt-5 rounded-lg bg-slate-50 p-4 text-sm font-semibold text-slate-600">
        공고를 불러오는 중입니다.
      </div>
      <div v-else-if="error" class="mt-5 rounded-lg border border-amber-100 bg-amber-50 p-4 text-sm font-semibold text-amber-800">
        {{ error }}
      </div>
      <div v-else-if="selectedNotices.length === 0" class="mt-5 rounded-lg bg-slate-50 p-4 text-sm font-semibold text-slate-600">
        이 지역에는 현재 노출 가능한 소유형 공공분양 공고가 없습니다.
      </div>

      <div v-else class="mt-5 space-y-3">
        <article v-for="notice in selectedNotices" :key="notice.id" class="rounded-lg border border-slate-200 p-4">
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="text-xs font-bold text-blue-700">{{ notice.supply_type }}</p>
              <h2 class="mt-1 text-sm font-bold leading-5 text-slate-950">{{ notice.title }}</h2>
            </div>
            <span class="shrink-0 rounded-md px-2 py-1 text-xs font-bold" :class="analysisBadgeClass(analysisSummary(notice.analysis_summary, notice.official_document_status))">
              {{ analysisSummary(notice.analysis_summary, notice.official_document_status).label }}
            </span>
          </div>
          <div class="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-500">
            <span>{{ notice.district }}</span>
            <span class="text-right">{{ notice.area || '면적 확인 필요' }}</span>
            <span>접수 마감 {{ notice.application_deadline }}</span>
            <span class="text-right font-bold text-slate-700">{{ priceLabel(notice.price) }}</span>
            <span>주택형 옵션 {{ notice.unit_option_count ?? 0 }}개</span>
            <span class="text-right">문서 {{ notice.document_count ?? 0 }}건</span>
          </div>
          <p class="mt-2 text-xs leading-5 text-slate-500">
            {{ analysisSummary(notice.analysis_summary, notice.official_document_status).next_action }}
          </p>
          <RouterLink
            :to="`/notices/${notice.id}`"
            class="mt-3 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-bold text-white transition hover:bg-blue-700"
          >
            옵션 보기
            <ChevronRight class="h-4 w-4" />
          </RouterLink>
        </article>
      </div>

      <div class="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4 text-xs leading-5 text-slate-600">
        <p class="flex items-center gap-2 font-bold text-slate-800">
          <FileSearch class="h-4 w-4" />
          PDF 분석 상태
        </p>
        <p class="mt-1">
          지도는 지역 탐색용입니다. 공식 공고문 분석, 주택형 옵션, 계약금 부족액은 상세와 자금 화면에서 확인합니다.
        </p>
      </div>
    </aside>
  </div>
</template>
