<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Bookmark, CalendarDays, Calculator, ExternalLink, Landmark, PiggyBank, ShieldAlert, WalletCards } from 'lucide-vue-next'
import { addFavorite, fetchFavorites, fetchFundingPlan, fetchHousingRecommendations, fetchNotice, fetchPolicies, fetchProducts, removeFavorite } from '../api/firsthome'
import type { Favorite, FinancialProduct, FundingPlan, Notice, Policy } from '../types/firsthome'
import { formatMoney } from '../utils/format'

const route = useRoute()
const noticeId = computed(() => Number(route.params.noticeId ?? 0))
const selectedNotice = ref<Notice | null>(null)
const fundingPlan = ref<FundingPlan | null>(null)
const financialProducts = ref<FinancialProduct[]>([])
const policies = ref<Policy[]>([])
const favorites = ref<Favorite[]>([])
const loading = ref(true)
const savingFavoriteKey = ref('')
const error = ref('')

const readinessRate = computed(() => {
  if (!fundingPlan.value?.down_payment) return 0
  return Math.round((fundingPlan.value.available_cash / fundingPlan.value.down_payment) * 100)
})
const readinessWidth = computed(() => `${Math.min(readinessRate.value, 100)}%`)

function favoriteKey(favoriteType: Favorite['favorite_type'], objectId: number) {
  return `${favoriteType}-${objectId}`
}

function isFavorite(favoriteType: Favorite['favorite_type'], objectId: number) {
  return favorites.value.some((favorite) => favorite.favorite_type === favoriteType && favorite.object_id === objectId)
}

async function toggleFavorite(favoriteType: Favorite['favorite_type'], objectId: number) {
  const favorite = { favorite_type: favoriteType, object_id: objectId }
  savingFavoriteKey.value = favoriteKey(favoriteType, objectId)
  try {
    if (isFavorite(favoriteType, objectId)) {
      await removeFavorite(favorite)
      favorites.value = favorites.value.filter((item) => item.favorite_type !== favoriteType || item.object_id !== objectId)
    } else {
      const saved = await addFavorite(favorite)
      favorites.value = [...favorites.value, saved]
    }
  } finally {
    savingFavoriteKey.value = ''
  }
}

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
    const [noticeResponse, fundingResponse, productsResponse, policiesResponse, favoriteResponse] = await Promise.all([
      fetchNotice(targetNoticeId),
      fetchFundingPlan(targetNoticeId),
      fetchProducts(),
      fetchPolicies(),
      fetchFavorites(),
    ])
    selectedNotice.value = noticeResponse
    fundingPlan.value = fundingResponse
    financialProducts.value = productsResponse
    policies.value = policiesResponse
    favorites.value = favoriteResponse
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
            <RouterLink :to="`/notices/${selectedNotice.id}`" class="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700">
              공고 상세
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
          <p class="mt-3 text-xs leading-5 text-slate-400">{{ fundingPlan.notice }}</p>
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

      <section class="rounded-lg border border-amber-100 bg-amber-50 p-5 text-sm leading-6 text-amber-800">
        <p class="flex items-center gap-2 font-bold">
          <ShieldAlert class="h-4 w-4" />
          참고용 안내
        </p>
        <p class="mt-2">
          자금 로드맵은 입력값과 fixture 공고 기준의 단순 계산입니다. 실제 계약금, 중도금, 잔금 납부 조건은 공식 공고와 기관 안내를 확인해야 합니다.
        </p>
        <a
          v-if="selectedNotice.source_url"
          :href="selectedNotice.source_url"
          target="_blank"
          rel="noreferrer"
          class="mt-3 inline-flex items-center gap-1 font-bold text-amber-900 underline underline-offset-4"
        >
          공식 출처 열기
          <ExternalLink class="h-4 w-4" />
        </a>
      </section>

      <section class="grid gap-5 lg:grid-cols-2">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-bold text-slate-950">예·적금 후보</h2>
          <div class="mt-4 grid gap-3">
            <p v-if="financialProducts.length === 0" class="rounded-lg bg-slate-50 p-4 text-sm font-semibold text-slate-600">
              조건에 맞는 상품 후보가 없습니다. 목표 기간이나 월 저축 가능액을 완화해 보세요.
            </p>
            <div v-for="product in financialProducts" :key="product.id" class="rounded-lg border border-slate-100 bg-slate-50 p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="font-bold text-slate-950">{{ product.name }}</p>
                <div class="flex flex-wrap gap-2">
                  <span class="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">{{ product.category }}</span>
                  <span v-if="product.protection_status" class="rounded-md bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-700">예금자보호</span>
                </div>
              </div>
              <p class="mt-1 text-sm text-slate-500">{{ product.provider }} · {{ product.rate }} · {{ product.period }}</p>
              <p class="mt-2 text-sm text-slate-600">{{ product.reasons[0] }}</p>
              <button
                type="button"
                class="mt-3 inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700"
                :disabled="savingFavoriteKey === favoriteKey('product', product.id)"
                @click="toggleFavorite('product', product.id)"
              >
                <Bookmark class="h-4 w-4" :class="isFavorite('product', product.id) ? 'fill-blue-600 text-blue-600' : ''" />
                {{ isFavorite('product', product.id) ? '저장됨' : '상품 저장' }}
              </button>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-bold text-slate-950">지원정책 후보</h2>
          <div class="mt-4 grid gap-3">
            <p v-if="policies.length === 0" class="rounded-lg bg-slate-50 p-4 text-sm font-semibold text-slate-600">
              조건에 맞는 정책 후보가 없습니다. 공식 청년정책 검색에서 지역과 소득 조건을 다시 확인하세요.
            </p>
            <div v-for="policy in policies" :key="policy.id" class="rounded-lg border border-slate-100 bg-slate-50 p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="font-bold text-slate-950">{{ policy.name }}</p>
                <span v-if="policy.policy_category" class="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">{{ policy.policy_category }}</span>
              </div>
              <p class="mt-1 text-sm text-slate-500">{{ policy.provider }} · {{ policy.target }}</p>
              <p class="mt-2 text-sm text-slate-600">{{ policy.benefit }}</p>
              <button
                type="button"
                class="mt-3 inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-bold text-slate-700"
                :disabled="savingFavoriteKey === favoriteKey('policy', policy.id)"
                @click="toggleFavorite('policy', policy.id)"
              >
                <Bookmark class="h-4 w-4" :class="isFavorite('policy', policy.id) ? 'fill-blue-600 text-blue-600' : ''" />
                {{ isFavorite('policy', policy.id) ? '저장됨' : '정책 저장' }}
              </button>
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
