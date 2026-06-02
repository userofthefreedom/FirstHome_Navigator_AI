<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Bookmark, CalendarDays, Calculator, ExternalLink, Landmark, PiggyBank, ShieldAlert, WalletCards } from 'lucide-vue-next';
import { addFavorite, fetchFavorites, fetchFundingPlan, fetchHousingRecommendations, fetchNotice, fetchNoticeUnitOptions, fetchPolicies, fetchProducts, removeFavorite } from '../api/firsthome';
import { analysisBadgeClass, analysisSummary } from '../utils/analysisStatus';
import { formatMoney } from '../utils/format';

const route = useRoute();
const router = useRouter();
const noticeId = computed(() => Number(route.params.noticeId ?? 0));
const selectedOptionId = computed(() => Number(route.query.option_id ?? 0) || null);
const selectedNotice = ref(null);
const fundingPlan = ref(null);
const unitOptions = ref([]);
const optionFundingPlans = ref({});
const activeOptionType = ref('');
const financialProducts = ref([]);
const policies = ref([]);
const favorites = ref([]);
const loading = ref(true);
const savingFavoriteKey = ref('');
const error = ref('');

const readinessRate = computed(() => {
    if (!fundingPlan.value?.down_payment)
        return 0;
    return Math.round((fundingPlan.value.available_cash / fundingPlan.value.down_payment) * 100);
});
const readinessWidth = computed(() => `${Math.min(readinessRate.value, 100)}%`);
const optionComparisons = computed(() => unitOptions.value.map((option) => ({ option, plan: optionFundingPlans.value[option.id] })));
const selectedOption = computed(() => unitOptions.value.find((option) => option.id === fundingPlan.value?.option_id) ?? null);
const selectedComparison = computed(() => optionComparisons.value.find(({ option }) => option.id === fundingPlan.value?.option_id) ?? null);
const groupedOptionComparisons = computed(() => {
    const groups = new Map();
    for (const comparison of optionComparisons.value) {
        const key = comparison.option.option_type || 'basic';
        if (!groups.has(key)) {
            groups.set(key, {
                key,
                label: optionTypeLabel(key),
                comparisons: [],
            });
        }
        groups.get(key).comparisons.push(comparison);
    }
    return [...groups.values()].sort((left, right) => optionTypeOrder(left.key) - optionTypeOrder(right.key));
});
const hasMultipleOptionGroups = computed(() => groupedOptionComparisons.value.length > 1);
const activeOptionGroup = computed(() => {
    const selectedType = activeOptionType.value || selectedOption.value?.option_type || groupedOptionComparisons.value[0]?.key || '';
    return groupedOptionComparisons.value.find((group) => group.key === selectedType) ?? groupedOptionComparisons.value[0] ?? null;
});
const visibleOptionComparisons = computed(() => activeOptionGroup.value?.comparisons ?? []);
const otherVisibleComparisons = computed(() => visibleOptionComparisons.value.filter(({ option }) => option.id !== fundingPlan.value?.option_id));
const currentAnalysisSummary = computed(() => analysisSummary(selectedNotice.value?.analysis_summary, selectedNotice.value?.official_document_status));
const timelineSummary = computed(() => fundingPlan.value?.timeline_summary ?? {});
const middleSchedules = computed(() => fundingPlan.value?.timeline.filter((item) => item.payment_type === 'middle_payment') ?? []);
const installmentSchedules = computed(() => fundingPlan.value?.timeline.filter((item) => item.payment_type === 'installment_payment') ?? []);
const postBalanceItems = computed(() => fundingPlan.value?.post_balance_items ?? []);

function priceLabel(price) {
    return Number(price || 0) > 0 ? formatMoney(price) : '공식 확인 필요';
}

function optionTypeLabel(type) {
    const labels = {
        pre_subscription: '사전청약 당첨자',
        general_supply: '본청약',
        basic: '기본 유형',
        minus: '마이너스 옵션',
    };
    return labels[type] ?? type ?? '기본 유형';
}

function optionTypeOrder(type) {
    const order = {
        general_supply: 1,
        basic: 2,
        pre_subscription: 3,
        minus: 4,
    };
    return order[type] ?? 99;
}

function isFixtureNotice(notice) {
    const source = String(notice?.data_source || '').toLowerCase();
    return source.includes('fixture') || Boolean(notice?.source_meta?.fixture_id);
}

function favoriteKey(favoriteType, objectId) {
    return `${favoriteType}-${objectId}`;
}

function isFavorite(favoriteType, objectId) {
    return favorites.value.some((favorite) => favorite.favorite_type === favoriteType && favorite.object_id === objectId);
}

async function toggleFavorite(favoriteType, objectId) {
    const favorite = { favorite_type: favoriteType, object_id: objectId };
    savingFavoriteKey.value = favoriteKey(favoriteType, objectId);
    try {
        if (isFavorite(favoriteType, objectId)) {
            await removeFavorite(favorite);
            favorites.value = favorites.value.filter((item) => item.favorite_type !== favoriteType || item.object_id !== objectId);
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

async function resolveNoticeId() {
    if (noticeId.value)
        return noticeId.value;
    const recommendations = await fetchHousingRecommendations();
    return recommendations[0]?.notice_id ?? 101;
}

async function loadOptionFundingPlans(targetNoticeId, options, currentPlan) {
    if (options.length === 0) {
        optionFundingPlans.value = {};
        return;
    }
    const entries = await Promise.all(options.map(async (option) => {
        if (currentPlan.option_id === option.id)
            return [option.id, currentPlan];
        try {
            const plan = await fetchFundingPlan(targetNoticeId, option.id);
            return [option.id, plan];
        }
        catch {
            return [option.id, undefined];
        }
    }));
    optionFundingPlans.value = Object.fromEntries(entries.filter((entry) => Boolean(entry[1])));
}

async function loadFunding() {
    loading.value = true;
    error.value = '';
    try {
        const targetNoticeId = await resolveNoticeId();
        const [noticeResponse, fundingResponse, unitOptionResponse, productsResponse, policiesResponse, favoriteResponse] = await Promise.all([
            fetchNotice(targetNoticeId),
            fetchFundingPlan(targetNoticeId, selectedOptionId.value),
            fetchNoticeUnitOptions(targetNoticeId).catch(() => []),
            fetchProducts(),
            fetchPolicies(),
            fetchFavorites(),
        ]);
        selectedNotice.value = noticeResponse;
        fundingPlan.value = fundingResponse;
        unitOptions.value = unitOptionResponse;
        financialProducts.value = productsResponse;
        policies.value = policiesResponse;
        favorites.value = favoriteResponse;
        await loadOptionFundingPlans(targetNoticeId, unitOptionResponse, fundingResponse);
        syncActiveOptionType(fundingResponse, unitOptionResponse);
    }
    catch {
        error.value = '자금 로드맵 API에 연결하지 못했습니다. Django 서버 실행 상태를 확인해 주세요.';
    }
    finally {
        loading.value = false;
    }
}

function syncActiveOptionType(plan, options) {
    const selected = options.find((option) => option.id === plan?.option_id);
    activeOptionType.value = selected?.option_type || options[0]?.option_type || 'basic';
}

function readinessForPlan(plan) {
    if (!plan?.down_payment)
        return 0;
    return Math.round((plan.available_cash / plan.down_payment) * 100);
}

function comparisonStatus(plan) {
    if (!plan)
        return '계산 대기';
    if (plan.shortfall <= 0)
        return '계약금 준비 완료';
    if (plan.monthly_target <= 0)
        return '추가 목표 없음';
    return `월 ${formatMoney(plan.monthly_target)} 목표`;
}

function comparisonStatusClass(plan) {
    if (!plan)
        return 'bg-slate-100 text-slate-500';
    if (plan.shortfall <= 0)
        return 'bg-emerald-50 text-emerald-700';
    return 'bg-blue-50 text-blue-700';
}

function middlePaymentSummary(plan) {
    if (!plan)
        return '-';
    const rows = plan.timeline?.filter((item) => item.payment_type === 'middle_payment') ?? [];
    if (rows.length === 0)
        return '없음';
    const total = rows.reduce((sum, item) => sum + Number(item.amount || 0), 0);
    return `${rows.length}회 · ${formatMoney(total)}`;
}

function compactPaymentSummary(plan) {
    if (!plan)
        return '계산 대기';
    const middleRows = plan.timeline?.filter((item) => item.payment_type === 'middle_payment') ?? [];
    const finalPayment = plan.timeline?.find((item) => item.payment_type === 'final_payment');
    const parts = [];
    if (middleRows.length) {
        parts.push(`중도금 ${middleRows.length}회`);
    }
    if (finalPayment) {
        parts.push(`잔금 ${formatMoney(finalPayment.amount)}`);
    }
    return parts.join(' · ') || '일정 확인 필요';
}

function selectedOptionLabel() {
    if (!selectedOption.value)
        return '';
    return `${selectedOption.value.unit_type} · ${selectedOption.value.floor_group || '전체'}`;
}

function isSelectedOption(option) {
    return fundingPlan.value?.option_id === option.id;
}

async function selectFundingOption(option) {
    if (!selectedNotice.value || isSelectedOption(option))
        return;
    activeOptionType.value = option.option_type || 'basic';
    await router.push({ path: `/funding/${selectedNotice.value.id}`, query: { option_id: option.id } });
}

async function selectOptionGroup(groupKey) {
    activeOptionType.value = groupKey;
    const group = groupedOptionComparisons.value.find((item) => item.key === groupKey);
    const selectedInGroup = group?.comparisons.find(({ option }) => option.id === fundingPlan.value?.option_id);
    const target = selectedInGroup?.option ?? group?.comparisons[0]?.option;
    if (target) {
        await selectFundingOption(target);
    }
}

function paymentTypeLabel(type) {
    const labels = {
        down_payment: '계약금',
        middle_payment: '중도금',
        final_payment: '잔금',
        installment_payment: '할부금',
        move_in_balance: '입주잔금',
        loan: '융자금',
        application: '접수',
        winner: '발표',
    };
    return labels[type] ?? '일정';
}

function paymentTypeClass(type) {
    if (type === 'down_payment')
        return 'bg-blue-50 text-blue-700';
    if (type === 'middle_payment')
        return 'bg-violet-50 text-violet-700';
    if (type === 'final_payment')
        return 'bg-amber-50 text-amber-700';
    if (type === 'installment_payment')
        return 'bg-emerald-50 text-emerald-700';
    if (type === 'move_in_balance')
        return 'bg-cyan-50 text-cyan-700';
    if (type === 'loan')
        return 'bg-slate-200 text-slate-700';
    return 'bg-slate-100 text-slate-600';
}

watch([noticeId, selectedOptionId], loadFunding);
onMounted(loadFunding);
</script>

<template>
  <div class="space-y-5">
    <section v-if="loading" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      자금 로드맵을 불러오는 중입니다.
    </section>

    <section v-else-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-semibold text-amber-800">
      {{ error }}
    </section>

    <template v-else-if="selectedNotice && fundingPlan">
      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p class="inline-flex items-center gap-2 text-sm font-semibold text-blue-700">
              <WalletCards class="h-4 w-4" />
              옵션 자금 로드맵
            </p>
            <h1 class="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">계약금과 납부 일정</h1>
            <p class="mt-2 text-sm text-slate-500">{{ selectedNotice.title }}의 선택 주택형 기준으로 필요한 현금 흐름을 계산합니다.</p>
            <div class="mt-3 flex flex-wrap gap-2">
              <span v-if="fundingPlan.schedule_source === 'payment_schedule'" class="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">
                {{ fundingPlan.unit_type }} · {{ fundingPlan.floor_group || '전체' }}
              </span>
              <span class="rounded-md px-2 py-1 text-xs font-bold" :class="analysisBadgeClass(currentAnalysisSummary)">
                {{ currentAnalysisSummary.label }}
              </span>
              <span v-if="timelineSummary.has_post_balance_loan" class="rounded-md bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700">융자금 분리</span>
            </div>
          </div>
          <div class="flex flex-wrap gap-2">
            <RouterLink to="/recommendations" class="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700">
              추천 다시 보기
            </RouterLink>
            <RouterLink :to="`/notices/${selectedNotice.id}`" class="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700">
              공식 근거
            </RouterLink>
            <button
              type="button"
              class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700"
              :disabled="savingFavoriteKey === favoriteKey('notice', selectedNotice.id)"
              @click="toggleFavorite('notice', selectedNotice.id)"
            >
              <Bookmark class="h-4 w-4" :class="isFavorite('notice', selectedNotice.id) ? 'fill-blue-600 text-blue-600' : ''" />
              {{ isFavorite('notice', selectedNotice.id) ? '공고 저장됨' : '공고 저장' }}
            </button>
          </div>
        </div>
      </section>

      <section class="grid gap-3 md:grid-cols-4">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="flex items-center gap-2 text-sm text-slate-500">
            <Landmark class="h-4 w-4" />
            예상 분양가
          </p>
          <p class="mt-2 text-2xl font-bold">{{ priceLabel(fundingPlan.price) }}</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="flex items-center gap-2 text-sm text-slate-500">
            <WalletCards class="h-4 w-4" />
            계약금
          </p>
          <p class="mt-2 text-2xl font-bold">{{ formatMoney(fundingPlan.down_payment) }}</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="flex items-center gap-2 text-sm text-slate-500">
            <PiggyBank class="h-4 w-4" />
            준비 가능 현금
          </p>
          <p class="mt-2 text-2xl font-bold">{{ formatMoney(fundingPlan.available_cash) }}</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="flex items-center gap-2 text-sm text-slate-500">
            <Calculator class="h-4 w-4" />
            부족액
          </p>
          <p class="mt-2 text-2xl font-bold text-blue-700">{{ formatMoney(fundingPlan.shortfall) }}</p>
        </div>
      </section>

      <section class="grid gap-5 lg:grid-cols-3">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm font-semibold text-blue-700">계약금 준비율</p>
          <h2 class="mt-1 text-xl font-bold">{{ readinessRate }}% 준비됨</h2>
          <div class="mt-6 h-3 overflow-hidden rounded-full bg-slate-100">
            <div class="h-full rounded-full bg-blue-600" :style="{ width: readinessWidth }" />
          </div>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm font-semibold text-slate-500">입주 전 필요 금액</p>
          <h2 class="mt-1 text-xl font-bold text-slate-950">{{ formatMoney(timelineSummary.due_before_move_in || 0) }}</h2>
          <p class="mt-3 text-xs leading-5 text-slate-500">계약금, 중도금, 잔금, 할부금을 합산한 금액입니다.</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-slate-950 p-5 text-white shadow-sm">
          <p class="text-sm font-semibold text-slate-300">월 저축 목표</p>
          <h2 class="mt-1 text-2xl font-bold">{{ formatMoney(fundingPlan.monthly_target) }}</h2>
          <p class="mt-3 text-sm leading-6 text-slate-300">계약 예정일까지 {{ fundingPlan.months_until_contract }}개월 기준입니다.</p>
        </div>
      </section>

      <section v-if="timelineSummary.has_post_balance_loan" class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <p class="text-sm font-semibold text-slate-500">잔금 이후 상환 항목</p>
        <h2 class="mt-1 text-xl font-bold text-slate-950">{{ formatMoney(timelineSummary.post_balance_amount || 0) }}</h2>
        <p class="mt-2 text-sm leading-6 text-slate-600">{{ fundingPlan.loan_repayment_note }}</p>
        <div class="mt-4 flex flex-wrap gap-2">
          <span v-for="item in postBalanceItems" :key="`${item.label}-${item.amount}`" class="rounded-md bg-slate-100 px-3 py-2 text-sm font-bold text-slate-700">
            {{ item.label }} · {{ formatMoney(item.amount) }}
          </span>
        </div>
      </section>

      <section v-if="optionComparisons.length" class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p class="text-sm font-semibold text-blue-700">주택형 옵션 비교</p>
            <h2 class="mt-1 text-lg font-bold text-slate-950">선택 옵션과 다른 주택형 빠른 비교</h2>
          </div>
          <span v-if="selectedOptionLabel()" class="rounded-md bg-slate-950 px-3 py-2 text-sm font-bold text-white">
            선택: {{ selectedOptionLabel() }}
          </span>
        </div>

        <div v-if="hasMultipleOptionGroups" class="mt-4 inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
          <button
            v-for="group in groupedOptionComparisons"
            :key="group.key"
            type="button"
            class="inline-flex h-9 items-center gap-2 rounded-md px-3 text-sm font-bold transition"
            :class="activeOptionGroup?.key === group.key ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-500 hover:text-slate-800'"
            @click="selectOptionGroup(group.key)"
          >
            {{ group.label }}
            <span class="text-xs text-slate-400">{{ group.comparisons.length }}</span>
          </button>
        </div>

        <div v-if="selectedComparison" class="mt-5 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p class="text-xs font-bold text-blue-700">현재 자금 로드맵 기준</p>
              <h3 class="mt-1 text-2xl font-bold text-slate-950">
                {{ selectedComparison.option.unit_type }} · {{ selectedComparison.option.floor_group || '전체' }}
                <span class="text-lg text-slate-500">{{ selectedComparison.option.exclusive_area_m2 }}㎡</span>
              </h3>
            </div>
            <div class="flex flex-wrap gap-2">
              <button
                type="button"
                class="flex h-9 w-9 items-center justify-center rounded-lg border border-blue-200 bg-white text-slate-600"
                :disabled="savingFavoriteKey === favoriteKey('option', selectedComparison.option.id)"
                title="주택형 저장"
                @click="toggleFavorite('option', selectedComparison.option.id)"
              >
                <Bookmark class="h-4 w-4" :class="isFavorite('option', selectedComparison.option.id) ? 'fill-blue-600 text-blue-600' : ''" />
              </button>
              <span class="inline-flex h-9 items-center rounded-lg bg-blue-600 px-3 text-sm font-bold text-white">현재 선택</span>
            </div>
          </div>
          <div class="mt-4 grid gap-2 md:grid-cols-4">
            <div class="rounded-lg bg-white p-3">
              <p class="text-xs font-bold text-slate-500">분양가</p>
              <p class="mt-1 font-bold text-slate-950">{{ priceLabel(selectedComparison.plan?.price ?? selectedComparison.option.base_price) }}</p>
            </div>
            <div class="rounded-lg bg-white p-3">
              <p class="text-xs font-bold text-slate-500">계약금</p>
              <p class="mt-1 font-bold text-slate-950">{{ selectedComparison.plan ? formatMoney(selectedComparison.plan.down_payment) : '-' }}</p>
            </div>
            <div class="rounded-lg bg-white p-3">
              <p class="text-xs font-bold text-slate-500">중도금</p>
              <p class="mt-1 font-bold text-slate-950">{{ middlePaymentSummary(selectedComparison.plan) }}</p>
            </div>
            <div class="rounded-lg bg-white p-3">
              <p class="text-xs font-bold text-slate-500">부족액</p>
              <p class="mt-1 font-bold text-blue-700">{{ selectedComparison.plan ? formatMoney(selectedComparison.plan.shortfall) : '-' }}</p>
            </div>
          </div>
        </div>

        <div class="mt-4 overflow-hidden rounded-lg border border-slate-200">
          <div
            v-for="{ option, plan } in otherVisibleComparisons"
            :key="option.id"
            class="grid gap-3 border-b border-slate-100 bg-white p-3 text-sm last:border-b-0 md:grid-cols-[minmax(0,1.2fr)_1fr_1fr_1fr_120px] md:items-center"
          >
            <div class="min-w-0">
              <p class="font-bold text-slate-950">{{ option.unit_type }} · {{ option.floor_group || '전체' }}</p>
              <p class="mt-0.5 text-xs text-slate-500">{{ option.exclusive_area_m2 }}㎡ · {{ optionTypeLabel(option.option_type) }}</p>
            </div>
            <div>
              <p class="text-xs font-bold text-slate-500">분양가</p>
              <p class="font-bold text-slate-950">{{ priceLabel(plan?.price ?? option.base_price) }}</p>
            </div>
            <div>
              <p class="text-xs font-bold text-slate-500">계약금</p>
              <p class="font-bold text-slate-950">{{ plan ? formatMoney(plan.down_payment) : '-' }}</p>
            </div>
            <div>
              <p class="text-xs font-bold text-slate-500">{{ compactPaymentSummary(plan) }}</p>
              <span class="rounded-md px-2 py-1 text-xs font-bold" :class="comparisonStatusClass(plan)">
                {{ comparisonStatus(plan) }}
              </span>
            </div>
            <div class="flex items-center justify-end gap-2">
              <button
                type="button"
                class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600"
                :disabled="savingFavoriteKey === favoriteKey('option', option.id)"
                title="주택형 저장"
                @click="toggleFavorite('option', option.id)"
              >
                <Bookmark class="h-4 w-4" :class="isFavorite('option', option.id) ? 'fill-blue-600 text-blue-600' : ''" />
              </button>
              <button
                type="button"
                class="inline-flex h-9 items-center justify-center rounded-lg bg-blue-600 px-3 text-xs font-bold text-white transition hover:bg-blue-700"
                @click="selectFundingOption(option)"
              >
                선택
              </button>
            </div>
          </div>
          <div v-if="otherVisibleComparisons.length === 0" class="bg-white p-4 text-sm font-semibold text-slate-500">
            이 그룹의 다른 주택형 옵션이 없습니다.
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 class="flex items-center gap-2 text-lg font-bold text-slate-950">
              <CalendarDays class="h-5 w-5 text-slate-400" />
              납부 타임라인
            </h2>
            <p class="mt-1 text-sm text-slate-500">공식 공고문에서 추출한 회차별 금액과 일정을 기준으로 표시합니다.</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <div v-if="middleSchedules.length" class="rounded-lg bg-violet-50 px-3 py-2 text-right text-xs font-bold text-violet-700">
              중도금 {{ middleSchedules.length }}회
            </div>
            <div v-if="installmentSchedules.length" class="rounded-lg bg-emerald-50 px-3 py-2 text-right text-xs font-bold text-emerald-700">
              할부금 {{ installmentSchedules.length }}회
            </div>
          </div>
        </div>
        <div class="mt-5 divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200">
          <div v-for="(item, index) in fundingPlan.timeline" :key="`${item.label}-${index}`" class="grid gap-3 bg-white p-4 text-sm md:grid-cols-[64px_120px_minmax(0,1fr)_160px] md:items-start">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-100 font-bold text-slate-700">
              {{ index + 1 }}
            </div>
            <span class="inline-flex w-fit rounded-md px-2 py-1 text-xs font-bold" :class="paymentTypeClass(item.payment_type)">
              {{ paymentTypeLabel(item.payment_type) }}
            </span>
            <div>
              <p class="font-bold text-slate-950">{{ item.label }}</p>
              <p class="mt-1 text-slate-500">{{ item.date }}</p>
              <p v-if="item.evidence_text" class="mt-2 rounded-md bg-slate-50 p-2 text-xs leading-5 text-slate-500">
                {{ item.evidence_text }}
              </p>
            </div>
            <p class="font-bold text-slate-950 md:text-right">{{ formatMoney(item.amount) }}</p>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-amber-100 bg-amber-50 p-5 text-sm leading-6 text-amber-800">
        <p class="flex items-center gap-2 font-bold">
          <ShieldAlert class="h-4 w-4" />
          참고 안내
        </p>
        <p class="mt-2">
          자금 로드맵은 입력값과 공고문 추출값 기반의 참고 계산입니다. 실제 계약금, 중도금, 잔금, 융자금 조건은 공식 공고문과 기금 안내를 확인하세요.
        </p>
        <span
          v-if="isFixtureNotice(selectedNotice)"
          class="mt-3 inline-flex items-center rounded-md bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-900"
        >
          Fixture
        </span>
        <a
          v-else-if="selectedNotice.source_url"
          :href="selectedNotice.source_url"
          target="_blank"
          rel="noreferrer"
          class="mt-3 inline-flex items-center gap-1 font-bold text-amber-900 underline underline-offset-4"
        >
          공식 출처 열기
          <ExternalLink class="h-4 w-4" />
        </a>
      </section>

      <section class="grid gap-5 lg:grid-cols-2">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-bold text-slate-950">대출 상품 후보</h2>
          <div class="mt-4 grid gap-3">
            <p v-if="financialProducts.length === 0" class="rounded-lg bg-slate-50 p-4 text-sm font-semibold text-slate-600">
              조건에 맞는 상품 후보가 없습니다.
            </p>
            <div v-for="product in financialProducts" :key="product.id" class="rounded-lg border border-slate-100 bg-slate-50 p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="font-bold text-slate-950">{{ product.name }}</p>
                <span class="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">{{ product.category }}</span>
              </div>
              <p class="mt-1 text-sm text-slate-500">{{ product.provider }} · {{ product.rate }} · {{ product.period }}</p>
              <p class="mt-2 text-sm text-slate-600">{{ product.reasons[0] }}</p>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-bold text-slate-950">지원정책 후보</h2>
          <div class="mt-4 grid gap-3">
            <p v-if="policies.length === 0" class="rounded-lg bg-slate-50 p-4 text-sm font-semibold text-slate-600">
              조건에 맞는 정책 후보가 없습니다.
            </p>
            <div v-for="policy in policies" :key="policy.id" class="rounded-lg border border-slate-100 bg-slate-50 p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="font-bold text-slate-950">{{ policy.name }}</p>
                <span v-if="policy.policy_category" class="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">{{ policy.policy_category }}</span>
              </div>
              <p class="mt-1 text-sm text-slate-500">{{ policy.provider }} · {{ policy.target }}</p>
              <p class="mt-2 text-sm text-slate-600">{{ policy.benefit }}</p>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
