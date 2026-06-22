<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { deleteJoinedProduct, fetchAuthSession, fetchFavorites, fetchJoinedProducts, fetchProfile } from '../api/firsthome';
import { formatMoney } from '../utils/format';

const session = ref(null);
const profile = ref(null);
const favorites = ref([]);
const joined = ref([]);
const loading = ref(true);
const joinedPage = ref(1);
const removingJoinedId = ref(null);
const joinedPageSize = 4;

const isLoggedIn = computed(() => Boolean(session.value?.user?.is_authenticated));
const compactJoined = computed(() => joined.value.length >= 4);
const joinedPageCount = computed(() => Math.max(1, Math.ceil(joined.value.length / joinedPageSize)));
const visibleJoined = computed(() => {
  if (!compactJoined.value)
    return joined.value;
  const start = (joinedPage.value - 1) * joinedPageSize;
  return joined.value.slice(start, start + joinedPageSize);
});
const chartItems = computed(() => {
  return joined.value
    .map((item) => {
      const selectedRate = Number(item.selected_option?.intr_rate2 || item.selected_option?.intr_rate || 0);
      const bestOptionRate = Number(item.product?.best_option?.intr_rate2 || item.product?.best_option?.intr_rate || 0);
      const textRate = parseRate(item.product?.rate);
      const rate = selectedRate || bestOptionRate || textRate;
      return {
        id: item.id,
        label: item.product?.name ?? '가입 상품',
        provider: item.product?.provider ?? '',
        rate,
      };
    })
    .filter((item) => item.rate > 0);
});
const chartMaxRate = computed(() => {
  const max = Math.max(0, ...chartItems.value.map((item) => item.rate));
  if (!max)
    return 1;
  return Math.ceil(max * 1.15 * 10) / 10;
});
const chartTicks = computed(() => [chartMaxRate.value, chartMaxRate.value / 2, 0].map((rate) => ({
  rate,
  label: `${rate.toFixed(rate >= 10 ? 0 : 2)}%`,
})));
const chartBars = computed(() => chartItems.value.map((item, index) => ({
  ...item,
  index: index + 1,
  height: Math.max(8, (item.rate / chartMaxRate.value) * 100),
})));
const chartSummary = computed(() => {
  if (!chartItems.value.length)
    return '금리 정보가 있는 가입 상품을 저장하면 비교 그래프가 표시됩니다.';
  if (chartItems.value.length === 1)
    return `${chartItems.value[0].label} 대표 금리`;
  return `가입 상품 ${chartItems.value.length}개의 대표 금리 비교`;
});

function parseRate(value) {
  const match = String(value || '').match(/\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : 0;
}

function shortProductName(value) {
  const text = String(value || '');
  return text.length > 13 ? `${text.slice(0, 13)}...` : text;
}

function visibleMemo(item) {
  const memo = String(item.memo || '').trim();
  return memo && memo !== '계약금 마련 후보' ? memo : '';
}

function setJoinedPage(page) {
  joinedPage.value = Math.min(Math.max(1, page), joinedPageCount.value);
}

async function removeJoinedProduct(item) {
  if (!item?.id || removingJoinedId.value)
    return;
  removingJoinedId.value = item.id;
  try {
    await deleteJoinedProduct(item.id);
    joined.value = joined.value.filter((candidate) => candidate.id !== item.id);
    setJoinedPage(joinedPage.value);
  }
  finally {
    removingJoinedId.value = null;
  }
}

function barStyle(item) {
  return { height: `${item.height}%` };
}
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

      <section class="grid items-start gap-5 xl:grid-cols-[1fr_1fr]">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex items-center justify-between gap-3">
            <h2 class="text-lg font-black text-slate-950">가입 금융상품</h2>
            <span v-if="joined.length" class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-black text-slate-500">{{ joined.length }}개</span>
          </div>
          <div v-if="compactJoined" class="mt-4 overflow-hidden rounded-lg border border-slate-200">
            <div v-for="item in visibleJoined" :key="item.id" class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3 last:border-b-0">
              <RouterLink :to="`/finance/products/${item.product.id}`" class="min-w-0">
                <p class="truncate font-black text-slate-950">{{ item.product.name }}</p>
                <p class="mt-1 truncate text-xs font-bold text-slate-500">{{ item.product.provider }} · {{ item.product.rate }}</p>
                <p v-if="visibleMemo(item)" class="mt-1 truncate text-xs font-bold text-slate-500">{{ visibleMemo(item) }}</p>
              </RouterLink>
              <button
                type="button"
                class="rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-black text-slate-500 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                :disabled="removingJoinedId === item.id"
                @click="removeJoinedProduct(item)"
              >
                해제
              </button>
            </div>
          </div>
          <div v-else class="mt-4 space-y-3">
            <article v-for="item in visibleJoined" :key="item.id" class="rounded-lg border border-slate-200 bg-slate-50 p-4">
              <div class="flex items-start justify-between gap-3">
                <RouterLink :to="`/finance/products/${item.product.id}`" class="min-w-0 flex-1">
                  <p class="line-clamp-2 font-black text-slate-950">{{ item.product.name }}</p>
                  <p class="mt-1 text-sm font-bold text-slate-500">{{ item.product.provider }} · {{ item.product.rate }}</p>
                  <p v-if="visibleMemo(item)" class="mt-2 text-sm text-slate-600">{{ visibleMemo(item) }}</p>
                </RouterLink>
                <button
                  type="button"
                  class="shrink-0 rounded-md border border-slate-200 bg-white px-3 py-2 text-xs font-black text-slate-500 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                  :disabled="removingJoinedId === item.id"
                  @click="removeJoinedProduct(item)"
                >
                  해제
                </button>
              </div>
            </article>
            <p v-if="!joined.length" class="rounded-lg bg-slate-50 p-4 text-sm font-bold text-slate-500">가입 후보로 저장한 상품이 없습니다.</p>
          </div>
          <div v-if="compactJoined && joinedPageCount > 1" class="mt-4 flex items-center justify-center gap-1.5">
            <button
              type="button"
              class="rounded-md px-2.5 py-1.5 text-xs font-black text-slate-500 transition hover:bg-slate-100 disabled:opacity-30"
              :disabled="joinedPage === 1"
              @click="setJoinedPage(joinedPage - 1)"
            >
              이전
            </button>
            <button
              v-for="page in joinedPageCount"
              :key="page"
              type="button"
              class="h-8 min-w-8 rounded-md px-2 text-sm font-black transition"
              :class="page === joinedPage ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'"
              @click="setJoinedPage(page)"
            >
              {{ page }}
            </button>
            <button
              type="button"
              class="rounded-md px-2.5 py-1.5 text-xs font-black text-slate-500 transition hover:bg-slate-100 disabled:opacity-30"
              :disabled="joinedPage === joinedPageCount"
              @click="setJoinedPage(joinedPage + 1)"
            >
              다음
            </button>
          </div>
        </div>

        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-black text-slate-950">가입 상품 금리 그래프</h2>
          <p class="mt-1 text-sm text-slate-500">{{ chartSummary }}</p>
          <div class="mt-4 rounded-lg bg-slate-950 p-5">
            <div v-if="chartBars.length" class="grid h-72 grid-cols-[58px_minmax(0,1fr)] gap-3">
              <div class="flex flex-col justify-between pb-7 pt-2 text-right text-xs font-black text-sky-100/80">
                <span v-for="tick in chartTicks" :key="tick.label">{{ tick.label }}</span>
              </div>
              <div class="relative min-w-0 border-b border-slate-700">
                <div class="pointer-events-none absolute inset-x-0 top-2 border-t border-dashed border-slate-800"></div>
                <div class="pointer-events-none absolute inset-x-0 top-1/2 border-t border-dashed border-slate-800"></div>
                <div class="flex h-full items-end gap-3 overflow-x-auto pb-7 pt-5">
                  <div v-for="item in chartBars" :key="item.id" class="flex h-full min-w-12 flex-1 flex-col justify-end">
                    <p class="mb-2 text-center text-[11px] font-black text-sky-100">{{ item.rate.toFixed(2) }}%</p>
                    <div class="mx-auto w-8 rounded-t-md bg-gradient-to-t from-blue-600 to-sky-300 shadow-[0_0_18px_rgba(96,165,250,0.25)]" :style="barStyle(item)"></div>
                    <p class="mt-2 text-center text-xs font-black text-slate-400">{{ item.index }}</p>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="flex h-72 items-center justify-center rounded-lg border border-slate-800 text-sm font-bold text-slate-500">
              금리 정보가 있는 상품을 저장하면 그래프가 표시됩니다.
            </div>
          </div>
          <div v-if="chartBars.length" class="mt-3 grid max-h-24 gap-2 overflow-y-auto text-xs font-bold text-slate-500 sm:grid-cols-2">
            <span v-for="item in chartBars" :key="item.id" class="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 rounded-md bg-slate-50 px-3 py-2">
              <b class="text-blue-700">{{ item.index }}</b>
              <span class="truncate">{{ shortProductName(item.label) }}</span>
              <b class="text-slate-700">{{ item.rate.toFixed(2) }}%</b>
            </span>
          </div>
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
