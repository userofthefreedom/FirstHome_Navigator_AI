<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Bookmark, Bot, CheckCircle2, ClipboardCheck, ExternalLink, ShieldAlert, WalletCards } from 'lucide-vue-next'
import { addFavorite, fetchCoachSummary, fetchFavorites, fetchFundingPlan, fetchHousingRecommendations, fetchNotice, removeFavorite } from '../api/firsthome'
import type { CoachSummary, Favorite, FundingPlan, Notice } from '../types/firsthome'
import { formatMoney } from '../utils/format'
import { useProfileStore } from '../stores/profileStore'

const route = useRoute()
const profileStore = useProfileStore()
const noticeId = computed(() => Number(route.params.noticeId ?? 0))
const selectedNotice = ref<Notice | null>(null)
const fundingPlan = ref<FundingPlan | null>(null)
const aiCoach = ref<CoachSummary | null>(null)
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

async function resolveNoticeId() {
  if (noticeId.value) return noticeId.value
  const recommendations = await fetchHousingRecommendations()
  return recommendations[0]?.notice_id ?? 101
}

async function loadCoach() {
  loading.value = true
  error.value = ''
  try {
    const targetNoticeId = await resolveNoticeId()
    if (!profileStore.loaded) {
      await profileStore.hydrateProfile()
    }
    const [noticeResponse, fundingResponse, coachResponse, favoriteResponse] = await Promise.all([
      fetchNotice(targetNoticeId),
      fetchFundingPlan(targetNoticeId),
      fetchCoachSummary(targetNoticeId, profileStore.profile),
      fetchFavorites(),
    ])
    selectedNotice.value = noticeResponse
    fundingPlan.value = fundingResponse
    aiCoach.value = coachResponse
    favorites.value = favoriteResponse
  } catch {
    error.value = '백엔드 AI 코치 API에 연결하지 못했습니다. Django 서버가 실행 중인지 확인하세요.'
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

watch(noticeId, loadCoach)
onMounted(loadCoach)
</script>

<template>
  <div class="space-y-5">
    <section v-if="loading" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      AI 코치 문장을 불러오는 중입니다.
    </section>

    <section v-else-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-semibold text-amber-800">
      {{ error }}
    </section>

    <template v-else-if="selectedNotice && fundingPlan && aiCoach">
      <section class="rounded-lg border border-slate-200 bg-slate-950 p-5 text-white shadow-sm sm:p-6">
        <p class="inline-flex items-center gap-2 text-sm font-semibold text-blue-200">
          <Bot class="h-4 w-4" />
          AI 주택형 자금 코치
        </p>
        <div class="mt-4 flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <h1 class="text-2xl font-bold">{{ selectedNotice.title }}</h1>
            <p class="mt-2 text-sm text-slate-300">{{ aiCoach.summary }}</p>
            <p class="mt-3 text-xs font-semibold text-blue-200">source: {{ aiCoach.source }}</p>
          </div>
          <div class="grid gap-2 sm:min-w-48">
            <div class="rounded-lg bg-white/10 px-5 py-4 text-center">
              <p class="flex items-center justify-center gap-2 text-xs text-blue-200">
                <WalletCards class="h-4 w-4" />
                부족 계약금
              </p>
              <p class="mt-1 text-2xl font-bold">{{ formatMoney(fundingPlan.shortfall) }}</p>
            </div>
            <button
              type="button"
              class="inline-flex items-center justify-center gap-2 rounded-lg bg-white px-4 py-2 text-sm font-bold text-slate-950"
              :disabled="savingFavorite"
              @click="toggleFavorite"
            >
              <Bookmark class="h-4 w-4" :class="isFavorite ? 'fill-blue-600 text-blue-600' : ''" />
              {{ isFavorite ? '공고 저장됨' : '공고 저장' }}
            </button>
          </div>
        </div>
      </section>

      <section class="grid gap-5 lg:grid-cols-2">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="flex items-center gap-2 text-lg font-bold text-slate-950">
            <ClipboardCheck class="h-5 w-5 text-blue-700" />
            이번 주 확인할 일
          </h2>
          <ol class="mt-5 space-y-3">
            <li v-for="(todo, index) in aiCoach.todo_this_week" :key="todo" class="flex gap-3 rounded-lg border border-slate-100 bg-slate-50 p-4">
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
            <div v-for="item in aiCoach.official_checklist" :key="item" class="rounded-lg border border-slate-100 bg-slate-50 p-4">
              <p class="font-bold text-slate-800">{{ item }}</p>
              <p class="mt-1 text-xs leading-5 text-slate-500">AI 답변과 별개로 공식 공고문에서 직접 확인해야 합니다.</p>
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
