<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router';
import { Bell, Bookmark, Bot, Building2, CalendarClock, Home, LogOut, MapPinned, Search, UserRound, WalletCards, X } from 'lucide-vue-next';
import FloatingCoachChat from '../components/FloatingCoachChat.vue';
import { fetchFavorites, fetchNotices, fetchPolicies } from '../api/firsthome';
import { useAuthStore } from '../stores/authStore';
import { useProfileStore } from '../stores/profileStore';
import { formatMoney } from '../utils/format';
import { clearCurrentSelection, currentSelectionRoute, syncCurrentSelectionWithAccount } from '../utils/selectionState';
const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const profileStore = useProfileStore();
const searchText = ref('');
const searchOpen = ref(false);
const notificationOpen = ref(false);
const activeNotices = ref([]);
const activePolicies = ref([]);
const favorites = ref([]);
const headerError = ref('');
const searchBox = ref(null);
const notificationBox = ref(null);
const displayName = computed(() => {
    if (profileStore.profile.name)
        return profileStore.profile.name;
    if (authStore.user.is_authenticated && authStore.user.username)
        return authStore.user.username;
    return '게스트';
});
const profileStatus = computed(() => (authStore.user.is_authenticated ? '계정 저장 중' : '임시 저장 중'));
const isProfileReady = computed(() => {
    const profile = profileStore.profile;
    return Boolean(
        profile.name
        && profile.preferred_regions?.length
        && Number(profile.asset || 0) > 0
        && Number(profile.annual_income || 0) > 0,
    );
});
const searchResults = computed(() => {
    const keyword = searchText.value.trim().toLowerCase();
    if (!keyword)
        return [];
    const noticeResults = activeNotices.value
        .filter((notice) => [notice.title, notice.region, notice.district, notice.provider, notice.supply_type, notice.housing_type]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword)))
        .map((notice) => ({ type: 'notice', id: `notice-${notice.id}`, item: notice }));
    const policyResults = activePolicies.value
        .filter((policy) => [policy.name, policy.provider, policy.target, policy.policy_category, policy.benefit]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword)))
        .map((policy) => ({ type: 'policy', id: `policy-${policy.id}`, item: policy }));
    return [...noticeResults, ...policyResults].slice(0, 6);
});
const upcomingDeadlines = computed(() => activeNotices.value
    .map((notice) => ({ ...notice, daysLeft: daysUntil(notice.application_deadline) }))
    .filter((notice) => notice.daysLeft >= 0 && notice.daysLeft <= 7)
    .sort((a, b) => a.daysLeft - b.daysLeft || String(a.title).localeCompare(String(b.title), 'ko'))
    .slice(0, 5));
const savedNoticeCount = computed(() => favorites.value.filter((favorite) => favorite.favorite_type === 'notice').length);
const notifications = computed(() => {
    const items = [];
    if (!isProfileReady.value) {
        items.push({
            id: 'profile',
            tone: 'blue',
            icon: UserRound,
            title: '조건 입력을 마무리해 주세요',
            description: '자산, 소득, 희망 지역이 채워지면 추천 정확도가 올라갑니다.',
            to: '/profile',
        });
    }
    upcomingDeadlines.value.forEach((notice) => {
        items.push({
            id: `deadline-${notice.id}`,
            tone: notice.daysLeft <= 2 ? 'rose' : 'amber',
            icon: CalendarClock,
            title: notice.daysLeft === 0 ? '오늘 접수 마감' : `${notice.daysLeft}일 후 접수 마감`,
            description: notice.title,
            to: `/notices/${notice.id}`,
        });
    });
    if (savedNoticeCount.value > 0) {
        items.push({
            id: 'favorites',
            tone: 'emerald',
            icon: Bookmark,
            title: `관심 공고 ${savedNoticeCount.value}건 저장됨`,
            description: '저장한 후보를 관심목록에서 다시 비교할 수 있습니다.',
            to: '/favorites',
        });
    }
    if (headerError.value) {
        items.push({
            id: 'api-error',
            tone: 'amber',
            icon: Bell,
            title: '일부 알림을 불러오지 못했습니다',
            description: headerError.value,
            to: route.fullPath,
        });
    }
    return items;
});
const notificationCount = computed(() => notifications.value.length);
const menus = [
    { label: '대시보드', shortLabel: '홈', path: '/', icon: Home },
    { label: '조건 입력', shortLabel: '조건', path: '/profile', icon: UserRound },
    { label: '추천 청약', shortLabel: '추천', path: '/recommendations', icon: Building2 },
    { label: '청약 지도', shortLabel: '지도', path: '/map', icon: MapPinned },
    { label: '자금 로드맵', shortLabel: '자금', path: '/funding', to: currentSelectionRoute('/funding'), icon: WalletCards },
    { label: 'AI 코치', shortLabel: '코치', path: '/ai-coach', to: currentSelectionRoute('/ai-coach'), icon: Bot },
    { label: '관심목록', shortLabel: '관심', path: '/favorites', icon: Bookmark },
];
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
function parseDate(value) {
    const date = new Date(`${value}T00:00:00`);
    return Number.isNaN(date.getTime()) ? null : date;
}
function daysUntil(value) {
    const date = parseDate(value);
    if (!date)
        return Number.POSITIVE_INFINITY;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return Math.ceil((date.getTime() - today.getTime()) / 86400000);
}
function deadlineLabel(value) {
    const days = daysUntil(value);
    if (!Number.isFinite(days))
        return '마감일 확인 필요';
    if (days === 0)
        return '오늘 마감';
    if (days > 0)
        return `D-${days}`;
    return '마감';
}
function selectSearchResult(result) {
    if (result.type === 'policy') {
        searchText.value = result.item.name;
        searchOpen.value = false;
        void router.push('/funding');
        return;
    }
    searchText.value = result.item.title;
    searchOpen.value = false;
    void router.push(`/notices/${result.item.id}`);
}
function submitSearch() {
    const firstResult = searchResults.value[0];
    if (firstResult) {
        selectSearchResult(firstResult);
        return;
    }
    if (searchText.value.trim()) {
        searchOpen.value = true;
    }
}
function clearSearch() {
    searchText.value = '';
    searchOpen.value = false;
}
function openNotification(item) {
    notificationOpen.value = false;
    void router.push(item.to);
}
function handleDocumentClick(event) {
    const target = event.target;
    if (searchBox.value && !searchBox.value.contains(target))
        searchOpen.value = false;
    if (notificationBox.value && !notificationBox.value.contains(target))
        notificationOpen.value = false;
}
async function handleLogout() {
    await authStore.logout();
    profileStore.resetProfile();
    clearCurrentSelection();
    await router.push('/');
}
async function loadHeaderData() {
    headerError.value = '';
    const [noticeResult, policyResult, favoriteResult] = await Promise.allSettled([
        fetchNotices({ active: '1' }),
        fetchPolicies(),
        fetchFavorites(),
    ]);
    if (noticeResult.status === 'fulfilled') {
        activeNotices.value = noticeResult.value;
    }
    else {
        headerError.value = '공고 데이터를 확인할 수 없습니다.';
    }
    if (policyResult.status === 'fulfilled') {
        activePolicies.value = policyResult.value;
    }
    if (favoriteResult.status === 'fulfilled') {
        favorites.value = favoriteResult.value;
    }
}
onMounted(async () => {
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
    await loadHeaderData();
    document.addEventListener('click', handleDocumentClick);
});
onBeforeUnmount(() => {
    document.removeEventListener('click', handleDocumentClick);
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
      <header class="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div class="flex min-h-16 flex-wrap items-center gap-3 px-4 py-3 sm:px-6 lg:h-16 lg:flex-nowrap lg:py-0">
          <RouterLink to="/" class="flex min-w-0 items-center gap-2 lg:hidden">
            <div class="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-600 text-white shadow-lg shadow-blue-600/20">
              <Home class="h-4 w-4" />
            </div>
            <span class="hidden font-semibold sm:inline">FirstHome</span>
          </RouterLink>

          <form ref="searchBox" class="order-last relative w-full min-w-0 md:order-none md:flex-1 lg:ml-0" @submit.prevent="submitSearch">
            <Search class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              v-model="searchText"
              class="h-10 w-full rounded-lg border border-slate-200 bg-slate-50/80 pl-10 pr-10 text-sm outline-none transition focus:border-blue-500 focus:bg-white focus:ring-4 focus:ring-blue-100"
              placeholder="청약명, 지역, 정책 검색"
              type="search"
              @focus="searchOpen = Boolean(searchText.trim())"
              @input="searchOpen = Boolean(searchText.trim())"
            />
            <button
              v-if="searchText"
              type="button"
              class="absolute right-2 top-1/2 flex h-7 w-7 -translate-y-1/2 items-center justify-center rounded-md text-slate-400 transition hover:bg-slate-200 hover:text-slate-700"
              title="검색어 지우기"
              @click="clearSearch"
            >
              <X class="h-4 w-4" />
            </button>
            <div
              v-if="searchOpen"
              class="absolute left-0 right-0 top-[calc(100%+8px)] z-50 overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg"
            >
              <button
                v-for="result in searchResults"
                :key="result.id"
                type="button"
                class="flex w-full items-start gap-3 border-b border-slate-100 px-4 py-3 text-left transition last:border-b-0 hover:bg-slate-50"
                @click="selectSearchResult(result)"
              >
                <span class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-blue-50 text-blue-700">
                  <WalletCards v-if="result.type === 'policy'" class="h-4 w-4" />
                  <Building2 v-else class="h-4 w-4" />
                </span>
                <span class="min-w-0 flex-1">
                  <span class="line-clamp-1 text-sm font-bold text-slate-950">
                    {{ result.type === 'policy' ? result.item.name : result.item.title }}
                  </span>
                  <span class="mt-1 block truncate text-xs text-slate-500">
                    <template v-if="result.type === 'policy'">
                      {{ result.item.provider }} · {{ result.item.policy_category || result.item.target || '지원정책' }}
                    </template>
                    <template v-else>
                      {{ result.item.provider }} · {{ result.item.region }} {{ result.item.district }} · {{ deadlineLabel(result.item.application_deadline) }}
                    </template>
                  </span>
                </span>
              </button>
              <div v-if="searchResults.length === 0" class="px-4 py-4 text-sm font-semibold text-slate-500">
                검색 결과가 없습니다. 지역명이나 공고명을 다시 입력해 주세요.
              </div>
            </div>
          </form>

          <div class="ml-auto flex items-center gap-2">
            <div ref="notificationBox" class="relative">
            <button
              class="relative flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 bg-white text-slate-600 shadow-sm transition hover:bg-slate-50"
              type="button"
              :aria-expanded="notificationOpen"
              aria-label="알림"
              @click.stop="notificationOpen = !notificationOpen"
            >
              <Bell class="h-4 w-4" />
              <span v-if="notificationCount" class="absolute right-1.5 top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold leading-none text-white">
                {{ notificationCount > 9 ? '9+' : notificationCount }}
              </span>
            </button>
            <div
              v-if="notificationOpen"
              class="absolute right-0 top-[calc(100%+8px)] z-50 w-[min(92vw,380px)] overflow-hidden rounded-lg border border-slate-200 bg-white shadow-lg"
            >
              <div class="flex items-center justify-between border-b border-slate-100 px-4 py-3">
                <p class="text-sm font-bold text-slate-950">알림</p>
                <span class="text-xs font-semibold text-slate-500">{{ notificationCount }}건</span>
              </div>
              <div v-if="notificationCount" class="max-h-[420px] overflow-y-auto">
                <button
                  v-for="item in notifications"
                  :key="item.id"
                  type="button"
                  class="flex w-full items-start gap-3 border-b border-slate-100 px-4 py-3 text-left transition last:border-b-0 hover:bg-slate-50"
                  @click="openNotification(item)"
                >
                  <span
                    class="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md"
                    :class="{
                      'bg-blue-50 text-blue-700': item.tone === 'blue',
                      'bg-amber-50 text-amber-700': item.tone === 'amber',
                      'bg-emerald-50 text-emerald-700': item.tone === 'emerald',
                      'bg-rose-500 text-white': item.tone === 'rose',
                    }"
                  >
                    <component :is="item.icon" class="h-4 w-4" />
                  </span>
                  <span class="min-w-0 flex-1">
                    <span class="block text-sm font-bold text-slate-950">{{ item.title }}</span>
                    <span class="mt-1 line-clamp-2 text-xs leading-5 text-slate-500">{{ item.description }}</span>
                  </span>
                </button>
              </div>
              <div v-else class="px-4 py-5 text-sm font-semibold text-slate-500">
                지금 확인할 새 알림이 없습니다.
              </div>
            </div>
            </div>

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
