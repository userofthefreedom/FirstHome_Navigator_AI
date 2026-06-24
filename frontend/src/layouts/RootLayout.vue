<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router';
import { Bookmark, Bot, Building2, ChevronDown, ChevronRight, Home, Landmark, LineChart, LogOut, MapPinned, MessageSquareText, Moon, PiggyBank, Search, Sun, UserCheck, UserRound, WalletCards } from 'lucide-vue-next';
import FloatingCoachChat from '../components/FloatingCoachChat.vue';
import { fetchHousingRecommendations } from '../api/firsthome';
import { useAuthStore } from '../stores/authStore';
import { useProfileStore } from '../stores/profileStore';
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
const financeOpen = ref(route.path.startsWith('/finance'));
const theme = ref(localStorage.getItem('firsthome-theme') === 'light' ? 'light' : 'dark');
const displayName = computed(() => {
    if (profileStore.profile.name)
        return profileStore.profile.name;
    if (authStore.user.is_authenticated && authStore.user.username)
        return authStore.user.username;
    return '게스트';
});
const preferredRegionLabel = computed(() => {
    const regions = (profileStore.profile.preferred_regions ?? []).filter(Boolean);
    if (!regions.length)
        return '지역 확인 중';
    return regions.length === 1 ? regions[0] : `${regions[0]} 등`;
});
const themeIcon = computed(() => (theme.value === 'dark' ? Moon : Sun));
const themeLabel = computed(() => (theme.value === 'dark' ? '다크 모드' : '라이트 모드'));
const nextThemeLabel = computed(() => (theme.value === 'dark' ? '라이트 모드로 전환' : '다크 모드로 전환'));
const menus = [
    { label: '대시보드', shortLabel: '홈', path: '/', icon: Home },
    { label: '조건 입력', shortLabel: '조건', path: '/profile', icon: UserRound },
    { label: '추천 청약', shortLabel: '추천', path: '/recommendations', icon: Building2 },
    { label: '청약 지도', shortLabel: '지도', path: '/map', icon: MapPinned },
    { label: '자금 로드맵', shortLabel: '자금', path: '/funding', to: currentSelectionRoute('/funding'), icon: WalletCards },
    { label: 'AI 코치', shortLabel: '코치', path: '/ai-coach', to: currentSelectionRoute('/ai-coach'), icon: Bot },
    {
        label: '금융 광장',
        shortLabel: '금융',
        path: '/finance',
        icon: Landmark,
        children: [
            { label: '금융상품', shortLabel: '상품', path: '/finance/products', icon: PiggyBank },
            { label: '경제 NOW', shortLabel: 'NOW', path: '/finance/economy-now', icon: LineChart },
            { label: '청약 아고라', shortLabel: '아고라', path: '/finance/agora', icon: MessageSquareText },
        ],
    },
    { label: 'MY PAGE', shortLabel: 'MY', path: '/my-page', icon: Bookmark },
];
const searchResults = computed(() => buildGlobalSearchResults({
    query: searchQuery.value,
    recommendations: searchRecommendations.value,
    selection: readCurrentSelection(),
}));
function menuTo(menu) {
    if (menu.children)
        return menu.children[0].path;
    if (menu.path === '/funding')
        return currentSelectionRoute('/funding');
    if (menu.path === '/ai-coach')
        return currentSelectionRoute('/ai-coach');
    return menu.path;
}
function toggleFinanceMenu() {
    financeOpen.value = !financeOpen.value;
}
function applyTheme(value) {
    document.documentElement.dataset.theme = value;
    document.documentElement.style.colorScheme = value;
}
function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark';
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
watch(() => route.path, (path) => {
    if (path.startsWith('/finance'))
        financeOpen.value = true;
});
watch(theme, (value) => {
    localStorage.setItem('firsthome-theme', value);
    applyTheme(value);
}, { immediate: true });
onBeforeUnmount(() => {
    document.removeEventListener('pointerdown', handleDocumentPointer);
});
</script>

<template>
  <div class="min-h-screen overflow-x-hidden bg-[#f5f7fb] text-slate-950">
    <aside class="hidden bg-slate-950 text-white lg:fixed lg:inset-y-0 lg:left-0 lg:z-40 lg:block lg:w-[260px]">
      <div class="flex h-screen flex-col lg:relative lg:after:absolute lg:after:bottom-0 lg:after:right-0 lg:after:top-0 lg:after:w-px lg:after:bg-white/10">
        <div class="flex h-16 items-center border-b border-white/10 px-6">
          <RouterLink to="/" class="flex min-w-0 items-center gap-3 rounded-lg transition hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-blue-300">
            <div class="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500 text-white shadow-lg shadow-blue-500/25">
              <Home class="h-5 w-5" />
            </div>
            <div>
              <p class="text-lg font-semibold text-white">청약 네비</p>
              <p class="text-xs text-slate-400">첫 집 준비 내비게이터</p>
            </div>
          </RouterLink>
        </div>

        <nav class="flex-1 space-y-1 px-3 py-4">
          <template v-for="menu in menus" :key="menu.path">
            <div v-if="menu.children">
              <button
                type="button"
                class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition"
                :class="isActive(menu.path) ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/20' : 'text-slate-300 hover:bg-white/10 hover:text-white'"
                @click="toggleFinanceMenu"
              >
                <component :is="menu.icon" class="h-5 w-5" />
                <span class="flex-1 text-left">{{ menu.label }}</span>
                <ChevronDown v-if="financeOpen" class="h-4 w-4" />
                <ChevronRight v-else class="h-4 w-4" />
              </button>
              <div v-if="financeOpen" class="mt-1 space-y-1 pl-5">
                <RouterLink
                  v-for="child in menu.children"
                  :key="child.path"
                  :to="child.path"
                  class="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition"
                  :class="isActive(child.path) ? 'bg-white/12 text-white' : 'text-slate-400 hover:bg-white/10 hover:text-white'"
                >
                  <component :is="child.icon" class="h-4 w-4" />
                  {{ child.label }}
                </RouterLink>
              </div>
            </div>
            <RouterLink
              v-else
              :to="menuTo(menu)"
              class="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition"
              :class="isActive(menu.path) ? 'bg-blue-500 text-white shadow-lg shadow-blue-500/20' : 'text-slate-300 hover:bg-white/10 hover:text-white'"
            >
              <component :is="menu.icon" class="h-5 w-5" />
              {{ menu.label }}
            </RouterLink>
          </template>
        </nav>

        <div class="border-t border-white/10 px-3 py-4">
          <button
            type="button"
            class="flex w-full items-center gap-3 rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-sm font-bold text-slate-200 transition hover:border-blue-300/50 hover:bg-white/10 hover:text-white"
            :title="nextThemeLabel"
            @click="toggleTheme"
          >
            <component :is="themeIcon" class="h-5 w-5" />
            <span class="flex-1 text-left">{{ themeLabel }}</span>
            <span class="rounded-md bg-white/10 px-2 py-1 text-[11px] font-black">{{ theme === 'dark' ? 'Dark' : 'Light' }}</span>
          </button>
        </div>
      </div>
    </aside>

    <main class="flex min-h-screen min-w-0 flex-col lg:pl-[260px]">
      <header class="sticky top-0 z-30 h-16 border-b border-slate-200 bg-slate-950">
        <div class="flex h-full items-center gap-3 px-4 sm:px-6">
          <RouterLink to="/" class="flex items-center gap-2 rounded-lg text-white transition hover:opacity-90 focus:outline-none focus:ring-2 focus:ring-blue-300 lg:hidden">
            <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white shadow-lg shadow-blue-600/20">
              <Home class="h-4 w-4" />
            </div>
            <span class="font-semibold">청약 네비</span>
          </RouterLink>

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
            <RouterLink
              to="/profile"
              class="account-state-card hidden h-10 min-w-0 items-center gap-2 rounded-full border px-2.5 py-0 transition sm:flex"
              :class="authStore.user.is_authenticated ? 'account-state-card-auth max-w-[250px]' : 'account-state-card-guest max-w-[250px]'"
            >
              <div
                class="account-state-icon flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-white"
                :class="authStore.user.is_authenticated ? 'account-state-icon-auth' : 'account-state-icon-guest'"
              >
                <component :is="authStore.user.is_authenticated ? UserCheck : UserRound" class="h-3.5 w-3.5" />
              </div>
              <div class="min-w-0 leading-tight">
                <div class="flex min-w-0 items-center gap-2">
                  <p class="truncate text-[13px] font-bold">{{ displayName }}</p>
                  <span
                    class="account-state-badge shrink-0 rounded-full border px-1.5 py-0.5 text-[10px] font-black leading-none"
                    :class="authStore.user.is_authenticated ? 'account-state-badge-auth' : 'account-state-badge-guest'"
                  >
                    {{ authStore.user.is_authenticated ? '회원' : '비회원' }}
                  </span>
                  <span class="account-region-badge truncate text-[10px] font-bold leading-none">
                    {{ preferredRegionLabel }}
                  </span>
                </div>
              </div>
            </RouterLink>

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

    <nav class="fixed inset-x-0 bottom-0 z-40 grid grid-cols-8 border-t border-slate-200 bg-white lg:hidden">
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
