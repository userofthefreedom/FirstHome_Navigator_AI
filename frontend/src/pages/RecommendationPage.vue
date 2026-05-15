<script setup lang="ts">
import {
  ArrowUpDown,
  CalendarDays,
  CheckCircle2,
  ChevronRight,
  Clock3,
  MapPin,
  ShieldAlert,
  Sparkles,
} from 'lucide-vue-next'
import { housingRecommendations } from '../data/sampleData'

function formatMoney(value: number) {
  return `${Math.round(value / 10000).toLocaleString()}만원`
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-sm font-semibold text-blue-700">추천 청약</p>
        <h1 class="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">조건 기반 매칭 결과</h1>
        <p class="mt-2 text-sm text-slate-500">React 백업의 리스트형 추천 카드 디자인을 Vue 화면에 맞췄습니다.</p>
      </div>
      <button class="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50">
        <ArrowUpDown class="h-4 w-4" />
        매칭률순
      </button>
    </div>

    <section class="space-y-4">
      <div class="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
            <Sparkles class="h-5 w-5" />
          </div>
          <div>
            <p class="font-bold text-slate-950">{{ housingRecommendations.length }}개 청약이 조건과 맞습니다</p>
            <p class="text-sm text-slate-500">매칭률, 자금 적합도, 일정 리스크를 함께 반영했습니다.</p>
          </div>
        </div>
      </div>

      <article
        v-for="(item, index) in housingRecommendations"
        :key="item.notice_id"
        class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
      >
        <div class="grid gap-5 lg:grid-cols-[1fr_220px]">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <span class="rounded-md bg-slate-950 px-2 py-1 text-xs font-bold text-white">추천 {{ index + 1 }}</span>
              <span class="rounded-md bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">{{ item.supply_type }}</span>
            </div>
            <h2 class="mt-3 text-xl font-bold text-slate-950">{{ item.title }}</h2>
            <p class="mt-2 flex items-center gap-1 text-sm text-slate-500">
              <MapPin class="h-4 w-4" />
              {{ item.provider }} · {{ item.region }} · {{ item.district }}
            </p>

            <div class="mt-5 grid gap-3 sm:grid-cols-5">
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">자격</p>
                <p class="mt-1 font-bold">{{ item.score_detail.eligibility }}점</p>
              </div>
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">자금</p>
                <p class="mt-1 font-bold">{{ item.score_detail.funding }}점</p>
              </div>
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">입지</p>
                <p class="mt-1 font-bold">{{ item.score_detail.location }}점</p>
              </div>
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">일정</p>
                <p class="mt-1 font-bold">{{ item.score_detail.schedule }}점</p>
              </div>
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">정책</p>
                <p class="mt-1 font-bold">{{ item.score_detail.policy_link }}점</p>
              </div>
            </div>

            <div class="mt-5 space-y-2">
              <p class="text-sm font-semibold text-slate-700">추천 근거</p>
              <div v-for="reason in item.reasons" :key="reason" class="flex items-start gap-2 text-sm text-slate-600">
                <CheckCircle2 class="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                <span>{{ reason }}</span>
              </div>
            </div>
          </div>

          <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div class="flex items-center justify-between">
              <p class="text-sm font-semibold text-slate-500">매칭률</p>
              <p class="text-2xl font-bold text-slate-950">{{ item.total_score }}%</p>
            </div>
            <div class="mt-3 h-3 overflow-hidden rounded-full bg-white">
              <div class="h-full rounded-full bg-blue-600" :style="{ width: `${item.total_score}%` }" />
            </div>
            <div class="mt-5 space-y-3 text-sm">
              <div class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-slate-500">
                  <CalendarDays class="h-4 w-4" />
                  접수 마감
                </span>
                <span class="font-bold text-slate-950">2026-05</span>
              </div>
              <div class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-slate-500">
                  <Clock3 class="h-4 w-4" />
                  공식 확인
                </span>
                <ShieldAlert class="h-4 w-4 text-amber-600" />
              </div>
            </div>
            <p class="mt-5 text-sm text-slate-500">예상 분양가</p>
            <p class="mt-1 text-lg font-bold text-slate-950">{{ formatMoney(item.price) }}</p>
            <RouterLink
              to="/funding"
              class="mt-5 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-bold text-white transition hover:bg-blue-700"
            >
              자금 로드맵 보기
              <ChevronRight class="h-4 w-4" />
            </RouterLink>
          </div>
        </div>
      </article>
    </section>
  </div>
</template>
