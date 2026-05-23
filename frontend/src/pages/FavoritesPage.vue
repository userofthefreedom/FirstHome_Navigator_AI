<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Bookmark, ExternalLink, Trash2, WalletCards } from 'lucide-vue-next'
import { fetchFavorites, removeFavorite } from '../api/firsthome'
import type { Favorite } from '../types/firsthome'
import { formatMoney } from '../utils/format'

const favorites = ref<Favorite[]>([])
const loading = ref(true)
const error = ref('')
const removingKey = ref('')

const noticeFavorites = computed(() => favorites.value.filter((favorite) => favorite.favorite_type === 'notice'))
const optionFavorites = computed(() => favorites.value.filter((favorite) => favorite.favorite_type === 'option'))
const productFavorites = computed(() => favorites.value.filter((favorite) => favorite.favorite_type === 'product'))
const policyFavorites = computed(() => favorites.value.filter((favorite) => favorite.favorite_type === 'policy'))

function favoriteKey(favorite: Favorite) {
  return `${favorite.favorite_type}-${favorite.object_id}`
}

function typeLabel(type: Favorite['favorite_type']) {
  if (type === 'notice') return '공고'
  if (type === 'option') return '주택형'
  if (type === 'product') return '상품'
  return '정책'
}

function itemName(favorite: Favorite) {
  return String(favorite.item?.title ?? favorite.item?.name ?? '저장 항목')
}

function itemMeta(favorite: Favorite) {
  if (favorite.favorite_type === 'notice') {
    return `${favorite.item?.provider ?? ''} · ${favorite.item?.region ?? ''} · ${favorite.item?.supply_type ?? ''}`
  }
  if (favorite.favorite_type === 'option') {
    return `${favorite.item?.unit_type ?? ''} · ${favorite.item?.floor_group ?? '전체'} · ${favorite.item?.exclusive_area_m2 ?? ''}㎡`
  }
  if (favorite.favorite_type === 'product') {
    return `${favorite.item?.provider ?? ''} · ${favorite.item?.category ?? ''} · ${favorite.item?.rate ?? ''}`
  }
  return `${favorite.item?.provider ?? ''} · ${favorite.item?.policy_category ?? favorite.item?.target ?? ''}`
}

function itemDescription(favorite: Favorite) {
  if (favorite.favorite_type === 'notice') {
    return `예상 분양가 ${formatMoney(Number(favorite.item?.price ?? 0))}, 접수 마감 ${favorite.item?.application_deadline ?? '확인 필요'}`
  }
  if (favorite.favorite_type === 'option') {
    return `분양가 ${formatMoney(Number(favorite.item?.base_price ?? 0))}, 계약금 ${formatMoney(downPayment(favorite))}`
  }
  if (favorite.favorite_type === 'product') {
    return String(favorite.item?.reasons?.[0] ?? favorite.item?.period ?? '저축 목표와 월 납입 여력을 기준으로 저장한 상품입니다.')
  }
  return String(favorite.item?.benefit ?? favorite.item?.reasons?.[0] ?? '나이, 소득, 지역 조건을 기준으로 저장한 정책입니다.')
}

function downPayment(favorite: Favorite) {
  const schedules = favorite.item?.payment_schedules ?? []
  const row = Array.isArray(schedules) ? schedules.find((item) => item.payment_type === 'down_payment') : null
  return Number(row?.amount ?? 0)
}

function sourceUrl(favorite: Favorite) {
  return String(favorite.item?.source_url ?? '')
}

async function loadFavorites() {
  loading.value = true
  error.value = ''
  try {
    favorites.value = await fetchFavorites()
  } catch {
    error.value = '관심 목록 API에 연결하지 못했습니다. Django 서버가 실행 중인지 확인하세요.'
  } finally {
    loading.value = false
  }
}

async function handleRemove(favorite: Favorite) {
  removingKey.value = favoriteKey(favorite)
  try {
    await removeFavorite({ favorite_type: favorite.favorite_type, object_id: favorite.object_id })
    favorites.value = favorites.value.filter((item) => favoriteKey(item) !== favoriteKey(favorite))
  } finally {
    removingKey.value = ''
  }
}

onMounted(loadFavorites)
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="inline-flex items-center gap-2 text-sm font-semibold text-blue-700">
          <Bookmark class="h-4 w-4" />
          관심 목록
        </p>
        <h1 class="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">저장한 공고와 자금 후보</h1>
        <p class="mt-2 text-sm text-slate-500">공고, 주택형 옵션, 금융상품, 정책을 한곳에서 다시 확인합니다.</p>
      </div>
      <RouterLink to="/recommendations" class="inline-flex h-10 items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-bold text-white">
        추천 보러 가기
      </RouterLink>
    </div>

    <section v-if="loading" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      관심 목록을 불러오는 중입니다.
    </section>

    <section v-else-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-semibold text-amber-800">
      {{ error }}
    </section>

    <section v-else-if="favorites.length === 0" class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <p class="font-bold text-slate-950">아직 저장한 항목이 없습니다.</p>
      <p class="mt-2 text-sm text-slate-500">추천, 공고 상세, 자금 로드맵 화면에서 관심 항목을 저장할 수 있습니다.</p>
    </section>

    <template v-else>
      <section class="grid gap-3 md:grid-cols-4">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm font-semibold text-slate-500">저장 공고</p>
          <p class="mt-2 text-2xl font-bold text-slate-950">{{ noticeFavorites.length }}건</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm font-semibold text-slate-500">저장 주택형</p>
          <p class="mt-2 text-2xl font-bold text-slate-950">{{ optionFavorites.length }}건</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm font-semibold text-slate-500">저장 상품</p>
          <p class="mt-2 text-2xl font-bold text-slate-950">{{ productFavorites.length }}건</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm font-semibold text-slate-500">저장 정책</p>
          <p class="mt-2 text-2xl font-bold text-slate-950">{{ policyFavorites.length }}건</p>
        </div>
      </section>

      <section class="grid gap-4 lg:grid-cols-2">
        <article v-for="favorite in favorites" :key="favoriteKey(favorite)" class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <div class="flex flex-wrap items-center gap-2">
                <span class="rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">
                  {{ typeLabel(favorite.favorite_type) }}
                </span>
                <span v-if="favorite.item?.data_source" class="rounded-md bg-emerald-50 px-2 py-1 text-xs font-bold text-emerald-700">{{ favorite.item.data_source }}</span>
                <span class="text-xs font-semibold text-slate-500">{{ itemMeta(favorite) }}</span>
              </div>
              <h2 class="mt-3 text-lg font-bold text-slate-950">{{ itemName(favorite) }}</h2>
              <p class="mt-2 text-sm leading-6 text-slate-600">{{ itemDescription(favorite) }}</p>
            </div>
            <button
              type="button"
              class="inline-flex h-9 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700"
              :disabled="removingKey === favoriteKey(favorite)"
              @click="handleRemove(favorite)"
            >
              <Trash2 class="h-4 w-4" />
              해제
            </button>
          </div>

          <div class="mt-4 flex flex-wrap gap-2">
            <RouterLink
              v-if="favorite.favorite_type === 'notice'"
              :to="`/notices/${favorite.object_id}`"
              class="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white"
            >
              공고 상세
            </RouterLink>
            <RouterLink
              v-if="favorite.favorite_type === 'notice'"
              :to="`/funding/${favorite.object_id}`"
              class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700"
            >
              <WalletCards class="h-4 w-4" />
              자금 로드맵
            </RouterLink>
            <RouterLink
              v-if="favorite.favorite_type === 'option' && favorite.item?.notice_id"
              :to="{ path: `/funding/${favorite.item.notice_id}`, query: { option_id: favorite.object_id } }"
              class="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white"
            >
              <WalletCards class="h-4 w-4" />
              옵션 자금 보기
            </RouterLink>
            <a
              v-if="sourceUrl(favorite)"
              :href="sourceUrl(favorite)"
              target="_blank"
              rel="noreferrer"
              class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700"
            >
              공식 출처
              <ExternalLink class="h-4 w-4" />
            </a>
          </div>
        </article>
      </section>
    </template>
  </div>
</template>
