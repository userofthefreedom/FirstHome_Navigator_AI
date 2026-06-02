<script setup>
import { computed, onMounted } from 'vue';
import { RouterLink, RouterView, useRoute } from 'vue-router';
import { Bell, Bookmark, Bot, Building2, Home, LogOut, MapPinned, Search, UserRound, WalletCards } from 'lucide-vue-next';
import FloatingCoachChat from '../components/FloatingCoachChat.vue';
import { useAuthStore } from '../stores/authStore';
import { useProfileStore } from '../stores/profileStore';
import { formatMoney } from '../utils/format';
const route = useRoute();
const authStore = useAuthStore();
const profileStore = useProfileStore();
const displayName = computed(() => {
    if (profileStore.profile.name)
        return profileStore.profile.name;
    if (authStore.user.is_authenticated && authStore.user.username)
        return authStore.user.username;
    return '게스트';
});
const profileStatus = computed(() => (authStore.user.is_authenticated ? '계정 저장 중' : '임시 저장 중'));
const menus = [
    { label: '대시보드', shortLabel: '홈', path: '/', icon: Home },
    { label: '조건 입력', shortLabel: '조건', path: '/profile', icon: UserRound },
    { label: '추천 청약', shortLabel: '추천', path: '/recommendations', icon: Building2 },
    { label: '청약 지도', shortLabel: '지도', path: '/map', icon: MapPinned },
    { label: '자금 로드맵', shortLabel: '자금', path: '/funding', icon: WalletCards },
    { label: 'AI 코치', shortLabel: '코치', path: '/ai-coach', icon: Bot },
    { label: '관심목록', shortLabel: '관심', path: '/favorites', icon: Bookmark },
];
function isActive(path) {
    if (path === '/')
        return route.path === '/';
    return route.path.startsWith(path);
}
async function handleLogout() {
    await authStore.logout();
    profileStore.loaded = false;
    await profileStore.hydrateProfile();
}
onMounted(async () => {
    if (!authStore.loaded) {
        const session = await authStore.hydrateAuth();
        if (session?.profile) {
            profileStore.setLocalProfile(session.profile);
            profileStore.loaded = true;
            return;
        }
    }
    if (!profileStore.loaded) {
        await profileStore.hydrateProfile();
    }
});
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

          <div class="relative ml-auto hidden min-w-0 flex-1 md:block lg:ml-0">
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

            <div class="hidden min-w-0 max-w-[300px] items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm sm:flex">
              <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-slate-900 text-white">
                <UserRound class="h-4 w-4" />
              </div>
              <div class="min-w-0">
                <div class="flex min-w-0 items-center gap-2">
                  <p class="truncate text-sm font-semibold">{{ displayName }}</p>
                  <span class="shrink-0 rounded-md bg-emerald-50 px-2 py-0.5 text-xs font-bold text-emerald-700">
                    {{ formatMoney(profileStore.profile.asset) }}
                  </span>
                </div>
                <p class="truncate text-xs text-slate-500">
                  {{ profileStatus }} · {{ profileStore.profile.preferred_regions.join(', ') || '희망 지역 확인 중' }}
                </p>
              </div>
            </div>

            <button
              v-if="authStore.user.is_authenticated"
              type="button"
              class="hidden h-10 items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold text-slate-600 shadow-sm transition hover:bg-slate-50 sm:inline-flex"
              title="로그아웃"
              @click="handleLogout"
            >
              <LogOut class="h-4 w-4" />
              로그아웃
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

      <section class="mx-auto w-full max-w-[1680px] flex-1 p-4 pb-24 sm:p-6 lg:pb-6">
        <RouterView />
      </section>
    </main>

    <FloatingCoachChat v-if="route.path === '/'" />

    <nav class="fixed inset-x-0 bottom-0 z-40 grid grid-cols-7 border-t border-slate-200 bg-white lg:hidden">
      <RouterLink
        v-for="menu in menus"
        :key="menu.path"
        :to="menu.path"
        class="flex h-16 flex-col items-center justify-center gap-1 text-[10px] font-medium transition"
        :class="isActive(menu.path) ? 'text-blue-700' : 'text-slate-500'"
      >
        <component :is="menu.icon" class="h-5 w-5" />
        <span>{{ menu.shortLabel }}</span>
      </RouterLink>
    </nav>
  </div>
</template>
