<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { CalendarDays, ClipboardList, FileCheck2, MapPin, ShieldAlert, Sparkles, Trophy } from 'lucide-vue-next'
import { fetchDashboard, fetchFundingPlan, fetchNotices } from '../api/firsthome'
import type { Dashboard, FundingPlan, HousingRecommendation, Notice } from '../types/firsthome'
import { formatMoney } from '../utils/format'
import { useProfileStore } from '../stores/profileStore'

const profileStore = useProfileStore()
const loading = ref(true)
const error = ref('')
const dashboard = ref<Dashboard | null>(null)
const notices = ref<Notice[]>([])
const selectedId = ref<number | null>(null)
const selectedPlan = ref<FundingPlan | null>(null)

const recommendations = computed<HousingRecommendation[]>(() => dashboard.value?.top_recommendations ?? [])
const selectedRecommendation = computed(() => recommendations.value.find((item) => item.notice_id === selectedId.value) ?? recommendations.value[0])
const selected = computed(() => notices.value.find((notice) => notice.id === selectedId.value) ?? notices.value[0])
const weekDays = ['일', '월', '화', '수', '목', '금', '토']
const calendarSlots = Array.from({ length: 42 }, (_, index) => {
  const day = index - 4
  return day >= 1 && day <= 31 ? day : null
})

const eventsByDay = computed(() => {
  return notices.value.reduce<Record<number, Array<{ id: number; label: string; type: 'deadline' | 'selected' }>>>((acc, item) => {
    const day = Number(item.application_deadline.split('-')[2])
    acc[day] = [
      ...(acc[day] ?? []),
      {
        id: item.id,
        label: item.title,
        type: item.id === selectedId.value ? 'selected' : 'deadline',
      },
    ]
    return acc
  }, {})
})

const preApplyTasks = computed(() => {
  if (!selected.value) return []
  return [
    {
      title: '청약 자격과 배점 확인',
      date: '오늘',
      status: '진행',
      description: `${selected.value.supply_type} 조건, 무주택 기준, 청약통장 가입기간을 공식 공고문 기준으로 다시 확인합니다.`,
    },
    {
      title: '필수 서류 발급 가능 여부 확인',
      date: 'D-7',
      status: '준비',
      description: `${selected.value.required_documents.slice(0, 3).join(', ')} 발급 시점과 유효 기간을 확인합니다.`,
    },
    {
      title: '청약 접수 완료',
      date: selected.value.application_deadline,
      status: '마감',
      description: '접수 번호와 신청 화면을 저장하고 당첨자 발표 일정을 알림으로 남깁니다.',
    },
    {
      title: '계약금 계좌 분리',
      date: selected.value.contract_date,
      status: '예정',
      description: `부족액 ${formatMoney(selectedPlan.value?.shortfall ?? 0)}을 기준으로 월 저축 목표를 점검합니다.`,
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
    await profileStore.hydrateProfile()
    await loadSelectedPlan()
  } catch {
    error.value = '백엔드 API에 연결하지 못했습니다. Django 서버가 실행 중인지 확인하세요.'
  } finally {
    loading.value = false
  }
}

watch(selectedId, () => {
  void loadSelectedPlan()
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
      <section class="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
        <div class="overflow-hidden rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
          <div class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
            <div class="min-w-0">
              <div class="mb-4 inline-flex items-center gap-2 rounded-md bg-blue-50 px-3 py-1 text-sm font-bold text-blue-700">
                <Sparkles class="h-4 w-4" />
                FirstHome Navigator AI
              </div>
              <h1 class="max-w-3xl break-words text-2xl font-bold leading-tight text-slate-950 sm:text-3xl">
                {{ dashboard?.profile.name }}님의 첫 집 준비 흐름을 한 화면에서 이어갑니다
              </h1>
              <p class="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
                백엔드 fixture/API 기준으로 청약 후보, 계약금 준비율, 예·적금 후보, 공식 확인 체크리스트를 계산합니다.
              </p>
            </div>
            <RouterLink to="/profile" class="inline-flex h-11 items-center justify-center rounded-lg bg-slate-950 px-4 text-sm font-bold text-white transition hover:bg-slate-800">
              조건 수정
            </RouterLink>
          </div>

          <div class="mt-6 grid gap-3 md:grid-cols-4">
            <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p class="text-sm font-semibold text-slate-500">추천 청약</p>
              <p class="mt-2 text-xl font-bold text-slate-950">{{ recommendations.length }}건</p>
            </div>
            <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p class="text-sm font-semibold text-slate-500">최고 점수</p>
              <p class="mt-2 text-xl font-bold text-slate-950">{{ recommendations[0]?.total_score ?? 0 }}점</p>
            </div>
            <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p class="text-sm font-semibold text-slate-500">가장 빠른 마감</p>
              <p class="mt-2 text-xl font-bold text-slate-950">{{ notices[0]?.application_deadline }}</p>
            </div>
            <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p class="text-sm font-semibold text-slate-500">보유 현금</p>
              <p class="mt-2 text-xl font-bold text-slate-950">{{ formatMoney(dashboard?.profile.asset ?? 0) }}</p>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-slate-200 bg-slate-950 p-5 text-white shadow-sm sm:p-6">
          <div class="flex items-start justify-between gap-3">
            <div>
              <p class="text-sm font-semibold text-slate-300">현재 선택 청약</p>
              <h2 class="mt-1 text-2xl font-bold">{{ selected.title }}</h2>
              <p class="mt-2 text-sm text-slate-300">{{ selected.district }}</p>
            </div>
            <span class="rounded-md bg-blue-500 px-2.5 py-1 text-sm font-bold text-white">
              {{ selectedRecommendation.total_score }}점
            </span>
          </div>
          <div class="mt-5 h-3 overflow-hidden rounded-full bg-white/10">
            <div class="h-full rounded-full bg-emerald-400" :style="{ width: `${selectedRecommendation.total_score}%` }" />
          </div>
          <div class="mt-5 grid grid-cols-2 gap-3 text-sm">
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
              공고 상세
            </RouterLink>
            <RouterLink :to="`/funding/${selected.id}`" class="inline-flex flex-1 items-center justify-center rounded-lg bg-blue-500 px-4 py-2 text-sm font-bold text-white">
              자금 보기
            </RouterLink>
          </div>
        </div>
      </section>

      <section class="grid gap-5 xl:grid-cols-[0.88fr_1.12fr]">
        <div class="rounded-lg border border-slate-200 bg-white shadow-sm">
          <div class="flex items-center justify-between gap-3 border-b border-slate-200 p-5">
            <div>
              <h2 class="text-lg font-bold text-slate-950">청약 순위 요약</h2>
              <p class="mt-1 text-sm text-slate-500">후보를 선택하면 오른쪽 일정과 하단 준비 계획이 함께 바뀝니다.</p>
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
              <h2 class="text-lg font-bold text-slate-950">2026년 6월 청약 캘린더</h2>
              <p class="mt-1 text-sm text-slate-500">접수 마감일과 선택 상태를 함께 표시합니다.</p>
            </div>
            <CalendarDays class="h-5 w-5 text-slate-400" />
          </div>

          <div class="grid grid-cols-7 border-b border-slate-200 pb-2 text-center text-xs font-bold text-slate-500">
            <div v-for="day in weekDays" :key="day">{{ day }}</div>
          </div>
          <div class="mt-2 grid grid-cols-7 gap-2">
            <div v-for="(day, index) in calendarSlots" :key="`${day ?? 'blank'}-${index}`" class="min-h-24 rounded-lg border p-2" :class="day ? 'border-slate-200 bg-slate-50' : 'border-transparent bg-transparent'">
              <template v-if="day">
                <span class="text-sm font-bold text-slate-700">{{ day }}</span>
                <div class="mt-2 space-y-1">
                  <button
                    v-for="event in eventsByDay[day] ?? []"
                    :key="`${event.id}-${event.label}`"
                    type="button"
                    class="w-full truncate rounded-md px-2 py-1 text-left text-[11px] font-bold"
                    :class="event.type === 'selected' ? 'bg-blue-600 text-white' : 'bg-amber-50 text-amber-700'"
                    @click="selectedId = event.id"
                  >
                    {{ event.label }}
                  </button>
                </div>
              </template>
            </div>
          </div>
        </div>
      </section>

      <section class="grid gap-5 xl:grid-cols-[0.88fr_1.12fr]">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="mb-5 flex items-center justify-between gap-3">
            <div>
              <h2 class="text-lg font-bold text-slate-950">선택 청약 상세 요약</h2>
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
              <h2 class="text-lg font-bold text-slate-950">접수 전 해야 할 일</h2>
              <p class="mt-1 text-sm text-slate-500">선택한 청약의 신청 준비 계획입니다.</p>
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
                <p class="font-bold text-slate-950">AI 코치로 다음 행동을 확인할 수 있습니다</p>
                <p class="mt-1 text-sm text-slate-600">
                  추천 사유, 이번 주 할 일, 공식 확인 항목을 같은 후보 기준으로 이어서 봅니다.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
