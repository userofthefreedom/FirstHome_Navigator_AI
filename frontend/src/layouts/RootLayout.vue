<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { Bell, Bookmark, Bot, Building2, Home, LogOut, Search, UserRound, WalletCards } from 'lucide-vue-next'
import { useAuthStore } from '../stores/authStore'
import { useProfileStore } from '../stores/profileStore'
import { formatMoney } from '../utils/format'

const route = useRoute()
const authStore = useAuthStore()
const profileStore = useProfileStore()

const menus = [
  { label: '대시보드', path: '/', icon: Home },
  { label: '조건 입력', path: '/profile', icon: UserRound },
  { label: '추천 청약', path: '/recommendations', icon: Building2 },
  { label: '자금 로드맵', path: '/funding', icon: WalletCards },
  { label: 'AI 코치', path: '/ai-coach', icon: Bot },
  { label: '관심목록', path: '/favorites', icon: Bookmark },
]

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

async function handleLogout() {
  await authStore.logout()
  profileStore.loaded = false
  await profileStore.hydrateProfile()
}

onMounted(() => {
  if (!authStore.loaded) {
    void authStore.hydrateAuth()
  }
  if (!profileStore.loaded) {
    void profileStore.hydrateProfile()
  }
})
</script>

<template>
  <div class="min-h-screen overflow-x-hidden bg-[#f5f7fb] text-slate-950 lg:grid lg:grid-cols-[260px_1fr]">
    <aside class="hidden bg-slate-950 text-white lg:block">
      <div class="sticky top-0 flex h-screen flex-col">
        <div class="border-b border-white/10 px-6 py-5">
          <RouterLink to="/" class="flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500 text-white shadow-lg shadow-blue-500/25">
              <Home class="h-5 w-5" />
            </div>
            <div>
              <p class="text-lg font-semibold text-white">FirstHome</p>
              <p class="text-xs text-slate-400">Navigator AI</p>
            </div>
          </RouterLink>
        </div>

        <nav class="flex-1 space-y-1 px-3 py-4">
          <RouterLink
            v-for="menu in menus"
            :key="menu.path"
            :to="menu.path"
            class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition"
            :class="isActive(menu.path) ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/20' : 'text-slate-300 hover:bg-white/10 hover:text-white'"
          >
            <component :is="menu.icon" class="h-5 w-5" />
            {{ menu.label }}
          </RouterLink>
        </nav>

        <div class="border-t border-white/10 p-4">
          <div class="rounded-lg border border-white/10 bg-white/[0.06] p-3">
            <p class="text-xs font-medium text-slate-400">현재 프로필</p>
            <div class="mt-3 flex items-center justify-between gap-3">
              <div class="min-w-0">
                <p class="truncate font-semibold text-white">{{ profileStore.profile.name || '프로필 로딩 중' }}</p>
                <p class="truncate text-xs text-slate-400">{{ profileStore.profile.preferred_regions.join(', ') || '희망 지역 확인 중' }}</p>
              </div>
              <span class="shrink-0 rounded-md bg-emerald-400/15 px-2 py-1 text-xs font-semibold text-emerald-300">
                {{ formatMoney(profileStore.profile.asset) }}
              </span>
            </div>

            <button
              v-if="authStore.user.is_authenticated"
              type="button"
              class="mt-3 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/10 text-sm font-bold text-white transition hover:bg-white/15"
              @click="handleLogout"
            >
              <LogOut class="h-4 w-4" />
              로그아웃
            </button>
            <RouterLink
              v-else
              to="/auth"
              class="mt-3 inline-flex h-9 w-full items-center justify-center gap-2 rounded-lg bg-blue-500 text-sm font-bold text-white transition hover:bg-blue-400"
            >
              <UserRound class="h-4 w-4" />
              로그인
            </RouterLink>
          </div>
        </div>
      </div>
    </aside>

    <main class="flex min-h-screen min-w-0 flex-col">
      <header class="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div class="flex h-16 items-center gap-3 px-4 sm:px-6">
          <RouterLink to="/" class="flex items-center gap-2 lg:hidden">
            <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white shadow-lg shadow-blue-600/20">
              <Home class="h-4 w-4" />
            </div>
            <span class="font-semibold">FirstHome</span>
          </RouterLink>

          <div class="relative ml-auto hidden w-full max-w-lg md:block lg:ml-0">
            <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              class="h-10 w-full rounded-lg border border-slate-200 bg-slate-50/80 pl-10 pr-4 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
              placeholder="청약명, 지역, 정책 검색"
              type="search"
            />
          </div>

          <div class="ml-auto flex items-center gap-2">
            <button class="relative flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50" type="button">
              <Bell class="h-4 w-4" />
              <span class="absolute right-2 top-2 h-2 w-2 rounded-full bg-rose-500" />
            </button>

            <div class="hidden items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm sm:flex">
              <div class="flex h-7 w-7 items-center justify-center rounded-md bg-slate-900 text-xs font-semibold text-white">
                AI
              </div>
              <div>
                <p class="text-sm font-semibold">{{ authStore.user.is_authenticated ? authStore.user.username : profileStore.profile.name || '게스트' }}</p>
                <p class="text-xs text-slate-500">{{ authStore.user.is_authenticated ? '계정 저장 중' : '임시 저장 중' }}</p>
              </div>
            </div>

            <button
              v-if="authStore.user.is_authenticated"
              type="button"
              class="hidden h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-slate-600 shadow-sm transition hover:bg-slate-50 sm:inline-flex"
              title="로그아웃"
              @click="handleLogout"
            >
              <LogOut class="h-4 w-4" />
            </button>
            <RouterLink
              v-else
              to="/auth"
              class="hidden h-10 items-center justify-center rounded-lg bg-blue-600 px-3 text-sm font-bold text-white shadow-sm transition hover:bg-blue-700 sm:inline-flex"
            >
              로그인
            </RouterLink>
          </div>
        </div>
      </header>

      <section class="mx-auto w-full max-w-7xl flex-1 p-4 pb-24 sm:p-6 lg:pb-6">
        <RouterView />
      </section>
    </main>

    <nav class="fixed inset-x-0 bottom-0 z-40 grid grid-cols-6 border-t border-slate-200 bg-white lg:hidden">
      <RouterLink
        v-for="menu in menus"
        :key="menu.path"
        :to="menu.path"
        class="flex h-16 flex-col items-center justify-center gap-1 text-[11px] font-medium transition"
        :class="isActive(menu.path) ? 'text-blue-700' : 'text-slate-500'"
      >
        <component :is="menu.icon" class="h-5 w-5" />
        <span>{{ menu.label }}</span>
      </RouterLink>
    </nav>
  </div>
</template>
