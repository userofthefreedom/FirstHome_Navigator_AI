<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ArrowUpDown, Bookmark, CalendarDays, CheckCircle2, ChevronRight, Clock3, ExternalLink, MapPin, Sparkles } from 'lucide-vue-next'
import { addFavorite, fetchFavorites, fetchHousingRecommendations, removeFavorite } from '../api/firsthome'
import type { BestUnitOption, Favorite, HousingRecommendation } from '../types/firsthome'
import { analysisBadgeClass, analysisSummary } from '../utils/analysisStatus'
import { formatMoney } from '../utils/format'
import { useProfileStore } from '../stores/profileStore'

const profileStore = useProfileStore()
const recommendations = ref<HousingRecommendation[]>([])
const favorites = ref<Favorite[]>([])
const loading = ref(true)
const savingFavoriteKey = ref('')
const error = ref('')

function priceLabel(price: number) {
  return price > 0 ? formatMoney(price) : '공식 확인 필요'
}

function favoriteKey(noticeId: number) {
  return `notice-${noticeId}`
}

function isFavorite(noticeId: number) {
  return favorites.value.some((favorite) => favorite.favorite_type === 'notice' && favorite.object_id === noticeId)
}

function recommendationOptions(item: HousingRecommendation): BestUnitOption[] {
  if (item.top_options?.length) return item.top_options
  return item.best_option ? [item.best_option] : []
}

async function toggleFavorite(noticeId: number) {
  const favorite = { favorite_type: 'notice', object_id: noticeId } satisfies Favorite
  savingFavoriteKey.value = favoriteKey(noticeId)
  try {
    if (isFavorite(noticeId)) {
      await removeFavorite(favorite)
      favorites.value = favorites.value.filter((item) => item.favorite_type !== 'notice' || item.object_id !== noticeId)
    } else {
      const saved = await addFavorite(favorite)
      favorites.value = [...favorites.value, saved]
    }
  } finally {
    savingFavoriteKey.value = ''
  }
}

async function loadRecommendations() {
  loading.value = true
  error.value = ''
  try {
    const [recommendationResponse, favoriteResponse] = await Promise.all([
      fetchHousingRecommendations(),
      fetchFavorites(),
    ])
    recommendations.value = recommendationResponse
    favorites.value = favoriteResponse
    if (!profileStore.loaded) {
      await profileStore.hydrateProfile()
    }
  } catch {
    error.value = '백엔드 추천 API에 연결하지 못했습니다. Django 서버가 실행 중인지 확인하세요.'
  } finally {
    loading.value = false
  }
}

onMounted(loadRecommendations)
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="text-sm font-semibold text-blue-700">주택형 옵션 추천</p>
        <h1 class="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">검토할 후보 TOP 3</h1>
        <p class="mt-2 text-sm text-slate-500">소유형 공공분양만 대상으로 자격, 자금, 지역, 일정, 정책 연계를 합산하고 공고 안의 주택형 옵션 맞춤도를 함께 봅니다.</p>
      </div>
      <button class="inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 transition hover:bg-slate-50" type="button">
        <ArrowUpDown class="h-4 w-4" />
        점수순
      </button>
    </div>

    <section v-if="loading" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      추천 결과를 불러오는 중입니다.
    </section>

    <section v-else-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-semibold text-amber-800">
      {{ error }}
    </section>

    <section v-else-if="recommendations.length === 0" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      조건에 맞는 검토 후보가 없습니다. 희망 지역, 면적, 분양가 범위를 조금 넓혀 보세요.
    </section>

    <section v-else class="space-y-4">
      <div class="flex flex-col gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center sm:justify-between">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
            <Sparkles class="h-5 w-5" />
          </div>
          <div>
            <p class="font-bold text-slate-950">{{ recommendations.length }}개 공고에서 검토할 주택형을 찾았습니다</p>
            <p class="text-sm text-slate-500">{{ profileStore.profile.name || '현재 사용자' }}님의 자금, 희망 면적, 분양가 조건이 추천 점수에 반영됩니다.</p>
          </div>
        </div>
        <RouterLink to="/profile" class="rounded-lg border border-slate-200 px-4 py-2 text-sm font-bold text-slate-700">
          조건 수정
        </RouterLink>
      </div>

      <article v-for="(item, index) in recommendations" :key="item.notice_id" class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="grid gap-5 lg:grid-cols-[1fr_220px]">
          <div>
            <div class="flex flex-wrap items-center gap-2">
              <span class="rounded-md bg-slate-950 px-2 py-1 text-xs font-bold text-white">추천 {{ index + 1 }}</span>
              <span class="rounded-md bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">{{ item.supply_type }}</span>
              <span class="rounded-md bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-700">{{ item.data_source ?? 'fixture' }}</span>
              <span class="rounded-md bg-violet-50 px-2 py-1 text-xs font-semibold text-violet-700">옵션 맞춤 {{ item.option_fit_score ?? 0 }}점</span>
              <span class="rounded-md px-2 py-1 text-xs font-semibold" :class="analysisBadgeClass(analysisSummary(item.analysis_summary, item.official_document_status))">
                {{ analysisSummary(item.analysis_summary, item.official_document_status).label }}
              </span>
              <span v-if="!item.is_price_confirmed" class="rounded-md bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700">금액 확인 필요</span>
            </div>
            <h2 class="mt-3 text-xl font-bold text-slate-950">{{ item.title }}</h2>
            <p class="mt-2 flex items-center gap-1 text-sm text-slate-500">
              <MapPin class="h-4 w-4" />
              {{ item.provider }} · {{ item.region }} · {{ item.district }}
            </p>

            <div class="mt-5 grid gap-3 sm:grid-cols-5">
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">자격</p>
                <p class="mt-1 font-bold">{{ item.score_detail.eligibility }}/35</p>
              </div>
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">자금</p>
                <p class="mt-1 font-bold">{{ item.score_detail.funding }}/25</p>
              </div>
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">지역</p>
                <p class="mt-1 font-bold">{{ item.score_detail.location }}/15</p>
              </div>
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">일정</p>
                <p class="mt-1 font-bold">{{ item.score_detail.schedule }}/10</p>
              </div>
              <div class="rounded-lg border border-slate-100 bg-slate-50 p-3">
                <p class="text-xs text-slate-500">정책</p>
                <p class="mt-1 font-bold">{{ item.score_detail.policy_link }}/15</p>
              </div>
            </div>

            <div class="mt-5 space-y-2">
              <p class="text-sm font-semibold text-slate-700">검토 근거</p>
              <div v-for="reason in item.reasons" :key="reason" class="flex items-start gap-2 text-sm text-slate-600">
                <CheckCircle2 class="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                <span>{{ reason }}</span>
              </div>
            </div>
          </div>

          <div class="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div class="flex items-center justify-between">
              <p class="text-sm font-semibold text-slate-500">총점</p>
              <p class="text-2xl font-bold text-slate-950">{{ item.total_score }}점</p>
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
                <span class="font-bold text-slate-950">{{ item.application_deadline }}</span>
              </div>
              <div class="flex items-center justify-between gap-3">
                <span class="flex items-center gap-2 text-slate-500">
                  <Clock3 class="h-4 w-4" />
                  공식 확인
                </span>
                <span class="rounded-md px-2 py-1 text-xs font-bold" :class="analysisBadgeClass(analysisSummary(item.analysis_summary, item.official_document_status))">
                  {{ analysisSummary(item.analysis_summary, item.official_document_status).label }}
                </span>
              </div>
            </div>
            <p class="mt-3 rounded-lg bg-white p-3 text-xs leading-5 text-slate-600">
              {{ analysisSummary(item.analysis_summary, item.official_document_status).next_action }}
            </p>
            <p class="mt-5 text-sm text-slate-500">예상 분양가</p>
            <p class="mt-1 text-lg font-bold text-slate-950">{{ priceLabel(item.price) }}</p>
            <div v-if="item.top_options?.length" class="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-3">
              <p class="text-xs font-bold text-blue-700">우선 검토할 주택형 옵션</p>
              <div class="mt-2 space-y-2">
                <RouterLink
                  v-for="option in recommendationOptions(item)"
                  :key="option.option_id"
                  :to="{ path: `/funding/${item.notice_id}`, query: { option_id: option.option_id } }"
                  class="block rounded-lg bg-white p-3 text-sm transition hover:bg-blue-100"
                >
                  <div class="flex items-start justify-between gap-2">
                    <div>
                      <p class="font-bold text-slate-950">{{ option.unit_type }} · {{ option.floor_group || '기본' }}</p>
                      <p class="mt-1 text-xs text-slate-600">{{ option.exclusive_area_m2 }}㎡ · {{ priceLabel(option.base_price) }}</p>
                      <p v-if="option.fit_reasons?.length" class="mt-2 text-xs leading-5 text-slate-500">
                        {{ option.fit_reasons[0] }}
                      </p>
                    </div>
                    <span class="rounded-md bg-slate-950 px-2 py-1 text-xs font-bold text-white">
                      {{ option.option_fit_score }}점
                    </span>
                  </div>
                </RouterLink>
              </div>
            </div>
            <div v-if="item.best_option && !item.top_options?.length" class="mt-4 rounded-lg border border-blue-100 bg-blue-50 p-3">
              <p class="text-xs font-bold text-blue-700">우선 검토할 주택형</p>
              <p class="mt-1 font-bold text-slate-950">
                {{ item.best_option.unit_type }} · {{ item.best_option.floor_group }}
              </p>
              <p class="mt-1 text-sm text-slate-600">
                {{ item.best_option.exclusive_area_m2 }}㎡ · {{ priceLabel(item.best_option.base_price) }}
              </p>
              <p v-if="item.best_option.fit_reasons?.length" class="mt-2 text-xs leading-5 text-slate-500">
                {{ item.best_option.fit_reasons[0] }}
              </p>
              <RouterLink
                :to="{ path: `/funding/${item.notice_id}`, query: { option_id: item.best_option.option_id } }"
                class="mt-3 inline-flex h-9 w-full items-center justify-center rounded-lg bg-slate-950 text-sm font-bold text-white"
              >
                이 옵션 자금 보기
              </RouterLink>
            </div>
            <RouterLink
              :to="`/notices/${item.notice_id}`"
              class="mt-5 inline-flex h-10 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 text-sm font-bold text-white transition hover:bg-blue-700"
            >
              공식 근거 보기
              <ChevronRight class="h-4 w-4" />
            </RouterLink>
            <button
              type="button"
              class="mt-2 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
              :disabled="savingFavoriteKey === favoriteKey(item.notice_id)"
              @click="toggleFavorite(item.notice_id)"
            >
              <Bookmark class="h-4 w-4" :class="isFavorite(item.notice_id) ? 'fill-blue-600 text-blue-600' : ''" />
              {{ isFavorite(item.notice_id) ? '공고 저장됨' : '공고 저장' }}
            </button>
            <a
              v-if="item.source_url"
              :href="item.source_url"
              target="_blank"
              rel="noreferrer"
              class="mt-2 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white text-sm font-bold text-slate-700 transition hover:bg-slate-50"
            >
              공식 출처
              <ExternalLink class="h-4 w-4" />
            </a>
          </div>
        </div>
      </article>

      <div class="rounded-lg border border-amber-100 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
        추천 결과는 공식 공고문 분석과 입력 조건 기반의 참고 정보이며 청약 당첨, 정책 수급, 대출 승인을 보장하지 않습니다. 실제 신청 전 공식 공고문을 확인하세요.
      </div>
    </section>
  </div>
</template>
