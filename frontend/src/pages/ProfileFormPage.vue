<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  BadgeCheck,
  Banknote,
  Home,
  MapPinned,
  UserRound,
} from 'lucide-vue-next'
import { profile } from '../data/sampleData'

const router = useRouter()
const saved = ref(false)

const form = reactive({
  birth_year: profile.birth_year,
  job_status: profile.job_status,
  annual_income: profile.annual_income,
  asset: profile.asset,
  debt: profile.debt,
  monthly_saving: profile.monthly_saving,
  is_homeless: profile.is_homeless,
  subscription_months: profile.subscription_months,
  special_conditions: [...profile.special_conditions],
  preferred_regions: [...profile.preferred_regions],
  preferred_supply_types: [...profile.preferred_supply_types],
  target_months: profile.target_months,
})

const specialConditionOptions = [
  { label: '생애최초', value: 'first_home' },
  { label: '청년', value: 'youth' },
  { label: '신혼부부', value: 'newlywed' },
]
const regionOptions = ['서울', '경기 남부', '경기 북부', '인천', '부산']
const supplyTypeOptions = ['공공분양', '민영', '청년 공공주택', '공공임대']

function formatMoney(value: number) {
  return `${Math.round(value / 10000).toLocaleString()}만원`
}

function toggleArrayValue(target: string[], value: string) {
  const index = target.indexOf(value)
  if (index >= 0) target.splice(index, 1)
  else target.push(value)
}

function handleSubmit() {
  saved.value = true
  setTimeout(() => router.push('/recommendations'), 500)
}
</script>

<template>
  <form class="space-y-5" @submit.prevent="handleSubmit">
    <div>
      <p class="inline-flex items-center gap-2 text-sm font-semibold text-blue-700">
        <UserRound class="h-4 w-4" />
        조건 입력
      </p>
      <h1 class="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">청약 추천 조건을 입력하세요</h1>
      <p class="mt-2 text-sm text-slate-500">추천, 자금 로드맵, AI 체크리스트에 사용할 기본 조건입니다.</p>
    </div>

    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="flex items-center gap-2 text-lg font-bold">
        <UserRound class="h-5 w-5 text-blue-700" />
        기본 정보
      </h2>
      <div class="mt-5 grid gap-4 md:grid-cols-2">
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

    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="flex items-center gap-2 text-lg font-bold">
        <Banknote class="h-5 w-5 text-blue-700" />
        자금 조건
      </h2>
      <div class="mt-5 grid gap-4 md:grid-cols-2">
        <label v-for="field in [
          ['annual_income', '연소득'],
          ['asset', '보유 현금'],
          ['debt', '부채'],
          ['monthly_saving', '월 저축 가능액'],
        ]" :key="field[0]" class="block">
          <span class="text-sm font-medium text-slate-700">{{ field[1] }}</span>
          <input v-model.number="form[field[0] as keyof typeof form]" type="number" class="mt-2 w-full rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500" />
          <p class="mt-1 text-xs text-slate-500">{{ formatMoney(Number(form[field[0] as keyof typeof form])) }}</p>
        </label>
      </div>
    </section>

    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="flex items-center gap-2 text-lg font-bold">
        <Home class="h-5 w-5 text-blue-700" />
        청약 조건
      </h2>
      <div class="mt-5 grid gap-4 md:grid-cols-2">
        <label class="block">
          <span class="text-sm font-medium text-slate-700">무주택 여부</span>
          <select v-model="form.is_homeless" class="mt-2 w-full rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500">
            <option :value="true">무주택</option>
            <option :value="false">주택 보유</option>
          </select>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-slate-700">청약통장 가입기간</span>
          <input v-model.number="form.subscription_months" type="number" class="mt-2 w-full rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500" />
          <p class="mt-1 text-xs text-slate-500">{{ form.subscription_months }}개월</p>
        </label>
      </div>

      <div class="mt-5">
        <p class="flex items-center gap-2 text-sm font-medium text-slate-700">
          <BadgeCheck class="h-4 w-4" />
          특별 조건
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

    <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
      <h2 class="flex items-center gap-2 text-lg font-bold">
        <MapPinned class="h-5 w-5 text-blue-700" />
        선호 조건
      </h2>
      <div class="mt-5">
        <p class="text-sm font-medium text-slate-700">선호 지역</p>
        <div class="mt-3 flex flex-wrap gap-2">
          <button
            v-for="region in regionOptions"
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

      <div class="mt-5">
        <p class="text-sm font-medium text-slate-700">공급 유형</p>
        <div class="mt-3 flex flex-wrap gap-2">
          <button
            v-for="type in supplyTypeOptions"
            :key="type"
            type="button"
            class="rounded-lg px-4 py-2 text-sm font-bold transition"
            :class="form.preferred_supply_types.includes(type) ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
            @click="toggleArrayValue(form.preferred_supply_types, type)"
          >
            {{ type }}
          </button>
        </div>
      </div>
    </section>

    <div class="sticky bottom-20 flex justify-end gap-3 lg:bottom-5">
      <p v-if="saved" class="rounded-lg bg-green-50 px-4 py-3 text-sm font-bold text-green-700">
        저장 완료
      </p>
      <button type="submit" class="rounded-lg bg-blue-600 px-6 py-3 text-sm font-bold text-white shadow-sm hover:bg-blue-700">
        조건 저장하고 추천 보기
      </button>
    </div>
  </form>
</template>
