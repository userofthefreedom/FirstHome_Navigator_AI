<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { fetchAuthSession, fetchFavorites, fetchJoinedProducts, fetchProfile } from '../api/firsthome';
import { formatMoney } from '../utils/format';

const session = ref(null);
const profile = ref(null);
const favorites = ref([]);
const joined = ref([]);
const loading = ref(true);

const isLoggedIn = computed(() => Boolean(session.value?.user?.is_authenticated));
const chartProduct = computed(() => joined.value[0]?.product ?? null);
const chartOptions = computed(() => {
  const options = chartProduct.value?.options ?? [];
  if (options.length)
    return [...options].sort((a, b) => Number(a.save_trm || 0) - Number(b.save_trm || 0));
  const selected = joined.value[0]?.selected_option;
  return selected ? [selected] : [];
});
const chartPoints = computed(() => {
  const options = chartOptions.value;
  if (!options.length)
    return '';
  const values = options.map((item) => Number(item.intr_rate2 || item.intr_rate || 0));
  const max = Math.max(...values, 1);
  return options.map((option, index) => {
    const x = options.length === 1 ? 50 : (index / (options.length - 1)) * 100;
    const y = 92 - (Number(option.intr_rate2 || option.intr_rate || 0) / max) * 78;
    return `${x},${y}`;
  }).join(' ');
});
const chartSinglePoint = computed(() => {
  const [x, y] = chartPoints.value.split(',').map(Number);
  return Number.isFinite(x) && Number.isFinite(y) ? { x, y } : null;
});
const noticeFavorites = computed(() => favorites.value.filter((favorite) => favorite.favorite_type === 'notice'));
const optionFavorites = computed(() => favorites.value.filter((favorite) => favorite.favorite_type === 'option'));
const otherFavorites = computed(() => favorites.value.filter((favorite) => !['notice', 'option'].includes(favorite.favorite_type)));

async function load() {
  loading.value = true;
  session.value = await fetchAuthSession();
  if (isLoggedIn.value) {
    const [profileResponse, favoriteResponse, joinedResponse] = await Promise.all([
      fetchProfile(),
      fetchFavorites(),
      fetchJoinedProducts().catch(() => []),
    ]);
    profile.value = profileResponse;
    favorites.value = favoriteResponse;
    joined.value = joinedResponse;
  }
  loading.value = false;
}

function favoriteTitle(favorite) {
  return favorite.item?.title || favorite.item?.name || `#${favorite.object_id}`;
}

onMounted(load);
</script>

<template>
  <div class="space-y-5">
    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <p class="text-sm font-bold text-blue-700">계정</p>
      <h1 class="mt-1 text-3xl font-black text-slate-950">MY PAGE</h1>
      <p class="mt-2 text-sm text-slate-500">가입 금융상품, 관심 공고, 관심 주택형 옵션을 분리해서 확인합니다.</p>
    </section>

    <section v-if="loading" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-bold text-slate-500">MY PAGE를 불러오는 중입니다.</section>
    <section v-else-if="!isLoggedIn" class="rounded-lg border border-slate-200 bg-white p-8 text-center shadow-sm">
      <h2 class="text-2xl font-black text-slate-950">MY PAGE는 로그인 후 이용할 수 있습니다.</h2>
      <p class="mt-2 text-sm text-slate-500">가입 금융상품, 관심목록, 프로필 조건을 한 곳에서 확인하세요.</p>
      <RouterLink to="/auth" class="mt-5 inline-flex rounded-lg bg-blue-600 px-5 py-3 text-sm font-black text-white">로그인 / 회원가입</RouterLink>
    </section>

    <template v-else>
      <section class="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.65fr)]">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <h2 class="text-lg font-black text-slate-950">내 프로필</h2>
            <div class="flex flex-wrap gap-2">
              <span class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-bold text-slate-500">관심 공고 {{ noticeFavorites.length }}</span>
              <span class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-bold text-slate-500">관심 옵션 {{ optionFavorites.length }}</span>
              <span class="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs font-bold text-slate-500">가입상품 {{ joined.length }}</span>
            </div>
          </div>
          <div class="mt-4 grid gap-2 sm:grid-cols-2">
            <div class="rounded-lg bg-slate-50 p-3"><p class="text-xs font-bold text-slate-500">아이디</p><p class="font-black">{{ session.user.username }}</p></div>
            <div class="rounded-lg bg-slate-50 p-3"><p class="text-xs font-bold text-slate-500">이름</p><p class="font-black">{{ profile?.name || '-' }}</p></div>
            <div class="rounded-lg bg-slate-50 p-3"><p class="text-xs font-bold text-slate-500">연소득</p><p class="font-black">{{ formatMoney(profile?.annual_income || 0) }}</p></div>
            <div class="rounded-lg bg-slate-50 p-3"><p class="text-xs font-bold text-slate-500">보유 현금</p><p class="font-black">{{ formatMoney(profile?.asset || 0) }}</p></div>
            <div class="rounded-lg bg-slate-50 p-3"><p class="text-xs font-bold text-slate-500">부채</p><p class="font-black">{{ formatMoney(profile?.debt || 0) }}</p></div>
            <div class="rounded-lg bg-slate-50 p-3"><p class="text-xs font-bold text-slate-500">희망 지역</p><p class="font-black">{{ profile?.preferred_regions?.join(', ') || '-' }}</p></div>
          </div>
        </div>

        <aside class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-black text-slate-950">저장 요약</h2>
          <div class="mt-4 space-y-2">
            <div class="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3">
              <span class="text-sm font-bold text-slate-500">관심 공고</span>
              <span class="text-lg font-black text-slate-950">{{ noticeFavorites.length }}</span>
            </div>
            <div class="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3">
              <span class="text-sm font-bold text-slate-500">관심 옵션</span>
              <span class="text-lg font-black text-slate-950">{{ optionFavorites.length }}</span>
            </div>
            <div class="flex items-center justify-between rounded-lg bg-slate-50 px-4 py-3">
              <span class="text-sm font-bold text-slate-500">가입 금융상품</span>
              <span class="text-lg font-black text-slate-950">{{ joined.length }}</span>
            </div>
          </div>
        </aside>
      </section>

      <section class="grid gap-5 xl:grid-cols-[1fr_1fr]">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-black text-slate-950">가입 금융상품</h2>
          <div class="mt-4 space-y-3">
            <RouterLink v-for="item in joined" :key="item.id" :to="`/finance/products/${item.product.id}`" class="block rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p class="font-black text-slate-950">{{ item.product.name }}</p>
              <p class="mt-1 text-sm font-bold text-slate-500">{{ item.product.provider }} · {{ item.product.rate }}</p>
              <p v-if="item.memo" class="mt-2 text-sm text-slate-600">{{ item.memo }}</p>
            </RouterLink>
            <p v-if="!joined.length" class="rounded-lg bg-slate-50 p-4 text-sm font-bold text-slate-500">가입 후보로 저장한 상품이 없습니다.</p>
          </div>
        </div>

        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-black text-slate-950">가입 상품 금리 그래프</h2>
          <p class="mt-1 text-sm text-slate-500">{{ chartProduct?.name || '상품을 저장하면 기간별 금리를 표시합니다.' }}</p>
          <div class="mt-4 aspect-[16/8] rounded-lg bg-slate-950 p-5">
            <svg viewBox="0 0 100 100" preserveAspectRatio="none" class="h-full w-full">
              <line x1="0" y1="92" x2="100" y2="92" stroke="#334155" stroke-width="0.8" vector-effect="non-scaling-stroke" />
              <polyline v-if="chartPoints && chartOptions.length > 1" :points="chartPoints" fill="none" stroke="#60a5fa" stroke-width="2.5" vector-effect="non-scaling-stroke" />
              <circle v-if="chartSinglePoint && chartOptions.length === 1" :cx="chartSinglePoint.x" :cy="chartSinglePoint.y" r="2.5" fill="#60a5fa" vector-effect="non-scaling-stroke" />
            </svg>
          </div>
          <div v-if="chartOptions.length" class="mt-3 grid gap-2 text-xs font-bold text-slate-500 sm:grid-cols-3">
            <span v-for="option in chartOptions.slice(0, 3)" :key="option.id" class="rounded-md bg-slate-50 px-3 py-2">
              {{ option.save_trm || '-' }}개월 · 최고 {{ Number(option.intr_rate2 || option.intr_rate || 0).toFixed(2) }}%
            </span>
          </div>
          <p v-else class="mt-3 rounded-lg bg-slate-50 p-3 text-sm font-bold text-slate-500">금리 옵션 데이터가 있는 상품을 저장하면 그래프가 표시됩니다.</p>
        </div>
      </section>

      <section class="grid gap-5 xl:grid-cols-2">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-black text-slate-950">관심 공고</h2>
          <div class="mt-4 grid gap-3 md:grid-cols-2">
            <div v-for="favorite in noticeFavorites" :key="favorite.id" class="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p class="text-xs font-black text-blue-700">공고</p>
              <p class="mt-1 line-clamp-2 font-black text-slate-950">{{ favoriteTitle(favorite) }}</p>
            </div>
          </div>
          <p v-if="!noticeFavorites.length" class="mt-4 rounded-lg bg-slate-50 p-4 text-sm font-bold text-slate-500">저장한 관심 공고가 없습니다.</p>
        </div>

        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-black text-slate-950">관심 옵션</h2>
          <div class="mt-4 grid gap-3 md:grid-cols-2">
            <div v-for="favorite in optionFavorites" :key="favorite.id" class="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <p class="text-xs font-black text-blue-700">옵션</p>
              <p class="mt-1 line-clamp-2 font-black text-slate-950">{{ favoriteTitle(favorite) }}</p>
            </div>
          </div>
          <p v-if="!optionFavorites.length" class="mt-4 rounded-lg bg-slate-50 p-4 text-sm font-bold text-slate-500">저장한 관심 옵션이 없습니다.</p>
        </div>
      </section>

      <section v-if="otherFavorites.length" class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-lg font-black text-slate-950">기타 저장 항목</h2>
        <div class="mt-4 grid gap-3 lg:grid-cols-3">
          <div v-for="favorite in otherFavorites" :key="favorite.id" class="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p class="text-xs font-black text-blue-700">{{ favorite.favorite_type }}</p>
            <p class="mt-1 line-clamp-2 font-black text-slate-950">{{ favoriteTitle(favorite) }}</p>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
