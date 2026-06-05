<script setup>
import { computed, onMounted, ref } from 'vue';
import { ArrowDown, ArrowUpDown, Bookmark, CalendarDays, ChevronRight, Clock3, ExternalLink, MapPin, Sparkles } from 'lucide-vue-next';
import { addFavorite, fetchFavorites, fetchHousingRecommendations, removeFavorite } from '../api/firsthome';
import { analysisBadgeClass, analysisSummary } from '../utils/analysisStatus';
import { formatMoney } from '../utils/format';
import { saveCurrentSelection } from '../utils/selectionState';
import { useProfileStore } from '../stores/profileStore';

const profileStore = useProfileStore();
const recommendations = ref([]);
const favorites = ref([]);
const loading = ref(true);
const savingFavoriteKey = ref('');
const error = ref('');
const sortMode = ref('score');

const sortOptions = [
    { value: 'score', label: '점수순' },
    { value: 'deadline', label: '마감 임박순' },
    { value: 'price_low', label: '분양가 낮은순' },
    { value: 'contract_low', label: '계약금 낮은순' },
    { value: 'shortfall_low', label: '부족액 낮은순' },
];

function priceLabel(price) {
    return Number(price || 0) > 0 ? formatMoney(price) : '공식 확인 필요';
}

function ownershipTypeLabel(type) {
    const labels = {
        public_sale: '공공분양',
        private_participation_public_sale: '민간참여 공공분양',
        newlywed_public_sale: '신혼희망타운 공공분양',
        unknown: '유형 확인 필요',
    };
    return labels[type] ?? type ?? '공공분양';
}

function isFixtureNotice(item) {
    const source = String(item?.data_source || '').toLowerCase();
    return source.includes('fixture') || Boolean(item?.source_meta?.fixture_id);
}

function favoriteKey(noticeId) {
    return `notice-${noticeId}`;
}

function isFavorite(noticeId) {
    return favorites.value.some((favorite) => favorite.favorite_type === 'notice' && favorite.object_id === noticeId);
}

function recommendationOptions(item) {
    if (item.top_options?.length)
        return item.top_options;
    return item.best_option ? [item.best_option] : [];
}

function defaultRecommendationOption(item) {
    const options = recommendationOptions(item);
    return options.find((option) => option.option_type === 'general_supply') ?? options.find((option) => option.option_type === 'basic') ?? item.best_option ?? options[0] ?? null;
}

function representativePrice(item) {
    return Number(defaultRecommendationOption(item)?.base_price || item.price || 0);
}

function detailRoute(item) {
    const option = defaultRecommendationOption(item);
    return { path: `/notices/${item.notice_id}`, query: option?.option_id ? { option_id: option.option_id } : {} };
}

function scorePercent(item) {
    const max = item.score_max || 100;
    return Math.min(100, Math.round(((item.total_score || 0) / max) * 100));
}

function optionInsightRows(option) {
    const insights = option.funding_insights || {};
    const rows = [];
    if (Number(insights.down_payment_shortfall || 0) > 0) {
        rows.push(`계약금 부족 ${formatMoney(insights.down_payment_shortfall)}`);
    }
    else if (Number(insights.down_payment || 0) > 0) {
        rows.push(`계약금 ${formatMoney(insights.down_payment)}`);
    }
    if (Number(insights.down_payment_monthly_target || 0) > 0) {
        rows.push(`월 ${formatMoney(insights.down_payment_monthly_target)} 준비`);
    }
    if (Number(insights.loan_amount || 0) > 0) {
        rows.push(`융자금 ${formatMoney(insights.loan_amount)}`);
    }
    return rows.slice(0, 3);
}

function optionDownPayment(item) {
    const option = defaultRecommendationOption(item);
    return Number(option?.down_payment || option?.funding_insights?.down_payment || 0);
}

function optionShortfall(item) {
    const option = defaultRecommendationOption(item);
    return Number(option?.funding_insights?.down_payment_shortfall || 0);
}

function deadlineValue(item) {
    const value = Date.parse(item.application_deadline || '');
    return Number.isFinite(value) ? value : Number.MAX_SAFE_INTEGER;
}

function sortLabel() {
    return sortOptions.find((option) => option.value === sortMode.value)?.label ?? '점수순';
}

const sortedRecommendations = computed(() => {
    const rows = [...recommendations.value];
    const sorters = {
        score: (a, b) => (b.total_score - a.total_score) || (b.option_fit_score - a.option_fit_score),
        deadline: (a, b) => deadlineValue(a) - deadlineValue(b) || (b.total_score - a.total_score),
        price_low: (a, b) => representativePrice(a) - representativePrice(b) || (b.total_score - a.total_score),
        contract_low: (a, b) => optionDownPayment(a) - optionDownPayment(b) || (b.total_score - a.total_score),
        shortfall_low: (a, b) => optionShortfall(a) - optionShortfall(b) || (b.total_score - a.total_score),
    };
    return rows.sort(sorters[sortMode.value] ?? sorters.score);
});

async function toggleFavorite(noticeId) {
    const favorite = { favorite_type: 'notice', object_id: noticeId };
    savingFavoriteKey.value = favoriteKey(noticeId);
    try {
        if (isFavorite(noticeId)) {
            await removeFavorite(favorite);
            favorites.value = favorites.value.filter((item) => item.favorite_type !== 'notice' || item.object_id !== noticeId);
        }
        else {
            const saved = await addFavorite(favorite);
            favorites.value = [...favorites.value, saved];
        }
    }
    finally {
        savingFavoriteKey.value = '';
    }
}

async function loadRecommendations() {
    loading.value = true;
    error.value = '';
    try {
        const [recommendationResponse, favoriteResponse] = await Promise.all([
            fetchHousingRecommendations(),
            fetchFavorites(),
        ]);
        recommendations.value = recommendationResponse;
        favorites.value = favoriteResponse;
        if (!profileStore.loaded) {
            await profileStore.hydrateProfile();
        }
    }
    catch {
        error.value = '추천 API에 연결하지 못했습니다. Django 서버 실행 상태를 확인해 주세요.';
    }
    finally {
        loading.value = false;
    }
}

onMounted(loadRecommendations);
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-sm font-semibold text-blue-700">주택형 옵션 추천</p>
        <h1 class="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">검토할 후보 TOP 6</h1>
        <p class="mt-2 text-sm text-slate-500">소유형 공공분양만 대상으로 자격, 자금, 지역, 일정을 합산합니다.</p>
      </div>
      <label class="inline-flex h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 transition focus-within:border-blue-400 focus-within:ring-4 focus-within:ring-blue-100">
        <ArrowUpDown class="h-4 w-4" />
        <span class="sr-only">정렬 기준</span>
        <select v-model="sortMode" class="h-full bg-transparent pr-7 text-sm font-semibold outline-none">
          <option v-for="option in sortOptions" :key="option.value" :value="option.value">
            {{ option.label }}
          </option>
        </select>
      </label>
    </div>

    <section v-if="loading" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      추천 결과를 불러오는 중입니다.
    </section>

    <section v-else-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-semibold text-amber-800">
      {{ error }}
    </section>

    <section v-else-if="recommendations.length === 0" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      조건에 맞는 검토 후보가 없습니다. 희망 지역, 면적, 분양가 범위를 조금 넓혀 보세요.
    </section>

    <section v-else class="space-y-4">
      <div class="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
            <Sparkles class="h-5 w-5" />
          </div>
          <div>
            <p class="font-bold text-slate-950">{{ recommendations.length }}개 공고에서 검토할 주택형을 찾았습니다</p>
            <p class="text-sm text-slate-500">{{ profileStore.profile.name || '현재 사용자' }}님의 자금, 희망 면적, 분양가 조건을 반영했습니다.</p>
          </div>
        </div>
        <RouterLink to="/profile" class="rounded-lg border border-slate-200 px-4 py-2 text-sm font-bold text-slate-700">
          조건 수정
        </RouterLink>
      </div>

      <div class="flex items-center justify-between text-xs font-bold text-slate-500">
        <span>{{ sortLabel() }}으로 정렬됨</span>
        <span>{{ sortedRecommendations.length }}건</span>
      </div>

      <article v-for="(item, index) in sortedRecommendations" :key="item.notice_id" class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="grid gap-5 xl:grid-cols-[minmax(0,1fr)_240px] 2xl:grid-cols-[minmax(0,1fr)_260px]">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <span class="rounded-md bg-slate-950 px-2 py-1 text-xs font-bold text-white">추천 {{ index + 1 }}</span>
              <span class="rounded-md bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">{{ item.supply_type }}</span>
              <span class="rounded-md bg-violet-50 px-2 py-1 text-xs font-semibold text-violet-700">{{ ownershipTypeLabel(item.ownership_type) }}</span>
            </div>
            <h2 class="mt-3 text-xl font-bold text-slate-950">{{ item.title }}</h2>
            <p class="mt-2 flex items-center gap-1 text-sm text-slate-500">
              <MapPin class="h-4 w-4" />
              {{ item.provider }} · {{ item.region }} · {{ item.district }}
            </p>

            <div class="mt-5 grid gap-3 sm:grid-cols-4">
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">자격</p>
                <p class="mt-1 font-bold">{{ item.score_detail.eligibility }}/35</p>
              </div>
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">자금</p>
                <p class="mt-1 font-bold">{{ item.score_detail.funding }}/25</p>
              </div>
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">지역</p>
                <p class="mt-1 font-bold">{{ item.score_detail.location }}/30</p>
              </div>
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">일정</p>
                <p class="mt-1 font-bold">{{ item.score_detail.schedule }}/10</p>
              </div>
            </div>

            <div v-if="recommendationOptions(item).length" class="mt-5 rounded-lg border border-blue-100 bg-blue-50 p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="text-sm font-bold text-blue-700">우선 검토할 주택형 옵션</p>
                <span class="text-xs font-semibold text-blue-600">{{ recommendationOptions(item).length }}개 옵션</span>
              </div>
              <div class="mt-3 grid gap-3 md:grid-cols-3">
                <RouterLink
                  v-for="option in recommendationOptions(item)"
                  :key="option.option_id"
                  :to="{ path: `/funding/${item.notice_id}`, query: { option_id: option.option_id } }"
                  @click="saveCurrentSelection(item.notice_id, option.option_id)"
                  class="block min-w-0 rounded-lg bg-white p-3 text-sm ring-1 ring-blue-100 transition hover:bg-blue-100"
                >
                  <div class="flex items-start justify-between gap-3">
                    <div class="min-w-0">
                      <p class="truncate font-bold text-slate-950">{{ option.unit_type }} · {{ option.floor_group || '기본' }}</p>
                      <p class="mt-1 text-xs text-slate-600">{{ option.exclusive_area_m2 }}㎡ · {{ priceLabel(option.base_price) }}</p>
                    </div>
                    <span class="shrink-0 rounded-md bg-slate-950 px-2 py-1 text-xs font-bold text-white">
                      {{ option.option_fit_score }}점
                    </span>
                  </div>
                  <p v-if="option.fit_reasons?.length" class="mt-2 line-clamp-2 text-xs leading-5 text-slate-500">
                    {{ option.fit_reasons[0] }}
                  </p>
                  <div v-if="optionInsightRows(option).length" class="mt-2 flex flex-wrap gap-1">
                    <span v-for="row in optionInsightRows(option)" :key="row" class="rounded-md bg-blue-50 px-2 py-0.5 text-[11px] font-bold text-blue-700">
                      {{ row }}
                    </span>
                  </div>
                </RouterLink>
              </div>
            </div>
          </div>

          <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p class="mb-3 inline-flex items-center gap-1 rounded-md bg-white px-2 py-1 text-xs font-bold text-slate-600">
              <ArrowDown class="h-3.5 w-3.5" />
              {{ sortLabel() }}
            </p>
            <div class="flex items-center justify-between">
              <p class="text-sm font-semibold text-slate-500">총점</p>
              <p class="text-2xl font-bold text-slate-950">{{ item.total_score }}/{{ item.score_max ?? 100 }}점</p>
            </div>
            <div class="mt-3 h-3 overflow-hidden rounded-full bg-white">
              <div class="h-full rounded-full bg-blue-600" :style="{ width: `${scorePercent(item)}%` }" />
            </div>
            <div class="mt-5 space-y-3 text-sm">
              <div class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-slate-500">
                  <CalendarDays class="h-4 w-4" />
                  접수 마감
                </span>
                <span class="font-bold text-slate-950">{{ item.application_deadline }}</span>
              </div>
              <div class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-slate-500">
                  <Clock3 class="h-4 w-4" />
                  공식 확인
                </span>
                <span class="rounded-md px-2 py-1 text-xs font-bold" :class="analysisBadgeClass(analysisSummary(item.analysis_summary, item.official_document_status))">
                  {{ analysisSummary(item.analysis_summary, item.official_document_status).label }}
                </span>
              </div>
            </div>
            <p class="mt-3 rounded-lg bg-white p-3 text-xs leading-5 text-slate-600">
              {{ analysisSummary(item.analysis_summary, item.official_document_status).next_action }}
            </p>
            <p class="mt-5 text-sm text-slate-500">예상 분양가</p>
            <p class="mt-1 text-lg font-bold text-slate-950">{{ priceLabel(representativePrice(item)) }}</p>
            <RouterLink
              :to="detailRoute(item)"
              @click="saveCurrentSelection(item.notice_id, defaultRecommendationOption(item)?.option_id)"
              class="mt-5 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-bold text-white transition hover:bg-blue-700"
            >
              공식 근거 보기
              <ChevronRight class="h-4 w-4" />
            </RouterLink>
            <button
              type="button"
              class="mt-2 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="savingFavoriteKey === favoriteKey(item.notice_id)"
              @click="toggleFavorite(item.notice_id)"
            >
              <Bookmark class="h-4 w-4" :class="isFavorite(item.notice_id) ? 'fill-blue-600 text-blue-600' : ''" />
              {{ isFavorite(item.notice_id) ? '공고 저장됨' : '공고 저장' }}
            </button>
            <span
              v-if="isFixtureNotice(item)"
              class="mt-2 inline-flex h-10 w-full items-center justify-center rounded-lg border border-slate-200 bg-slate-50 text-sm font-bold text-slate-600"
            >
              Fixture
            </span>
            <a
              v-else-if="item.source_url"
              :href="item.source_url"
              target="_blank"
              rel="noreferrer"
              class="mt-2 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white text-sm font-bold text-slate-700 transition hover:bg-slate-50"
            >
              공식 출처
              <ExternalLink class="h-4 w-4" />
            </a>
          </div>
        </div>
      </article>

      <div class="rounded-lg border border-amber-100 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
        추천 결과는 공식 공고문 분석과 입력 조건 기반 참고 정보입니다. 실제 신청 전 공식 공고문에서 소득, 자산, 무주택, 납부 일정을 확인하세요.
      </div>
    </section>
  </div>
</template>
