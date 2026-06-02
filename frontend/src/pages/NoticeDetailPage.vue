<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { ArrowLeft, Bookmark, Bot, CalendarDays, CheckCircle2, ExternalLink, FileCheck2, ShieldAlert, WalletCards } from 'lucide-vue-next';
import { addFavorite, analyzeNoticeDocument, fetchFavorites, fetchFundingPlan, fetchHousingRecommendations, fetchNotice, fetchNoticeDocumentStatus, fetchNoticeEligibilityChecklists, fetchNoticeUnitOptions, removeFavorite } from '../api/firsthome';
import { analysisBadgeClass, analysisSummary } from '../utils/analysisStatus';
import { formatMoney } from '../utils/format';
const route = useRoute();
const noticeId = computed(() => Number(route.params.noticeId ?? 0));
const selectedOptionId = computed(() => Number(route.query.option_id ?? 0) || null);
const selectedNotice = ref(null);
const recommendation = ref(null);
const fundingPlan = ref(null);
const documentStatus = ref(null);
const unitOptions = ref([]);
const activeOptionType = ref('');
const eligibilityChecklists = ref([]);
const favorites = ref([]);
const loading = ref(true);
const savingFavorite = ref(false);
const analyzing = ref(false);
const error = ref('');
const analysisError = ref('');
function priceLabel(price) {
    return price > 0 ? formatMoney(price) : '공식 확인 필요';
}
function extractionLabel(schemaVersion, source) {
    if (!schemaVersion)
        return '분석 전';
    if (schemaVersion === 'llm-v1' || source === 'llm' || source === 'llm_cache')
        return 'LLM structured output';
    if (schemaVersion === 'rules-v1')
        return '규칙 기반 PDF 추출';
    if (schemaVersion === 'mock-v1')
        return 'mock fallback';
    return schemaVersion;
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
function optionTypeLabel(type) {
    const labels = {
        pre_subscription: '사전청약 당첨자',
        general_supply: '본청약·일반 공급',
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
function checklistPageLabel(item) {
    return item.page_no ? `공고문 ${item.page_no}쪽` : '공고문 페이지 확인 필요';
}
function shouldShowChecklistCondition(item) {
    return item.condition_text && !item.condition_text.includes('공식 공고문 원문 기준');
}
function preferredFundingOptionId() {
    const routeOption = unitOptions.value.find((option) => option.id === selectedOptionId.value);
    const selectedType = currentOptionType();
    if (routeOption && (routeOption.option_type || 'basic') === selectedType)
        return routeOption.id;
    return representativeOptionIdForType(selectedType) ?? unitOptions.value[0]?.id ?? null;
}
const noticeFavorite = computed(() => {
    if (!selectedNotice.value)
        return null;
    return { favorite_type: 'notice', object_id: selectedNotice.value.id };
});
const isFavorite = computed(() => {
    if (!noticeFavorite.value)
        return false;
    return favorites.value.some((favorite) => favorite.favorite_type === 'notice' && favorite.object_id === noticeFavorite.value?.object_id);
});
const currentAnalysisSummary = computed(() => {
    return analysisSummary(documentStatus.value?.analysis_summary ?? selectedNotice.value?.analysis_summary, selectedNotice.value?.official_document_status);
});
const summaryPrice = computed(() => {
    const planPrice = Number(fundingPlan.value?.price || 0);
    const noticePrice = Number(selectedNotice.value?.price || 0);
    return planPrice > 0 ? planPrice : noticePrice;
});
const groupedUnitOptions = computed(() => {
    const groups = new Map();
    for (const option of unitOptions.value) {
        const key = option.option_type || 'basic';
        if (!groups.has(key)) {
            groups.set(key, {
                key,
                label: optionTypeLabel(key),
                options: [],
            });
        }
        groups.get(key).options.push(option);
    }
    return [...groups.values()].sort((left, right) => optionTypeOrder(left.key) - optionTypeOrder(right.key));
});
const hasMultipleOptionGroups = computed(() => groupedUnitOptions.value.length > 1);
const activeUnitOptionGroup = computed(() => {
    const selectedType = currentOptionType();
    return groupedUnitOptions.value.find((group) => group.key === selectedType) ?? groupedUnitOptions.value[0] ?? null;
});
const visibleUnitOptions = computed(() => activeUnitOptionGroup.value?.options ?? []);
const officialChecklist = computed(() => {
    if (eligibilityChecklists.value.length) {
        return eligibilityChecklists.value.map((item) => ({
            key: `checklist-${item.id}`,
            category: item.category,
            title: item.title,
            condition_text: item.condition_text,
            evidence_text: item.evidence_text,
            page_no: item.page_no,
            confidence: item.confidence,
            isExtracted: true,
        }));
    }
    if (!selectedNotice.value)
        return [];
    return [
        {
            key: 'fallback-supply',
            category: 'notice',
            title: '공급유형 자격 확인',
            condition_text: `${selectedNotice.value.supply_type} 세부 자격과 우선공급 기준을 공식 공고문에서 확인합니다.`,
            evidence_text: '공고 기본 정보 기반 임시 체크리스트입니다. 공고문 분석 후 공식 근거 문장으로 대체됩니다.',
            page_no: null,
            confidence: 0,
            isExtracted: false,
        },
        {
            key: 'fallback-income',
            category: 'notice',
            title: '소득·자산·서류 확인',
            condition_text: `${selectedNotice.value.required_documents.slice(0, 2).join(', ')} 발급 가능 여부와 소득·자산 기준을 확인합니다.`,
            evidence_text: '공고 기본 정보 기반 임시 체크리스트입니다.',
            page_no: null,
            confidence: 0,
            isExtracted: false,
        },
        {
            key: 'fallback-schedule',
            category: 'notice',
            title: '접수·계약 일정 확인',
            condition_text: `${selectedNotice.value.application_deadline} 접수 마감과 ${selectedNotice.value.contract_date} 계약 일정을 확인합니다.`,
            evidence_text: '공고 목록의 대표 일정 기반입니다. 실제 납부 일정은 공식 공고문을 우선합니다.',
            page_no: null,
            confidence: 0,
            isExtracted: false,
        },
    ];
});
async function resolveNoticeId() {
    if (noticeId.value)
        return noticeId.value;
    const recommendations = await fetchHousingRecommendations();
    return recommendations[0]?.notice_id ?? 101;
}
async function loadDetail() {
    loading.value = true;
    error.value = '';
    analysisError.value = '';
    activeOptionType.value = '';
    try {
        const targetNoticeId = await resolveNoticeId();
        const [noticeResponse, favoriteResponse, recommendations] = await Promise.all([
            fetchNotice(targetNoticeId),
            fetchFavorites(),
            fetchHousingRecommendations(),
        ]);
        selectedNotice.value = noticeResponse;
        favorites.value = favoriteResponse;
        recommendation.value = recommendations.find((item) => item.notice_id === targetNoticeId) ?? null;
        await loadDocumentAnalysis(targetNoticeId);
        syncActiveOptionType();
        await refreshFundingPlan(targetNoticeId);
    }
    catch {
        error.value = '공고 상세 API에 연결하지 못했습니다. Django 서버가 실행 중인지 확인하세요.';
    }
    finally {
        loading.value = false;
    }
}
async function loadDocumentAnalysis(targetNoticeId) {
    const [statusResponse, optionResponse, checklistResponse] = await Promise.all([
        fetchNoticeDocumentStatus(targetNoticeId).catch(() => null),
        fetchNoticeUnitOptions(targetNoticeId).catch(() => []),
        fetchNoticeEligibilityChecklists(targetNoticeId).catch(() => []),
    ]);
    documentStatus.value = statusResponse;
    unitOptions.value = optionResponse;
    eligibilityChecklists.value = checklistResponse;
}
function defaultOptionType() {
    if (groupedUnitOptions.value.some((group) => group.key === 'general_supply'))
        return 'general_supply';
    if (groupedUnitOptions.value.some((group) => group.key === 'basic'))
        return 'basic';
    return groupedUnitOptions.value[0]?.key ?? '';
}
function currentOptionType() {
    return activeOptionType.value || defaultOptionType();
}
function syncActiveOptionType() {
    const routeOption = unitOptions.value.find((option) => option.id === selectedOptionId.value);
    if (routeOption) {
        activeOptionType.value = routeOption.option_type || 'basic';
        return;
    }
    const fallbackType = defaultOptionType();
    if (!activeOptionType.value || !groupedUnitOptions.value.some((group) => group.key === activeOptionType.value)) {
        activeOptionType.value = fallbackType;
    }
}
function representativeOptionIdForType(optionType) {
    const options = unitOptions.value.filter((option) => (option.option_type || 'basic') === optionType);
    if (!options.length)
        return null;
    const optionIds = new Set(options.map((option) => option.id));
    const recommendedOptions = [
        ...(recommendation.value?.top_options ?? []),
        ...(recommendation.value?.best_option ? [recommendation.value.best_option] : []),
    ];
    const recommended = recommendedOptions.find((option) => optionIds.has(option.option_id));
    return recommended?.option_id ?? options[0].id;
}
async function refreshFundingPlan(targetNoticeId) {
    const optionId = preferredFundingOptionId();
    try {
        fundingPlan.value = await fetchFundingPlan(targetNoticeId, optionId);
    }
    catch {
        fundingPlan.value = await fetchFundingPlan(targetNoticeId);
    }
}
async function selectOptionType(optionType) {
    activeOptionType.value = optionType;
    if (selectedNotice.value) {
        await refreshFundingPlan(selectedNotice.value.id);
    }
}
async function handleAnalyzeNotice() {
    if (!selectedNotice.value)
        return;
    analyzing.value = true;
    analysisError.value = '';
    try {
        const response = await analyzeNoticeDocument(selectedNotice.value.id);
        selectedNotice.value = {
            ...selectedNotice.value,
            official_document_status: response.official_document_status,
            unit_option_count: response.unit_options.length,
        };
        unitOptions.value = response.unit_options;
        await loadDocumentAnalysis(selectedNotice.value.id);
        syncActiveOptionType();
        await refreshFundingPlan(selectedNotice.value.id);
    }
    catch {
        analysisError.value = '공고문 분석을 실행하지 못했습니다. 기존 상세 정보는 유지되며, 잠시 후 다시 시도해 주세요.';
    }
    finally {
        analyzing.value = false;
    }
}
async function toggleFavorite() {
    if (!noticeFavorite.value)
        return;
    savingFavorite.value = true;
    try {
        if (isFavorite.value) {
            await removeFavorite(noticeFavorite.value);
            favorites.value = favorites.value.filter((favorite) => favorite.favorite_type !== 'notice' || favorite.object_id !== noticeFavorite.value?.object_id);
        }
        else {
            const saved = await addFavorite(noticeFavorite.value);
            favorites.value = [...favorites.value, saved];
        }
    }
    finally {
        savingFavorite.value = false;
    }
}
watch([noticeId, selectedOptionId], loadDetail);
onMounted(loadDetail);
</script>

<template>
  <div class="space-y-5">
    <section v-if="loading" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      공고 상세를 불러오는 중입니다.
    </section>

    <section v-else-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-semibold text-amber-800">
      {{ error }}
    </section>

    <template v-else-if="selectedNotice && fundingPlan">
      <section v-if="analysisError" class="rounded-lg border border-amber-100 bg-amber-50 p-4 text-sm font-semibold text-amber-800">
        {{ analysisError }}
      </section>

      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <RouterLink to="/recommendations" class="inline-flex items-center gap-2 text-sm font-bold text-slate-600 hover:text-slate-950">
              <ArrowLeft class="h-4 w-4" />
              추천 목록
            </RouterLink>
            <div class="mt-4 flex flex-wrap items-center gap-2">
              <span class="rounded-md bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700" title="공고의 공급 유형입니다.">{{ selectedNotice.supply_type }}</span>
              <span class="rounded-md bg-violet-50 px-2.5 py-1 text-xs font-bold text-violet-700" title="서비스 내부의 소유형 청약 분류입니다.">{{ ownershipTypeLabel(selectedNotice.ownership_type) }}</span>
            </div>
            <h1 class="mt-3 text-2xl font-bold text-slate-950 sm:text-3xl">{{ selectedNotice.title }}</h1>
            <p class="mt-2 text-sm text-slate-500">{{ selectedNotice.provider }} · {{ selectedNotice.district }} · {{ selectedNotice.area }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              type="button"
              class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
              :disabled="savingFavorite"
              @click="toggleFavorite"
            >
              <Bookmark class="h-4 w-4" :class="isFavorite ? 'fill-blue-600 text-blue-600' : ''" />
              {{ isFavorite ? '공고 저장됨' : '공고 저장' }}
            </button>
            <RouterLink :to="{ path: `/funding/${selectedNotice.id}`, query: fundingPlan.option_id ? { option_id: fundingPlan.option_id } : {} }" class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white">
              <WalletCards class="h-4 w-4" />
              옵션 자금 보기
            </RouterLink>
            <a
              v-if="selectedNotice.source_url"
              :href="selectedNotice.source_url"
              target="_blank"
              rel="noreferrer"
              class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
            >
              <ExternalLink class="h-4 w-4" />
              공식 원문 보기
            </a>
          </div>
        </div>
      </section>

      <section class="grid gap-3 md:grid-cols-4">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm text-slate-500">예상 분양가</p>
          <p class="mt-2 text-2xl font-bold text-slate-950">{{ priceLabel(summaryPrice) }}</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm text-slate-500">계약금</p>
          <p class="mt-2 text-2xl font-bold text-slate-950">{{ formatMoney(fundingPlan.down_payment) }}</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm text-slate-500">부족액</p>
          <p class="mt-2 text-2xl font-bold text-blue-700">{{ formatMoney(fundingPlan.shortfall) }}</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm text-slate-500">접수 마감</p>
          <p class="mt-2 text-2xl font-bold text-slate-950">{{ selectedNotice.application_deadline }}</p>
        </div>
      </section>

      <section class="grid gap-5 lg:grid-cols-[1fr_0.92fr]">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="flex items-center gap-2 text-lg font-bold text-slate-950">
            <FileCheck2 class="h-5 w-5 text-blue-700" />
            공식 확인 체크리스트
          </h2>
          <div class="mt-5 grid gap-3">
            <div v-for="item in officialChecklist" :key="item.key" class="grid gap-2 rounded-lg bg-slate-50 p-4 text-sm text-slate-700">
              <div class="flex items-start gap-3">
              <CheckCircle2 class="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                <div class="min-w-0">
                  <div class="flex flex-wrap items-center gap-2">
                    <p class="font-bold text-slate-950">{{ item.title }}</p>
                    <span v-if="item.isExtracted" class="rounded-md bg-emerald-50 px-2 py-0.5 text-[11px] font-bold text-emerald-700">
                      공식 근거
                    </span>
                    <span v-else class="rounded-md bg-amber-50 px-2 py-0.5 text-[11px] font-bold text-amber-700">
                      분석 전
                    </span>
                  </div>
                  <p v-if="shouldShowChecklistCondition(item)" class="mt-1 leading-6">{{ item.condition_text }}</p>
                </div>
              </div>
              <div class="flex flex-wrap items-center gap-2 pl-7 text-xs font-bold text-slate-500">
                <span class="rounded-md bg-white px-2 py-1 text-slate-600">출처 {{ checklistPageLabel(item) }}</span>
                <span v-if="item.confidence">근거 매칭 신뢰도 {{ Math.round(item.confidence * 100) }}%</span>
              </div>
            </div>
          </div>

          <div class="mt-5">
            <p class="mb-2 text-sm font-bold text-slate-700">필수 서류</p>
            <div class="flex flex-wrap gap-2">
              <span v-for="document in selectedNotice.required_documents" :key="document" class="rounded-md bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700">
                {{ document }}
              </span>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="flex items-center gap-2 text-lg font-bold text-slate-950">
            <CalendarDays class="h-5 w-5 text-slate-400" />
            주요 일정
          </h2>
          <div class="mt-5 divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200">
            <div v-for="(item, index) in fundingPlan.timeline" :key="`${item.label}-${index}`" class="grid gap-1 bg-white p-4 text-sm">
              <p class="font-bold text-slate-950">{{ item.label }}</p>
              <div class="flex flex-wrap justify-between gap-3 text-slate-500">
                <span>{{ item.date }}</span>
                <span>{{ formatMoney(item.amount) }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p class="inline-flex items-center gap-2 text-sm font-bold text-blue-700">
              <Bot class="h-4 w-4" />
              공식 공고문 분석 상태
            </p>
            <div class="mt-1 flex flex-wrap items-center gap-2">
              <h2 class="text-lg font-bold text-slate-950">{{ currentAnalysisSummary.label }}</h2>
              <span class="rounded-md px-2 py-1 text-xs font-bold" :class="analysisBadgeClass(currentAnalysisSummary)">
                {{ currentAnalysisSummary.is_mock ? '임시 추정' : currentAnalysisSummary.schema_version || currentAnalysisSummary.stage }}
              </span>
            </div>
            <p class="mt-2 text-sm leading-6 text-slate-500">
              {{ currentAnalysisSummary.next_action }}
            </p>
            <p v-if="currentAnalysisSummary.latest_error" class="mt-2 rounded-lg bg-rose-50 p-3 text-xs font-semibold leading-5 text-rose-700">
              {{ currentAnalysisSummary.latest_error }}
            </p>
            <p v-if="documentStatus" class="mt-2 text-xs font-semibold text-slate-500">
              문서 {{ documentStatus.document_count }}건 · 주택형 옵션 {{ documentStatus.unit_option_count }}개
              <span v-if="documentStatus.latest_extraction">
                · {{ documentStatus.latest_extraction.schema_version }} · {{ documentStatus.latest_extraction.status }}
              </span>
            </p>
          </div>
          <button
            type="button"
            class="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-lg bg-slate-900 px-4 text-sm font-bold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
            :disabled="analyzing"
            @click="handleAnalyzeNotice"
          >
            <Bot class="h-4 w-4" />
            {{ analyzing ? '분석 중' : unitOptions.length ? '다시 분석' : '공고문 분석하기' }}
          </button>
        </div>
      </section>

      <section v-if="unitOptions.length" class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-lg font-bold text-slate-950">검토 가능한 주택형 옵션</h2>
        <p class="mt-1 text-sm text-slate-500">
          {{ extractionLabel(documentStatus?.latest_extraction?.schema_version, documentStatus?.latest_extraction?.source) }} 기준입니다. 공식 원문과 다르면 원문이 우선입니다.
        </p>
        <div v-if="hasMultipleOptionGroups" class="mt-4 inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
          <button
            v-for="group in groupedUnitOptions"
            :key="group.key"
            type="button"
            class="inline-flex h-9 items-center gap-2 rounded-md px-3 text-sm font-bold transition"
            :class="activeUnitOptionGroup?.key === group.key ? 'bg-white text-slate-950 shadow-sm' : 'text-slate-500 hover:text-slate-800'"
            @click="selectOptionType(group.key)"
          >
            {{ group.label }}
            <span class="text-xs text-slate-400">{{ group.options.length }}</span>
          </button>
        </div>
        <div class="mt-5">
          <div v-if="activeUnitOptionGroup">
            <div class="grid gap-3 lg:grid-cols-3">
              <article v-for="option in visibleUnitOptions" :key="option.id" class="rounded-lg border border-slate-200 p-4" :class="fundingPlan.option_id === option.id ? 'border-blue-300 bg-blue-50/40' : ''">
                <div class="flex items-start justify-between gap-3">
                  <div>
                    <p class="text-xs font-bold text-blue-700">{{ option.unit_type }} · {{ option.floor_group }}</p>
                    <h3 class="mt-1 text-lg font-bold text-slate-950">{{ option.exclusive_area_m2 }}㎡</h3>
                  </div>
                  <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-bold text-slate-700" title="표 기반 추출은 주택형, 분양가, 납부일정이 같은 행에서 함께 확인될 때 높은 값으로 표시됩니다.">
                    신뢰도 {{ Math.round(option.confidence * 100) }}%
                  </span>
                </div>
                <p class="mt-2 text-xs font-bold text-slate-500">
                  {{ extractionLabel(option.extraction_schema_version, option.extraction_source) }}
                </p>
                <p class="mt-3 text-sm text-slate-500">기준 분양가</p>
                <p class="text-lg font-bold text-slate-950">{{ priceLabel(option.base_price) }}</p>
                <div class="mt-3 divide-y divide-slate-100 rounded-lg border border-slate-100">
                  <div v-for="schedule in option.payment_schedules" :key="schedule.id" class="grid gap-1 p-3 text-xs">
                    <div class="flex justify-between gap-2">
                      <span class="font-bold text-slate-700">{{ schedule.label }}</span>
                      <span class="text-slate-500">{{ schedule.due_date || '일정 확인 필요' }}</span>
                    </div>
                    <p class="text-right font-bold text-slate-950">{{ formatMoney(schedule.amount) }}</p>
                  </div>
                  <div v-if="option.loan_amount" class="grid gap-1 p-3 text-xs">
                    <div class="flex justify-between gap-2">
                      <span class="font-bold text-slate-700">융자금</span>
                      <span class="text-slate-500">잔금 이후 상환</span>
                    </div>
                    <p class="text-right font-bold text-slate-950">{{ formatMoney(option.loan_amount) }}</p>
                  </div>
                </div>
                <RouterLink
                  :to="{ path: `/funding/${selectedNotice.id}`, query: { option_id: option.id } }"
                  class="mt-3 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-bold text-white transition hover:bg-blue-700"
                >
                  이 옵션 자금 보기
                  <WalletCards class="h-4 w-4" />
                </RouterLink>
              </article>
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-amber-100 bg-amber-50 p-5 text-sm leading-6 text-amber-800">
        <p class="flex items-center gap-2 font-bold">
          <ShieldAlert class="h-4 w-4" />
          참고용 안내
        </p>
        <p class="mt-2">
          분석 결과는 공식 공고문과 입력 조건 기반의 참고 정보이며 청약 당첨, 정책 수급, 대출 승인을 보장하지 않습니다.
          실제 신청 전 공식 공고문에서 소득·자산·무주택·납부 일정을 확인해야 합니다.
        </p>
        <a
          v-if="selectedNotice.source_url"
          :href="selectedNotice.source_url"
          target="_blank"
          rel="noreferrer"
          class="mt-3 inline-flex items-center gap-1 font-bold text-amber-900 underline underline-offset-4"
        >
          공식 출처 열기
          <ExternalLink class="h-4 w-4" />
        </a>
      </section>
    </template>
  </div>
</template>
