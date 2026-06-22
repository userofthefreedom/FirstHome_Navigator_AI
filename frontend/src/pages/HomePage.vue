<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { Bot, CalendarDays, ClipboardList, SearchCheck, Sparkles, Trophy, WalletCards } from 'lucide-vue-next';
import { fetchCoachSummary, fetchDashboard, fetchFundingPlan, fetchNotices } from '../api/firsthome';
import { formatMoney } from '../utils/format';
import { saveCurrentSelection } from '../utils/selectionState';
import { useProfileStore } from '../stores/profileStore';
const profileStore = useProfileStore();
const loading = ref(true);
const error = ref('');
const dashboard = ref(null);
const notices = ref([]);
const selectedId = ref(null);
const selectedPlan = ref(null);
const selectedCoachSummary = ref(null);
const selectedCalendarDay = ref(null);
const selectedMonthKey = ref('');
const recommendations = computed(() => dashboard.value?.top_recommendations ?? []);
const activeNoticeCount = computed(() => dashboard.value?.notice_count ?? sortedNotices.value.length);
const selectedRecommendation = computed(() => recommendations.value.find((item) => item.notice_id === selectedId.value) ?? recommendations.value[0]);
const selected = computed(() => notices.value.find((notice) => notice.id === selectedId.value) ?? notices.value[0]);
const weekDays = ['일', '월', '화', '수', '목', '금', '토'];
const serviceSteps = [
    {
        icon: SearchCheck,
        title: '조건 입력',
        description: '희망 지역, 자금, 면적을 먼저 저장합니다.',
    },
    {
        icon: Trophy,
        title: '후보 비교',
        description: '점수와 마감일 기준으로 검토할 공고를 고릅니다.',
    },
    {
        icon: WalletCards,
        title: '옵션 자금',
        description: '선택 주택형의 계약금과 부족액을 확인합니다.',
    },
    {
        icon: Bot,
        title: 'AI 코치',
        description: '서류, 공고문 조건, 다음 행동을 정리합니다.',
    },
];
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
function recommendationPrice(item) {
    return Number(item?.best_option?.base_price || item?.price || 0);
}
const selectedDisplayPrice = computed(() => Number(selectedBestOption.value?.base_price || selected.value?.price || 0));
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
                label: item.title,
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
        label: item.title,
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
const coachTodos = computed(() => (selectedCoachSummary.value?.todo_this_week ?? []).filter(Boolean).slice(0, 5));
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
async function loadSelectedPlan() {
    if (!selectedId.value)
        return;
    const optionId = selectedRecommendation.value?.best_option?.option_id ?? null;
    selectedPlan.value = await fetchFundingPlan(selectedId.value, optionId);
    await loadCoachSummary(optionId);
}
async function loadCoachSummary(optionId = null) {
    selectedCoachSummary.value = null;
    if (!selectedId.value)
        return;
    try {
        const response = await fetchCoachSummary(selectedId.value, profileStore.profile, optionId);
        selectedCoachSummary.value = response?.todo_this_week?.length && !response?.requires_login ? response : null;
    }
    catch {
        selectedCoachSummary.value = null;
    }
}
async function loadDashboard() {
    loading.value = true;
    error.value = '';
    try {
        const [dashboardResponse, noticeResponse] = await Promise.all([fetchDashboard(), fetchNotices({ active: '1' })]);
        dashboard.value = dashboardResponse;
        notices.value = noticeResponse.filter(isActiveNotice);
        selectedId.value = dashboardResponse.top_recommendations[0]?.notice_id ?? notices.value[0]?.id ?? null;
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
    <section v-if="loading" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      대시보드 데이터를 불러오는 중입니다.
    </section>

    <section v-else-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-semibold text-amber-800">
      {{ error }}
    </section>

    <template v-else-if="selected && selectedRecommendation">
      <section class="grid items-start gap-4 xl:grid-cols-[minmax(0,0.92fr)_minmax(360px,0.58fr)]">
        <div class="flex min-h-full flex-col overflow-hidden rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <div class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div class="min-w-0">
              <div class="mb-4 inline-flex items-center gap-2 rounded-md bg-blue-50 px-3 py-1 text-xs font-bold uppercase tracking-normal text-blue-700">
                <Sparkles class="h-4 w-4" />
                주택형 옵션 준비 대시보드
              </div>
              <h1 class="max-w-2xl break-words text-3xl font-bold leading-tight text-slate-950 sm:text-4xl">
                {{ dashboard?.profile.name || '게스트' }}님의 첫 집 준비 현황
              </h1>
            </div>
            <RouterLink to="/profile" class="inline-flex h-10 items-center justify-center rounded-lg bg-slate-950 px-4 text-sm font-bold text-white transition hover:bg-slate-800">
              조건 수정
            </RouterLink>
          </div>

          <div class="mt-6 grid gap-3 md:grid-cols-4">
            <div class="rounded-lg bg-slate-50 p-4">
              <p class="text-xs font-bold text-slate-500">검토 후보</p>
              <p class="mt-2 text-2xl font-bold text-slate-950">{{ activeNoticeCount }}</p>
            </div>
            <div class="rounded-lg bg-slate-50 p-4">
              <p class="text-xs font-bold text-slate-500">최고 점수</p>
              <p class="mt-2 text-2xl font-bold text-slate-950">{{ scoreLabel(recommendations[0]) }}</p>
            </div>
            <div class="rounded-lg bg-slate-50 p-4">
              <p class="text-xs font-bold text-slate-500">빠른 마감</p>
              <p class="mt-2 text-2xl font-bold text-slate-950">{{ sortedNotices[0]?.application_deadline ?? '-' }}</p>
            </div>
            <div class="rounded-lg bg-slate-50 p-4">
              <p class="text-xs font-bold text-slate-500">보유 현금</p>
              <p class="mt-2 text-2xl font-bold text-slate-950">{{ formatMoney(dashboard?.profile.asset ?? 0) }}</p>
            </div>
          </div>

          <div class="mt-6 border-t border-slate-200 pt-5">
            <div class="grid w-full gap-x-4 gap-y-5 sm:grid-cols-2 xl:grid-cols-4">
              <div
                v-for="(step, index) in serviceSteps"
                :key="step.title"
                class="grid min-w-0 grid-cols-[28px_minmax(0,1fr)] items-start justify-center gap-3 xl:grid-cols-[28px_minmax(0,9.75rem)]"
              >
                <span class="mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-blue-50 text-blue-700">
                  <component :is="step.icon" class="h-3.5 w-3.5" />
                </span>
                <div class="min-w-0">
                  <div class="flex items-center gap-2">
                    <p class="text-sm font-bold text-slate-950">{{ step.title }}</p>
                    <span v-if="index < serviceSteps.length - 1" class="hidden text-xs font-bold text-slate-300 xl:inline">→</span>
                  </div>
                  <p class="mt-1.5 max-w-[9.75rem] text-xs leading-5 text-slate-500">{{ step.description }}</p>
                </div>
              </div>
            </div>
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

      <section class="grid items-stretch gap-4 xl:grid-cols-[0.82fr_1.18fr]">
        <div class="flex h-full flex-col justify-between gap-5 rounded-lg border border-slate-200 bg-slate-950 p-5 text-white shadow-sm sm:p-6">
          <div>
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0">
                <p class="text-xs font-bold uppercase tracking-normal text-slate-300">현재 선택</p>
                <h2 class="mt-2 break-words text-xl font-bold leading-tight">{{ selected.title }}</h2>
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
              <p class="text-slate-300">계약금 부족액</p>
              <p class="mt-1 font-bold text-white">{{ formatMoney(selectedPlan?.shortfall ?? 0) }}</p>
            </div>
            <div class="rounded-lg bg-white/10 p-3">
              <p class="text-slate-300">접수 마감</p>
              <p class="mt-1 font-bold text-white">{{ selected.application_deadline }}</p>
            </div>
            <div class="rounded-lg bg-white/10 p-3">
              <p class="text-slate-300">입주 예정</p>
              <p class="mt-1 font-bold text-white">{{ selected.move_in }}</p>
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

        <div class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:p-5">
          <div class="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-bold text-slate-950">{{ calendarTitle }}</h2>
            </div>
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

          <div class="grid gap-3 lg:grid-cols-[1fr_230px]">
            <div>
              <div class="grid grid-cols-7 border-b border-slate-200 pb-2 text-center text-xs font-bold text-slate-500">
                <div v-for="day in weekDays" :key="day">{{ day }}</div>
              </div>
              <div class="mt-2 grid grid-cols-7 gap-1.5">
                <button
                  v-for="slot in calendarSlots"
                  :key="slot.key"
                  type="button"
                  class="relative flex h-11 items-center justify-center rounded-lg border text-center transition sm:h-12"
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

            <aside class="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div class="mb-2 flex items-center justify-between gap-2">
                <h3 class="text-sm font-bold text-slate-950">
                  {{ selectedCalendarDay ? `${selectedCalendarDay}일 마감` : '빠른 마감' }}
                </h3>
                <span class="rounded-md bg-slate-950 px-1.5 py-0.5 text-[11px] font-bold text-white">{{ selectedDayEvents.length }}건</span>
              </div>
              <div class="max-h-64 space-y-2 overflow-y-auto pr-1">
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

      <section class="grid items-stretch gap-5 xl:grid-cols-[0.88fr_1.12fr]">
        <div class="h-full rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-5 flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-bold text-slate-950">검토 후보 요약</h2>
            </div>
            <Trophy class="h-5 w-5 text-blue-600" />
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
                <h3 class="mt-2 line-clamp-2 text-sm font-bold leading-5 text-slate-950">{{ item.title }}</h3>
              </div>
              <div class="flex items-end justify-between gap-3 text-xs font-bold text-slate-600 sm:flex-col sm:items-end sm:justify-center">
                <span>마감 {{ item.application_deadline }}</span>
                <span class="text-slate-950">{{ formatMoney(recommendationPrice(item)) }}</span>
              </div>
            </button>
          </div>
        </div>

        <div class="flex h-full flex-col rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-5 flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-bold text-slate-950">선택 후보 상세 요약</h2>
              <p class="mt-1 line-clamp-1 text-sm text-slate-500">{{ selected.title }} 기준</p>
            </div>
            <RouterLink
              :to="{ path: `/notices/${selected.id}`, query: selectedRecommendation.best_option?.option_id ? { option_id: selectedRecommendation.best_option.option_id } : {} }"
              class="shrink-0 text-sm font-bold text-blue-700 hover:text-blue-800"
              @click="saveCurrentSelection(selected.id, selectedRecommendation.best_option?.option_id)"
            >
              상세 보기
            </RouterLink>
          </div>

          <div class="flex flex-1 flex-col overflow-hidden rounded-lg border border-slate-200">
            <div
              v-for="[label, value] in [
                ['위치', [selected.region, selected.district].filter(Boolean).join(' · ')],
                ['공급 유형', selected.supply_type],
                ['접수 마감', selected.application_deadline],
                ['입주 예정', selected.move_in],
                ['대표 가격', formatMoney(selectedDisplayPrice)],
                ['선택 주택형', selectedOptionLabel],
                ['계약금 부족액', formatMoney(selectedPlan?.shortfall ?? 0)],
                ['현재 점수', scoreLabel(selectedRecommendation)],
              ]"
              :key="label"
              class="grid flex-1 items-center gap-3 border-b border-slate-200 px-4 py-3 last:border-b-0 sm:grid-cols-[128px_1fr]"
            >
              <p class="text-sm font-bold text-slate-500">{{ label }}</p>
              <p class="break-words font-bold text-slate-950">{{ value || '-' }}</p>
            </div>
          </div>
        </div>
      </section>
    </template>

    <section v-else class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      현재 접수 마감일이 남아 있는 검토 후보가 없습니다. 실제 공고를 다시 가져오거나 보조 fixture를 import한 뒤 확인하세요.
    </section>
  </div>
</template>
