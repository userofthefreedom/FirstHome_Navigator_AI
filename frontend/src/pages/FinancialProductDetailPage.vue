<script setup>
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRoute, useRouter } from 'vue-router';
import { ArrowLeft, CheckCircle2, ExternalLink } from 'lucide-vue-next';
import { fetchAuthSession, fetchFinancialProduct, joinFinancialProduct } from '../api/firsthome';

const route = useRoute();
const router = useRouter();
const productId = computed(() => Number(route.params.productId));
const product = ref(null);
const session = ref(null);
const selectedOptionId = ref(null);
const memo = ref('계약금 마련 후보');
const loading = ref(true);
const error = ref('');
const joinedMessage = ref('');

const isLoggedIn = computed(() => Boolean(session.value?.user?.is_authenticated));
const bestOptionId = computed(() => product.value?.best_option?.id ?? product.value?.options?.[0]?.id ?? null);

function displayRate(value) {
  if (value === null || value === undefined || value === '') return '확인 필요';
  return `${Number(value).toFixed(2).replace(/\.?0+$/, '')}%`;
}

async function loadDetail() {
  loading.value = true;
  error.value = '';
  try {
    const [productResponse, sessionResponse] = await Promise.all([fetchFinancialProduct(productId.value), fetchAuthSession()]);
    product.value = productResponse;
    session.value = sessionResponse;
    selectedOptionId.value = bestOptionId.value;
  } catch {
    error.value = '상품 상세 정보를 불러오지 못했습니다.';
  } finally {
    loading.value = false;
  }
}

async function joinProduct() {
  if (!isLoggedIn.value) {
    await router.push('/auth');
    return;
  }
  await joinFinancialProduct(productId.value, selectedOptionId.value, memo.value);
  joinedMessage.value = '가입상품으로 저장했습니다. MY PAGE에서 확인할 수 있습니다.';
}

onMounted(loadDetail);
</script>

<template>
  <div class="space-y-5">
    <RouterLink to="/finance/products" class="inline-flex items-center gap-2 text-sm font-bold text-slate-600">
      <ArrowLeft class="h-4 w-4" /> 금융상품 목록
    </RouterLink>

    <section v-if="loading" class="rounded-lg border border-slate-200 bg-white p-6 text-sm font-bold text-slate-500">상품 정보를 불러오는 중입니다.</section>
    <section v-else-if="error" class="rounded-lg border border-amber-100 bg-amber-50 p-6 text-sm font-bold text-amber-800">{{ error }}</section>
    <template v-else-if="product">
      <section class="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <p class="text-sm font-bold text-blue-700">{{ product.provider }} · {{ product.category_label ?? product.category }}</p>
            <h1 class="mt-2 text-3xl font-black text-slate-950">{{ product.name }}</h1>
            <p class="mt-3 text-sm leading-6 text-slate-500">{{ product.join_way || '가입 방법은 금융회사 공식 설명서를 확인하세요.' }}</p>
          </div>
          <a v-if="product.source_url" :href="product.source_url" target="_blank" rel="noreferrer" class="inline-flex items-center gap-2 rounded-lg border border-slate-200 px-4 py-2 text-sm font-bold text-slate-700">
            공식 확인 <ExternalLink class="h-4 w-4" />
          </a>
        </div>
        <div class="mt-5 grid gap-3 md:grid-cols-3">
          <div class="rounded-lg bg-blue-50 p-4">
            <p class="text-xs font-bold text-blue-700">대표 금리</p>
            <p class="mt-1 text-xl font-black text-slate-950">{{ product.rate || '확인 필요' }}</p>
          </div>
          <div class="rounded-lg bg-slate-50 p-4">
            <p class="text-xs font-bold text-slate-500">대표 기간</p>
            <p class="mt-1 text-xl font-black text-slate-950">{{ product.term_months || '-' }}개월</p>
          </div>
          <div class="rounded-lg bg-slate-50 p-4">
            <p class="text-xs font-bold text-slate-500">예금자 보호</p>
            <p class="mt-1 text-xl font-black text-slate-950">{{ product.protection_status ? '대상' : '확인 필요' }}</p>
          </div>
        </div>
      </section>

      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-lg font-black text-slate-950">기간별 금리 옵션</h2>
        <div class="mt-4 overflow-hidden rounded-lg border border-slate-200">
          <label v-for="(option, index) in product.options ?? []" :key="option.id ?? `single-${index}`" class="grid cursor-pointer gap-3 border-b border-slate-100 p-4 last:border-b-0 md:grid-cols-[40px_1fr_1fr_1fr]">
            <input v-model="selectedOptionId" type="radio" :value="option.id" />
            <span class="font-bold text-slate-950">{{ option.save_trm }}개월</span>
            <span class="text-sm font-semibold text-slate-600">기본 {{ displayRate(option.intr_rate) }}</span>
            <span class="text-sm font-black text-blue-700">최고 {{ displayRate(option.intr_rate2) }}</span>
          </label>
          <p v-if="!(product.options ?? []).length" class="p-4 text-sm font-bold text-slate-500">옵션 데이터가 없습니다.</p>
        </div>
      </section>

      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="text-lg font-black text-slate-950">가입하기</h2>
        <p class="mt-2 text-sm text-slate-500">실제 금융 가입이 아니라, MY PAGE에서 관리할 관심 가입 후보로 저장합니다.</p>
        <input v-model="memo" class="mt-4 h-11 w-full rounded-lg border border-slate-200 px-3 text-sm font-bold" maxlength="200" />
        <div class="mt-4 flex flex-wrap items-center gap-3">
          <button type="button" class="rounded-lg bg-blue-600 px-4 py-2 text-sm font-black text-white" @click="joinProduct">
            {{ isLoggedIn ? '가입상품으로 저장' : '로그인 후 가입 가능' }}
          </button>
          <p v-if="joinedMessage" class="inline-flex items-center gap-2 text-sm font-bold text-emerald-700">
            <CheckCircle2 class="h-4 w-4" /> {{ joinedMessage }}
          </p>
        </div>
      </section>
    </template>
  </div>
</template>
