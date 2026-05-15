<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'
import {
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  FileCheck2,
  MapPin,
  ShieldAlert,
  Sparkles,
  Trophy,
} from 'lucide-vue-next'
import { documents, profile, subscriptions } from '../data/sampleData'

const selectedId = ref(subscriptions[0].id)
const weekDays = ['일', '월', '화', '수', '목', '금', '토']
const calendarSlots = Array.from({ length: 42 }, (_, index) => {
  const day = index - 4
  return day >= 1 && day <= 31 ? day : null
})

const selected = computed(() => subscriptions.find((item) => item.id === selectedId.value) ?? subscriptions[0])

const eventsByDay = computed(() => {
  return subscriptions.reduce<Record<number, Array<{ id: number; label: string; type: 'deadline' | 'selected' }>>>(
    (acc, item) => {
      const day = Number(item.deadline.split('-')[2])
      acc[day] = [
        ...(acc[day] ?? []),
        {
          id: item.id,
          label: item.name,
          type: item.id === selectedId.value ? 'selected' : 'deadline',
        },
      ]
      return acc
    },
    {},
  )
})

const preApplyTasks = computed(() => [
  {
    title: '청약 자격과 예치금 확인',
    date: '오늘',
    status: '진행',
    description: `${selected.value.supplyType} 1순위 조건, 지역별 예치금, 무주택 기준을 다시 확인합니다.`,
  },
  {
    title: '필수 서류 발급 기준 확인',
    date: 'D-7',
    status: '준비',
    description: `${documents.slice(0, 3).join(', ')}가 공고일 이후 발급본인지 확인합니다.`,
  },
  {
    title: '청약 접수 완료',
    date: selected.value.deadline,
    status: '마감',
    description: '신청 대상 주택형과 접수번호를 저장하고 접수 화면을 보관합니다.',
  },
  {
    title: '당첨자 발표 알림 설정',
    date: selected.value.winnerDate,
    status: '예정',
    description: '발표일 이후 계약금 납부와 중도금 대출 검토 일정으로 이어갑니다.',
  },
])

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
</script>

<template>
  <div class="space-y-5">
    <section class="grid gap-5 xl:grid-cols-[1.08fr_0.92fr]">
      <div class="overflow-hidden rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
        <div class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div class="min-w-0">
            <div class="mb-4 inline-flex items-center gap-2 rounded-md bg-blue-50 px-3 py-1 text-sm font-bold text-blue-700">
              <Sparkles class="h-4 w-4" />
              청약 AI 대시보드
            </div>
            <h1 class="max-w-3xl break-words text-2xl font-bold leading-tight text-slate-950 sm:text-3xl">
              {{ profile.name }}님의 추천 청약 순위와 접수 일정을 한눈에 관리합니다
            </h1>
            <p class="mt-3 max-w-2xl text-sm leading-6 text-slate-600">
              React 백업 화면의 달력, 순위 리스트, 선택 청약 상세, 접수 전 체크리스트 구조를 Vue로 옮겼습니다.
            </p>
          </div>
          <RouterLink
            to="/profile"
            class="inline-flex h-11 items-center justify-center rounded-lg bg-slate-950 px-4 text-sm font-bold text-white transition hover:bg-slate-800"
          >
            조건 수정
          </RouterLink>
        </div>

        <div class="mt-6 grid gap-3 md:grid-cols-4">
          <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p class="text-sm font-semibold text-slate-500">추천 청약</p>
            <p class="mt-2 text-xl font-bold text-slate-950">{{ subscriptions.length }}건</p>
          </div>
          <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p class="text-sm font-semibold text-slate-500">최고 매칭률</p>
            <p class="mt-2 text-xl font-bold text-slate-950">{{ subscriptions[0].matchScore }}%</p>
          </div>
          <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p class="text-sm font-semibold text-slate-500">가장 빠른 마감</p>
            <p class="mt-2 text-xl font-bold text-slate-950">{{ subscriptions[0].deadline }}</p>
          </div>
          <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p class="text-sm font-semibold text-slate-500">자격 점수</p>
            <p class="mt-2 text-xl font-bold text-slate-950">{{ profile.score }}점</p>
          </div>
        </div>
      </div>

      <div class="rounded-lg border border-slate-200 bg-slate-950 p-5 text-white shadow-sm sm:p-6">
        <div class="flex items-start justify-between gap-3">
          <div>
            <p class="text-sm font-semibold text-slate-300">현재 선택 청약</p>
            <h2 class="mt-1 text-2xl font-bold">{{ selected.name }}</h2>
            <p class="mt-2 text-sm text-slate-300">{{ selected.district }}</p>
          </div>
          <span class="rounded-md bg-blue-500 px-2.5 py-1 text-sm font-bold text-white">
            {{ selected.matchScore }}%
          </span>
        </div>
        <div class="mt-5 h-3 overflow-hidden rounded-full bg-white/10">
          <div class="h-full rounded-full bg-emerald-400" :style="{ width: `${selected.matchScore}%` }" />
        </div>
        <div class="mt-5 grid grid-cols-2 gap-3 text-sm">
          <div class="rounded-lg bg-white/10 p-3">
            <p class="text-slate-300">분양가</p>
            <p class="mt-1 font-bold text-white">{{ selected.price }}</p>
          </div>
          <div class="rounded-lg bg-white/10 p-3">
            <p class="text-slate-300">당첨 발표</p>
            <p class="mt-1 font-bold text-white">{{ selected.winnerDate }}</p>
          </div>
          <div class="rounded-lg bg-white/10 p-3">
            <p class="text-slate-300">계약금</p>
            <p class="mt-1 font-bold text-white">{{ selected.deposit }}</p>
          </div>
          <div class="rounded-lg bg-white/10 p-3">
            <p class="text-slate-300">입주 예정</p>
            <p class="mt-1 font-bold text-white">{{ selected.moveIn }}</p>
          </div>
        </div>
      </div>
    </section>

    <section class="grid gap-5 xl:grid-cols-[0.88fr_1.12fr]">
      <div class="rounded-lg border border-slate-200 bg-white shadow-sm">
        <div class="flex items-center justify-between gap-3 border-b border-slate-200 p-5">
          <div>
            <h2 class="text-lg font-bold text-slate-950">청약 순위 요약</h2>
            <p class="mt-1 text-sm text-slate-500">청약을 선택하면 오른쪽 달력과 하단 상세가 함께 바뀝니다.</p>
          </div>
          <Trophy class="h-5 w-5 text-blue-600" />
        </div>
        <div class="divide-y divide-slate-100">
          <button
            v-for="(item, index) in subscriptions"
            :key="item.id"
            type="button"
            class="grid w-full gap-4 p-5 text-left transition sm:grid-cols-[1fr_auto]"
            :class="item.id === selectedId ? 'bg-blue-50/80' : 'hover:bg-slate-50'"
            @click="selectedId = item.id"
          >
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <span class="rounded-md px-2.5 py-1 text-xs font-bold" :class="rankClass(index + 1)">
                  {{ index + 1 }}순위
                </span>
                <h3 class="font-bold text-slate-950">{{ item.name }}</h3>
                <span class="rounded-md bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600">
                  {{ item.supplyType }}
                </span>
              </div>
              <div class="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-slate-500">
                <span class="inline-flex items-center gap-1">
                  <MapPin class="h-4 w-4" />
                  {{ item.district }}
                </span>
                <span>{{ item.area }}</span>
                <span>{{ item.price }}</span>
              </div>
            </div>
            <div class="grid grid-cols-2 gap-2 text-sm sm:w-52">
              <div class="rounded-lg bg-white p-3">
                <p class="text-slate-500">매칭률</p>
                <p class="mt-1 font-bold text-blue-700">{{ item.matchScore }}%</p>
              </div>
              <div class="rounded-lg bg-white p-3">
                <p class="text-slate-500">마감</p>
                <p class="mt-1 font-bold text-slate-950">{{ item.deadline }}</p>
              </div>
            </div>
          </button>
        </div>
      </div>

      <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="mb-5 flex items-center justify-between gap-3">
          <div>
            <h2 class="text-lg font-bold text-slate-950">2026년 5월 청약 캘린더</h2>
            <p class="mt-1 text-sm text-slate-500">접수 마감일과 선택 상태를 함께 표시합니다.</p>
          </div>
          <CalendarDays class="h-5 w-5 text-slate-400" />
        </div>

        <div class="grid grid-cols-7 border-b border-slate-200 pb-2 text-center text-xs font-bold text-slate-500">
          <div v-for="day in weekDays" :key="day">{{ day }}</div>
        </div>
        <div class="mt-2 grid grid-cols-7 gap-2">
          <div
            v-for="(day, index) in calendarSlots"
            :key="`${day ?? 'blank'}-${index}`"
            class="min-h-24 rounded-lg border p-2"
            :class="[
              day ? 'border-slate-200 bg-slate-50' : 'border-transparent bg-transparent',
              day === 15 ? 'ring-2 ring-blue-200' : '',
            ]"
          >
            <template v-if="day">
              <div class="flex items-center justify-between">
                <span class="text-sm font-bold" :class="day === 15 ? 'text-blue-700' : 'text-slate-700'">
                  {{ day }}
                </span>
                <span v-if="day === 15" class="rounded-md bg-blue-600 px-1.5 py-0.5 text-[10px] font-bold text-white">
                  오늘
                </span>
              </div>
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
            <p class="mt-1 text-sm text-slate-500">{{ selected.name }} 기준</p>
          </div>
          <RouterLink to="/recommendations" class="text-sm font-bold text-blue-700 hover:text-blue-800">상세 비교</RouterLink>
        </div>

        <div class="grid gap-3 sm:grid-cols-2">
          <div v-for="[label, value] in [
            ['위치', selected.district],
            ['공급 유형', selected.supplyType],
            ['분양가', selected.price],
            ['전용면적', selected.area],
            ['경쟁률', selected.competition],
            ['입주 예정', selected.moveIn],
          ]" :key="label" class="rounded-lg bg-slate-50 p-4">
            <p class="text-sm text-slate-500">{{ label }}</p>
            <p class="mt-1 font-bold text-slate-950">{{ value }}</p>
          </div>
        </div>

        <div class="mt-5 grid gap-4 md:grid-cols-2">
          <div>
            <p class="mb-2 text-sm font-bold text-slate-700">추천 근거</p>
            <div class="space-y-2">
              <div v-for="strength in selected.strengths" :key="strength" class="flex items-start gap-2 text-sm text-slate-600">
                <CheckCircle2 class="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                <span>{{ strength }}</span>
              </div>
            </div>
          </div>
          <div>
            <p class="mb-2 text-sm font-bold text-slate-700">주의 사항</p>
            <div class="space-y-2">
              <div v-for="caution in selected.cautions" :key="caution" class="flex items-start gap-2 text-sm text-slate-600">
                <ShieldAlert class="mt-0.5 h-4 w-4 shrink-0 text-amber-600" />
                <span>{{ caution }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="mb-5 flex items-center justify-between gap-3">
          <div>
            <h2 class="text-lg font-bold text-slate-950">접수 전 해야 할 일</h2>
            <p class="mt-1 text-sm text-slate-500">선택한 청약의 신청 준비 계획</p>
          </div>
          <ClipboardList class="h-5 w-5 text-slate-400" />
        </div>

        <div class="space-y-3">
          <div
            v-for="(task, index) in preApplyTasks"
            :key="task.title"
            class="grid gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4 sm:grid-cols-[72px_1fr]"
          >
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
              <p class="font-bold text-slate-950">신청 후에는 계약 관리 모드로 전환됩니다</p>
              <p class="mt-1 text-sm text-slate-600">
                당첨 발표, 계약금, 중도금 대출, 잔금 계획을 단계별로 이어서 관리할 수 있습니다.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>
