<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { Bot, CalendarDays, ClipboardList, Route, SearchCheck, Sparkles, Trophy, WalletCards } from 'lucide-vue-next';
import { fetchDashboard, fetchFundingPlan, fetchLatestCoachSummary, fetchNotices } from '../api/firsthome';
import { formatMoney, formatMoneyText } from '../utils/format';
import { readCurrentSelection, saveCurrentSelection, syncCurrentSelectionWithAccount } from '../utils/selectionState';
import { useAuthStore } from '../stores/authStore';
import { useProfileStore } from '../stores/profileStore';
const profileStore = useProfileStore();
const authStore = useAuthStore();
const loading = ref(true);
const error = ref('');
const dashboard = ref(null);
const notices = ref([]);
const selectedId = ref(null);
const selectedPlan = ref(null);
const selectedCoachSummary = ref(null);
const latestCoachRequestKey = ref('');
const selectedCalendarDay = ref(null);
const selectedMonthKey = ref('');
const calendarOpen = ref(false);
const recommendations = computed(() => dashboard.value?.top_recommendations ?? []);
const selectedRecommendation = computed(() => recommendations.value.find((item) => item.notice_id === selectedId.value) ?? recommendations.value[0]);
const selected = computed(() => notices.value.find((notice) => notice.id === selectedId.value) ?? notices.value[0]);
const isLoggedIn = computed(() => Boolean(authStore.user?.is_authenticated));
const weekDays = ['일', '월', '화', '수', '목', '금', '토'];
function scoreLabel(item) {
    if (!item)
        return '0점';
    return `${item.total_score}/${item.score_max ?? 100}점`;
}
function scorePercent(item) {
    if (!item)
        return 0;
    const max = item.score_max || 100;
    return Math.min(100, Math.round(((item.total_score || 0) / max) * 100));
}
const selectedBestOption = computed(() => selectedRecommendation.value?.best_option ?? null);
const currentProfile = computed(() => dashboard.value?.profile ?? {});
const selectedRouteOptionId = computed(() => {
    const storedSelection = readCurrentSelection();
    if (storedSelection.noticeId === selected.value?.id && storedSelection.optionId)
        return storedSelection.optionId;
    return selectedRecommendation.value?.best_option?.option_id ?? null;
});
const selectedAiCoachRoute = computed(() => ({
    path: `/ai-coach/${selected.value?.id}`,
    query: selectedRouteOptionId.value ? { option_id: selectedRouteOptionId.value } : {},
}));
function recommendationPrice(item) {
    return Number(item?.best_option?.base_price || item?.price || 0);
}
const selectedDisplayPrice = computed(() => Number(selectedBestOption.value?.base_price || selected.value?.price || 0));
const selectedShortTitle = computed(() => shortNoticeTitle(selected.value?.title));
const selectedOptionLabel = computed(() => {
    const option = selectedBestOption.value;
    if (!option)
        return selected.value?.area || '대표 주택형';
    return [option.unit_type, option.floor_group].filter(Boolean).join(' · ') || '대표 주택형';
});
function parseDeadline(value) {
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? null : date;
}
function todayStart() {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return today;
}
function isActiveNotice(notice) {
    const deadline = parseDeadline(notice?.application_deadline);
    return Boolean(deadline && deadline >= todayStart());
}
function monthKey(date) {
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
}
function monthLabel(key) {
    const [year, month] = key.split('-');
    return `${year}년 ${Number(month)}월`;
}
function compactMonthLabel(key) {
    const [year, month] = key.split('-');
    return `${String(year).slice(2)}년 ${Number(month)}월`;
}
const sortedNotices = computed(() => {
    return [...notices.value]
        .filter(isActiveNotice)
        .sort((a, b) => a.application_deadline.localeCompare(b.application_deadline) || a.title.localeCompare(b.title));
});
const availableMonths = computed(() => {
    const buckets = new Map();
    for (const notice of sortedNotices.value) {
        const deadline = parseDeadline(notice.application_deadline);
        if (!deadline)
            continue;
        const key = monthKey(deadline);
        buckets.set(key, (buckets.get(key) ?? 0) + 1);
    }
    return [...buckets.entries()]
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([key, count]) => ({ key, label: monthLabel(key), compactLabel: compactMonthLabel(key), count }));
});
const activeMonthKey = computed(() => selectedMonthKey.value || availableMonths.value[0]?.key || '2026-06');
const calendarMonth = computed(() => {
    const [year, month] = activeMonthKey.value.split('-').map(Number);
    return new Date(year, month - 1, 1);
});
const calendarTitle = computed(() => `${calendarMonth.value.getFullYear()}년 ${calendarMonth.value.getMonth() + 1}월 청약 캘린더`);
const calendarSlots = computed(() => {
    const year = calendarMonth.value.getFullYear();
    const month = calendarMonth.value.getMonth();
    const firstWeekDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const slotCount = Math.ceil((firstWeekDay + daysInMonth) / 7) * 7;
    return Array.from({ length: slotCount }, (_, index) => {
        const day = index - firstWeekDay + 1;
        return {
            key: `${year}-${month}-${index}`,
            day: day >= 1 && day <= daysInMonth ? day : null,
        };
    });
});
const eventsByDay = computed(() => {
    return sortedNotices.value.reduce((acc, item) => {
        const deadline = parseDeadline(item.application_deadline);
        if (!deadline)
            return acc;
        if (deadline.getFullYear() !== calendarMonth.value.getFullYear() || deadline.getMonth() !== calendarMonth.value.getMonth())
            return acc;
        const day = deadline.getDate();
        acc[day] = [
            ...(acc[day] ?? []),
            {
                id: item.id,
                label: shortNoticeTitle(item.title),
                region: item.region,
                supplyType: item.supply_type,
                deadline: item.application_deadline,
                type: item.id === selectedId.value ? 'selected' : 'deadline',
            },
        ];
        return acc;
    }, {});
});
const selectedDayEvents = computed(() => {
    if (selectedCalendarDay.value)
        return eventsByDay.value[selectedCalendarDay.value] ?? [];
    return sortedNotices.value
        .filter((item) => {
        const deadline = parseDeadline(item.application_deadline);
        return deadline && monthKey(deadline) === activeMonthKey.value;
    })
        .slice(0, 6)
        .map((item) => ({
        id: item.id,
        label: shortNoticeTitle(item.title),
        region: item.region,
        supplyType: item.supply_type,
        deadline: item.application_deadline,
        type: item.id === selectedId.value ? 'selected' : 'deadline',
    }));
});
const preApplyTasks = computed(() => {
    if (!selected.value)
        return [];
    const requiredDocuments = selected.value.required_documents ?? [];
    return [
        {
            title: '주택형 옵션의 공식 자격 확인',
            date: '오늘',
            status: '진행',
            description: `${selected.value.supply_type} 조건, 무주택 기준, 청약통장 가입기간을 선택 후보의 공식 공고문 기준으로 다시 확인합니다.`,
        },
        {
            title: '필수 서류 발급 가능 여부 확인',
            date: 'D-7',
            status: '준비',
            description: `${requiredDocuments.slice(0, 3).join(', ') || '필수 서류'} 발급 시점과 유효 기간을 확인합니다.`,
        },
        {
            title: '접수 전 공식 일정 고정',
            date: selected.value.application_deadline,
            status: '마감',
            description: '접수 마감, 당첨자 발표, 계약일을 공식 공고문 기준으로 다시 확인하고 일정에 남깁니다.',
        },
        {
            title: '계약금 부족액 준비',
            date: selected.value.contract_date,
            status: '예정',
            description: `부족액 ${formatMoney(selectedPlan.value?.shortfall ?? 0)}을 기준으로 계약 전까지 필요한 월 저축 목표를 점검합니다.`,
        },
    ];
});
const coachTodos = computed(() => (selectedCoachSummary.value?.todo_this_week ?? []).filter(Boolean).slice(0, 5).map(formatMoneyText));
const dashboardBaseTasks = computed(() => {
    if (!selected.value)
        return [];
    const optionLabel = selectedOptionLabel.value;
    const downPayment = formatMoney(selectedPlan.value?.down_payment ?? 0);
    const shortfall = formatMoney(selectedPlan.value?.shortfall ?? 0);
    return [
        `${optionLabel} 기준 계약금 ${downPayment}과 부족액 ${shortfall}을 준비 계획으로 바꾸세요.`,
        '무주택, 소득·자산, 청약통장 요건을 공식 공고문 페이지 기준으로 한 번에 확인하세요.',
        '당첨자 제출서류와 주민등록표등본 등 발급 서류의 준비 순서를 정하세요.',
        '지역우선, 특별공급, 선택품목, 감액 조건처럼 본인에게 적용될 공고문 세부 항목을 표시하세요.',
    ];
});
const dashboardTasks = computed(() => {
    if (selectedCoachSummary.value) {
        const orderedTasks = selectedCoachSummary.value.source === 'llm'
            ? [...coachTodos.value, ...dashboardBaseTasks.value]
            : [...dashboardBaseTasks.value, ...coachTodos.value];
        return [...new Set(orderedTasks)].slice(0, 4).map((title) => ({
            title,
            date: '',
            status: '제안',
        }));
    }
    return preApplyTasks.value.map(({ title, date, status }) => ({ title, date, status })).slice(0, 4);
});
const dashboardTaskSource = computed(() => (coachTodos.value.length ? 'AI 코치 제안' : '기본 점검'));
const visibleRecommendations = computed(() => recommendations.value.slice(0, 5));
const preferredRegionsLabel = computed(() => {
    const regions = Array.isArray(currentProfile.value.preferred_regions) ? currentProfile.value.preferred_regions : [];
    return regions.length ? regions.slice(0, 3).join(', ') : '조건 입력 필요';
});
const monthlyPlanLabel = computed(() => {
    const target = Number(selectedPlan.value?.monthly_target || 0);
    const saved = Number(currentProfile.value.monthly_saving || 0);
    return target ? formatMoney(target) : saved ? formatMoney(saved) : '계산 필요';
});
const monthlyPlanCaption = computed(() => {
    const saved = Number(currentProfile.value.monthly_saving || 0);
    if (saved)
        return `현재 저축 ${formatMoney(saved)}`;
    return `${currentProfile.value.target_months || 18}개월 목표 기준`;
});
const cashPlanCaption = computed(() => {
    const debt = Number(currentProfile.value.debt || 0);
    return debt ? `부채 ${formatMoney(debt)} 별도 관리` : '저장 자산 기준';
});
const memberRoadmapCards = computed(() => [
    { label: '희망 지역', value: preferredRegionsLabel.value, caption: '추천 조건 기준', icon: SearchCheck },
    { label: '가용 현금', value: formatMoney(currentProfile.value.asset ?? 0), caption: cashPlanCaption.value, icon: WalletCards },
    { label: '월 준비 기준', value: monthlyPlanLabel.value, caption: monthlyPlanCaption.value, icon: Route },
]);
const coachHeroText = computed(() => {
    const summary = selectedCoachSummary.value;
    if (summary)
        return '선택 기준과 공식 확인 포인트가 저장됐습니다.';
    return 'AI 코치로 이번 주 행동 순서를 받으세요.';
});
const hasCoachSummary = computed(() => Boolean(selectedCoachSummary.value));
const coachInsightChips = computed(() => {
    const summary = selectedCoachSummary.value;
    if (!summary)
        return [];
    return [
        { label: '선택 기준', count: Array.isArray(summary.decision_points) ? summary.decision_points.length : 0 },
        { label: '공식 체크', count: Array.isArray(summary.official_checklist) ? summary.official_checklist.length : 0 },
        { label: '심화 검토', count: Array.isArray(summary.deep_review_items) ? summary.deep_review_items.length : 0 },
    ].filter((item) => item.count > 0);
});
const guestHighlights = [
    { icon: SearchCheck, label: '조건 입력', value: '희망 지역, 자금, 면적을 저장' },
    { icon: Trophy, label: '후보 비교', value: '점수와 마감일로 공고를 압축' },
    { icon: WalletCards, label: '자금 로드맵', value: '계약금 부족액과 월 목표 확인' },
    { icon: Bot, label: 'AI 코치', value: '선택 후보 기준 다음 행동 정리' },
];
function rankClass(rank) {
    if (rank === 1)
        return 'bg-blue-600 text-white';
    if (rank === 2)
        return 'bg-emerald-500 text-white';
    if (rank === 3)
        return 'bg-amber-500 text-white';
    return 'bg-slate-200 text-slate-700';
}
function eventCountClass(count) {
    if (count >= 6)
        return 'bg-rose-500 text-white';
    if (count >= 3)
        return 'bg-amber-500 text-white';
    if (count >= 1)
        return 'bg-blue-600 text-white';
    return 'bg-slate-200 text-slate-500';
}
function dayEvents(day) {
    if (!day)
        return [];
    return eventsByDay.value[day] ?? [];
}
function selectCalendarDay(day) {
    if (!day)
        return;
    selectedCalendarDay.value = day;
    const firstEvent = dayEvents(day)[0];
    if (firstEvent)
        selectedId.value = firstEvent.id;
}
function selectNoticeFromCalendar(noticeId, day) {
    selectedId.value = noticeId;
    if (day)
        selectedCalendarDay.value = day;
}
function selectCalendarMonth(key) {
    selectedMonthKey.value = key;
    selectedCalendarDay.value = null;
}
function syncCalendarToDeadline(value) {
    const deadline = parseDeadline(value);
    if (!deadline)
        return;
    selectedMonthKey.value = monthKey(deadline);
    selectedCalendarDay.value = deadline.getDate();
}
function deadlineDay(value) {
    const deadline = parseDeadline(value);
    if (!deadline)
        return undefined;
    return deadline.getFullYear() === calendarMonth.value.getFullYear() && deadline.getMonth() === calendarMonth.value.getMonth()
        ? deadline.getDate()
        : undefined;
}
function shortNoticeTitle(value) {
    return String(value || '')
        .replace(/\s+/g, ' ')
        .replace(/\s*(?:입주자\s*)?모집\s*공고\s*$/g, '')
        .replace(/\s*입주자모집공고\s*$/g, '')
        .replace(/\s*예비입주자모집공고\s*$/g, '')
        .replace(/\s*(?:신혼희망타운|공공분양주택|공공분양|분양주택|민간참여형 공공분양|국민임대|행복주택|영구임대|통합공공임대)(?:\([^)]*\))?/g, '')
        .replace(/\((?:공공분양|분양주택|신혼희망타운|국민임대|행복주택|영구임대|통합공공임대)\)/g, '')
        .replace(/\s{2,}/g, ' ')
        .trim();
}
function saveSelectedCoachRoute() {
    saveCurrentSelection(selected.value?.id, selectedRouteOptionId.value);
}
async function loadSelectedPlan() {
    if (!selectedId.value)
        return;
    const storedSelection = readCurrentSelection();
    const optionId = storedSelection.noticeId === selectedId.value && storedSelection.optionId
        ? storedSelection.optionId
        : selectedRecommendation.value?.best_option?.option_id ?? null;
    selectedCoachSummary.value = null;
    selectedPlan.value = await fetchFundingPlan(selectedId.value, optionId);
    if (isLoggedIn.value) {
        void loadLatestCoachSummary(optionId);
    }
}
async function loadLatestCoachSummary(optionId = null) {
    if (!selectedId.value)
        return;
    const requestKey = `${selectedId.value}:${optionId ?? ''}`;
    latestCoachRequestKey.value = requestKey;
    try {
        const response = await fetchLatestCoachSummary(selectedId.value, optionId);
        if (latestCoachRequestKey.value !== requestKey)
            return;
        selectedCoachSummary.value = response?.exists ? response : null;
    }
    catch {
        if (latestCoachRequestKey.value === requestKey)
            selectedCoachSummary.value = null;
    }
}
async function loadDashboard() {
    loading.value = true;
    error.value = '';
    try {
        const [dashboardResponse, noticeResponse] = await Promise.all([fetchDashboard(), fetchNotices({ active: '1' }), authStore.hydrateAuth()]);
        dashboard.value = dashboardResponse;
        notices.value = noticeResponse.filter(isActiveNotice);
        const accountSelection = await syncCurrentSelectionWithAccount().catch(() => ({}));
        const persistedRecommendation = dashboardResponse.top_recommendations.find((item) => item.notice_id === accountSelection.noticeId);
        selectedId.value = persistedRecommendation?.notice_id ?? dashboardResponse.top_recommendations[0]?.notice_id ?? notices.value[0]?.id ?? null;
        syncCalendarToDeadline(notices.value.find((notice) => notice.id === selectedId.value)?.application_deadline ?? '');
        await profileStore.hydrateProfile();
        await loadSelectedPlan();
    }
    catch {
        error.value = '백엔드 API에 연결하지 못했습니다. Django 서버가 실행 중인지 확인하세요.';
    }
    finally {
        loading.value = false;
    }
}
watch(selectedId, (nextId) => {
    const nextNotice = notices.value.find((notice) => notice.id === nextId);
    syncCalendarToDeadline(nextNotice?.application_deadline ?? '');
    void loadSelectedPlan();
});
watch(availableMonths, (months) => {
    if (months.length === 0)
        return;
    if (!months.some((month) => month.key === selectedMonthKey.value)) {
        selectedMonthKey.value = months[0].key;
    }
});
onMounted(loadDashboard);
</script>

<template>
  <div class="space-y-5">
    <section v-if="loading" class="loading-surface">
      <p class="text-sm font-black text-slate-950">첫 집 준비 현황을 불러오고 있습니다</p>
      <p class="mt-1 text-sm text-slate-500">저장된 조건, 추천 후보, 이번 주 행동 순서를 맞춰 보는 중입니다.</p>
      <div class="mt-5 grid gap-3 md:grid-cols-3">
        <div v-for="index in 3" :key="index" class="loading-surface-tile">
          <span class="loading-surface-line w-1/3" />
          <span class="loading-surface-line mt-5 w-4/5" />
          <span class="loading-surface-line mt-3 w-2/3" />
        </div>
      </div>
    </section>

    <section v-else-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-semibold text-amber-800">
      {{ error }}
    </section>

    <template v-else-if="selected && selectedRecommendation">
      <section :class="isLoggedIn ? 'dashboard-member-hero' : 'overflow-hidden rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6'">
        <div v-if="!isLoggedIn" class="grid gap-6 xl:grid-cols-[minmax(0,0.92fr)_minmax(320px,0.48fr)] xl:items-center">
          <div>
            <div class="inline-flex items-center gap-2 rounded-md bg-blue-50 px-3 py-1 text-xs font-bold text-blue-700">
              <Sparkles class="h-4 w-4" />
              청약 네비
            </div>
            <h1 class="mt-4 text-3xl font-black leading-tight text-slate-950 sm:text-4xl">첫 집 준비를 한 화면에서</h1>
            <p class="mt-3 max-w-2xl text-sm leading-6 text-slate-500">
              공고를 찾고 끝나는 서비스가 아니라, 내 조건에 맞는 후보를 고르고 계약금 부족액과 이번 주 행동까지 이어서 확인하는 준비 화면입니다.
            </p>
            <div class="relative mt-7 grid gap-5 sm:grid-cols-4">
              <div class="absolute left-5 right-5 top-5 hidden h-[1.5px] bg-slate-200 sm:block" />
              <div v-for="item in guestHighlights" :key="item.label" class="relative min-w-0">
                <span class="inline-flex h-10 w-10 items-center justify-center rounded-full border border-blue-100 bg-white text-blue-700 shadow-sm">
                  <component :is="item.icon" class="h-5 w-5" />
                </span>
                <p class="mt-3 text-sm font-black text-slate-950">{{ item.label }}</p>
                <p class="mt-1 max-w-[13rem] text-xs font-bold leading-5 text-slate-500">{{ item.value }}</p>
              </div>
            </div>
          </div>
          <div class="border-t border-slate-200 pt-5 xl:border-l xl:border-t-0 xl:pl-6 xl:pt-0">
            <div class="inline-flex h-10 w-10 items-center justify-center rounded-full bg-slate-950 text-white">
              <Bot class="h-5 w-5" />
            </div>
            <p class="mt-4 text-xl font-black text-slate-950">회원이면 이어서 관리합니다</p>
            <p class="mt-2 max-w-sm text-sm leading-6 text-slate-500">
              조건과 관심 공고를 저장하고, 선택 후보 기준 자금 로드맵과 AI 코치의 할 일을 대시보드에서 이어서 확인합니다.
            </p>
            <RouterLink to="/auth" class="mt-5 inline-flex h-10 items-center rounded-lg bg-blue-500 px-4 text-sm font-black text-white">
              시작하기
            </RouterLink>
          </div>
        </div>

        <div v-else class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(300px,0.42fr)] xl:items-center">
          <div>
            <div class="inline-flex items-center gap-2 rounded-md bg-blue-50 px-3 py-1 text-xs font-bold text-blue-700">
              <Sparkles class="h-4 w-4" />
              준비 현황
            </div>
            <h1 class="mt-4 text-3xl font-black leading-tight text-slate-950 sm:text-4xl">
              {{ dashboard?.profile.name || '회원' }}님의 첫 집 로드맵
            </h1>
            <div class="member-roadmap-flow mt-6">
              <div v-for="card in memberRoadmapCards" :key="card.label" class="member-roadmap-step">
                <span class="member-roadmap-icon">
                  <component :is="card.icon" class="h-5 w-5" />
                </span>
                <p class="mt-3 text-xs font-bold text-slate-500">{{ card.label }}</p>
                <p class="mt-1 line-clamp-2 text-lg font-black leading-6 text-slate-950">{{ card.value }}</p>
                <p class="mt-2 line-clamp-1 text-xs font-bold text-slate-500">{{ card.caption }}</p>
              </div>
            </div>
          </div>
          <div class="member-coach-strip">
            <div class="flex items-center gap-2 text-sm font-black text-blue-700">
              <Bot class="h-4 w-4" />
              {{ hasCoachSummary ? '최근 AI 코치' : 'AI 코치' }}
            </div>
            <p class="mt-3 text-lg font-black leading-7 text-slate-950">{{ coachHeroText }}</p>
            <div v-if="coachInsightChips.length" class="mt-3 flex flex-wrap gap-2">
              <span
                v-for="chip in coachInsightChips"
                :key="chip.label"
                class="rounded-full border border-blue-100 bg-white px-3 py-1 text-xs font-black text-blue-700"
              >
                {{ chip.label }} {{ chip.count }}
              </span>
            </div>
            <RouterLink
              :to="selectedAiCoachRoute"
              class="mt-5 inline-flex h-10 items-center rounded-lg bg-slate-950 px-4 text-sm font-black text-white"
              @click="saveSelectedCoachRoute"
            >
              {{ hasCoachSummary ? '코치 보기' : 'AI 코치 받기' }}
            </RouterLink>
          </div>
        </div>
      </section>

      <section class="grid items-stretch gap-4 xl:grid-cols-[0.82fr_1.18fr]">
        <div class="flex h-full flex-col justify-between gap-5 rounded-lg border border-slate-200 bg-slate-950 p-5 text-white shadow-sm sm:p-6">
          <div>
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="text-xs font-bold uppercase tracking-normal text-slate-300">현재 선택</p>
                <h2 class="mt-2 break-words text-xl font-bold leading-tight">{{ selectedShortTitle }}</h2>
                <p class="mt-2 text-sm text-slate-300">{{ selected.district }}</p>
              </div>
              <span class="shrink-0 rounded-md bg-blue-500 px-2.5 py-1 text-sm font-bold text-white">
                {{ scoreLabel(selectedRecommendation) }}
              </span>
            </div>
            <div class="mt-5 h-3 overflow-hidden rounded-full bg-white/10">
              <div class="h-full rounded-full bg-emerald-400" :style="{ width: `${scorePercent(selectedRecommendation)}%` }" />
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3 text-sm">
            <div class="rounded-lg bg-white/10 p-3">
              <p class="text-slate-300">분양가</p>
              <p class="mt-1 font-bold text-white">{{ formatMoney(selectedDisplayPrice) }}</p>
            </div>
            <div class="rounded-lg bg-white/10 p-3">
              <p class="text-slate-300">부족액</p>
              <p class="mt-1 font-bold text-white">{{ formatMoney(selectedPlan?.shortfall ?? 0) }}</p>
            </div>
            <div class="rounded-lg bg-white/10 p-3">
              <p class="text-slate-300">마감</p>
              <p class="mt-1 font-bold text-white">{{ selected.application_deadline }}</p>
            </div>
            <div class="rounded-lg bg-white/10 p-3">
              <p class="text-slate-300">주택형</p>
              <p class="mt-1 font-bold text-white">{{ selectedOptionLabel }}</p>
            </div>
          </div>

          <div class="flex flex-wrap gap-2">
            <RouterLink
              :to="{ path: `/notices/${selected.id}`, query: selectedRecommendation.best_option?.option_id ? { option_id: selectedRecommendation.best_option.option_id } : {} }"
              class="inline-flex flex-1 items-center justify-center rounded-lg bg-white px-4 py-2 text-sm font-bold text-slate-950"
              @click="saveCurrentSelection(selected.id, selectedRecommendation.best_option?.option_id)"
            >
              공고문 근거
            </RouterLink>
            <RouterLink
              :to="{ path: `/funding/${selected.id}`, query: selectedRecommendation.best_option?.option_id ? { option_id: selectedRecommendation.best_option.option_id } : {} }"
              class="inline-flex flex-1 items-center justify-center rounded-lg bg-blue-500 px-4 py-2 text-sm font-bold text-white"
              @click="saveCurrentSelection(selected.id, selectedRecommendation.best_option?.option_id)"
            >
              옵션 자금
            </RouterLink>
          </div>
        </div>

        <div class="flex min-h-full flex-col rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-bold text-slate-950">이번 주 확인할 일</h2>
              <p class="mt-1 text-xs font-bold text-blue-700">{{ dashboardTaskSource }}</p>
            </div>
            <ClipboardList class="h-5 w-5 text-slate-400" />
          </div>

          <ol class="grid flex-1 gap-2">
            <li
              v-for="(task, index) in dashboardTasks"
              :key="`${task.title}-${index}`"
              class="grid grid-cols-[38px_1fr] items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-3"
            >
              <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-white text-sm font-bold text-blue-700">
                {{ index + 1 }}
              </span>
              <span class="min-w-0">
                <span class="line-clamp-2 text-sm font-bold leading-5 text-slate-950">{{ task.title }}</span>
                <span v-if="task.date" class="mt-0.5 block text-xs font-bold text-slate-500">{{ task.date }}</span>
              </span>
            </li>
          </ol>

          <div v-if="!dashboardTasks.length" class="rounded-lg bg-slate-50 p-4 text-sm font-bold text-slate-500">
            선택 후보를 정하면 확인할 일이 표시됩니다.
          </div>
        </div>
      </section>

      <section class="grid gap-4" :class="calendarOpen ? 'xl:grid-cols-[minmax(0,0.86fr)_minmax(430px,0.58fr)]' : 'xl:grid-cols-1'">
        <div class="h-full rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-5 flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-bold text-slate-950">검토 후보 요약</h2>
              <p class="mt-1 text-xs font-bold text-slate-500">{{ visibleRecommendations.length }}개 후보</p>
            </div>
            <button
              type="button"
              class="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50"
              :class="calendarOpen ? 'border-blue-500 bg-blue-50 text-blue-700' : ''"
              aria-label="청약 캘린더 보기"
              @click="calendarOpen = !calendarOpen"
            >
              <CalendarDays class="h-5 w-5" />
            </button>
          </div>

          <div class="grid gap-2">
            <button
              v-for="(item, index) in visibleRecommendations"
              :key="item.notice_id"
              type="button"
              class="grid gap-3 rounded-lg border p-3 text-left transition sm:grid-cols-[minmax(0,1fr)_140px]"
              :class="item.notice_id === selectedId ? 'border-blue-500 bg-blue-50/80' : 'border-slate-200 hover:bg-slate-50'"
              @click="selectedId = item.notice_id"
            >
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="rounded-md px-2 py-0.5 text-[11px] font-bold" :class="rankClass(index + 1)">
                    {{ index + 1 }}순위
                  </span>
                  <span class="rounded-md bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-600">
                    {{ item.supply_type }}
                  </span>
                </div>
                <h3 class="mt-2 line-clamp-2 text-sm font-bold leading-5 text-slate-950">{{ shortNoticeTitle(item.title) }}</h3>
              </div>
              <div class="flex items-end justify-between gap-3 text-xs font-bold text-slate-600 sm:flex-col sm:items-end sm:justify-center">
                <span>마감 {{ item.application_deadline }}</span>
                <span class="text-slate-950">{{ formatMoney(recommendationPrice(item)) }}</span>
              </div>
            </button>
          </div>
        </div>

        <div v-if="calendarOpen" class="flex h-full flex-col rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
          <div class="mb-3 flex items-center justify-between gap-3">
            <h2 class="text-lg font-bold text-slate-950">{{ calendarTitle }}</h2>
            <CalendarDays class="h-5 w-5 text-slate-400" />
          </div>

          <div class="mb-3 flex flex-wrap gap-1.5">
            <button
              v-for="month in availableMonths"
              :key="month.key"
              type="button"
              class="rounded-md border px-2.5 py-1.5 text-[11px] font-bold transition"
              :class="month.key === activeMonthKey ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100'"
              @click="selectCalendarMonth(month.key)"
            >
              {{ month.compactLabel }} · {{ month.count }}건
            </button>
          </div>

          <div class="grid flex-1 gap-3 lg:grid-cols-[1fr_210px]">
            <div class="flex min-h-0 flex-col">
              <div class="grid grid-cols-7 border-b border-slate-200 pb-2 text-center text-xs font-bold text-slate-500">
                <div v-for="day in weekDays" :key="day">{{ day }}</div>
              </div>
              <div class="mt-2 grid flex-1 auto-rows-fr grid-cols-7 gap-1.5">
                <button
                  v-for="slot in calendarSlots"
                  :key="slot.key"
                  type="button"
                  class="relative flex min-h-10 items-center justify-center rounded-lg border text-center transition"
                  :class="[
                    slot.day ? 'border-slate-200 bg-slate-50 hover:bg-slate-100' : 'pointer-events-none border-transparent bg-transparent',
                    slot.day && selectedCalendarDay === slot.day ? 'ring-2 ring-blue-200' : '',
                  ]"
                  @click="selectCalendarDay(slot.day)"
                >
                  <template v-if="slot.day">
                    <span class="text-sm font-bold text-slate-700">{{ slot.day }}</span>
                    <span
                      v-if="dayEvents(slot.day).length"
                      class="absolute right-1 top-1 min-w-4 rounded-full px-1 py-0.5 text-[9px] font-bold"
                      :class="eventCountClass(dayEvents(slot.day).length)"
                    >
                      {{ dayEvents(slot.day).length }}
                    </span>
                  </template>
                </button>
              </div>
            </div>

            <aside class="flex min-h-0 flex-col rounded-lg border border-slate-200 bg-slate-50 p-3 lg:max-h-[390px]">
              <div class="mb-2 flex items-center justify-between gap-2">
                <h3 class="text-sm font-bold text-slate-950">
                  {{ selectedCalendarDay ? `${selectedCalendarDay}일 마감` : '빠른 마감' }}
                </h3>
                <span class="rounded-md bg-slate-950 px-1.5 py-0.5 text-[11px] font-bold text-white">{{ selectedDayEvents.length }}건</span>
              </div>
              <div class="min-h-0 max-h-[330px] flex-1 space-y-2 overflow-y-auto pr-1">
                <button
                  v-for="event in selectedDayEvents"
                  :key="`${event.id}-${event.deadline}`"
                  type="button"
                  class="w-full rounded-lg border border-slate-200 bg-white p-2.5 text-left transition hover:bg-blue-50"
                  :class="event.id === selectedId ? 'border-blue-500' : ''"
                  @click="selectNoticeFromCalendar(event.id, deadlineDay(event.deadline))"
                >
                  <div class="flex items-center justify-between gap-2">
                    <span class="rounded-md bg-blue-50 px-1.5 py-0.5 text-[10px] font-bold text-blue-700">{{ event.supplyType }}</span>
                    <span class="text-xs font-bold text-slate-500">{{ event.deadline }}</span>
                  </div>
                  <p class="mt-1.5 line-clamp-2 text-xs font-bold leading-5 text-slate-950">{{ event.label }}</p>
                  <p class="mt-1 text-xs text-slate-500">{{ event.region }}</p>
                </button>
              </div>
            </aside>
          </div>
        </div>
      </section>
    </template>

    <section v-else class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      현재 접수 마감일이 남아 있는 검토 후보가 없습니다. 실제 공고를 다시 가져오거나 보조 fixture를 import한 뒤 확인하세요.
    </section>
  </div>
</template>
