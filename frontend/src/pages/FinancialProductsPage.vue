<script setup>
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import { Search, SlidersHorizontal } from 'lucide-vue-next';
import { fetchFinancialProducts } from '../api/firsthome';

const loading = ref(true);
const error = ref('');
const items = ref([]);
const filters = ref({ providers: [], categories: [] });
const form = ref({ category: 'all', provider: '', term_months: '', q: '', ordering: 'fit' });

const categoryLabels = { all: '전체', deposit: '정기예금', saving: '적금', 예금: '예금', 적금: '적금' };
const visibleProviders = computed(() => filters.value.providers ?? []);

function optionLabel(product) {
  const count = Number(product.option_count ?? 0);
  return count > 0 ? `${count}개` : '단일';
}

async function loadProducts() {
  loading.value = true;
  error.value = '';
  try {
    const response = await fetchFinancialProducts(form.value);
    items.value = response.items ?? [];
    filters.value = response.filters ?? { providers: [], categories: [] };
  } catch {
    error.value = '금융상품 목록을 불러오지 못했습니다.';
  } finally {
    loading.value = false;
  }
}

watch(form, loadProducts, { deep: true });
onMounted(loadProducts);
</script>

<template>
  <div class="space-y-5">
    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <p class="text-sm font-bold text-blue-700">금융 광장</p>
      <h1 class="mt-1 text-3xl font-black text-slate-950">금융상품</h1>
      <p class="mt-2 text-sm leading-6 text-slate-500">계약금과 잔금 준비에 활용할 수 있는 예적금 상품을 비교합니다.</p>
    </section>

    <section class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div class="grid gap-3 lg:grid-cols-[140px_180px_140px_minmax(0,1fr)_160px]">
        <select v-model="form.category" class="h-11 rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold">
          <option value="all">전체</option>
          <option value="deposit">정기예금</option>
          <option value="saving">적금</option>
        </select>
        <select v-model="form.provider" class="h-11 rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold">
          <option value="">전체 은행</option>
          <option v-for="provider in visibleProviders" :key="provider" :value="provider">{{ provider }}</option>
        </select>
        <select v-model="form.term_months" class="h-11 rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold">
          <option value="">전체 기간</option>
          <option value="6">6개월</option>
          <option value="12">12개월</option>
          <option value="24">24개월</option>
          <option value="36">36개월</option>
        </select>
        <label class="relative block">
          <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input v-model="form.q" class="h-11 w-full rounded-lg border border-slate-200 bg-white pl-10 pr-3 text-sm font-bold" type="search" placeholder="상품명 또는 은행 검색" />
        </label>
        <select v-model="form.ordering" class="h-11 rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold">
          <option value="fit">자금로드맵 적합순</option>
          <option value="rate">최고 금리순</option>
          <option value="term">기간 짧은순</option>
          <option value="provider">은행명순</option>
          <option value="name">상품명순</option>
        </select>
      </div>
    </section>

    <section v-if="loading" class="loading-surface">
      <p class="text-sm font-black text-slate-950">금융상품을 비교할 준비를 하고 있습니다</p>
      <p class="mt-1 text-sm text-slate-500">금리, 기간, 자금 로드맵 적합도를 함께 정리하는 중입니다.</p>
      <div class="mt-5 grid gap-3 lg:grid-cols-3">
        <div v-for="index in 6" :key="index" class="loading-surface-tile">
          <span class="loading-surface-line w-1/3" />
          <span class="loading-surface-line mt-4 w-2/3" />
          <span class="loading-surface-line mt-3 w-full" />
        </div>
      </div>
    </section>
    <section v-else-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-bold text-amber-800">{{ error }}</section>
    <section v-else class="grid gap-4 xl:grid-cols-3">
      <RouterLink
        v-for="product in items"
        :key="`${product.id}-${product.name}`"
        :to="`/finance/products/${product.id}`"
        class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:border-blue-300 hover:shadow-md"
      >
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="text-sm font-bold text-blue-700">{{ product.provider }}</p>
            <h2 class="mt-1 line-clamp-2 text-lg font-black text-slate-950">{{ product.name }}</h2>
          </div>
          <div class="flex shrink-0 flex-col items-end gap-1">
            <span class="rounded-md bg-blue-50 px-2 py-1 text-xs font-black text-blue-700">{{ categoryLabels[product.category] ?? product.category }}</span>
            <span v-if="form.ordering === 'fit' && product.match_score" class="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-black text-emerald-700">
              적합도 {{ product.match_score }}점
            </span>
          </div>
        </div>
        <div class="mt-4 grid grid-cols-3 gap-2 text-sm">
          <div class="rounded-lg bg-slate-50 p-3">
            <p class="text-xs font-bold text-slate-500">대표 금리</p>
            <p class="mt-1 font-black text-slate-950">{{ product.rate || '확인 필요' }}</p>
          </div>
          <div class="rounded-lg bg-slate-50 p-3">
            <p class="text-xs font-bold text-slate-500">기간</p>
            <p class="mt-1 font-black text-slate-950">{{ product.term_months || product.best_option?.save_trm || '-' }}개월</p>
          </div>
          <div class="rounded-lg bg-slate-50 p-3">
            <p class="text-xs font-bold text-slate-500">구성</p>
            <p class="mt-1 font-black text-slate-950">{{ optionLabel(product) }}</p>
          </div>
        </div>
      </RouterLink>
      <div v-if="!items.length" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-bold text-slate-500 xl:col-span-3">
        조건에 맞는 상품이 없습니다.
      </div>
    </section>
  </div>
</template>
