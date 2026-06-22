<script setup>
import { onMounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { BadgeCheck, Banknote, ChevronDown, Home, MapPinned, Save, UserRound } from 'lucide-vue-next';
import { emptyProfile, useProfileStore } from '../stores/profileStore';
import { formatMoney } from '../utils/format';
const router = useRouter();
const profileStore = useProfileStore();
const saved = ref(false);
const saving = ref(false);
const saveError = ref('');
const showExtraRegions = ref(false);
const areaUnit = ref('m2');
const M2_PER_PYEONG = 3.305785;
const form = reactive({
    ...emptyProfile,
    ...profileStore.profile,
    special_conditions: [...profileStore.profile.special_conditions],
    preferred_regions: [...profileStore.profile.preferred_regions],
    preferred_supply_types: [...profileStore.profile.preferred_supply_types],
});
const specialConditionOptions = [
    { label: '생애최초', value: 'first_home' },
    { label: '청년', value: 'youth' },
    { label: '신혼부부', value: 'newlywed' },
];
const primaryRegionOptions = ['서울', '경기 남부', '경기 북부', '인천'];
const extraRegionOptions = ['부산', '대구', '광주', '대전', '울산', '세종', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'];
const supplyTypeOptions = ['공공분양', '뉴홈', '신혼희망타운', '민간참여형 공공분양'];
const moneyFields = [
    { key: 'annual_income', label: '연소득' },
    { key: 'asset', label: '보유 현금' },
    { key: 'debt', label: '부채' },
    { key: 'monthly_saving', label: '월 저축 가능액' },
    { key: 'desired_price_min', label: '희망 분양가 최소' },
    { key: 'desired_price_max', label: '희망 분양가 최대' },
    { key: 'max_down_payment', label: '최대 계약금 준비액' },
    { key: 'monthly_payment_capacity', label: '월 납부 감당액' },
];
const moneyInputValues = reactive({});
const areaInputValues = reactive({
    min: '',
    max: '',
});
function applyProfile(profile) {
    Object.assign(form, {
        ...profile,
        special_conditions: [...profile.special_conditions],
        preferred_regions: [...profile.preferred_regions],
        preferred_supply_types: [...profile.preferred_supply_types],
    });
    syncFriendlyInputs();
}
function toggleArrayValue(target, value) {
    const index = target.indexOf(value);
    if (index >= 0)
        target.splice(index, 1);
    else
        target.push(value);
}
function wonToMan(value) {
    const numberValue = Number(value || 0);
    if (!numberValue)
        return '';
    return String(Math.round(numberValue / 10000));
}
function pyeongToM2(value) {
    const numberValue = Number(value || 0);
    return numberValue ? Math.round(numberValue * M2_PER_PYEONG * 10) / 10 : 0;
}
function m2ToPyeong(value) {
    const numberValue = Number(value || 0);
    return numberValue ? String(Math.round((numberValue / M2_PER_PYEONG) * 10) / 10) : '';
}
function m2ToInput(value) {
    const numberValue = Number(value || 0);
    return numberValue ? String(Math.round(numberValue * 10) / 10) : '';
}
function syncFriendlyInputs() {
    moneyFields.forEach((field) => {
        moneyInputValues[field.key] = wonToMan(form[field.key]);
    });
    areaInputValues.min = areaUnit.value === 'pyeong' ? m2ToPyeong(form.desired_area_min_m2) : m2ToInput(form.desired_area_min_m2);
    areaInputValues.max = areaUnit.value === 'pyeong' ? m2ToPyeong(form.desired_area_max_m2) : m2ToInput(form.desired_area_max_m2);
}
function sanitizeIntegerText(value) {
    return String(value ?? '').replace(/[^\d]/g, '');
}
function sanitizeDecimalText(value) {
    const text = String(value ?? '').replace(/[^\d.]/g, '');
    const [head, ...tail] = text.split('.');
    return tail.length ? `${head}.${tail.join('')}` : head;
}
function updateMoneyField(key) {
    const numericText = sanitizeIntegerText(moneyInputValues[key]);
    moneyInputValues[key] = numericText;
    form[key] = numericText ? Number(numericText) * 10000 : 0;
}
function updateAreaField(bound) {
    const key = bound === 'min' ? 'desired_area_min_m2' : 'desired_area_max_m2';
    const numericText = sanitizeDecimalText(areaInputValues[bound]);
    areaInputValues[bound] = numericText;
    if (areaUnit.value === 'pyeong') {
        form[key] = pyeongToM2(numericText);
    }
    else {
        const numberValue = Number(numericText || 0);
        form[key] = numberValue ? Math.round(numberValue * 10) / 10 : 0;
    }
}
function switchAreaUnit(unit) {
    areaUnit.value = unit;
    syncFriendlyInputs();
}
function areaHelper(bound) {
    const value = bound === 'min' ? form.desired_area_min_m2 : form.desired_area_max_m2;
    if (!value)
        return '면적 조건 없음';
    if (areaUnit.value === 'pyeong') {
        return `약 ${Math.round(Number(value) * 10) / 10}㎡ 기준`;
    }
    return `약 ${m2ToPyeong(value)}평 기준`;
}
async function handleSubmit() {
    saving.value = true;
    saveError.value = '';
    try {
        await profileStore.saveProfile({ ...form });
        saved.value = true;
        setTimeout(() => router.push('/recommendations'), 350);
    }
    catch {
        saveError.value = '백엔드 프로필 저장 API에 연결하지 못했습니다.';
    }
    finally {
        saving.value = false;
    }
}
onMounted(async () => {
    if (!profileStore.loaded) {
        await profileStore.hydrateProfile();
    }
    applyProfile(profileStore.profile);
});
watch(() => profileStore.profile, (profile) => applyProfile(profile), { deep: true });
</script>

<template>
  <form class="space-y-5" @submit.prevent="handleSubmit">
    <div>
      <p class="inline-flex items-center gap-2 text-sm font-semibold text-blue-700">
        <UserRound class="h-4 w-4" />
        조건 입력
      </p>
      <h1 class="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">첫 집 청약 추천 조건</h1>
      <p class="mt-2 text-sm text-slate-500">로그인하면 조건이 계정 기준으로 저장되고, 비로그인 상태에서는 임시 세션 기준으로 추천, 자금 로드맵, AI 코치에 반영됩니다.</p>
    </div>

    <p v-if="profileStore.error" class="rounded-lg border border-amber-100 bg-amber-50 p-4 text-sm font-semibold text-amber-800">
      {{ profileStore.error }}
    </p>

    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="flex items-center gap-2 text-lg font-bold">
        <UserRound class="h-5 w-5 text-blue-700" />
        기본 정보
      </h2>
      <div class="mt-5 grid gap-4 md:grid-cols-3">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">이름</span>
          <input v-model="form.name" type="text" class="mt-2 w-full rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500" />
        </label>
        <label class="block">
          <span class="text-sm font-medium text-slate-700">출생연도</span>
          <input v-model.number="form.birth_year" type="number" class="mt-2 w-full rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500" />
        </label>
        <label class="block">
          <span class="text-sm font-medium text-slate-700">직업 상태</span>
          <select v-model="form.job_status" class="mt-2 w-full rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500">
            <option value="employed">직장인</option>
            <option value="student">학생</option>
            <option value="unemployed">구직 중</option>
            <option value="self_employed">자영업</option>
          </select>
        </label>
      </div>
    </section>

    <section class="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <h2 class="flex items-center gap-2 text-lg font-bold">
        <Banknote class="h-5 w-5 text-blue-700" />
        자금 조건
      </h2>
      <div class="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <label v-for="field in moneyFields" :key="field.key" class="block">
          <span class="text-sm font-medium text-slate-700">{{ field.label }}</span>
          <div class="relative mt-1.5">
            <input
              v-model="moneyInputValues[field.key]"
              type="text"
              inputmode="numeric"
              autocomplete="off"
              class="w-full rounded-lg border border-slate-200 px-3 py-2.5 pr-12 text-sm outline-none focus:border-blue-500"
              placeholder="0"
              @input="updateMoneyField(field.key)"
            />
            <span class="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-xs font-bold text-slate-500">만원</span>
          </div>
          <p class="mt-1 text-[11px] text-slate-500">{{ formatMoney(Number(form[field.key])) }}</p>
        </label>
      </div>
    </section>

    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <h2 class="flex items-center gap-2 text-lg font-bold">
          <Home class="h-5 w-5 text-blue-700" />
          희망 주택형 범위
        </h2>
        <div class="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs font-bold">
          <button
            type="button"
            class="rounded-md px-3 py-1.5 transition"
            :class="areaUnit === 'm2' ? 'bg-white text-blue-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
            @click="switchAreaUnit('m2')"
          >
            ㎡ 기준
          </button>
          <button
            type="button"
            class="rounded-md px-3 py-1.5 transition"
            :class="areaUnit === 'pyeong' ? 'bg-white text-blue-700 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
            @click="switchAreaUnit('pyeong')"
          >
            평 기준
          </button>
        </div>
      </div>
      <div class="mt-5 grid gap-4 md:grid-cols-2">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">희망 면적 최소</span>
          <div class="relative mt-2">
            <input
              v-model="areaInputValues.min"
              type="text"
              inputmode="decimal"
              autocomplete="off"
              class="w-full rounded-lg border border-slate-200 px-4 py-3 pr-12 text-sm outline-none focus:border-blue-500"
              :placeholder="areaUnit === 'm2' ? '예: 59' : '예: 18'"
              @input="updateAreaField('min')"
            />
            <span class="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm font-bold text-slate-500">{{ areaUnit === 'm2' ? '㎡' : '평' }}</span>
          </div>
          <p class="mt-1 text-xs text-slate-500">{{ areaHelper('min') }} · 내부 계산은 ㎡로 저장</p>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-slate-700">희망 면적 최대</span>
          <div class="relative mt-2">
            <input
              v-model="areaInputValues.max"
              type="text"
              inputmode="decimal"
              autocomplete="off"
              class="w-full rounded-lg border border-slate-200 px-4 py-3 pr-12 text-sm outline-none focus:border-blue-500"
              :placeholder="areaUnit === 'm2' ? '예: 84' : '예: 25'"
              @input="updateAreaField('max')"
            />
            <span class="pointer-events-none absolute right-4 top-1/2 -translate-y-1/2 text-sm font-bold text-slate-500">{{ areaUnit === 'm2' ? '㎡' : '평' }}</span>
          </div>
          <p class="mt-1 text-xs text-slate-500">{{ areaHelper('max') }} · 내부 계산은 ㎡로 저장</p>
        </label>
      </div>
      <p class="mt-3 text-xs leading-5 text-slate-500">
        실제 PDF 분석 전까지는 공고 목록의 대표 면적과 대표 분양가를 기준으로 맞춤도를 계산합니다.
      </p>
    </section>

    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="flex items-center gap-2 text-lg font-bold">
        <Home class="h-5 w-5 text-blue-700" />
        청약 조건
      </h2>
      <div class="mt-5 grid gap-4 md:grid-cols-3">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">무주택 여부</span>
          <select v-model="form.is_homeless" class="mt-2 w-full rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500">
            <option :value="true">무주택</option>
            <option :value="false">주택 보유</option>
          </select>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-slate-700">청약통장 가입기간</span>
          <input v-model.number="form.subscription_months" type="number" min="0" class="mt-2 w-full rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500" />
          <p class="mt-1 text-xs text-slate-500">{{ form.subscription_months }}개월</p>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-slate-700">계약금 목표 기간</span>
          <input v-model.number="form.target_months" type="number" min="1" class="mt-2 w-full rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500" />
          <p class="mt-1 text-xs text-slate-500">{{ form.target_months }}개월</p>
        </label>
      </div>

      <div class="mt-5">
        <p class="flex items-center gap-2 text-sm font-medium text-slate-700">
          <BadgeCheck class="h-4 w-4" />
          관심 특별 조건
        </p>
        <div class="mt-3 flex flex-wrap gap-2">
          <button
            v-for="option in specialConditionOptions"
            :key="option.value"
            type="button"
            class="rounded-lg px-4 py-2 text-sm font-bold transition"
            :class="form.special_conditions.includes(option.value) ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
            @click="toggleArrayValue(form.special_conditions, option.value)"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
    </section>

    <section class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(340px,0.82fr)]">
      <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="flex items-center gap-2 text-lg font-bold">
          <MapPinned class="h-5 w-5 text-blue-700" />
          희망 지역
        </h2>
        <div class="mt-5">
          <p class="text-sm font-medium text-slate-700">희망 지역</p>
          <div class="mt-3 flex flex-wrap gap-2">
            <button
              v-for="region in primaryRegionOptions"
              :key="region"
              type="button"
              class="rounded-lg px-4 py-2 text-sm font-bold transition"
              :class="form.preferred_regions.includes(region) ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
              @click="toggleArrayValue(form.preferred_regions, region)"
            >
              {{ region }}
            </button>
          </div>
          <button
            type="button"
            class="mt-3 inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-bold text-slate-700 transition hover:bg-slate-50"
            :aria-expanded="showExtraRegions"
            @click="showExtraRegions = !showExtraRegions"
          >
            기타 지역
            <ChevronDown class="h-4 w-4 transition" :class="showExtraRegions ? 'rotate-180' : ''" />
          </button>
          <div v-if="showExtraRegions" class="mt-3 flex flex-wrap gap-2">
            <button
              v-for="region in extraRegionOptions"
              :key="region"
              type="button"
              class="rounded-lg px-4 py-2 text-sm font-bold transition"
              :class="form.preferred_regions.includes(region) ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
              @click="toggleArrayValue(form.preferred_regions, region)"
            >
              {{ region }}
            </button>
          </div>
        </div>
      </div>

      <div class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 class="flex items-center gap-2 text-lg font-bold">
          <BadgeCheck class="h-5 w-5 text-blue-700" />
          공급 유형
        </h2>
        <div class="mt-5 rounded-lg border border-slate-200 bg-slate-50 p-4">
          <p class="text-sm font-medium text-slate-700">선호 공급 유형</p>
          <p class="mt-1 text-xs text-slate-500">추천은 소유형 공공분양 범위 안에서만 계산됩니다.</p>
          <div class="mt-3 flex flex-wrap gap-2">
            <button
              v-for="type in supplyTypeOptions"
              :key="type"
              type="button"
              class="rounded-lg px-4 py-2 text-sm font-bold transition"
              :class="form.preferred_supply_types.includes(type) ? 'bg-blue-600 text-white' : 'bg-white text-slate-600 shadow-sm ring-1 ring-slate-200 hover:bg-slate-100'"
              @click="toggleArrayValue(form.preferred_supply_types, type)"
            >
              {{ type }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <div class="sticky bottom-20 z-30 flex flex-col items-center gap-3 pt-2 lg:bottom-6">
      <p v-if="saved" class="rounded-lg bg-green-50 px-4 py-3 text-sm font-bold text-green-700">
        저장 완료
      </p>
      <p v-if="saveError" class="rounded-lg border border-amber-100 bg-amber-50 px-4 py-3 text-sm font-bold text-amber-800">
        {{ saveError }}
      </p>
      <button type="submit" class="inline-flex min-h-14 min-w-[240px] items-center justify-center gap-2 rounded-lg bg-blue-600 px-8 py-4 text-base font-black text-white shadow-lg hover:bg-blue-700 disabled:opacity-60" :disabled="saving">
        <Save class="h-5 w-5" />
        {{ saving ? '저장 중' : '저장하고 추천 보기' }}
      </button>
    </div>
  </form>
</template>
