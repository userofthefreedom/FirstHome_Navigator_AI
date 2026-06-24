<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import {
    ArrowRight,
    Bookmark,
    CheckCircle2,
    ClipboardCheck,
    ExternalLink,
    FileCheck2,
    LoaderCircle,
    ListChecks,
    Sparkles,
    ShieldAlert,
    Target,
    WalletCards,
} from 'lucide-vue-next';
import {
    addFavorite,
    fetchCoachSummary,
    fetchFavorites,
    fetchFundingPlan,
    fetchHousingRecommendations,
    fetchNotice,
    removeFavorite,
} from '../api/firsthome';
import { formatMoney, formatMoneyText } from '../utils/format';
import { readCurrentSelection, saveCurrentSelection } from '../utils/selectionState';
import { useProfileStore } from '../stores/profileStore';
import { useAuthStore } from '../stores/authStore';

const route = useRoute();
const profileStore = useProfileStore();
const authStore = useAuthStore();
const routeNoticeId = computed(() => Number(route.params.noticeId ?? 0) || null);
const routeOptionId = computed(() => Number(route.query.option_id ?? 0) || null);

const recommendations = ref([]);
const selectedNotice = ref(null);
const fundingPlan = ref(null);
const aiCoach = ref(null);
const favorites = ref([]);
const loading = ref(true);
const coachLoading = ref(false);
const switchingNoticeId = ref(null);
const savingFavorite = ref(false);
const error = ref('');
const activeOfficialIndex = ref(0);

const selectedRecommendation = computed(() => {
    if (!selectedNotice.value)
        return null;
    return recommendations.value.find((item) => item.notice_id === selectedNotice.value.id) ?? null;
});

const selectedOption = computed(() => {
    if (fundingPlan.value?.option_id) {
        return {
            option_id: fundingPlan.value.option_id,
            unit_type: fundingPlan.value.unit_type,
            floor_group: fundingPlan.value.floor_group,
            exclusive_area_m2: fundingPlan.value.exclusive_area_m2,
            base_price: fundingPlan.value.price,
        };
    }
    return selectedRecommendation.value?.best_option ?? null;
});

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

const profileName = computed(() => profileStore.profile.name || '사용자');

const scoreText = computed(() => {
    const item = selectedRecommendation.value;
    if (!item)
        return '확인 필요';
    return `${item.total_score}/${item.score_max ?? 100}점`;
});

const optionLabel = computed(() => {
    const option = selectedOption.value;
    if (!option)
        return '대표 주택형 확인 필요';
    return [option.unit_type, option.floor_group].filter(Boolean).join(' · ');
});

const deadlineDays = computed(() => {
    const value = selectedNotice.value?.application_deadline;
    if (!value)
        return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const deadline = new Date(`${value}T00:00:00`);
    if (Number.isNaN(deadline.getTime()))
        return null;
    return Math.ceil((deadline.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
});

const deadlineLabel = computed(() => {
    if (!selectedNotice.value?.application_deadline)
        return '공식 확인 필요';
    if (deadlineDays.value === null)
        return selectedNotice.value.application_deadline;
    if (deadlineDays.value < 0)
        return '마감 지남';
    if (deadlineDays.value === 0)
        return '오늘 마감';
    return `${deadlineDays.value}일 남음`;
});

const readinessLabel = computed(() => {
    if (!fundingPlan.value)
        return '계산 필요';
    if (fundingPlan.value.shortfall <= 0)
        return '계약금 준비 가능';
    return `월 ${formatMoney(fundingPlan.value.monthly_target)} 목표`;
});

const readinessPercent = computed(() => {
    if (!fundingPlan.value?.down_payment)
        return 0;
    return Math.min(100, Math.round((fundingPlan.value.available_cash / fundingPlan.value.down_payment) * 100));
});

const isFixtureCoach = computed(() => isFixtureNotice(selectedNotice.value) || Boolean(aiCoach.value?.is_fixture));

const coachSourceLabel = computed(() => {
    if (isFixtureCoach.value)
        return 'Fixture';
    if (aiCoach.value?.source === 'llm')
        return 'OpenAI LLM 신규 분석';
    if (aiCoach.value?.source === 'cached_llm')
        return '저장된 LLM 분석';
    if (aiCoach.value?.requires_login)
        return '예시 화면';
    return '규칙 기반 대체 플랜';
});

const coachSourceBadgeClass = computed(() => (
    isFixtureCoach.value
        ? 'bg-amber-400/15 text-amber-200'
        : 'bg-emerald-400/15 text-emerald-200'
));

const loginRequiredMessage = computed(() => aiCoach.value?.login_message || (
    isFixtureCoach.value
        ? '회원가입 또는 로그인하면 fixture 구조화 데이터와 선택 주택형을 바탕으로 OpenAI LLM 예시 코칭을 받을 수 있습니다. fixture에는 실제 공식 PDF 원문이 연결되어 있지 않습니다.'
        : '회원가입 또는 로그인하면 선택한 공고와 주택형, 공식 PDF 분석 근거를 바탕으로 OpenAI LLM 맞춤 코칭을 받을 수 있습니다.'
));

const coachLoadingDescription = computed(() => (
    isFixtureCoach.value
        ? 'Fixture 주택형, 금액, 일정, 서류 후보를 바탕으로 LLM 예시 코칭을 구성하는 중입니다. 실제 공식 PDF 원문은 연결되어 있지 않습니다.'
        : '지역우선, 특별공급, 제출서류, 선택품목, 납부 유의사항처럼 룰로 모두 처리하기 어려운 항목을 공고문 근거와 함께 찾아보고 있습니다.'
));

const planCards = computed(() => {
    if (!selectedNotice.value || !fundingPlan.value)
        return [];
    return [
        {
            label: '현재 선택',
            value: optionLabel.value,
            description: `${selectedNotice.value.region} · ${selectedNotice.value.supply_type}`,
        },
        {
            label: '계약금 부족액',
            value: formatMoney(fundingPlan.value.shortfall),
            description: readinessLabel.value,
            accent: fundingPlan.value.shortfall > 0,
        },
        {
            label: '접수 마감',
            value: selectedNotice.value.application_deadline || '공식 확인 필요',
            description: deadlineLabel.value,
        },
        {
            label: isFixtureCoach.value ? 'Fixture 근거' : '공식 확인',
            value: isFixtureCoach.value ? 'PDF 없음' : selectedNotice.value.official_document_status === 'verified' ? '분석 완료' : '확인 필요',
            description: isFixtureCoach.value ? '구조화 데이터 기준' : `${selectedNotice.value.unit_option_count ?? 0}개 주택형 옵션`,
        },
    ];
});

const decisionPoints = computed(() => {
    if (!selectedNotice.value || !fundingPlan.value)
        return [];
    const routeQuery = fundingPlan.value.option_id ? { option_id: fundingPlan.value.option_id } : {};
    const fundingPath = { path: `/funding/${selectedNotice.value.id}`, query: routeQuery };
    const noticePath = { path: `/notices/${selectedNotice.value.id}`, query: routeQuery };
    const sourceName = isFixtureCoach.value ? 'fixture 구조화 데이터' : '공식 공고문';
    const llmPoints = aiCoach.value?.decision_points ?? [];
    if (llmPoints.length) {
        return llmPoints.slice(0, 3).map((point) => ({
            title: formatMoneyText(point.title),
            body: formatMoneyText(point.body),
            to: decisionPointRoute(point, fundingPath, noticePath),
            cta: formatMoneyText(point.cta || '자세히 보기'),
        }));
    }
    const points = [
        {
            title: '선택 옵션의 납부 흐름을 확정하세요',
            body: `${optionLabel.value} 기준 계약금, 중도금, 잔금, 융자금 흐름을 ${sourceName} 기준으로 확인합니다.`,
            to: fundingPath,
            cta: '옵션 자금 보기',
        },
    ];
    if (fundingPlan.value.shortfall > 0) {
        points.push({
            title: '계약금 부족액을 준비 계획으로 바꾸세요',
            body: `현재 기준 부족액은 ${formatMoney(fundingPlan.value.shortfall)}입니다. ${fundingPlan.value.months_until_contract}개월 기준 ${readinessLabel.value}로 봅니다.`,
            to: '/profile',
            cta: '조건 수정',
        });
    }
    else {
        points.push({
            title: '계약금 이후 납부 일정을 비교하세요',
            body: '계약금은 준비 가능한 범위입니다. 이제 중도금, 잔금, 융자금 흐름을 비교할 차례입니다.',
            to: fundingPath,
            cta: '납부 일정 보기',
        });
    }
    points.push({
        title: isFixtureCoach.value ? 'Fixture에는 공식 PDF가 없음을 표시하세요' : '공식 공고문 기준을 마지막 기준으로 삼으세요',
        body: isFixtureCoach.value ? '무주택, 소득, 자산, 청약통장, 납부 일정은 fixture 구조화 데이터 기준의 예시이며 실제 공식 원문 근거가 없습니다.' : '무주택, 소득, 자산, 청약통장, 납부 일정은 화면 계산보다 공식 공고문 원문이 우선입니다.',
        to: noticePath,
        cta: isFixtureCoach.value ? 'Fixture 상세 보기' : '공식 근거 보기',
    });
    return points;
});

const weeklyTasks = computed(() => {
    const fromCoach = aiCoach.value?.todo_this_week ?? [];
    const base = isFixtureCoach.value
        ? [
            `${optionLabel.value} 기준 계약금 ${formatMoney(fundingPlan.value?.down_payment)}과 부족액 ${formatMoney(fundingPlan.value?.shortfall)}을 fixture 자금 계획으로 정리하세요.`,
            '이 후보는 실제 PDF가 없는 fixture이므로 공식 원문 확인 항목은 별도로 검증할 수 없다고 표시하세요.',
            'fixture에 들어있는 제출서류 후보와 자격 후보를 예시 체크리스트로만 검토하세요.',
            '지역우선, 특별공급, 선택품목, 감액 조건은 fixture 구조화 데이터 기준의 판단거리로 정리하세요.',
        ]
        : [
            `${optionLabel.value} 기준 계약금 ${formatMoney(fundingPlan.value?.down_payment)}과 부족액 ${formatMoney(fundingPlan.value?.shortfall)}을 준비 계획으로 바꾸세요.`,
            '무주택, 소득·자산, 청약통장 요건을 공식 공고문 페이지 기준으로 한 번에 확인하세요.',
            '당첨자 제출서류와 주민등록표등본 등 발급 서류의 준비 순서를 정하세요.',
            '지역우선, 특별공급, 선택품목, 감액 조건처럼 본인에게 적용될 공고문 세부 항목을 표시하세요.',
        ];
    if (aiCoach.value?.source === 'llm' && fromCoach.length) {
        return [...new Set([...fromCoach, ...base])].slice(0, 5).map(formatMoneyText);
    }
    return [...new Set([...base, ...fromCoach])].slice(0, 5).map(formatMoneyText);
});

const officialChecklist = computed(() => {
    const items = aiCoach.value?.official_checklist ?? [];
    if (isFixtureCoach.value && !items.length) {
        return ['fixture 주택형·분양가 데이터', 'fixture 납부 일정 데이터', 'fixture 자격·서류 후보'];
    }
    return items.length ? items : ['무주택 및 세대 구성 기준', '소득, 자산, 청약통장 가입 인정 기준', '접수 마감일, 계약일, 분양가와 납부 일정'];
});

const officialSectionEyebrow = computed(() => (isFixtureCoach.value ? 'Fixture 데이터 확인' : '공식 원문 확인'));
const officialSectionTitle = computed(() => (isFixtureCoach.value ? '공식 PDF가 없는 보강 데이터입니다' : '공고문에서 직접 대조할 것'));
const officialSectionDescription = computed(() => (
    isFixtureCoach.value
        ? '이 후보는 실제 공식 PDF 원문이 연결되지 않아, 아래 내용은 fixture 구조화 데이터와 LLM 해석 기준입니다.'
        : 'AI 답변보다 공식 공고문 원문을 우선합니다.'
));

const deepReviewItems = computed(() => {
    const items = aiCoach.value?.deep_review_items ?? [];
    if (items.length)
        return items.slice(0, 6).map((item) => ({
            ...item,
            title: formatMoneyText(item.title),
            body: formatMoneyText(item.body),
            why_it_matters: formatMoneyText(item.why_it_matters),
        }));
    return [
        {
            title: '지역우선 및 거주기간 기준',
            body: '공고문에 지역우선 물량이나 거주기간 기준이 있으면 현재 거주지와 전입일을 대조해야 합니다.',
            why_it_matters: '같은 공고라도 거주기간에 따라 우선순위나 배정 물량이 달라질 수 있습니다.',
        },
        {
            title: '특별공급 세부 자격',
            body: '다자녀, 신혼부부, 생애최초 등 특별공급 유형은 별도 소득, 자산, 세대 구성 기준을 가질 수 있습니다.',
            why_it_matters: '큰 공급유형만으로는 실제 신청 가능 유형을 확정할 수 없습니다.',
        },
        {
            title: '선택품목, 감액, 별도계약',
            body: '추가 선택품목이나 미선택 시 감액 조건이 있으면 실제 부담금과 계약 판단에 반영해야 합니다.',
            why_it_matters: '구조화된 분양가 외 비용이나 감액 조건이 자금 계획을 바꿀 수 있습니다.',
        },
    ];
});

const officialReviewPairs = computed(() => {
    const reviews = deepReviewItems.value;
    return officialChecklist.value.map((title, index) => {
        const review = reviews[index % Math.max(reviews.length, 1)];
        return {
            title,
            detailTitle: review?.title ?? title,
            body: review?.body ?? title,
            why_it_matters: review?.why_it_matters ?? '',
        };
    });
});

const compactCandidates = computed(() => recommendations.value.slice(0, 5));

function isFixtureNotice(notice) {
    const source = String(notice?.data_source || '').toLowerCase();
    return source.includes('fixture') || Boolean(notice?.source_meta?.fixture_id);
}

function candidateOptionLabel(item) {
    const option = item.best_option;
    if (!option)
        return '대표 주택형 확인 필요';
    return [option.unit_type, option.floor_group].filter(Boolean).join(' · ');
}

function candidatePrice(item) {
    return formatMoney(item.best_option?.base_price ?? item.price ?? 0);
}

function candidateReason(item) {
    if (item.best_option?.funding_insights?.down_payment_shortfall > 0) {
        return `계약금 부족 ${formatMoney(item.best_option.funding_insights.down_payment_shortfall)}`;
    }
    if (item.best_option?.loan_amount > 0) {
        return `융자금 ${formatMoney(item.best_option.loan_amount)} 별도 확인`;
    }
    return item.selection_summary || '조건 적합도를 기준으로 비교합니다.';
}

function decisionPointRoute(point, fundingPath, noticePath) {
    const text = `${point?.title ?? ''} ${point?.body ?? ''} ${point?.cta ?? ''}`;
    if (text.includes('서류') || text.includes('공식') || text.includes('지역우선') || text.includes('특별공급') || text.includes('선택품목') || text.includes('추가 선택') || text.includes('추가선택') || text.includes('감액')) {
        return noticePath;
    }
    if (text.includes('조건') || text.includes('프로필') || text.includes('현금') || text.includes('저축')) {
        return '/profile';
    }
    return fundingPath;
}

async function resolveInitialNoticeId(nextRecommendations) {
    if (routeNoticeId.value)
        return routeNoticeId.value;
    const stored = readCurrentSelection();
    if (stored.noticeId)
        return stored.noticeId;
    return nextRecommendations[0]?.notice_id ?? null;
}

function optionIdForNotice(targetNoticeId) {
    if (routeNoticeId.value === targetNoticeId && routeOptionId.value)
        return routeOptionId.value;
    const stored = readCurrentSelection();
    if (stored.noticeId === targetNoticeId && stored.optionId)
        return stored.optionId;
    const recommendation = recommendations.value.find((item) => item.notice_id === targetNoticeId);
    return recommendation?.best_option?.option_id ?? null;
}

async function loadTargetNotice(targetNoticeId) {
    if (!targetNoticeId)
        return;
    switchingNoticeId.value = targetNoticeId;
    aiCoach.value = null;
    activeOfficialIndex.value = 0;
    const optionId = optionIdForNotice(targetNoticeId);
    const [noticeResponse, fundingResponse] = await Promise.all([
        fetchNotice(targetNoticeId),
        fetchFundingPlan(targetNoticeId, optionId),
    ]);
    selectedNotice.value = noticeResponse;
    fundingPlan.value = fundingResponse;
    const resolvedOptionId = fundingResponse.option_id || optionId;
    saveCurrentSelection(targetNoticeId, resolvedOptionId);
    switchingNoticeId.value = null;
    coachLoading.value = true;
    try {
        aiCoach.value = await fetchCoachSummary(targetNoticeId, profileStore.profile, resolvedOptionId);
    }
    catch {
        error.value = 'AI 코치 LLM 분석을 아직 불러오지 못했습니다. 공고와 자금 정보는 표시했고, 잠시 후 다시 시도해 주세요.';
    }
    finally {
        coachLoading.value = false;
    }
}

async function loadCoach() {
    loading.value = true;
    error.value = '';
    try {
        if (!profileStore.loaded) {
            await profileStore.hydrateProfile();
        }
        if (!authStore.loaded) {
            await authStore.hydrateAuth();
        }
        const [recommendationResponse, favoriteResponse] = await Promise.all([
            fetchHousingRecommendations(),
            fetchFavorites(),
        ]);
        recommendations.value = recommendationResponse;
        favorites.value = favoriteResponse;
        await loadTargetNotice(await resolveInitialNoticeId(recommendationResponse));
    }
    catch {
        error.value = 'AI 코치 정보를 불러오지 못했습니다. Django 서버가 실행 중인지 확인하세요.';
    }
    finally {
        loading.value = false;
        switchingNoticeId.value = null;
        coachLoading.value = false;
    }
}

async function selectCandidate(item) {
    if (item.notice_id === selectedNotice.value?.id || switchingNoticeId.value)
        return;
    try {
        error.value = '';
        await loadTargetNotice(item.notice_id);
    }
    catch {
        error.value = '선택한 후보의 준비 플랜을 불러오지 못했습니다.';
        switchingNoticeId.value = null;
        coachLoading.value = false;
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

watch([routeNoticeId, routeOptionId], () => {
    void loadCoach();
});
onMounted(loadCoach);
</script>

<template>
  <div class="space-y-5">
    <section v-if="loading" class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div class="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p class="inline-flex items-center gap-2 rounded-md bg-emerald-50 px-2.5 py-1 text-sm font-black text-emerald-700">
            <Sparkles class="h-4 w-4" />
            AI 코치 분석 준비
          </p>
          <h1 class="mt-4 text-2xl font-black text-slate-950">공고문과 선택 옵션을 읽고 있습니다</h1>
          <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
            추천 후보, 선택 주택형, 자금 로드맵, 공식 PDF 분석 근거를 모아 맞춤 코칭을 구성하는 중입니다.
          </p>
        </div>
        <div class="relative flex h-24 w-24 shrink-0 items-center justify-center">
          <div class="loading-orbit" />
          <LoaderCircle class="h-10 w-10 animate-spin text-emerald-600" />
        </div>
      </div>
      <div class="mt-6 grid gap-3 md:grid-cols-3">
        <div class="rounded-lg border border-slate-100 bg-slate-50 p-4">
          <p class="text-xs font-black text-emerald-700">1단계</p>
          <p class="mt-1 text-sm font-bold text-slate-900">선택 공고 확인</p>
          <div class="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
            <div class="loading-bar h-full rounded-full bg-emerald-500" />
          </div>
        </div>
        <div class="rounded-lg border border-slate-100 bg-slate-50 p-4">
          <p class="text-xs font-black text-emerald-700">2단계</p>
          <p class="mt-1 text-sm font-bold text-slate-900">자금 조건 계산</p>
          <div class="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
            <div class="loading-bar loading-bar-delay h-full rounded-full bg-emerald-500" />
          </div>
        </div>
        <div class="rounded-lg border border-slate-100 bg-slate-50 p-4">
          <p class="text-xs font-black text-emerald-700">3단계</p>
          <p class="mt-1 text-sm font-bold text-slate-900">LLM 코칭 구성</p>
          <div class="mt-3 h-2 overflow-hidden rounded-full bg-slate-200">
            <div class="loading-bar loading-bar-delay-more h-full rounded-full bg-emerald-500" />
          </div>
        </div>
      </div>
      <div class="coach-loading-workbench mt-6">
        <div class="coach-loading-canvas">
          <div class="coach-loading-document">
            <span class="coach-loading-docline w-3/4" />
            <span class="coach-loading-docline w-11/12" />
            <span class="coach-loading-docline w-2/3" />
            <span class="coach-loading-docline w-5/6" />
            <span class="coach-loading-scan" />
          </div>
          <div class="coach-loading-document coach-loading-document-back">
            <span class="coach-loading-docline w-2/3" />
            <span class="coach-loading-docline w-4/5" />
            <span class="coach-loading-docline w-1/2" />
          </div>
          <div class="coach-loading-flow" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
        </div>
        <div class="coach-loading-panel">
          <p class="text-sm font-black text-slate-950">분석 보드를 구성하고 있습니다</p>
          <p class="mt-1 text-sm leading-6 text-slate-600">
            공고문 근거, 선택 주택형, 자금 계획, 이번 주 행동 순서를 한 화면에 맞게 정리합니다.
          </p>
          <div class="mt-4 grid gap-3">
            <div class="coach-loading-task">
              <span>공식 근거 문장 추출</span>
              <strong>PDF</strong>
            </div>
            <div class="coach-loading-task">
              <span>계약금과 준비 목표 계산</span>
              <strong>자금</strong>
            </div>
            <div class="coach-loading-task">
              <span>바로 처리할 일 우선순위화</span>
              <strong>코치</strong>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section v-else-if="error && !selectedNotice" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-semibold text-amber-800">
      {{ error }}
    </section>

    <template v-else-if="selectedNotice && fundingPlan">
      <section class="rounded-lg border border-slate-200 bg-slate-950 p-5 text-white shadow-sm sm:p-6">
        <div class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div class="max-w-4xl">
            <p class="inline-flex items-center gap-2 rounded-md bg-emerald-500/15 px-2.5 py-1 text-sm font-bold text-emerald-200">
              <Target class="h-4 w-4" />
              AI 청약 준비 플랜
            </p>
            <h1 class="mt-4 text-3xl font-bold tracking-tight">{{ profileName }}님의 다음 선택과 할 일</h1>
            <p class="mt-3 text-sm leading-6 text-slate-300">
              현재 추천 후보와 선택 주택형을 기준으로 자금 부담, 공식 확인 항목, 이번 주 행동을 정리했습니다.
            </p>
            <div class="mt-4 flex flex-wrap gap-2">
              <span class="rounded-md bg-white/10 px-2.5 py-1 text-xs font-bold text-slate-200">{{ selectedNotice.region }}</span>
              <span class="rounded-md bg-white/10 px-2.5 py-1 text-xs font-bold text-slate-200">{{ selectedNotice.supply_type }}</span>
              <span class="rounded-md px-2.5 py-1 text-xs font-bold" :class="coachSourceBadgeClass">{{ coachSourceLabel }}</span>
            </div>
          </div>
          <div class="grid gap-2 sm:min-w-56">
            <div class="rounded-lg bg-white/10 px-5 py-4">
              <p class="text-xs font-bold text-slate-300">현재 우선 후보</p>
              <p class="mt-2 text-lg font-black leading-6">{{ selectedNotice.title }}</p>
              <p class="mt-2 text-sm font-bold text-emerald-200">{{ scoreText }}</p>
            </div>
            <button
              type="button"
              class="inline-flex h-11 items-center justify-center gap-2 rounded-lg bg-white px-4 text-sm font-bold text-slate-950 transition hover:bg-slate-100 disabled:opacity-60"
              :disabled="savingFavorite"
              @click="toggleFavorite"
            >
              <Bookmark class="h-4 w-4" :class="isFavorite ? 'fill-blue-600 text-blue-600' : ''" />
              {{ isFavorite ? '공고 저장됨' : '공고 저장' }}
            </button>
          </div>
        </div>
      </section>

      <section v-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-4 text-sm font-semibold text-amber-800">
        {{ error }}
      </section>

      <section v-if="coachLoading" class="overflow-hidden rounded-lg border border-emerald-200 bg-emerald-50 p-5 text-sm leading-6 text-emerald-950 shadow-sm">
        <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p class="inline-flex items-center gap-2 font-black">
              <LoaderCircle class="h-4 w-4 animate-spin" />
              LLM이 공고문 세부 조건을 정리하는 중입니다
            </p>
            <p class="mt-1 text-emerald-800">{{ coachLoadingDescription }}</p>
          </div>
          <div class="flex min-w-56 gap-2">
            <span class="loading-dot" />
            <span class="loading-dot loading-dot-delay" />
            <span class="loading-dot loading-dot-delay-more" />
          </div>
        </div>
        <div class="mt-4 h-2 overflow-hidden rounded-full bg-emerald-100">
          <div class="loading-bar h-full rounded-full bg-emerald-600" />
        </div>
      </section>

      <section v-if="aiCoach?.requires_login" class="rounded-lg border border-blue-200 bg-blue-50 p-5 text-sm leading-6 text-blue-900 shadow-sm">
        <p class="font-black">현재 화면은 예시 코칭입니다.</p>
        <p class="mt-1">{{ loginRequiredMessage }}</p>
        <RouterLink to="/auth" class="mt-3 inline-flex h-10 items-center justify-center rounded-lg bg-blue-700 px-4 text-sm font-black text-white transition hover:bg-blue-800">
          로그인 / 회원가입
        </RouterLink>
      </section>

      <section class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <article
          v-for="card in planCards"
          :key="card.label"
          class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
          :class="card.accent ? 'border-amber-200 bg-amber-50' : ''"
        >
          <p class="text-sm font-bold text-slate-500">{{ card.label }}</p>
          <p class="mt-2 text-2xl font-black text-slate-950">{{ card.value }}</p>
          <p class="mt-2 text-sm text-slate-500">{{ card.description }}</p>
        </article>
      </section>

      <section class="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]">
        <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="inline-flex items-center gap-2 text-sm font-bold text-emerald-700">
                <ClipboardCheck class="h-4 w-4" />
                이번 주 행동 순서
              </p>
              <h2 class="mt-1 text-xl font-black text-slate-950">바로 처리할 일</h2>
            </div>
            <span class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-600">{{ weeklyTasks.length }}개</span>
          </div>
          <ol class="mt-5 space-y-3">
            <li v-for="(todo, index) in weeklyTasks" :key="todo" class="flex gap-3 rounded-lg border border-slate-100 bg-slate-50 p-4">
              <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-emerald-600 text-xs font-black text-white">
                {{ index + 1 }}
              </span>
              <span class="text-sm leading-6 text-slate-700">{{ todo }}</span>
            </li>
          </ol>
        </section>

        <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="inline-flex items-center gap-2 text-sm font-bold text-emerald-700">
            <WalletCards class="h-4 w-4" />
            자금 준비 상태
          </p>
          <div class="mt-4">
            <div class="flex items-end justify-between gap-3">
              <div>
                <p class="text-sm font-bold text-slate-500">계약금 준비율</p>
                <p class="mt-1 text-3xl font-black text-slate-950">{{ readinessPercent }}%</p>
              </div>
              <p class="text-right text-sm font-bold text-slate-600">{{ readinessLabel }}</p>
            </div>
            <div class="mt-4 h-3 rounded-full bg-slate-100">
              <div class="h-3 rounded-full bg-emerald-500" :style="{ width: `${readinessPercent}%` }" />
            </div>
          </div>
          <div class="mt-5 grid grid-cols-2 gap-3">
            <div class="rounded-lg bg-slate-50 p-4">
              <p class="text-xs font-bold text-slate-500">분양가</p>
              <p class="mt-1 text-lg font-black text-slate-950">{{ formatMoney(fundingPlan.price) }}</p>
            </div>
            <div class="rounded-lg bg-slate-50 p-4">
              <p class="text-xs font-bold text-slate-500">계약금</p>
              <p class="mt-1 text-lg font-black text-slate-950">{{ formatMoney(fundingPlan.down_payment) }}</p>
            </div>
            <div class="rounded-lg bg-slate-50 p-4">
              <p class="text-xs font-bold text-slate-500">보유 현금</p>
              <p class="mt-1 text-lg font-black text-slate-950">{{ formatMoney(fundingPlan.available_cash) }}</p>
            </div>
            <div class="rounded-lg bg-slate-50 p-4">
              <p class="text-xs font-bold text-slate-500">부족액</p>
              <p class="mt-1 text-lg font-black" :class="fundingPlan.shortfall > 0 ? 'text-amber-700' : 'text-emerald-700'">
                {{ formatMoney(fundingPlan.shortfall) }}
              </p>
            </div>
          </div>
        </section>
      </section>

      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p class="inline-flex items-center gap-2 text-sm font-bold text-purple-700">
              <Sparkles class="h-4 w-4" />
              {{ officialSectionEyebrow }}
            </p>
            <h2 class="mt-1 text-xl font-black text-slate-950">{{ officialSectionTitle }}</h2>
          </div>
          <p class="text-sm font-semibold text-slate-500">{{ officialSectionDescription }}</p>
        </div>
        <div v-if="isFixtureCoach" class="mt-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold leading-6 text-amber-900">
          Fixture 후보는 실제 공식 원문 보기나 공식 출처 버튼을 제공하지 않습니다. LLM은 fixture에 들어있는 주택형, 금액, 일정, 서류 후보를 기준으로 예시 코칭을 만들며 실제 신청 판단에는 사용할 수 없습니다.
        </div>
        <div class="mt-5 grid gap-5 xl:grid-cols-[minmax(260px,0.42fr)_minmax(0,1fr)]">
          <div class="official-rail">
            <button
              v-for="(item, index) in officialReviewPairs"
              :key="item.title"
              type="button"
              class="official-rail-item w-full text-left transition"
              :class="activeOfficialIndex === index ? 'text-emerald-700' : 'text-slate-700 hover:text-slate-950'"
              @click="activeOfficialIndex = index"
            >
              <span class="official-rail-dot" />
              <span class="block text-sm font-bold">{{ item.title }}</span>
            </button>
          </div>
          <article class="official-detail-panel">
            <p class="text-xs font-bold text-emerald-700">
              {{ officialReviewPairs[activeOfficialIndex]?.title || officialReviewPairs[0]?.title }}
            </p>
            <h3 class="mt-2 text-lg font-bold text-slate-950">
              {{ officialReviewPairs[activeOfficialIndex]?.detailTitle || officialReviewPairs[0]?.detailTitle }}
            </h3>
            <p class="mt-3 text-sm leading-7 text-slate-700">
              {{ officialReviewPairs[activeOfficialIndex]?.body || officialReviewPairs[0]?.body }}
            </p>
            <p
              v-if="officialReviewPairs[activeOfficialIndex]?.why_it_matters || officialReviewPairs[0]?.why_it_matters"
              class="mt-4 rounded-lg bg-white px-4 py-3 text-xs font-bold leading-5 text-slate-600"
            >
              {{ officialReviewPairs[activeOfficialIndex]?.why_it_matters || officialReviewPairs[0]?.why_it_matters }}
            </p>
          </article>
        </div>
      </section>

      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <p class="inline-flex items-center gap-2 text-sm font-bold text-blue-700">
          <ListChecks class="h-4 w-4" />
          선택 판단 기준
        </p>
        <h2 class="mt-1 text-xl font-black text-slate-950">무엇을 먼저 선택할지</h2>
        <div class="mt-5 grid gap-3 lg:grid-cols-3">
          <article v-for="point in decisionPoints" :key="point.title" class="rounded-lg border border-slate-200 p-4">
            <h3 class="font-black text-slate-950">{{ point.title }}</h3>
            <p class="mt-2 text-sm leading-6 text-slate-600">{{ point.body }}</p>
            <RouterLink :to="point.to" class="mt-3 inline-flex items-center gap-1 text-sm font-black text-blue-700">
              {{ point.cta }}
              <ArrowRight class="h-4 w-4" />
            </RouterLink>
          </article>
        </div>
      </section>

      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p class="inline-flex items-center gap-2 text-sm font-bold text-blue-700">
              <FileCheck2 class="h-4 w-4" />
              검토 후보 비교
            </p>
            <h2 class="mt-1 text-xl font-black text-slate-950">지금 선택할 후보</h2>
          </div>
          <RouterLink to="/recommendations" class="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 px-4 text-sm font-black text-slate-700 transition hover:bg-slate-50">
            추천 목록 보기
          </RouterLink>
        </div>
        <div class="mt-5 grid gap-3 xl:grid-cols-5">
          <button
            v-for="(item, index) in compactCandidates"
            :key="item.notice_id"
            type="button"
            class="rounded-lg border p-4 text-left transition"
            :class="item.notice_id === selectedNotice.id ? 'border-emerald-500 bg-emerald-50 ring-1 ring-emerald-500' : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50'"
            :disabled="switchingNoticeId === item.notice_id"
            @click="selectCandidate(item)"
          >
            <span class="rounded-md bg-slate-950 px-2 py-1 text-xs font-black text-white">후보 {{ index + 1 }}</span>
            <h3 class="mt-3 line-clamp-2 min-h-12 text-sm font-black leading-6 text-slate-950">{{ item.title }}</h3>
            <p class="mt-2 text-xs font-bold text-emerald-700">{{ candidateOptionLabel(item) }}</p>
            <p class="mt-1 text-lg font-black text-slate-950">{{ candidatePrice(item) }}</p>
            <p class="mt-2 text-xs leading-5 text-slate-500">{{ candidateReason(item) }}</p>
            <div class="mt-3 flex items-center justify-between text-xs font-black">
              <span class="text-slate-500">{{ item.application_deadline }}</span>
              <span class="text-blue-700">{{ item.total_score }}/{{ item.score_max ?? 100 }}점</span>
            </div>
          </button>
        </div>
      </section>

      <section class="rounded-lg border border-amber-100 bg-amber-50 p-5 text-sm leading-6 text-amber-800">
        <p class="flex items-center gap-2 font-bold">
          <ShieldAlert class="h-4 w-4" />
          주의
        </p>
        <p class="mt-2">
          {{ aiCoach?.warning || '추천 결과는 공고문 분석과 입력 프로필 기반의 참고 정보이며 청약 당첨, 정책 수급, 대출 승인을 보장하지 않습니다.' }}
        </p>
        <div class="mt-3 flex flex-wrap gap-2">
          <span v-if="isFixtureNotice(selectedNotice)" class="inline-flex items-center rounded-md bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-900">
            Fixture · 공식 PDF 없음
          </span>
          <span v-if="isFixtureNotice(selectedNotice)" class="inline-flex items-center rounded-md bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-900">
            공식 출처 버튼 미제공
          </span>
          <a
            v-else-if="selectedNotice.source_url"
            :href="selectedNotice.source_url"
            target="_blank"
            rel="noreferrer"
            class="inline-flex items-center gap-1 font-bold text-amber-900 underline underline-offset-4"
          >
            공식 출처 열기
            <ExternalLink class="h-4 w-4" />
          </a>
          <RouterLink
            :to="{ path: `/notices/${selectedNotice.id}`, query: fundingPlan.option_id ? { option_id: fundingPlan.option_id } : {} }"
            class="inline-flex items-center gap-1 font-bold text-amber-900 underline underline-offset-4"
          >
            공고 상세 보기
            <ExternalLink class="h-4 w-4" />
          </RouterLink>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.loading-orbit {
    position: absolute;
    inset: 0;
    border-radius: 9999px;
    border: 2px solid rgba(16, 185, 129, 0.16);
    border-top-color: rgba(16, 185, 129, 0.85);
    animation: firsthome-orbit 1.6s linear infinite;
}

.loading-bar {
    width: 45%;
    animation: firsthome-scan 1.7s ease-in-out infinite;
}

.loading-bar-delay {
    animation-delay: 0.18s;
}

.loading-bar-delay-more {
    animation-delay: 0.36s;
}

.loading-dot {
    height: 0.75rem;
    width: 0.75rem;
    border-radius: 9999px;
    background: rgb(5, 150, 105);
    opacity: 0.35;
    animation: firsthome-dot 1.2s ease-in-out infinite;
}

.loading-dot-delay {
    animation-delay: 0.2s;
}

.loading-dot-delay-more {
    animation-delay: 0.4s;
}

.coach-loading-workbench {
    display: grid;
    gap: 1rem;
}

@media (min-width: 1024px) {
    .coach-loading-workbench {
        grid-template-columns: minmax(0, 1.1fr) minmax(320px, 0.9fr);
    }
}

.coach-loading-canvas,
.coach-loading-panel {
    min-height: 15rem;
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: 0.75rem;
    background:
        radial-gradient(circle at 18% 18%, rgba(64, 215, 186, 0.16), transparent 28%),
        linear-gradient(135deg, rgba(64, 215, 186, 0.08), rgba(59, 130, 246, 0.05)),
        var(--card);
}

.coach-loading-canvas {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
}

.coach-loading-panel {
    padding: 1.25rem;
}

.coach-loading-document {
    position: absolute;
    left: 16%;
    top: 18%;
    z-index: 2;
    display: grid;
    width: min(20rem, 58%);
    gap: 0.75rem;
    border: 1px solid rgba(64, 215, 186, 0.22);
    border-radius: 0.85rem;
    background: rgba(15, 23, 42, 0.72);
    padding: 1.3rem;
    box-shadow: 0 1.5rem 3rem rgba(0, 0, 0, 0.18);
}

.coach-loading-document-back {
    left: auto;
    right: 14%;
    top: 28%;
    z-index: 1;
    opacity: 0.68;
    transform: scale(0.92);
}

.coach-loading-docline {
    display: block;
    height: 0.55rem;
    border-radius: 999px;
    background: linear-gradient(90deg, rgba(64, 215, 186, 0.65), rgba(148, 163, 184, 0.2));
}

.coach-loading-scan {
    position: absolute;
    inset: 0;
    background: linear-gradient(180deg, transparent, rgba(64, 215, 186, 0.24), transparent);
    animation: firsthome-document-scan 2.2s ease-in-out infinite;
}

.coach-loading-flow {
    position: absolute;
    bottom: 1.4rem;
    left: 10%;
    right: 10%;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.75rem;
}

.coach-loading-flow span {
    height: 0.45rem;
    border-radius: 999px;
    background: rgba(64, 215, 186, 0.34);
    animation: firsthome-flow-pulse 1.7s ease-in-out infinite;
}

.coach-loading-flow span:nth-child(2) {
    animation-delay: 0.18s;
}

.coach-loading-flow span:nth-child(3) {
    animation-delay: 0.36s;
}

.coach-loading-task {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.8rem;
    color: var(--text);
    font-size: 0.88rem;
    font-weight: 800;
}

.coach-loading-task:last-child {
    border-bottom: 0;
    padding-bottom: 0;
}

.coach-loading-task strong {
    border-radius: 999px;
    background: rgba(64, 215, 186, 0.16);
    color: var(--primary);
    padding: 0.3rem 0.55rem;
    font-size: 0.75rem;
    font-weight: 900;
}

:root[data-theme="light"] .coach-loading-document {
    background: rgba(248, 250, 252, 0.88);
    box-shadow: 0 1.25rem 2.5rem rgba(15, 23, 42, 0.12);
}

:root[data-theme="light"] .coach-loading-docline {
    background: linear-gradient(90deg, rgba(15, 118, 110, 0.7), rgba(100, 116, 139, 0.2));
}

@keyframes firsthome-orbit {
    to {
        transform: rotate(360deg);
    }
}

@keyframes firsthome-scan {
    0% {
        transform: translateX(-120%);
    }
    55% {
        transform: translateX(80%);
    }
    100% {
        transform: translateX(240%);
    }
}

@keyframes firsthome-dot {
    0%,
    100% {
        opacity: 0.35;
        transform: translateY(0);
    }
    50% {
        opacity: 1;
        transform: translateY(-0.25rem);
    }
}

@keyframes firsthome-document-scan {
    0% {
        transform: translateY(-100%);
        opacity: 0;
    }
    20%,
    80% {
        opacity: 1;
    }
    100% {
        transform: translateY(100%);
        opacity: 0;
    }
}

@keyframes firsthome-flow-pulse {
    0%,
    100% {
        opacity: 0.35;
        transform: scaleX(0.78);
        transform-origin: left;
    }
    50% {
        opacity: 1;
        transform: scaleX(1);
    }
}
</style>
