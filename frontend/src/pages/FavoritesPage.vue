<script setup>
import { computed, onMounted, ref } from 'vue';
import { Bookmark, ExternalLink, Trash2, WalletCards } from 'lucide-vue-next';
import { fetchFavorites, removeFavorite } from '../api/firsthome';
import { formatMoney } from '../utils/format';
import { saveCurrentSelection } from '../utils/selectionState';
const favorites = ref([]);
const loading = ref(true);
const error = ref('');
const removingKey = ref('');
const noticeFavorites = computed(() => favorites.value.filter((favorite) => favorite.favorite_type === 'notice'));
const optionFavorites = computed(() => favorites.value.filter((favorite) => favorite.favorite_type === 'option'));
const hasVisibleFavorites = computed(() => noticeFavorites.value.length > 0 || savedOptionRows.value.length > 0);
const savedOptionRows = computed(() => {
    return optionFavorites.value
        .map((favorite) => {
        const unitType = String(favorite.item?.unit_type ?? '').trim();
        const floorGroup = String(favorite.item?.floor_group ?? '').trim();
        const area = Number(favorite.item?.exclusive_area_m2 ?? 0);
        const price = Number(favorite.item?.base_price ?? 0);
        return {
        favorite,
        name: itemName(favorite),
        noticeId: Number(favorite.item?.notice_id ?? 0),
        unitType,
        floorGroup: floorGroup || '전체',
        area,
        price,
        downPayment: downPayment(favorite),
        middlePayment: paymentAmount(favorite, 'middle_payment'),
        finalPayment: paymentAmount(favorite, 'final_payment'),
        confidence: Number(favorite.item?.confidence ?? 0),
        };
    })
        .filter(isMeaningfulOptionRow)
        .sort((a, b) => a.downPayment - b.downPayment || a.price - b.price);
});
function isMeaningfulOptionRow(row) {
    const label = `${row.unitType}${row.floorGroup}`.trim();
    const hasNamedUnit = Boolean(row.unitType) && label !== '전체';
    const hasMoney = row.price > 0 || row.downPayment > 0 || row.middlePayment > 0 || row.finalPayment > 0;
    return row.noticeId > 0 && row.area > 0 && hasNamedUnit && hasMoney;
}
function noticeDisplayPrice(favorite) {
    const directPrice = Number(favorite.item?.price ?? 0);
    const representativePrice = Number(favorite.item?.representative_option?.base_price ?? 0);
    const options = Array.isArray(favorite.item?.unit_options) ? favorite.item.unit_options : [];
    const optionPrice = options
        .map((option) => Number(option?.base_price ?? 0))
        .find((price) => price > 0);
    return directPrice || representativePrice || optionPrice || 0;
}
function favoriteKey(favorite) {
    return `${favorite.favorite_type}-${favorite.object_id}`;
}
function typeLabel(type) {
    if (type === 'notice')
        return '공고';
    if (type === 'option')
        return '주택형';
    return '저장 항목';
}
function itemName(favorite) {
    return String(favorite.item?.title ?? favorite.item?.name ?? '저장 항목');
}
function itemMeta(favorite) {
    if (favorite.favorite_type === 'notice') {
        return `${favorite.item?.provider ?? ''} · ${favorite.item?.region ?? ''} · ${favorite.item?.supply_type ?? ''}`;
    }
    if (favorite.favorite_type === 'option') {
        return `${favorite.item?.unit_type ?? ''} · ${favorite.item?.floor_group ?? '전체'} · ${favorite.item?.exclusive_area_m2 ?? ''}㎡`;
    }
    return `${favorite.item?.provider ?? ''} · ${favorite.item?.category ?? favorite.item?.policy_category ?? ''}`;
}
function itemDescription(favorite) {
    if (favorite.favorite_type === 'notice') {
        return `예상 분양가 ${formatMoney(noticeDisplayPrice(favorite))}, 접수 마감 ${favorite.item?.application_deadline ?? '확인 필요'}`;
    }
    if (favorite.favorite_type === 'option') {
        return `분양가 ${formatMoney(Number(favorite.item?.base_price ?? 0))}, 계약금 ${formatMoney(downPayment(favorite))}`;
    }
    return String(favorite.item?.benefit ?? favorite.item?.reasons?.[0] ?? '저장한 항목입니다.');
}
function downPayment(favorite) {
    return paymentAmount(favorite, 'down_payment');
}
function paymentAmount(favorite, paymentType) {
    const schedules = favorite.item?.payment_schedules ?? [];
    if (!Array.isArray(schedules))
        return 0;
    return schedules
        .filter((item) => item.payment_type === paymentType)
        .reduce((total, item) => total + Number(item.amount ?? 0), 0);
}
function sourceUrl(favorite) {
    return String(favorite.item?.source_url ?? '');
}
function isFixtureFavorite(favorite) {
    const source = String(favorite.item?.data_source || '').toLowerCase();
    return source.includes('fixture') || Boolean(favorite.item?.source_meta?.fixture_id);
}
async function loadFavorites() {
    loading.value = true;
    error.value = '';
    try {
        favorites.value = await fetchFavorites();
    }
    catch {
        error.value = '관심 목록 API에 연결하지 못했습니다. Django 서버가 실행 중인지 확인하세요.';
    }
    finally {
        loading.value = false;
    }
}
async function handleRemove(favorite) {
    removingKey.value = favoriteKey(favorite);
    try {
        await removeFavorite({ favorite_type: favorite.favorite_type, object_id: favorite.object_id });
        favorites.value = favorites.value.filter((item) => favoriteKey(item) !== favoriteKey(favorite));
    }
    finally {
        removingKey.value = '';
    }
}
onMounted(loadFavorites);
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p class="inline-flex items-center gap-2 text-sm font-semibold text-blue-700">
          <Bookmark class="h-4 w-4" />
          관심 목록
        </p>
        <h1 class="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">저장한 공고와 주택형</h1>
        <p class="mt-2 text-sm text-slate-500">저장한 청약 공고와 주택형 옵션을 다시 확인합니다.</p>
      </div>
      <RouterLink to="/recommendations" class="inline-flex h-10 items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-bold text-white">
        추천 옵션 보러 가기
      </RouterLink>
    </div>

    <section v-if="loading" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-semibold text-slate-600 shadow-sm">
      관심 목록을 불러오는 중입니다.
    </section>

    <section v-else-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-semibold text-amber-800">
      {{ error }}
    </section>

    <section v-else-if="!hasVisibleFavorites" class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <p class="font-bold text-slate-950">아직 저장한 항목이 없습니다.</p>
      <p class="mt-2 text-sm text-slate-500">추천, 공고 상세, 자금 로드맵 화면에서 검토할 공고와 주택형 옵션을 저장할 수 있습니다.</p>
    </section>

    <template v-else>
      <section class="grid gap-3 sm:grid-cols-2">
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm font-semibold text-slate-500">저장 공고</p>
          <p class="mt-2 text-2xl font-bold text-slate-950">{{ noticeFavorites.length }}건</p>
        </div>
        <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <p class="text-sm font-semibold text-slate-500">저장 옵션</p>
          <p class="mt-2 text-2xl font-bold text-slate-950">{{ savedOptionRows.length }}건</p>
        </div>
      </section>

      <section v-if="savedOptionRows.length" class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div class="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <p class="text-sm font-semibold text-blue-700">저장 옵션 비교</p>
            <h2 class="mt-1 text-lg font-bold text-slate-950">계약금이 낮은 순서로 다시 보기</h2>
            <p class="mt-1 text-sm text-slate-500">저장한 주택형의 분양가, 계약금, 중도금, 잔금을 한눈에 비교합니다.</p>
          </div>
          <span class="rounded-md bg-slate-950 px-3 py-2 text-sm font-bold text-white">{{ savedOptionRows.length }}개 옵션</span>
        </div>

        <div class="mt-4 overflow-x-auto">
          <table class="min-w-[760px] w-full text-left text-sm">
            <thead class="border-b border-slate-200 text-xs font-bold text-slate-500">
              <tr>
                <th class="py-3 pr-3">주택형</th>
                <th class="px-3 py-3">면적</th>
                <th class="px-3 py-3">분양가</th>
                <th class="px-3 py-3">계약금</th>
                <th class="px-3 py-3">중도금</th>
                <th class="px-3 py-3">잔금</th>
                <th class="py-3 pl-3 text-right">이동</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
              <tr v-for="row in savedOptionRows" :key="favoriteKey(row.favorite)" class="align-top">
                <td class="py-3 pr-3">
                  <p class="font-bold text-slate-950">{{ row.unitType }} · {{ row.floorGroup }}</p>
                  <p class="mt-1 line-clamp-1 text-xs text-slate-500">{{ row.name }}</p>
                </td>
                <td class="px-3 py-3 font-semibold text-slate-700">{{ row.area }}㎡</td>
                <td class="px-3 py-3 font-semibold text-slate-950">{{ formatMoney(row.price) }}</td>
                <td class="px-3 py-3 font-bold text-blue-700">{{ formatMoney(row.downPayment) }}</td>
                <td class="px-3 py-3 text-slate-700">{{ formatMoney(row.middlePayment) }}</td>
                <td class="px-3 py-3 text-slate-700">{{ formatMoney(row.finalPayment) }}</td>
                <td class="py-3 pl-3 text-right">
                  <RouterLink
                    v-if="row.noticeId"
                    :to="{ path: `/funding/${row.noticeId}`, query: { option_id: row.favorite.object_id } }"
                    class="inline-flex h-9 items-center justify-center rounded-lg bg-blue-600 px-3 text-xs font-bold text-white"
                    @click="saveCurrentSelection(row.noticeId, row.favorite.object_id)"
                  >
                    자금 보기
                  </RouterLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="noticeFavorites.length" class="grid gap-4 lg:grid-cols-2">
        <article v-for="favorite in noticeFavorites" :key="favoriteKey(favorite)" class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div class="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div class="min-w-0">
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
              class="inline-flex h-9 min-w-20 shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700"
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
              :to="{ path: `/notices/${favorite.object_id}` }"
              class="inline-flex items-center justify-center rounded-lg bg-blue-600 px-4 py-2 text-sm font-bold text-white"
              @click="saveCurrentSelection(favorite.object_id, null)"
            >
              공고 상세
            </RouterLink>
            <RouterLink
              v-if="favorite.favorite_type === 'notice'"
              :to="{ path: `/funding/${favorite.object_id}` }"
              class="inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-slate-700"
              @click="saveCurrentSelection(favorite.object_id, null)"
            >
              <WalletCards class="h-4 w-4" />
              공고 자금 보기
            </RouterLink>
            <span
              v-if="isFixtureFavorite(favorite)"
              class="inline-flex items-center rounded-lg border border-slate-200 bg-slate-50 px-4 py-2 text-sm font-bold text-slate-600"
            >
              Fixture
            </span>
            <a
              v-else-if="sourceUrl(favorite)"
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
