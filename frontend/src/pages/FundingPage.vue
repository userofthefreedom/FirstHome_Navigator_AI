<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Bookmark, CalendarDays, Calculator, ExternalLink, Landmark, PiggyBank, ShieldAlert, WalletCards } from 'lucide-vue-next'
import { addFavorite, fetchFavorites, fetchFundingPlan, fetchHousingRecommendations, fetchNotice, fetchNoticeUnitOptions, fetchPolicies, fetchProducts, removeFavorite } from '../api/firsthome'
import type { Favorite, FinancialProduct, FundingPlan, HousingUnitOption, Notice, Policy } from '../types/firsthome'
import { analysisBadgeClass, analysisSummary } from '../utils/analysisStatus'
import { formatMoney } from '../utils/format'

type OptionComparison = {
  option: HousingUnitOption
  plan?: FundingPlan
}

const route = useRoute()
const noticeId = computed(() => Number(route.params.noticeId ?? 0))
const selectedOptionId = computed(() => Number(route.query.option_id ?? 0) || null)
const selectedNotice = ref<Notice | null>(null)
const fundingPlan = ref<FundingPlan | null>(null)
const unitOptions = ref<HousingUnitOption[]>([])
const optionFundingPlans = ref<Record<number, FundingPlan>>({})
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
const optionComparisons = computed<OptionComparison[]>(() => unitOptions.value.map((option) => ({ option, plan: optionFundingPlans.value[option.id] })))
const selectedOption = computed(() => {
  if (!fundingPlan.value?.option_id) return null
  return unitOptions.value.find((option) => option.id === fundingPlan.value?.option_id) ?? null
})
const currentAnalysisSummary = computed(() => analysisSummary(selectedNotice.value?.analysis_summary, selectedNotice.value?.official_document_status))

function priceLabel(price: number) {
  return price > 0 ? formatMoney(price) : '공식 확인 필요'
}

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

async function loadOptionFundingPlans(targetNoticeId: number, options: HousingUnitOption[], currentPlan: FundingPlan) {
  if (options.length === 0) {
    optionFundingPlans.value = {}
    return
  }

  const entries = await Promise.all(
    options.map(async (option) => {
      if (currentPlan.option_id === option.id) return [option.id, currentPlan] as const
      try {
        const plan = await fetchFundingPlan(targetNoticeId, option.id)
        return [option.id, plan] as const
      } catch {
        return [option.id, undefined] as const
      }
    }),
  )
  optionFundingPlans.value = Object.fromEntries(entries.filter((entry): entry is readonly [number, FundingPlan] => Boolean(entry[1])))
}

async function loadFunding() {
  loading.value = true
  error.value = ''
  try {
    const targetNoticeId = await resolveNoticeId()
    const [noticeResponse, fundingResponse, unitOptionResponse, productsResponse, policiesResponse, favoriteResponse] = await Promise.all([
      fetchNotice(targetNoticeId),
      fetchFundingPlan(targetNoticeId, selectedOptionId.value),
      fetchNoticeUnitOptions(targetNoticeId).catch(() => []),
      fetchProducts(),
      fetchPolicies(),
      fetchFavorites(),
    ])
    selectedNotice.value = noticeResponse
    fundingPlan.value = fundingResponse
    unitOptions.value = unitOptionResponse
    financialProducts.value = productsResponse
    policies.value = policiesResponse
    favorites.value = favoriteResponse
    await loadOptionFundingPlans(targetNoticeId, unitOptionResponse, fundingResponse)
  } catch {
    error.value = '자금 로드맵 API에 연결하지 못했습니다. Django 서버가 실행 중인지 확인하세요.'
  } finally {
    loading.value = false
  }
}

function readinessForPlan(plan?: FundingPlan) {
  if (!plan?.down_payment) return 0
  return Math.round((plan.available_cash / plan.down_payment) * 100)
}

function comparisonStatus(plan?: FundingPlan) {
  if (!plan) return '계산 대기'
  if (plan.shortfall <= 0) return '계약금 준비 완료'
  if (plan.monthly_target <= 0) return '추가 목표 없음'
  return `월 ${formatMoney(plan.monthly_target)} 목표`
}

function comparisonStatusClass(plan?: FundingPlan) {
  if (!plan) return 'bg-slate-100 text-slate-500'
  if (plan.shortfall <= 0) return 'bg-emerald-50 text-emerald-700'
  return 'bg-blue-50 text-blue-700'
}

function selectedOptionLabel() {
  if (!selectedOption.value) return ''
  return `${selectedOption.value.unit_type} · ${selectedOption.value.floor_group || '전체'}`
}

watch([noticeId, selectedOptionId], loadFunding)
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
            <p class="mt-2 text-sm text-slate-500">{{ selectedNotice.title }} 기준으로 필요한 현금 흐름을 계산합니다.</p>
            <div class="mt-3 flex flex-wrap gap-2">
              <span class="rounded-md bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-700">{{ selectedNotice.data_source ?? 'fixture' }}</span>
              <span v-if="fundingPlan.schedule_source === 'payment_schedule'" class="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">
                {{ fundingPlan.unit_type }} · {{ fundingPlan.floor_group }}
              </span>
              <span class="rounded-md px-2 py-1 text-xs font-bold" :class="analysisBadgeClass(currentAnalysisSummary)">
                {{ currentAnalysisSummary.label }}
              </span>
              <span v-if="!selectedNotice.is_price_confirmed" class="rounded-md bg-amber-50 px-2 py-1 text-xs font-bold text-amber-700">금액 확인 필요</span>
            </div>
          </div>
          <div class="flex flex-wrap gap-2">
            <RouterLink to="/recommendations" class="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700">
              추천 다시 보기
            </RouterLink>
            <RouterLink :to="`/notices/${selectedNotice.id}`" class="rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700">
              공고 상세
            </RouterLink>
            <button
              type="button"
              class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700"
              :disabled="savingFavoriteKey === favoriteKey('notice', selectedNotice.id)"
              @click="toggleFavorite('notice', selectedNotice.id)"
            >
              <Bookmark class="h-4 w-4" :class="isFavorite('notice', selectedNotice.id) ? 'fill-blue-600 text-blue-600' : ''" />
              {{ isFavorite('notice', selectedNotice.id) ? '공고 저장됨' : '공고 저장' }}
            </button>
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
          <p class="mt-2 text-2xl font-bold">{{ priceLabel(fundingPlan.price) }}</p>
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
            계약 예정일까지 {{ fundingPlan.months_until_contract }}개월을 기준으로 부족액을 나눈 계산입니다.
          </p>
          <p class="mt-2 text-xs leading-5 text-blue-100">{{ currentAnalysisSummary.next_action }}</p>
          <p class="mt-3 text-xs leading-5 text-slate-400">{{ fundingPlan.notice }}</p>
        </div>
      </section>

      <section v-if="optionComparisons.length" class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p class="text-sm font-semibold text-blue-700">주택형 옵션 비교</p>
            <h2 class="mt-1 text-lg font-bold text-slate-950">분양가, 계약금, 부족액을 한 번에 비교</h2>
            <p class="mt-1 text-sm text-slate-500">공식 공고문에서 추출한 주택형별 납부 일정 기준입니다.</p>
          </div>
          <span v-if="selectedOptionLabel()" class="rounded-md bg-slate-950 px-3 py-2 text-sm font-bold text-white">
            선택: {{ selectedOptionLabel() }}
          </span>
        </div>

        <div class="mt-5 grid gap-3 xl:grid-cols-3">
          <div
            v-for="{ option, plan } in optionComparisons"
            :key="option.id"
            class="rounded-lg border p-4 transition"
            :class="fundingPlan.option_id === option.id ? 'border-blue-500 bg-blue-50 shadow-sm' : 'border-slate-200 bg-white'"
          >
            <div class="flex items-start justify-between gap-3">
              <RouterLink :to="{ path: `/funding/${selectedNotice.id}`, query: { option_id: option.id } }" class="min-w-0">
                <p class="text-xs font-bold text-blue-700">{{ option.unit_type }} · {{ option.floor_group || '전체' }}</p>
                <p class="mt-1 text-xl font-bold text-slate-950">{{ option.exclusive_area_m2 }}㎡</p>
              </RouterLink>
              <button
                type="button"
                class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600"
                :disabled="savingFavoriteKey === favoriteKey('option', option.id)"
                title="주택형 저장"
                @click="toggleFavorite('option', option.id)"
              >
                <Bookmark class="h-4 w-4" :class="isFavorite('option', option.id) ? 'fill-blue-600 text-blue-600' : ''" />
              </button>
            </div>

            <div class="mt-4 grid grid-cols-2 gap-2 text-sm">
              <div class="rounded-lg bg-slate-50 p-3">
                <p class="text-xs font-bold text-slate-500">분양가</p>
                <p class="mt-1 font-bold text-slate-950">{{ priceLabel(plan?.price ?? option.base_price) }}</p>
              </div>
              <div class="rounded-lg bg-slate-50 p-3">
                <p class="text-xs font-bold text-slate-500">계약금</p>
                <p class="mt-1 font-bold text-slate-950">{{ plan ? formatMoney(plan.down_payment) : '-' }}</p>
              </div>
              <div class="rounded-lg bg-slate-50 p-3">
                <p class="text-xs font-bold text-slate-500">부족액</p>
                <p class="mt-1 font-bold text-blue-700">{{ plan ? formatMoney(plan.shortfall) : '-' }}</p>
              </div>
              <div class="rounded-lg bg-slate-50 p-3">
                <p class="text-xs font-bold text-slate-500">준비율</p>
                <p class="mt-1 font-bold text-slate-950">{{ readinessForPlan(plan) }}%</p>
              </div>
            </div>

            <div class="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
              <div class="h-full rounded-full bg-blue-600" :style="{ width: `${Math.min(readinessForPlan(plan), 100)}%` }" />
            </div>

            <div class="mt-3 flex flex-wrap items-center gap-2">
              <span class="rounded-md px-2 py-1 text-xs font-bold" :class="comparisonStatusClass(plan)">
                {{ comparisonStatus(plan) }}
              </span>
              <span v-if="fundingPlan.option_id === option.id" class="rounded-md bg-slate-950 px-2 py-1 text-xs font-bold text-white">
                현재 선택
              </span>
              <span v-if="option.extraction_source" class="rounded-md bg-slate-100 px-2 py-1 text-xs font-bold text-slate-600">
                {{ option.extraction_source }}
              </span>
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="flex items-center gap-2 text-lg font-bold text-slate-950">
          <CalendarDays class="h-5 w-5 text-slate-400" />
          납부 타임라인
        </h2>
        <div class="mt-5 divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200">
          <div v-for="(item, index) in fundingPlan.timeline" :key="`${item.label}-${index}`" class="grid gap-3 bg-white p-4 text-sm md:grid-cols-[72px_1fr_160px]">
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
          참고 안내
        </p>
        <p class="mt-2">
          자금 로드맵은 입력값과 공고문 추출값 기반의 참고 계산입니다. 실제 계약금, 중도금, 잔금 납부 조건은 공식 공고문과 기관 안내를 확인해야 합니다.
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
          <h2 class="text-lg font-bold text-slate-950">저축 상품 후보</h2>
          <div class="mt-4 grid gap-3">
            <p v-if="financialProducts.length === 0" class="rounded-lg bg-slate-50 p-4 text-sm font-semibold text-slate-600">
              조건에 맞는 상품 후보가 없습니다. 목표 기간이나 월 저축 가능액을 조정해보세요.
            </p>
            <div v-for="product in financialProducts" :key="product.id" class="rounded-lg border border-slate-100 bg-slate-50 p-4">
              <div class="flex flex-wrap items-center justify-between gap-2">
                <p class="font-bold text-slate-950">{{ product.name }}</p>
                <span class="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">{{ product.category }}</span>
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
