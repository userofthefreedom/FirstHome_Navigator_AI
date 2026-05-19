<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeft, Bookmark, CalendarDays, CheckCircle2, ExternalLink, FileCheck2, ShieldAlert, WalletCards } from 'lucide-vue-next'
import { addFavorite, fetchFavorites, fetchFundingPlan, fetchHousingRecommendations, fetchNotice, removeFavorite } from '../api/firsthome'
import type { Favorite, FundingPlan, HousingRecommendation, Notice } from '../types/firsthome'
import { formatMoney } from '../utils/format'

const route = useRoute()
const noticeId = computed(() => Number(route.params.noticeId ?? 0))
const selectedNotice = ref<Notice | null>(null)
const recommendation = ref<HousingRecommendation | null>(null)
const fundingPlan = ref<FundingPlan | null>(null)
const favorites = ref<Favorite[]>([])
const loading = ref(true)
const savingFavorite = ref(false)
const error = ref('')

const noticeFavorite = computed<Favorite | null>(() => {
  if (!selectedNotice.value) return null
  return { favorite_type: 'notice', object_id: selectedNotice.value.id }
})
const isFavorite = computed(() => {
  if (!noticeFavorite.value) return false
  return favorites.value.some((favorite) => favorite.favorite_type === 'notice' && favorite.object_id === noticeFavorite.value?.object_id)
})
const officialChecklist = computed(() => {
  if (!selectedNotice.value) return []
  return [
    `${selectedNotice.value.supply_type} 세부 자격과 우선공급 기준`,
    `소득·자산 기준과 ${selectedNotice.value.required_documents.slice(0, 2).join(', ')} 발급 가능 여부`,
    `${selectedNotice.value.application_deadline} 접수 마감과 ${selectedNotice.value.contract_date} 계약 일정`,
  ]
})

async function resolveNoticeId() {
  if (noticeId.value) return noticeId.value
  const recommendations = await fetchHousingRecommendations()
  return recommendations[0]?.notice_id ?? 101
}

async function loadDetail() {
  loading.value = true
  error.value = ''
  try {
    const targetNoticeId = await resolveNoticeId()
    const [noticeResponse, fundingResponse, favoriteResponse, recommendations] = await Promise.all([
      fetchNotice(targetNoticeId),
      fetchFundingPlan(targetNoticeId),
      fetchFavorites(),
      fetchHousingRecommendations(),
    ])
    selectedNotice.value = noticeResponse
    fundingPlan.value = fundingResponse
    favorites.value = favoriteResponse
    recommendation.value = recommendations.find((item) => item.notice_id === targetNoticeId) ?? null
  } catch {
    error.value = '공고 상세 API에 연결하지 못했습니다. Django 서버가 실행 중인지 확인하세요.'
  } finally {
    loading.value = false
  }
}

async function toggleFavorite() {
  if (!noticeFavorite.value) return
  savingFavorite.value = true
  try {
    if (isFavorite.value) {
      await removeFavorite(noticeFavorite.value)
      favorites.value = favorites.value.filter((favorite) => favorite.favorite_type !== 'notice' || favorite.object_id !== noticeFavorite.value?.object_id)
    } else {
      const saved = await addFavorite(noticeFavorite.value)
      favorites.value = [...favorites.value, saved]
    }
  } finally {
    savingFavorite.value = false
  }
}

watch(noticeId, loadDetail)
onMounted(loadDetail)
</script>

<template>
  <div class="space-y-5">
    <section v-if="loading" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      공고 상세를 불러오는 중입니다.
    </section>

    <section v-else-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-semibold text-amber-800">
      {{ error }}
    </section>

    <template v-else-if="selectedNotice && fundingPlan">
      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <RouterLink to="/recommendations" class="inline-flex items-center gap-2 text-sm font-bold text-slate-600 hover:text-slate-950">
              <ArrowLeft class="h-4 w-4" />
              추천 목록
            </RouterLink>
            <div class="mt-4 flex flex-wrap items-center gap-2">
              <span class="rounded-md bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700">{{ selectedNotice.supply_type }}</span>
              <span class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-bold text-slate-700">{{ selectedNotice.region }}</span>
              <span v-if="recommendation" class="rounded-md bg-slate-950 px-2.5 py-1 text-xs font-bold text-white">{{ recommendation.total_score }}점</span>
            </div>
            <h1 class="mt-3 text-2xl font-bold text-slate-950 sm:text-3xl">{{ selectedNotice.title }}</h1>
            <p class="mt-2 text-sm text-slate-500">{{ selectedNotice.provider }} · {{ selectedNotice.district }} · {{ selectedNotice.area }}</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button
              type="button"
              class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
              :disabled="savingFavorite"
              @click="toggleFavorite"
            >
              <Bookmark class="h-4 w-4" :class="isFavorite ? 'fill-blue-600 text-blue-600' : ''" />
              {{ isFavorite ? '관심 저장됨' : '관심 저장' }}
            </button>
            <RouterLink :to="`/funding/${selectedNotice.id}`" class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white">
              <WalletCards class="h-4 w-4" />
              자금 로드맵
            </RouterLink>
          </div>
        </div>
      </section>

      <section class="grid gap-3 md:grid-cols-4">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm text-slate-500">예상 분양가</p>
          <p class="mt-2 text-2xl font-bold text-slate-950">{{ formatMoney(selectedNotice.price) }}</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm text-slate-500">계약금</p>
          <p class="mt-2 text-2xl font-bold text-slate-950">{{ formatMoney(fundingPlan.down_payment) }}</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm text-slate-500">부족액</p>
          <p class="mt-2 text-2xl font-bold text-blue-700">{{ formatMoney(fundingPlan.shortfall) }}</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm text-slate-500">접수 마감</p>
          <p class="mt-2 text-2xl font-bold text-slate-950">{{ selectedNotice.application_deadline }}</p>
        </div>
      </section>

      <section class="grid gap-5 lg:grid-cols-[1fr_0.92fr]">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="flex items-center gap-2 text-lg font-bold text-slate-950">
            <FileCheck2 class="h-5 w-5 text-blue-700" />
            공식 확인 체크리스트
          </h2>
          <div class="mt-5 grid gap-3">
            <div v-for="item in officialChecklist" :key="item" class="flex items-start gap-3 rounded-lg bg-slate-50 p-4 text-sm text-slate-700">
              <CheckCircle2 class="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
              <span>{{ item }}</span>
            </div>
          </div>

          <div class="mt-5">
            <p class="mb-2 text-sm font-bold text-slate-700">필수 서류</p>
            <div class="flex flex-wrap gap-2">
              <span v-for="document in selectedNotice.required_documents" :key="document" class="rounded-md bg-blue-50 px-2.5 py-1 text-xs font-bold text-blue-700">
                {{ document }}
              </span>
            </div>
          </div>
        </div>

        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="flex items-center gap-2 text-lg font-bold text-slate-950">
            <CalendarDays class="h-5 w-5 text-slate-400" />
            주요 일정
          </h2>
          <div class="mt-5 divide-y divide-slate-100 overflow-hidden rounded-lg border border-slate-200">
            <div v-for="item in fundingPlan.timeline" :key="item.label" class="grid gap-1 bg-white p-4 text-sm">
              <p class="font-bold text-slate-950">{{ item.label }}</p>
              <div class="flex flex-wrap justify-between gap-3 text-slate-500">
                <span>{{ item.date }}</span>
                <span>{{ formatMoney(item.amount) }}</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-amber-100 bg-amber-50 p-5 text-sm leading-6 text-amber-800">
        <p class="flex items-center gap-2 font-bold">
          <ShieldAlert class="h-4 w-4" />
          참고용 안내
        </p>
        <p class="mt-2">
          추천 결과는 fixture 기반 참고 정보이며 청약 당첨, 정책 수급, 대출 승인을 보장하지 않습니다.
          실제 신청 전 공식 공고문에서 소득·자산·무주택·접수 일정을 확인해야 합니다.
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
    </template>
  </div>
</template>
