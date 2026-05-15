<script setup lang="ts">
import {
  Bot,
  CheckCircle2,
  ClipboardCheck,
  ShieldAlert,
  WalletCards,
} from 'lucide-vue-next'
import { aiCoach, fundingPlan, housingRecommendations } from '../data/sampleData'

const selectedNotice = housingRecommendations.find((item) => item.notice_id === fundingPlan.notice_id)

function formatMoney(value: number) {
  return `${Math.round(value / 10000).toLocaleString()}만원`
}
</script>

<template>
  <div class="space-y-5">
    <section class="rounded-lg border border-slate-200 bg-slate-950 p-5 text-white shadow-sm sm:p-6">
      <p class="inline-flex items-center gap-2 text-sm font-semibold text-blue-200">
        <Bot class="h-4 w-4" />
        AI 코치
      </p>
      <div class="mt-4 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div>
          <h1 class="text-2xl font-bold">{{ selectedNotice?.title }}</h1>
          <p class="mt-2 text-sm text-slate-300">{{ aiCoach.summary }}</p>
        </div>
        <div class="rounded-lg bg-white/10 px-5 py-4 text-center">
          <p class="flex items-center justify-center gap-2 text-xs text-blue-200">
            <WalletCards class="h-4 w-4" />
            부족 계약금
          </p>
          <p class="mt-1 text-2xl font-bold">{{ formatMoney(fundingPlan.shortfall) }}</p>
        </div>
      </div>
    </section>

    <section class="grid gap-5 lg:grid-cols-2">
      <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="flex items-center gap-2 text-lg font-bold text-slate-950">
          <ClipboardCheck class="h-5 w-5 text-blue-700" />
          이번 주 체크리스트
        </h2>
        <ol class="mt-5 space-y-3">
          <li
            v-for="(todo, index) in aiCoach.todo_this_week"
            :key="todo"
            class="flex gap-3 rounded-lg border border-slate-100 bg-slate-50 p-4"
          >
            <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-blue-600 text-xs font-bold text-white">
              {{ index + 1 }}
            </span>
            <span class="text-sm leading-6 text-slate-700">{{ todo }}</span>
          </li>
        </ol>
      </div>

      <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="flex items-center gap-2 text-lg font-bold text-slate-950">
          <CheckCircle2 class="h-5 w-5 text-emerald-600" />
          공식 확인 항목
        </h2>
        <div class="mt-5 grid gap-3">
          <div
            v-for="item in aiCoach.official_checklist"
            :key="item"
            class="rounded-lg border border-slate-100 bg-slate-50 p-4"
          >
            <p class="font-bold text-slate-800">{{ item }}</p>
            <p class="mt-1 text-xs leading-5 text-slate-500">추천 결과와 별개로 공식 공고문에서 직접 확인해야 합니다.</p>
          </div>
        </div>
      </div>
    </section>

    <section class="rounded-lg border border-amber-100 bg-amber-50 p-5 text-sm leading-6 text-amber-800">
      <p class="flex items-center gap-2 font-bold">
        <ShieldAlert class="h-4 w-4" />
        주의
      </p>
      <p class="mt-2">{{ aiCoach.warning }}</p>
    </section>
  </div>
</template>
