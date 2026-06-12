<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router';
import { Bookmark, Bot, Building2, ChevronRight, Home, LogOut, MapPinned, Search, UserRound, WalletCards } from 'lucide-vue-next';
import FloatingCoachChat from '../components/FloatingCoachChat.vue';
import { fetchHousingRecommendations } from '../api/firsthome';
import { useAuthStore } from '../stores/authStore';
import { useProfileStore } from '../stores/profileStore';
import { formatMoney } from '../utils/format';
import { buildGlobalSearchResults } from '../utils/globalSearch';
import { clearCurrentSelection, currentSelectionRoute, readCurrentSelection, syncCurrentSelectionWithAccount } from '../utils/selectionState';
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const profileStore = useProfileStore();
const searchBox = ref(null);
const searchQuery = ref('');
const searchOpen = ref(false);
const searchLoading = ref(false);
const searchError = ref('');
const searchRecommendations = ref([]);
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
    { label: '자금 로드맵', shortLabel: '자금', path: '/funding', to: currentSelectionRoute('/funding'), icon: WalletCards },
    { label: 'AI 코치', shortLabel: '코치', path: '/ai-coach', to: currentSelectionRoute('/ai-coach'), icon: Bot },
    { label: '관심목록', shortLabel: '관심', path: '/favorites', icon: Bookmark },
];
const searchResults = computed(() => buildGlobalSearchResults({
    query: searchQuery.value,
    recommendations: searchRecommendations.value,
    selection: readCurrentSelection(),
}));
function menuTo(menu) {
    if (menu.path === '/funding')
        return currentSelectionRoute('/funding');
    if (menu.path === '/ai-coach')
        return currentSelectionRoute('/ai-coach');
    return menu.path;
}
function isActive(path) {
    if (path === '/')
        return route.path === '/';
    return route.path.startsWith(path);
}
async function handleLogout() {
    await authStore.logout();
    profileStore.resetProfile();
    clearCurrentSelection();
    await router.push('/');
}
async function loadSearchRecommendations() {
    if (searchRecommendations.value.length || searchLoading.value)
        return;
    searchLoading.value = true;
    searchError.value = '';
    try {
        searchRecommendations.value = await fetchHousingRecommendations();
    }
    catch {
        searchError.value = '검색 후보를 불러오지 못했습니다.';
    }
    finally {
        searchLoading.value = false;
    }
}
function openSearch() {
    searchOpen.value = true;
    void loadSearchRecommendations();
}
function closeSearch() {
    searchOpen.value = false;
}
function handleSearchInput() {
    searchOpen.value = true;
    void loadSearchRecommendations();
}
async function goSearchResult(result) {
    if (!result?.route)
        return;
    closeSearch();
    searchQuery.value = '';
    await router.push(result.route);
}
async function handleSearchKeydown(event) {
    if (event.key === 'Escape') {
        closeSearch();
        return;
    }
    if (event.key === 'Enter' && searchResults.value.length) {
        event.preventDefault();
        await goSearchResult(searchResults.value[0]);
    }
}
function handleDocumentPointer(event) {
    if (searchBox.value && !searchBox.value.contains(event.target))
        closeSearch();
}
onMounted(async () => {
    document.addEventListener('pointerdown', handleDocumentPointer);
    let session = null;
    if (!authStore.loaded) {
        session = await authStore.hydrateAuth();
        if (session?.profile) {
            profileStore.setLocalProfile(session.profile);
            profileStore.loaded = true;
        }
    }
    if (!profileStore.loaded) {
        await profileStore.hydrateProfile();
    }
    await syncCurrentSelectionWithAccount(session?.account_state);
});
onBeforeUnmount(() => {
    document.removeEventListener('pointerdown', handleDocumentPointer);
});
</script>

<template>
  <div class="min-h-screen overflow-x-hidden bg-[#f5f7fb] text-slate-950 lg:grid lg:grid-cols-[260px_1fr]">
    <aside class="hidden bg-slate-950 text-white lg:block">
      <div class="sticky top-0 flex h-screen flex-col lg:relative lg:after:absolute lg:after:bottom-0 lg:after:right-0 lg:after:top-16 lg:after:w-px lg:after:bg-white/10">
        <div class="flex h-16 items-center border-b border-white/10 px-6">
          <div class="flex items-center gap-3">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500 text-white shadow-lg shadow-blue-500/25">
              <Home class="h-5 w-5" />
            </div>
            <div>
              <p class="text-lg font-semibold text-white">FirstHome</p>
              <p class="text-xs text-slate-400">Navigator AI</p>
            </div>
          </div>
        </div>

        <nav class="flex-1 space-y-1 px-3 py-4">
          <RouterLink
            v-for="menu in menus"
            :key="menu.path"
            :to="menuTo(menu)"
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
      <header class="sticky top-0 z-30 h-16 border-b border-slate-200 bg-slate-950">
        <div class="flex h-full items-center gap-3 px-4 sm:px-6">
          <div class="flex items-center gap-2 lg:hidden">
            <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white shadow-lg shadow-blue-600/20">
              <Home class="h-4 w-4" />
            </div>
            <span class="font-semibold">FirstHome</span>
          </div>

          <div ref="searchBox" class="relative ml-auto hidden min-w-0 flex-1 md:block lg:ml-0">
            <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              v-model="searchQuery"
              class="h-10 w-full rounded-lg border border-slate-200 bg-slate-50/80 pl-10 pr-4 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
              placeholder="청약명, 지역, 화면 검색"
              type="search"
              @focus="openSearch"
              @input="handleSearchInput"
              @keydown="handleSearchKeydown"
            />
            <div
              v-if="searchOpen && (searchQuery.trim() || searchLoading || searchError)"
              class="absolute left-0 right-0 top-12 z-50 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-2xl shadow-slate-950/15"
            >
              <div v-if="searchLoading" class="px-4 py-3 text-sm font-semibold text-slate-500">
                검색 후보를 불러오는 중입니다.
              </div>
              <div v-else-if="searchError" class="px-4 py-3 text-sm font-semibold text-amber-700">
                {{ searchError }}
              </div>
              <div v-else-if="searchResults.length" class="max-h-[420px] overflow-y-auto p-2">
                <button
                  v-for="result in searchResults"
                  :key="result.id"
                  type="button"
                  class="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left transition hover:bg-slate-50"
                  @click="goSearchResult(result)"
                >
                  <span class="shrink-0 rounded-md bg-blue-50 px-2 py-1 text-xs font-bold text-blue-700">{{ result.type }}</span>
                  <span class="min-w-0 flex-1">
                    <span class="block truncate text-sm font-bold text-slate-950">{{ result.title }}</span>
                    <span class="mt-0.5 block truncate text-xs font-semibold text-slate-500">{{ result.description }}</span>
                  </span>
                  <span v-if="result.meta" class="hidden shrink-0 text-xs font-bold text-slate-400 xl:inline">{{ result.meta }}</span>
                  <ChevronRight class="h-4 w-4 shrink-0 text-slate-400" />
                </button>
              </div>
              <div v-else class="px-4 py-3 text-sm font-semibold text-slate-500">
                검색 결과가 없습니다. 공고명, 지역, 지구명, 화면 이름으로 검색해보세요.
              </div>
            </div>
          </div>

          <div class="ml-auto flex items-center gap-2">
            <div
              class="hidden min-w-0 items-center gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2 shadow-sm sm:flex"
              :class="authStore.user.is_authenticated ? 'max-w-[300px]' : 'max-w-[360px]'"
            >
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

    <FloatingCoachChat />

    <nav class="fixed inset-x-0 bottom-0 z-40 grid grid-cols-7 border-t border-slate-200 bg-white lg:hidden">
      <RouterLink
        v-for="menu in menus"
        :key="menu.path"
        :to="menuTo(menu)"
        class="flex h-16 flex-col items-center justify-center gap-1 text-[10px] font-medium transition"
        :class="isActive(menu.path) ? 'text-blue-700' : 'text-slate-500'"
      >
        <component :is="menu.icon" class="h-5 w-5" />
        <span>{{ menu.shortLabel }}</span>
      </RouterLink>
    </nav>
  </div>
</template>
