<script setup lang="ts">
import {
  CalendarDays,
  Calculator,
  Landmark,
  PiggyBank,
  WalletCards,
} from 'lucide-vue-next'
import { fundingPlan, housingRecommendations } from '../data/sampleData'

const selectedNotice = housingRecommendations.find((item) => item.notice_id === fundingPlan.notice_id)
const readinessRate = Math.round((fundingPlan.available_cash / fundingPlan.down_payment) * 100)
const readinessWidth = `${Math.min(readinessRate, 100)}%`

function formatMoney(value: number) {
  return `${Math.round(value / 10000).toLocaleString()}만원`
}
</script>

<template>
  <div class="space-y-5">
    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <p class="inline-flex items-center gap-2 text-sm font-semibold text-blue-700">
            <WalletCards class="h-4 w-4" />
            자금 로드맵
          </p>
          <h1 class="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">계약금 준비 계획</h1>
          <p class="mt-2 text-sm text-slate-500">{{ selectedNotice?.title }} 기준으로 계산한 자금 흐름입니다.</p>
        </div>
        <RouterLink to="/recommendations" class="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700">
          추천 다시 보기
        </RouterLink>
      </div>
    </section>

    <section class="grid gap-3 md:grid-cols-4">
      <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <p class="flex items-center gap-2 text-sm text-slate-500">
          <Landmark class="h-4 w-4" />
          예상 분양가
        </p>
        <p class="mt-2 text-2xl font-bold">{{ formatMoney(fundingPlan.price) }}</p>
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
          보유 현금
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

    <section class="grid gap-5 lg:grid-cols-2">
      <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex items-center justify-between gap-3">
          <div>
            <p class="text-sm font-semibold text-blue-700">계약금 준비율</p>
            <h2 class="mt-1 text-xl font-bold">{{ readinessRate }}% 준비됨</h2>
          </div>
          <span class="rounded-md bg-blue-50 px-3 py-1 text-sm font-bold text-blue-700">
            목표 {{ formatMoney(fundingPlan.down_payment) }}
          </span>
        </div>
        <div class="mt-6 h-3 overflow-hidden rounded-full bg-slate-100">
          <div class="h-full rounded-full bg-blue-600" :style="{ width: readinessWidth }" />
        </div>
      </div>

      <div class="rounded-lg border border-slate-200 bg-slate-950 p-5 text-white shadow-sm">
        <p class="text-sm font-semibold text-slate-300">월 저축 목표</p>
        <h2 class="mt-1 text-2xl font-bold">{{ formatMoney(fundingPlan.monthly_target) }}</h2>
        <p class="mt-3 text-sm leading-6 text-slate-300">
          계약 예정까지 {{ fundingPlan.months_until_contract }}개월을 기준으로 부족액을 나눠 계산했습니다.
        </p>
      </div>
    </section>

    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="flex items-center gap-2 text-lg font-bold text-slate-950">
        <CalendarDays class="h-5 w-5 text-slate-400" />
        납부 타임라인
      </h2>
      <div class="mt-5 divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200">
        <div
          v-for="(item, index) in fundingPlan.timeline"
          :key="item.label"
          class="grid gap-3 bg-white p-4 text-sm md:grid-cols-[72px_1fr_160px]"
        >
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 font-bold text-blue-700">
            {{ index + 1 }}
          </div>
          <div>
            <p class="font-bold text-slate-950">{{ item.label }}</p>
            <p class="mt-1 text-slate-500">{{ item.date }}</p>
          </div>
          <p class="font-bold text-slate-950 md:text-right">{{ formatMoney(item.amount) }}</p>
        </div>
      </div>
    </section>
  </div>
</template>
