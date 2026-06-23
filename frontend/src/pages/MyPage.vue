<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { Bookmark, Building2, CalendarDays, Home, ReceiptText, Ruler, WalletCards, X } from 'lucide-vue-next';
import { deleteJoinedProduct, fetchAuthSession, fetchFavorites, fetchJoinedProducts, fetchProfile, removeFavorite } from '../api/firsthome';
import { formatMoney } from '../utils/format';

const session = ref(null);
const profile = ref(null);
const favorites = ref([]);
const joined = ref([]);
const loading = ref(true);
const joinedPage = ref(1);
const removingJoinedId = ref(null);
const removingFavoriteKey = ref('');
const joinedPageSize = 5;

const isLoggedIn = computed(() => Boolean(session.value?.user?.is_authenticated));
const joinedPageCount = computed(() => Math.max(1, Math.ceil(joined.value.length / joinedPageSize)));
const visibleJoined = computed(() => {
  const start = (joinedPage.value - 1) * joinedPageSize;
  return joined.value.slice(start, start + joinedPageSize);
});
const joinedListCentered = computed(() => joined.value.length > 0 && joined.value.length <= joinedPageSize);
const chartItems = computed(() => {
  return joined.value
    .map((item) => {
      const productOptions = Array.isArray(item.product?.options) ? item.product.options : [];
      const selectedOption = item.selected_option || item.product?.best_option || productOptions[0] || null;
      const selectedRate = optionRate(selectedOption);
      const textRate = parseRate(item.product?.rate);
      const rate = selectedRate || textRate;
      let optionBars = productOptions
        .map((option) => ({
          id: option.id ?? `${item.id}-${option.save_trm}`,
          term: Number(option.save_trm || 0),
          rate: optionRate(option),
          selected: selectedOption ? option.id === selectedOption.id : false,
        }))
        .filter((option) => option.rate > 0);
      const hasSelectedBar = optionBars.some((option) => option.selected);
      if (!hasSelectedBar && rate > 0) {
        optionBars.push({
          id: `${item.id}-selected`,
          term: Number(selectedOption?.save_trm || productTerm(item) || 0),
          rate,
          selected: true,
        });
      }
      optionBars = optionBars.sort((a, b) => a.term - b.term || a.rate - b.rate);
      return {
        id: item.id,
        label: item.product?.name ?? '가입 상품',
        provider: item.product?.provider ?? '',
        term: Number(selectedOption?.save_trm || productTerm(item) || 0),
        rate,
        optionBars,
      };
    })
    .filter((item) => item.rate > 0);
});
const chartMaxRate = computed(() => {
  const rates = chartItems.value.flatMap((item) => [item.rate, ...item.optionBars.map((option) => option.rate)]);
  const max = Math.max(0, ...rates);
  if (!max)
    return 1;
  if (max < 5)
    return Math.min(5, Math.ceil((max + 0.2) * 10) / 10);
  return Math.ceil(max * 1.12 * 10) / 10;
});
const chartTicks = computed(() => [chartMaxRate.value, chartMaxRate.value / 2, 0].map((rate) => ({
  rate,
  label: `${rate.toFixed(rate >= 10 ? 0 : 2)}%`,
})));
const chartBars = computed(() => {
  const bars = chartItems.value.map((item, index) => ({
    ...item,
    index: index + 1,
    height: Math.max(8, (item.rate / chartMaxRate.value) * 100),
    selectedOption: item.optionBars.find((option) => option.selected) || item.optionBars[0],
    selectedMarker: selectedMarkerMetrics(item.optionBars),
  }));

  return bars.map((item, index) => ({
    ...item,
    badgeLane: shouldStaggerBadge(item, bars[index - 1]) ? 1 : 0,
  }));
});
const chartNeedsScroll = computed(() => chartBars.value.length > 8);
const chartTrackStyle = computed(() => ({
  minWidth: chartNeedsScroll.value ? `${chartBars.value.length * 86}px` : '100%',
  width: chartNeedsScroll.value ? 'max-content' : '100%',
}));
const chartSummary = computed(() => {
  if (!chartItems.value.length)
    return '금리 정보가 있는 가입 상품을 저장하면 비교 그래프가 표시됩니다.';
  if (chartItems.value.length === 1)
    return `${chartItems.value[0].label} 금리`;
  return `가입 상품 ${chartItems.value.length}개의 금리 비교`;
});
const noticeFavorites = computed(() => favorites.value.filter((favorite) => favorite.favorite_type === 'notice'));
const optionFavorites = computed(() => favorites.value.filter((favorite) => favorite.favorite_type === 'option'));
const otherFavorites = computed(() => favorites.value.filter((favorite) => !['notice', 'option'].includes(favorite.favorite_type)));
const profileRows = computed(() => [
  { label: '아이디', value: session.value?.user?.username || '-' },
  { label: '이메일', value: session.value?.user?.email || '미등록' },
  { label: '이름', value: profile.value?.name || '-' },
  { label: '출생연도', value: profile.value?.birth_year ? `${profile.value.birth_year}년` : '-' },
  { label: '주거 상태', value: profile.value?.is_homeless ? '무주택' : '확인 필요' },
  { label: '청약통장', value: `${Number(profile.value?.subscription_months || 0)}개월` },
  { label: '연소득', value: formatMoney(profile.value?.annual_income || 0) },
  { label: '보유 현금', value: formatMoney(profile.value?.asset || 0) },
  { label: '부채', value: formatMoney(profile.value?.debt || 0) },
  { label: '월 저축', value: formatMoney(profile.value?.monthly_saving || 0) },
  { label: '준비 목표', value: `${Number(profile.value?.target_months || 0)}개월` },
  { label: '희망 지역', value: profile.value?.preferred_regions?.join(', ') || '-' },
]);

function parseRate(value) {
  const match = String(value || '').match(/\d+(?:\.\d+)?/);
  return match ? Number(match[0]) : 0;
}

function optionRate(option) {
  return Number(option?.intr_rate2 || option?.intr_rate || 0);
}

function chartLegendName(value) {
  const text = String(value || '')
    .replace(/\s*\(\s*\d+\s*개월\s*\)\s*/g, '')
    .trim();
  return text.length > 6 ? `${text.slice(0, 6)}...` : text;
}

function optionBarStyle(option) {
  return {
    height: `${Math.max(8, (option.rate / chartMaxRate.value) * 100)}%`,
  };
}

function selectedMarkerMetrics(optionBars = []) {
  if (!optionBars.length)
    return { left: '50%', position: 0.5 };

  const gap = 4;
  const selectedIndex = Math.max(0, optionBars.findIndex((option) => option.selected));
  const widths = optionBars.map((option) => option.selected ? 28 : 12);
  const clusterWidth = widths.reduce((sum, width) => sum + width, 0) + gap * Math.max(0, widths.length - 1);
  const beforeWidth = widths.slice(0, selectedIndex).reduce((sum, width) => sum + width, 0);
  const selectedCenter = beforeWidth + gap * selectedIndex + widths[selectedIndex] / 2;

  return {
    left: `calc(50% - ${clusterWidth / 2}px + ${selectedCenter}px)`,
    position: selectedCenter / Math.max(clusterWidth, 1),
  };
}

function shouldStaggerBadge(item, previousItem) {
  if (!previousItem)
    return false;
  return previousItem.selectedMarker.position > 0.62 && item.selectedMarker.position < 0.38;
}

function selectedBadgeStyle(item) {
  return {
    left: item.selectedMarker.left,
    top: item.badgeLane ? '22px' : '0px',
  };
}

function selectedConnectorStyle(item) {
  return {
    left: item.selectedMarker.left,
    top: item.badgeLane ? '29px' : '7px',
  };
}

function verticalTermChars(term) {
  return Array.from(`${Number(term || 0)}개월`);
}

function visibleMemo(item) {
  const memo = String(item.memo || '').trim();
  return memo;
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

function favoriteKey(favorite) {
  return `${favorite.favorite_type}:${favorite.object_id}`;
}

async function removeSavedFavorite(favorite) {
  const key = favoriteKey(favorite);
  if (removingFavoriteKey.value)
    return;
  removingFavoriteKey.value = key;
  try {
    await removeFavorite({ favorite_type: favorite.favorite_type, object_id: favorite.object_id });
    favorites.value = favorites.value.filter((item) => favoriteKey(item) !== key);
  }
  finally {
    removingFavoriteKey.value = '';
  }
}

function favoriteTitle(favorite) {
  return favorite.item?.title || favorite.item?.name || `#${favorite.object_id}`;
}

function productTerm(item) {
  return Number(item.selected_option?.save_trm || item.product?.term_months || item.product?.best_option?.save_trm || 0);
}

function productRate(item) {
  const rate = Number(item.selected_option?.intr_rate2 || item.selected_option?.intr_rate || item.product?.best_option?.intr_rate2 || item.product?.best_option?.intr_rate || 0);
  return rate || parseRate(item.product?.rate);
}

function productRateLabel(item) {
  const rate = productRate(item);
  return rate ? `최고 연 ${rate.toFixed(2)}%` : item.product?.rate || '금리 확인 필요';
}

function selectedOptionLabel(item) {
  const option = item.selected_option;
  if (!option)
    return productTerm(item) ? `${productTerm(item)}개월` : '선택 조건';
  const rawType = option.intr_rate_type_nm || option.rsrv_type_nm;
  const type = ['대표 금리', '대표 조건'].includes(rawType) ? '' : rawType;
  return [option.save_trm ? `${option.save_trm}개월` : '', type].filter(Boolean).join(' · ') || '선택 조건';
}

function noticeBadge(favorite) {
  const item = favorite.item || {};
  if (item.data_source === 'fixture')
    return 'Fixture';
  return item.provider || '공고';
}

function noticeDeadline(favorite) {
  const value = favorite.item?.application_deadline;
  return value ? `마감 ${value}` : '마감일 확인 필요';
}

function noticeLocation(favorite) {
  const item = favorite.item || {};
  return [item.region, item.district].filter(Boolean).join(' · ') || '지역 확인 필요';
}

function noticePrice(favorite) {
  const price = Number(favorite.item?.price || favorite.item?.representative_option?.base_price || 0);
  return price > 0 ? formatMoney(price) : '가격 확인 필요';
}

function optionItem(favorite) {
  return favorite.item || {};
}

function optionUnitLabel(favorite) {
  const item = optionItem(favorite);
  return [item.unit_type, item.floor_group].filter(Boolean).join(' · ') || item.name || '선택 주택형';
}

function optionAreaLabel(favorite) {
  const area = Number(optionItem(favorite).exclusive_area_m2 || 0);
  return area ? `${area.toFixed(area % 1 ? 1 : 0)}m²` : '면적 확인';
}

function optionPriceLabel(favorite) {
  const price = Number(optionItem(favorite).base_price || 0);
  return price > 0 ? formatMoney(price) : '분양가 확인';
}

function optionDownPaymentLabel(favorite) {
  const schedules = optionItem(favorite).payment_schedules || [];
  const downPayment = schedules.find((schedule) => schedule.payment_type === 'down_payment') || schedules[0];
  return downPayment?.amount ? `계약금 ${formatMoney(downPayment.amount)}` : '납부 일정 확인';
}

function optionSourceLabel(favorite) {
  const source = optionItem(favorite).extraction_source || optionItem(favorite).extraction_schema_version;
  if (!source)
    return '공식 근거 확인';
  if (source.includes('llm'))
    return 'LLM 보조 추출';
  if (source.includes('rules'))
    return '공식 PDF 규칙 추출';
  if (source.includes('fixture'))
    return 'Fixture 보강';
  return source;
}

function optionFundingRoute(favorite) {
  const noticeId = optionItem(favorite).notice_id;
  return {
    path: noticeId ? `/funding/${noticeId}` : '/funding',
    query: { option_id: favorite.object_id },
  };
}

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
    setJoinedPage(joinedPage.value);
  }
  loading.value = false;
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
      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 class="text-lg font-black text-slate-950">내 프로필</h2>
            <p class="mt-1 text-sm font-bold text-slate-500">계정 정보와 추천 조건을 한 번에 확인합니다.</p>
          </div>
          <div class="flex flex-wrap gap-2">
            <span class="rounded-md border border-slate-200 px-3 py-2 text-xs font-bold text-slate-500">관심 공고 {{ noticeFavorites.length }}</span>
            <span class="rounded-md border border-slate-200 px-3 py-2 text-xs font-bold text-slate-500">관심 옵션 {{ optionFavorites.length }}</span>
            <span class="rounded-md border border-slate-200 px-3 py-2 text-xs font-bold text-slate-500">가입상품 {{ joined.length }}</span>
          </div>
        </div>
        <dl class="mt-5 grid border-y border-slate-200 md:grid-cols-2 xl:grid-cols-4">
          <div
            v-for="row in profileRows"
            :key="row.label"
            class="grid min-h-[64px] grid-cols-[86px_minmax(0,1fr)] items-center gap-3 border-b border-slate-200 py-3 md:px-4 md:[&:nth-last-child(-n+2)]:border-b-0 xl:[&:nth-last-child(-n+4)]:border-b-0"
          >
            <dt class="text-xs font-black text-slate-500">{{ row.label }}</dt>
            <dd class="truncate text-sm font-black text-slate-950" :title="row.value">{{ row.value }}</dd>
          </div>
        </dl>
      </section>

      <section class="grid items-stretch gap-5 xl:grid-cols-[minmax(380px,1fr)_minmax(0,1fr)]">
        <div class="flex rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex min-h-[390px] w-full flex-col">
            <div class="flex items-center justify-between gap-3">
              <h2 class="text-lg font-black text-slate-950">가입 금융상품</h2>
              <span v-if="joined.length" class="rounded-md bg-slate-100 px-2.5 py-1 text-xs font-black text-slate-500">{{ joined.length }}개</span>
            </div>

            <div v-if="joined.length" class="mt-4 flex flex-1" :class="joinedListCentered ? 'items-center' : 'items-start'">
              <div class="w-full overflow-hidden rounded-lg border border-slate-200">
                <div
                  v-for="item in visibleJoined"
                  :key="item.id"
                  class="grid min-h-[64px] grid-cols-[minmax(0,1fr)_auto] items-center gap-3 border-b border-slate-200 bg-slate-50 px-4 py-3 last:border-b-0 md:grid-cols-[minmax(0,1fr)_minmax(150px,220px)_auto]"
                >
                  <RouterLink :to="`/finance/products/${item.product.id}`" class="min-w-0">
                    <p class="truncate font-black text-slate-950">{{ item.product.name }}</p>
                    <p class="mt-1 truncate text-xs font-bold text-slate-500">
                      {{ item.product.provider }} · {{ selectedOptionLabel(item) }} · {{ productRateLabel(item) }}
                    </p>
                  </RouterLink>
                  <p
                    class="hidden truncate rounded-md bg-white px-3 py-2 text-xs font-bold text-slate-600 md:block"
                    :title="visibleMemo(item) || '메모 없음'"
                  >
                    {{ visibleMemo(item) || '메모 없음' }}
                  </p>
                  <button
                    type="button"
                    class="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                    :disabled="removingJoinedId === item.id"
                    :aria-label="`${item.product.name} 해제`"
                    @click="removeJoinedProduct(item)"
                  >
                    <X class="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>

            <div v-else class="mt-4 flex flex-1 items-center justify-center rounded-lg bg-slate-50 p-6 text-center text-sm font-bold text-slate-500">
              가입 후보로 저장한 상품이 없습니다.
            </div>

            <div v-if="joinedPageCount > 1" class="mt-4 flex items-center justify-center gap-1.5">
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
        </div>

        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 class="text-lg font-black text-slate-950">가입 상품 금리 그래프</h2>
          <p class="mt-1 text-sm text-slate-500">{{ chartSummary }}</p>
          <div class="mt-4 rounded-lg bg-slate-950 p-5">
            <div v-if="chartBars.length" class="grid h-72 grid-cols-[58px_minmax(0,1fr)] gap-3">
              <div class="flex flex-col justify-between pb-7 pt-2 text-right text-xs font-black text-sky-100/80">
                <span v-for="tick in chartTicks" :key="tick.label">{{ tick.label }}</span>
              </div>
              <div class="relative min-w-0 overflow-x-auto">
                <div class="pointer-events-none absolute inset-x-0 top-2 border-t border-dashed border-slate-800"></div>
                <div class="pointer-events-none absolute inset-x-0 top-1/2 border-t border-dashed border-slate-800"></div>
                <div class="pointer-events-none absolute inset-x-0 bottom-7 border-b border-slate-700"></div>
                <div class="flex h-full items-end gap-4 pt-5" :style="chartTrackStyle">
                  <div
                    v-for="item in chartBars"
                    :key="item.id"
                    class="relative grid h-full min-w-0 grid-rows-[minmax(0,1fr)_28px] pt-12"
                    :class="chartNeedsScroll ? 'w-20 shrink-0' : 'flex-1'"
                  >
                    <div
                      class="absolute z-10 inline-flex -translate-x-1/2 items-center gap-1 rounded-full border border-sky-400 bg-slate-950 px-2 py-1 text-[11px] font-black text-sky-100 shadow-sm"
                      :style="selectedBadgeStyle(item)"
                    >
                      <span class="h-1.5 w-1.5 rounded-full bg-sky-300"></span>
                      {{ item.rate.toFixed(2) }}%
                    </div>
                    <div
                      class="absolute bottom-7 z-0 w-px -translate-x-1/2 bg-sky-400/70"
                      :style="selectedConnectorStyle(item)"
                    ></div>
                    <div class="flex min-h-0 items-end justify-center gap-1">
                      <div
                        v-for="option in item.optionBars"
                        :key="option.id"
                        class="relative -mb-px rounded-t-md transition"
                        :class="option.selected ? 'z-10 w-7 overflow-visible bg-gradient-to-t from-blue-600 to-sky-300 shadow-[0_0_18px_rgba(96,165,250,0.25)]' : 'z-10 w-3 bg-sky-300/30'"
                        :style="optionBarStyle(option)"
                        :title="`${option.term || '-'}개월 ${option.rate.toFixed(2)}%`"
                      >
                        <span
                          v-if="option.selected && option.term"
                          class="pointer-events-none absolute inset-0 z-20 flex flex-col items-center justify-center text-[9px] font-semibold leading-none text-white/95 drop-shadow"
                        >
                          <span v-for="(char, charIndex) in verticalTermChars(option.term)" :key="`${option.id}-${charIndex}`">{{ char }}</span>
                        </span>
                      </div>
                    </div>
                    <p class="flex h-7 items-center justify-center text-center text-xs font-black text-slate-400">{{ item.index }}</p>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="flex h-72 items-center justify-center rounded-lg border border-slate-800 text-sm font-bold text-slate-500">
              금리 정보가 있는 상품을 저장하면 그래프가 표시됩니다.
            </div>
          </div>
          <div v-if="chartBars.length" class="mt-3 overflow-x-auto pb-1">
            <div class="flex gap-2">
              <span
                v-for="item in chartBars"
                :key="item.id"
                class="grid min-w-[132px] shrink-0 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 rounded-md bg-slate-50 px-3 py-2 text-xs font-bold text-slate-500"
              >
                <b class="text-blue-700">{{ item.index }}</b>
                <span class="truncate">{{ chartLegendName(item.label) }}</span>
                <b class="text-slate-700">{{ item.rate.toFixed(2) }}%</b>
              </span>
            </div>
          </div>
        </div>
      </section>

      <section class="space-y-5">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-black text-slate-950">관심 공고</h2>
            <span class="text-xs font-black text-slate-400">{{ noticeFavorites.length }}개</span>
          </div>
          <div class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            <article
              v-for="favorite in noticeFavorites"
              :key="favorite.id"
              class="group relative rounded-lg border border-slate-200 bg-slate-50 p-4 pr-14 transition hover:border-blue-200 hover:bg-blue-50"
            >
              <RouterLink :to="`/notices/${favorite.object_id}`" class="block">
                <div class="flex items-center gap-2">
                  <span class="inline-flex h-7 w-7 items-center justify-center rounded-md bg-blue-50 text-blue-700">
                    <Bookmark class="h-4 w-4" />
                  </span>
                  <span class="rounded-md bg-white px-2 py-1 text-[11px] font-black text-blue-700">{{ noticeBadge(favorite) }}</span>
                </div>
                <p class="mt-3 line-clamp-2 min-h-[44px] font-black leading-snug text-slate-950 group-hover:text-blue-800">{{ favoriteTitle(favorite) }}</p>
                <div class="mt-4 grid gap-2 text-xs font-bold text-slate-500">
                  <span class="inline-flex items-center gap-1.5"><Building2 class="h-3.5 w-3.5" />{{ noticeLocation(favorite) }}</span>
                  <span class="inline-flex items-center gap-1.5"><CalendarDays class="h-3.5 w-3.5" />{{ noticeDeadline(favorite) }}</span>
                  <span class="inline-flex items-center gap-1.5"><WalletCards class="h-3.5 w-3.5" />{{ noticePrice(favorite) }}</span>
                </div>
              </RouterLink>
              <button
                type="button"
                class="absolute right-4 top-4 inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                :disabled="removingFavoriteKey === favoriteKey(favorite)"
                :aria-label="`${favoriteTitle(favorite)} 관심 해제`"
                @click="removeSavedFavorite(favorite)"
              >
                <X class="h-4 w-4" />
              </button>
            </article>
          </div>
          <p v-if="!noticeFavorites.length" class="mt-4 rounded-lg bg-slate-50 p-4 text-sm font-bold text-slate-500">저장한 관심 공고가 없습니다.</p>
        </div>

        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex items-center justify-between">
            <h2 class="text-lg font-black text-slate-950">관심 옵션</h2>
            <span class="text-xs font-black text-slate-400">{{ optionFavorites.length }}개</span>
          </div>
          <div v-if="optionFavorites.length" class="mt-4 overflow-hidden rounded-lg border border-slate-200 bg-slate-50">
            <article
              v-for="favorite in optionFavorites"
              :key="favorite.id"
              class="group grid gap-3 border-b border-slate-200 bg-white px-4 py-4 transition last:border-b-0 hover:bg-blue-50 md:grid-cols-[minmax(0,1fr)_minmax(320px,auto)_auto_auto] md:items-center"
            >
              <RouterLink :to="optionFundingRoute(favorite)" class="min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-blue-50 text-emerald-600">
                    <Home class="h-4 w-4" />
                  </span>
                  <span class="rounded-md bg-blue-50 px-2 py-1 text-[11px] font-black text-emerald-600">{{ optionSourceLabel(favorite) }}</span>
                </div>
                <p class="mt-2 line-clamp-2 font-black leading-snug text-slate-950 group-hover:text-blue-800">{{ favoriteTitle(favorite) }}</p>
              </RouterLink>
              <div class="flex flex-wrap gap-2 text-xs font-black text-slate-700">
                <span class="inline-flex items-center gap-1.5 rounded-full bg-slate-50 px-3 py-1.5"><Home class="h-3.5 w-3.5 text-emerald-600" />{{ optionUnitLabel(favorite) }}</span>
                <span class="inline-flex items-center gap-1.5 rounded-full bg-slate-50 px-3 py-1.5"><Ruler class="h-3.5 w-3.5 text-emerald-600" />{{ optionAreaLabel(favorite) }}</span>
                <span class="inline-flex items-center gap-1.5 rounded-full bg-slate-50 px-3 py-1.5"><WalletCards class="h-3.5 w-3.5 text-emerald-600" />{{ optionPriceLabel(favorite) }}</span>
                <span class="inline-flex items-center gap-1.5 rounded-full bg-slate-50 px-3 py-1.5">{{ optionDownPaymentLabel(favorite) }}</span>
              </div>
              <RouterLink :to="optionFundingRoute(favorite)" class="inline-flex justify-self-start rounded-md bg-blue-600 px-3 py-2 text-xs font-black text-white transition hover:bg-blue-700 md:justify-self-end">
                자금 보기
              </RouterLink>
              <button
                type="button"
                class="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500 transition hover:border-red-200 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                :disabled="removingFavoriteKey === favoriteKey(favorite)"
                :aria-label="`${favoriteTitle(favorite)} 관심 해제`"
                @click="removeSavedFavorite(favorite)"
              >
                <X class="h-4 w-4" />
              </button>
            </article>
          </div>
          <p v-if="!optionFavorites.length" class="mt-4 rounded-lg bg-slate-50 p-4 text-sm font-bold text-slate-500">저장한 관심 옵션이 없습니다.</p>
        </div>
      </section>

      <section v-if="otherFavorites.length" class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-lg font-black text-slate-950">기타 저장 항목</h2>
        <div class="mt-4 grid gap-3 lg:grid-cols-3">
          <div v-for="favorite in otherFavorites" :key="favorite.id" class="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <p class="inline-flex items-center gap-1.5 text-xs font-black text-blue-700"><ReceiptText class="h-3.5 w-3.5" />{{ favorite.favorite_type }}</p>
            <p class="mt-1 line-clamp-2 font-black text-slate-950">{{ favoriteTitle(favorite) }}</p>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>
