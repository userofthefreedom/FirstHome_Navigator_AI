<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { CalendarDays, Calculator, Landmark, PiggyBank, WalletCards } from 'lucide-vue-next'
import { fetchFundingPlan, fetchHousingRecommendations, fetchNotice, fetchPolicies, fetchProducts } from '../api/firsthome'
import type { FinancialProduct, FundingPlan, Notice, Policy } from '../types/firsthome'
import { formatMoney } from '../utils/format'

const route = useRoute()
const noticeId = computed(() => Number(route.params.noticeId ?? 0))
const selectedNotice = ref<Notice | null>(null)
const fundingPlan = ref<FundingPlan | null>(null)
const financialProducts = ref<FinancialProduct[]>([])
const policies = ref<Policy[]>([])
const loading = ref(true)
const error = ref('')

const readinessRate = computed(() => {
  if (!fundingPlan.value?.down_payment) return 0
  return Math.round((fundingPlan.value.available_cash / fundingPlan.value.down_payment) * 100)
})
const readinessWidth = computed(() => `${Math.min(readinessRate.value, 100)}%`)

async function resolveNoticeId() {
  if (noticeId.value) return noticeId.value
  const recommendations = await fetchHousingRecommendations()
  return recommendations[0]?.notice_id ?? 101
}

async function loadFunding() {
  loading.value = true
  error.value = ''
  try {
    const targetNoticeId = await resolveNoticeId()
    const [noticeResponse, fundingResponse, productsResponse, policiesResponse] = await Promise.all([
      fetchNotice(targetNoticeId),
      fetchFundingPlan(targetNoticeId),
      fetchProducts(),
      fetchPolicies(),
    ])
    selectedNotice.value = noticeResponse
    fundingPlan.value = fundingResponse
    financialProducts.value = productsResponse
    policies.value = policiesResponse
  } catch {
    error.value = '백엔드 자금 로드맵 API에 연결하지 못했습니다. Django 서버가 실행 중인지 확인하세요.'
  } finally {
    loading.value = false
  }
}

watch(noticeId, loadFunding)
onMounted(loadFunding)
</script>

<template>
  <div class="space-y-5">
    <section v-if="loading" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      자금 로드맵을 불러오는 중입니다.
    </section>

    <section v-else-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-semibold text-amber-800">
      {{ error }}
    </section>

    <template v-else-if="selectedNotice && fundingPlan">
      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p class="inline-flex items-center gap-2 text-sm font-semibold text-blue-700">
              <WalletCards class="h-4 w-4" />
              자금 로드맵
            </p>
            <h1 class="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">계약금 준비 계획</h1>
            <p class="mt-2 text-sm text-slate-500">{{ selectedNotice.title }} 기준으로 계산한 자금 흐름입니다.</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <RouterLink to="/recommendations" class="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700">
              추천 다시 보기
            </RouterLink>
            <RouterLink :to="`/ai-coach/${selectedNotice.id}`" class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white">
              AI 코치 보기
            </RouterLink>
          </div>
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
            준비 가능 현금
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
            계약 예정일까지 {{ fundingPlan.months_until_contract }}개월을 기준으로 부족액을 나눠 계산했습니다.
          </p>
        </div>
      </section>

      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="flex items-center gap-2 text-lg font-bold text-slate-950">
          <CalendarDays class="h-5 w-5 text-slate-400" />
          납부 타임라인
        </h2>
        <div class="mt-5 divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200">
          <div v-for="(item, index) in fundingPlan.timeline" :key="item.label" class="grid gap-3 bg-white p-4 text-sm md:grid-cols-[72px_1fr_160px]">
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

      <section class="grid gap-5 lg:grid-cols-2">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-bold text-slate-950">예·적금 후보</h2>
          <div class="mt-4 grid gap-3">
            <div v-for="product in financialProducts" :key="product.id" class="rounded-lg border border-slate-100 bg-slate-50 p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="font-bold text-slate-950">{{ product.name }}</p>
                <span class="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">{{ product.category }}</span>
              </div>
              <p class="mt-1 text-sm text-slate-500">{{ product.provider }} · {{ product.rate }} · {{ product.period }}</p>
              <p class="mt-2 text-sm text-slate-600">{{ product.reasons[0] }}</p>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-bold text-slate-950">지원정책 후보</h2>
          <div class="mt-4 grid gap-3">
            <div v-for="policy in policies" :key="policy.id" class="rounded-lg border border-slate-100 bg-slate-50 p-4">
              <p class="font-bold text-slate-950">{{ policy.name }}</p>
              <p class="mt-1 text-sm text-slate-500">{{ policy.provider }} · {{ policy.target }}</p>
              <p class="mt-2 text-sm text-slate-600">{{ policy.benefit }}</p>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
