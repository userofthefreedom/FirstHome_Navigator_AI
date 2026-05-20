<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { MapPin } from 'lucide-vue-next'
import { fetchNotices } from '../api/firsthome'
import type { Notice } from '../types/firsthome'

const notices = ref<Notice[]>([])

const regionCounts = computed(() => {
  return notices.value.reduce<Record<string, number>>((acc, notice) => {
    const region = notice.region || '전국'
    acc[region] = (acc[region] ?? 0) + 1
    return acc
  }, {})
})

const markers = computed(() => [
  { region: '서울', x: 49, y: 37, count: regionCounts.value['서울'] ?? 0 },
  { region: '인천', x: 39, y: 39, count: regionCounts.value['인천'] ?? 0 },
  { region: '경기 남부', x: 53, y: 48, count: regionCounts.value['경기 남부'] ?? regionCounts.value['경기'] ?? 0 },
  { region: '경기 북부', x: 51, y: 28, count: regionCounts.value['경기 북부'] ?? 0 },
  { region: '부산', x: 76, y: 76, count: regionCounts.value['부산'] ?? 0 },
])

onMounted(async () => {
  try {
    notices.value = await fetchNotices()
  } catch {
    notices.value = []
  }
})
</script>

<template>
  <div class="relative h-[calc(100vh-8rem)] min-h-[560px] overflow-hidden rounded-lg border border-slate-200 bg-slate-950 shadow-sm lg:h-[calc(100vh-5.5rem)]">
    <div class="absolute inset-0 bg-[radial-gradient(circle_at_50%_40%,rgba(64,215,186,0.18),transparent_34%),linear-gradient(135deg,#0b1117,#152331)]" />

    <svg class="absolute inset-0 h-full w-full" viewBox="0 0 1000 720" preserveAspectRatio="none" aria-hidden="true">
      <path d="M116 118 C240 70 338 90 438 152 C532 210 640 206 760 154 C862 110 940 126 990 180 L990 720 L0 720 L0 174 C28 148 68 132 116 118Z" fill="#162936" />
      <path d="M182 458 C270 344 384 294 498 330 C606 364 686 310 760 246 C838 178 924 190 1000 254 L1000 720 L114 720 C116 624 132 528 182 458Z" fill="#11242f" />
      <path d="M0 252 C118 226 230 254 324 340 C418 426 520 434 638 372 C770 304 884 324 1000 408" fill="none" stroke="#30515d" stroke-width="22" stroke-linecap="round" opacity="0.55" />
      <path d="M82 612 C214 520 308 482 422 502 C542 522 628 474 720 372 C794 290 874 248 1000 230" fill="none" stroke="#254653" stroke-width="12" stroke-linecap="round" opacity="0.7" />
      <path d="M192 80 C232 196 280 304 380 390 C488 484 560 564 612 720" fill="none" stroke="#3ee0b8" stroke-width="7" stroke-linecap="round" opacity="0.56" />
      <path d="M514 0 C500 114 506 232 558 330 C610 428 702 506 830 604" fill="none" stroke="#f5c86a" stroke-width="6" stroke-linecap="round" opacity="0.42" />
      <path d="M0 404 C118 388 224 394 310 430 C404 470 490 470 594 430 C734 376 850 380 1000 446" fill="none" stroke="#6f8090" stroke-width="5" stroke-dasharray="12 18" opacity="0.4" />
      <circle cx="490" cy="266" r="74" fill="#1f9f89" opacity="0.12" />
      <circle cx="760" cy="550" r="96" fill="#f59e0b" opacity="0.10" />
      <circle cx="390" cy="280" r="56" fill="#72f0d4" opacity="0.09" />
    </svg>

    <div class="absolute inset-0">
      <button
        v-for="marker in markers"
        :key="marker.region"
        type="button"
        class="absolute -translate-x-1/2 -translate-y-1/2 rounded-lg border border-white/15 bg-slate-950/85 px-3 py-2 text-left text-white shadow-lg backdrop-blur transition hover:bg-blue-600"
        :style="{ left: `${marker.x}%`, top: `${marker.y}%` }"
      >
        <span class="flex items-center gap-2 text-sm font-bold">
          <MapPin class="h-4 w-4 text-emerald-300" />
          {{ marker.region }}
        </span>
        <span class="mt-1 block text-xs text-slate-300">{{ marker.count }}건</span>
      </button>
    </div>
  </div>
</template>
