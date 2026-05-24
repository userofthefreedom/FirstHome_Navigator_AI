<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { CalendarDays, ClipboardList, FileCheck2, MapPin, ShieldAlert, Sparkles, Trophy } from 'lucide-vue-next'
import { fetchDashboard, fetchFundingPlan, fetchNotices } from '../api/firsthome'
import type { Dashboard, FundingPlan, HousingRecommendation, Notice } from '../types/firsthome'
import { formatMoney } from '../utils/format'
import { useProfileStore } from '../stores/profileStore'

type CalendarEvent = {
  id: number
  label: string
  region: string
  supplyType: string
  deadline: string
  type: 'deadline' | 'selected'
}

type CalendarSlot = {
  key: string
  day: number | null
}

const profileStore = useProfileStore()
const loading = ref(true)
const error = ref('')
const dashboard = ref<Dashboard | null>(null)
const notices = ref<Notice[]>([])
const selectedId = ref<number | null>(null)
const selectedPlan = ref<FundingPlan | null>(null)
const selectedCalendarDay = ref<number | null>(null)
const selectedMonthKey = ref('')

const recommendations = computed<HousingRecommendation[]>(() => dashboard.value?.top_recommendations ?? [])
const selectedRecommendation = computed(() => recommendations.value.find((item) => item.notice_id === selectedId.value) ?? recommendations.value[0])
const selected = computed(() => notices.value.find((notice) => notice.id === selectedId.value) ?? notices.value[0])
const weekDays = ['일', '월', '화', '수', '목', '금', '토']

function parseDeadline(value: string) {
  const date = new Date(`${value}T00:00:00`)
  return Number.isNaN(date.getTime()) ? null : date
}

function monthKey(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`
}

function monthLabel(key: string) {
  const [year, month] = key.split('-')
  return `${year}년 ${Number(month)}월`
}

const sortedNotices = computed(() => {
  return [...notices.value].sort((a, b) => a.application_deadline.localeCompare(b.application_deadline) || a.title.localeCompare(b.title))
})

const availableMonths = computed(() => {
  const buckets = new Map<string, number>()
  for (const notice of sortedNotices.value) {
    const deadline = parseDeadline(notice.application_deadline)
    if (!deadline) continue
    const key = monthKey(deadline)
    buckets.set(key, (buckets.get(key) ?? 0) + 1)
  }
  return [...buckets.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([key, count]) => ({ key, label: monthLabel(key), count }))
})

const activeMonthKey = computed(() => selectedMonthKey.value || availableMonths.value[0]?.key || '2026-06')

const calendarMonth = computed(() => {
  const [year, month] = activeMonthKey.value.split('-').map(Number)
  return new Date(year, month - 1, 1)
})

const calendarTitle = computed(() => `${calendarMonth.value.getFullYear()}년 ${calendarMonth.value.getMonth() + 1}월 청약 캘린더`)

const calendarSlots = computed<CalendarSlot[]>(() => {
  const year = calendarMonth.value.getFullYear()
  const month = calendarMonth.value.getMonth()
  const firstWeekDay = new Date(year, month, 1).getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const slotCount = Math.ceil((firstWeekDay + daysInMonth) / 7) * 7

  return Array.from({ length: slotCount }, (_, index) => {
    const day = index - firstWeekDay + 1
    return {
      key: `${year}-${month}-${index}`,
      day: day >= 1 && day <= daysInMonth ? day : null,
    }
  })
})

const eventsByDay = computed(() => {
  return sortedNotices.value.reduce<Record<number, CalendarEvent[]>>((acc, item) => {
    const deadline = parseDeadline(item.application_deadline)
    if (!deadline) return acc
    if (deadline.getFullYear() !== calendarMonth.value.getFullYear() || deadline.getMonth() !== calendarMonth.value.getMonth()) return acc

    const day = deadline.getDate()
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
    ]
    return acc
  }, {})
})

const selectedDayEvents = computed(() => {
  if (selectedCalendarDay.value) return eventsByDay.value[selectedCalendarDay.value] ?? []
  return sortedNotices.value
    .filter((item) => {
      const deadline = parseDeadline(item.application_deadline)
      return deadline && monthKey(deadline) === activeMonthKey.value
    })
    .slice(0, 6)
    .map((item) => ({
      id: item.id,
      label: item.title,
      region: item.region,
      supplyType: item.supply_type,
      deadline: item.application_deadline,
      type: item.id === selectedId.value ? 'selected' : 'deadline',
    }))
})

const preApplyTasks = computed(() => {
  if (!selected.value) return []
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
      description: `${selected.value.required_documents.slice(0, 3).join(', ')} 발급 시점과 유효 기간을 확인합니다.`,
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
  ]
})

function rankClass(rank: number) {
  if (rank === 1) return 'bg-blue-600 text-white'
  if (rank === 2) return 'bg-emerald-500 text-white'
  if (rank === 3) return 'bg-amber-500 text-white'
  return 'bg-slate-200 text-slate-700'
}

function statusClass(status: string) {
  if (status === '진행') return 'bg-blue-50 text-blue-700'
  if (status === '준비') return 'bg-slate-100 text-slate-600'
  if (status === '마감') return 'bg-amber-50 text-amber-700'
  return 'bg-emerald-50 text-emerald-700'
}

function eventCountClass(count: number) {
  if (count >= 6) return 'bg-rose-500 text-white'
  if (count >= 3) return 'bg-amber-500 text-white'
  if (count >= 1) return 'bg-blue-600 text-white'
  return 'bg-slate-200 text-slate-500'
}

function dayEvents(day: number | null) {
  if (!day) return []
  return eventsByDay.value[day] ?? []
}

function selectCalendarDay(day: number | null) {
  if (!day) return
  selectedCalendarDay.value = day
  const firstEvent = dayEvents(day)[0]
  if (firstEvent) selectedId.value = firstEvent.id
}

function selectNoticeFromCalendar(noticeId: number, day?: number) {
  selectedId.value = noticeId
  if (day) selectedCalendarDay.value = day
}

function selectCalendarMonth(key: string) {
  selectedMonthKey.value = key
  selectedCalendarDay.value = null
}

function syncCalendarToDeadline(value: string) {
  const deadline = parseDeadline(value)
  if (!deadline) return
  selectedMonthKey.value = monthKey(deadline)
  selectedCalendarDay.value = deadline.getDate()
}

function deadlineDay(value: string) {
  const deadline = parseDeadline(value)
  if (!deadline) return undefined
  return deadline.getFullYear() === calendarMonth.value.getFullYear() && deadline.getMonth() === calendarMonth.value.getMonth()
    ? deadline.getDate()
    : undefined
}

async function loadSelectedPlan() {
  if (!selectedId.value) return
  selectedPlan.value = await fetchFundingPlan(selectedId.value)
}

async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    const [dashboardResponse, noticeResponse] = await Promise.all([fetchDashboard(), fetchNotices()])
    dashboard.value = dashboardResponse
    notices.value = noticeResponse
    selectedId.value = dashboardResponse.top_recommendations[0]?.notice_id ?? noticeResponse[0]?.id ?? null
    syncCalendarToDeadline(noticeResponse.find((notice) => notice.id === selectedId.value)?.application_deadline ?? '')
    await profileStore.hydrateProfile()
    await loadSelectedPlan()
  } catch {
    error.value = '백엔드 API에 연결하지 못했습니다. Django 서버가 실행 중인지 확인하세요.'
  } finally {
    loading.value = false
  }
}

watch(selectedId, (nextId) => {
  const nextNotice = notices.value.find((notice) => notice.id === nextId)
  syncCalendarToDeadline(nextNotice?.application_deadline ?? '')
  void loadSelectedPlan()
})

watch(availableMonths, (months) => {
  if (months.length === 0) return
  if (!months.some((month) => month.key === selectedMonthKey.value)) {
    selectedMonthKey.value = months[0].key
  }
})

onMounted(loadDashboard)
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
      <section class="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div class="overflow-hidden rounded-lg border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div class="min-w-0">
              <div class="mb-5 inline-flex items-center gap-2 rounded-md bg-blue-50 px-3 py-1 text-xs font-bold uppercase tracking-normal text-blue-700">
                <Sparkles class="h-4 w-4" />
                주택형 옵션 준비 대시보드
              </div>
              <h1 class="max-w-3xl break-words text-3xl font-bold leading-tight text-slate-950 sm:text-4xl">
                {{ dashboard?.profile.name || '게스트' }}님의 첫 집 준비 현황
              </h1>
              <p class="mt-4 max-w-2xl text-sm leading-6 text-slate-600">
                소유형 공공분양 안에서 검토할 주택형 옵션, 계약금 부족액, 공식 확인 항목을 우선순위대로 정리했습니다.
              </p>
            </div>
            <RouterLink to="/profile" class="inline-flex h-10 items-center justify-center rounded-lg bg-slate-950 px-4 text-sm font-bold text-white transition hover:bg-slate-800">
              조건 수정
            </RouterLink>
          </div>

          <div class="mt-7 grid gap-3 md:grid-cols-4">
            <div class="rounded-lg bg-slate-50 p-4">
              <p class="text-xs font-bold text-slate-500">검토 후보</p>
              <p class="mt-2 text-2xl font-bold text-slate-950">{{ recommendations.length }}</p>
            </div>
            <div class="rounded-lg bg-slate-50 p-4">
              <p class="text-xs font-bold text-slate-500">최고 점수</p>
              <p class="mt-2 text-2xl font-bold text-slate-950">{{ recommendations[0]?.total_score ?? 0 }}점</p>
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
        </div>

        <div class="rounded-lg border border-slate-200 bg-slate-950 p-5 text-white shadow-sm sm:p-6">
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="text-xs font-bold uppercase tracking-normal text-slate-300">현재 선택</p>
              <h2 class="mt-2 break-words text-xl font-bold leading-tight">{{ selected.title }}</h2>
              <p class="mt-2 text-sm text-slate-300">{{ selected.district }}</p>
            </div>
            <span class="rounded-md bg-blue-500 px-2.5 py-1 text-sm font-bold text-white">
              {{ selectedRecommendation.total_score }}점
            </span>
          </div>
          <div class="mt-5 h-3 overflow-hidden rounded-full bg-white/10">
            <div class="h-full rounded-full bg-emerald-400" :style="{ width: `${selectedRecommendation.total_score}%` }" />
          </div>
          <div class="mt-6 grid grid-cols-2 gap-3 text-sm">
            <div class="rounded-lg bg-white/10 p-3">
              <p class="text-slate-300">분양가</p>
              <p class="mt-1 font-bold text-white">{{ formatMoney(selected.price) }}</p>
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
          <div class="mt-5 flex flex-wrap gap-2">
            <RouterLink :to="`/notices/${selected.id}`" class="inline-flex flex-1 items-center justify-center rounded-lg bg-white px-4 py-2 text-sm font-bold text-slate-950">
              공고문 근거
            </RouterLink>
            <RouterLink :to="`/funding/${selected.id}`" class="inline-flex flex-1 items-center justify-center rounded-lg bg-blue-500 px-4 py-2 text-sm font-bold text-white">
              옵션 자금
            </RouterLink>
          </div>
        </div>
      </section>

      <section class="grid gap-4 xl:grid-cols-[0.86fr_1.14fr]">
        <div class="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div class="flex items-center justify-between gap-3 border-b border-slate-200 p-5">
            <div>
              <h2 class="text-lg font-bold text-slate-950">검토 후보 요약</h2>
              <p class="mt-1 text-sm text-slate-500">후보를 선택하면 공식 일정과 계약금 준비 계획이 함께 바뀝니다.</p>
            </div>
            <Trophy class="h-5 w-5 text-blue-600" />
          </div>
          <div class="divide-y divide-slate-100">
            <button
              v-for="(item, index) in recommendations"
              :key="item.notice_id"
              type="button"
              class="grid w-full gap-4 p-5 text-left transition sm:grid-cols-[1fr_auto]"
              :class="item.notice_id === selectedId ? 'bg-blue-50/80' : 'hover:bg-slate-50'"
              @click="selectedId = item.notice_id"
            >
              <div class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="rounded-md px-2.5 py-1 text-xs font-bold" :class="rankClass(index + 1)">
                    {{ index + 1 }}순위
                  </span>
                  <h3 class="font-bold text-slate-950">{{ item.title }}</h3>
                  <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">
                    {{ item.supply_type }}
                  </span>
                </div>
                <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
                  <span class="inline-flex items-center gap-1">
                    <MapPin class="h-4 w-4" />
                    {{ item.region }}
                  </span>
                  <span>{{ formatMoney(item.price) }}</span>
                </div>
              </div>
              <div class="grid grid-cols-2 gap-2 text-sm sm:w-52">
                <div class="rounded-lg bg-white p-3">
                  <p class="text-slate-500">점수</p>
                  <p class="mt-1 font-bold text-blue-700">{{ item.total_score }}점</p>
                </div>
                <div class="rounded-lg bg-white p-3">
                  <p class="text-slate-500">마감</p>
                  <p class="mt-1 font-bold text-slate-950">{{ item.application_deadline }}</p>
                </div>
              </div>
            </button>
          </div>
        </div>

        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-5 flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-bold text-slate-950">{{ calendarTitle }}</h2>
              <p class="mt-1 text-sm text-slate-500">날짜에는 숫자만 남기고 상세 공고는 오른쪽에서 확인합니다.</p>
            </div>
            <CalendarDays class="h-5 w-5 text-slate-400" />
          </div>

          <div class="mb-3 flex flex-wrap gap-2">
            <button
              v-for="month in availableMonths"
              :key="month.key"
              type="button"
              class="rounded-lg border px-3 py-2 text-xs font-bold transition"
              :class="month.key === activeMonthKey ? 'border-blue-500 bg-blue-50 text-blue-700' : 'border-slate-200 bg-slate-50 text-slate-600 hover:bg-slate-100'"
              @click="selectCalendarMonth(month.key)"
            >
              {{ month.label }} · {{ month.count }}건
            </button>
          </div>

          <div class="grid gap-4 lg:grid-cols-[1fr_260px]">
            <div>
              <div class="grid grid-cols-7 border-b border-slate-200 pb-2 text-center text-xs font-bold text-slate-500">
                <div v-for="day in weekDays" :key="day">{{ day }}</div>
              </div>
              <div class="mt-2 grid grid-cols-7 gap-2">
                <button
                  v-for="slot in calendarSlots"
                  :key="slot.key"
                  type="button"
                  class="relative flex h-14 items-center justify-center rounded-lg border text-center transition sm:h-16"
                  :class="[
                    slot.day ? 'border-slate-200 bg-slate-50 hover:bg-slate-100' : 'pointer-events-none border-transparent bg-transparent',
                    slot.day && selectedCalendarDay === slot.day ? 'ring-2 ring-blue-200' : '',
                  ]"
                  @click="selectCalendarDay(slot.day)"
                >
                  <template v-if="slot.day">
                    <span class="text-base font-bold text-slate-700">{{ slot.day }}</span>
                    <span
                      v-if="dayEvents(slot.day).length"
                      class="absolute right-1.5 top-1.5 min-w-5 rounded-md px-1 py-0.5 text-[10px] font-bold"
                      :class="eventCountClass(dayEvents(slot.day).length)"
                    >
                        {{ dayEvents(slot.day).length }}
                    </span>
                  </template>
                </button>
              </div>
            </div>

            <aside class="rounded-lg border border-slate-200 bg-slate-50 p-3">
              <div class="mb-3 flex items-center justify-between gap-2">
                <h3 class="text-base font-bold text-slate-950">
                  {{ selectedCalendarDay ? `${selectedCalendarDay}일 마감` : '빠른 마감' }}
                </h3>
                <span class="rounded-md bg-slate-950 px-2 py-1 text-xs font-bold text-white">{{ selectedDayEvents.length }}건</span>
              </div>
              <div class="max-h-80 space-y-2 overflow-y-auto pr-1">
                <button
                  v-for="event in selectedDayEvents"
                  :key="`${event.id}-${event.deadline}`"
                  type="button"
                  class="w-full rounded-lg border border-slate-200 bg-white p-3 text-left transition hover:bg-blue-50"
                  :class="event.id === selectedId ? 'border-blue-500' : ''"
                  @click="selectNoticeFromCalendar(event.id, deadlineDay(event.deadline))"
                >
                  <div class="flex items-center justify-between gap-2">
                    <span class="rounded-md bg-blue-50 px-2 py-1 text-[11px] font-bold text-blue-700">{{ event.supplyType }}</span>
                    <span class="text-xs font-bold text-slate-500">{{ event.deadline }}</span>
                  </div>
                  <p class="mt-2 line-clamp-2 text-sm font-bold text-slate-950">{{ event.label }}</p>
                  <p class="mt-1 text-xs text-slate-500">{{ event.region }}</p>
                </button>
              </div>
            </aside>
          </div>
        </div>
      </section>

      <section class="grid gap-5 xl:grid-cols-[0.88fr_1.12fr]">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-5 flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-bold text-slate-950">선택 후보 상세 요약</h2>
              <p class="mt-1 text-sm text-slate-500">{{ selected.title }} 기준</p>
            </div>
            <RouterLink :to="`/notices/${selected.id}`" class="text-sm font-bold text-blue-700 hover:text-blue-800">상세 보기</RouterLink>
          </div>

          <div class="grid gap-3 sm:grid-cols-2">
            <div v-for="[label, value] in [
              ['위치', selected.district],
              ['공급 유형', selected.supply_type],
              ['분양가', formatMoney(selected.price)],
              ['전용면적', selected.area],
              ['경쟁률', selected.competition],
              ['입주 예정', selected.move_in],
            ]" :key="label" class="rounded-lg bg-slate-50 p-4">
              <p class="text-sm text-slate-500">{{ label }}</p>
              <p class="mt-1 font-bold text-slate-950">{{ value }}</p>
            </div>
          </div>

          <div class="mt-5">
            <p class="mb-2 text-sm font-bold text-slate-700">공식 확인 주의사항</p>
            <div class="space-y-2">
              <div v-for="caution in selected.cautions" :key="caution" class="flex items-start gap-2 text-sm text-slate-600">
                <ShieldAlert class="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                <span>{{ caution }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-5 flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-bold text-slate-950">이번 주 확인할 일</h2>
              <p class="mt-1 text-sm text-slate-500">선택한 후보를 실제로 검토하기 위한 준비 계획입니다.</p>
            </div>
            <ClipboardList class="h-5 w-5 text-slate-400" />
          </div>

          <div class="space-y-3">
            <div v-for="(task, index) in preApplyTasks" :key="task.title" class="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 sm:grid-cols-[72px_1fr]">
              <div>
                <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-white text-sm font-bold text-blue-700">
                  {{ index + 1 }}
                </div>
                <p class="mt-2 text-xs font-bold text-slate-500">{{ task.date }}</p>
              </div>
              <div>
                <div class="flex flex-wrap items-center gap-2">
                  <h3 class="font-bold text-slate-950">{{ task.title }}</h3>
                  <span class="rounded-md px-2 py-1 text-xs font-bold" :class="statusClass(task.status)">
                    {{ task.status }}
                  </span>
                </div>
                <p class="mt-2 text-sm leading-6 text-slate-600">{{ task.description }}</p>
              </div>
            </div>
          </div>

          <div class="mt-5 rounded-lg bg-blue-50 p-4">
            <div class="flex items-start gap-3">
              <FileCheck2 class="mt-0.5 h-5 w-5 shrink-0 text-blue-700" />
              <div>
                <p class="font-bold text-slate-950">AI 코치로 옵션별 다음 행동을 확인할 수 있습니다</p>
                <p class="mt-1 text-sm text-slate-600">
                  계약금 부족액, 이번 주 할 일, 공식 확인 항목을 같은 주택형 기준으로 이어서 봅니다.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
