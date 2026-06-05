<script setup>
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { LogIn, LogOut, UserPlus } from 'lucide-vue-next';
import { useAuthStore } from '../stores/authStore';
import { useProfileStore } from '../stores/profileStore';
import { clearCurrentSelection, syncCurrentSelectionWithAccount } from '../utils/selectionState';
const router = useRouter();
const authStore = useAuthStore();
const profileStore = useProfileStore();
const mode = ref('login');
const loading = ref(false);
const error = ref('');
const form = reactive({
    username: '',
    email: '',
    password: '',
});
async function submit() {
    loading.value = true;
    error.value = '';
    try {
        const session = mode.value === 'login'
            ? await authStore.login({ username: form.username, password: form.password })
            : await authStore.register({ username: form.username, email: form.email, password: form.password });
        if (session.profile) {
            profileStore.setLocalProfile(session.profile);
            profileStore.loaded = true;
        }
        else {
            profileStore.loaded = false;
            await profileStore.hydrateProfile();
        }
        await syncCurrentSelectionWithAccount(session.account_state);
        await router.push('/profile');
    }
    catch (exc) {
        error.value = exc?.response?.data?.detail ?? '계정 처리 중 오류가 발생했습니다.';
    }
    finally {
        loading.value = false;
    }
}
async function logout() {
    loading.value = true;
    try {
        await authStore.logout();
        profileStore.resetProfile();
        clearCurrentSelection();
        await router.push('/');
    }
    finally {
        loading.value = false;
    }
}
</script>

<template>
  <div class="mx-auto max-w-xl space-y-5">
    <template v-if="authStore.user.is_authenticated">
      <div>
        <p class="text-sm font-semibold text-blue-700">계정</p>
        <h1 class="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">로그인됨</h1>
        <p class="mt-2 text-sm text-slate-500">현재 계정 기준으로 조건과 관심목록이 저장됩니다.</p>
      </div>

      <section class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <p class="text-sm font-semibold text-slate-500">아이디</p>
        <p class="mt-1 text-xl font-bold text-slate-950">{{ authStore.user.username }}</p>
        <button
          type="button"
          :disabled="loading"
          class="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg border border-slate-200 bg-white text-sm font-bold text-slate-700 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60"
          @click="logout"
        >
          <LogOut class="h-4 w-4" />
          로그아웃
        </button>
      </section>
    </template>

    <template v-else>
      <div>
        <p class="text-sm font-semibold text-blue-700">계정</p>
        <h1 class="mt-1 text-2xl font-bold text-slate-950 sm:text-3xl">
          {{ mode === 'login' ? '로그인' : '회원가입' }}
        </h1>
        <p class="mt-2 text-sm text-slate-500">
          로그인하면 조건 입력값과 관심 청약·상품·정책이 계정 기준으로 저장됩니다.
        </p>
      </div>

      <form class="rounded-lg border border-slate-200 bg-white p-5 shadow-sm" @submit.prevent="submit">
        <div class="grid gap-4">
          <label class="block">
            <span class="text-sm font-medium text-slate-700">아이디</span>
            <input v-model.trim="form.username" required type="text" autocomplete="username" class="mt-2 w-full rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500" />
          </label>

          <label v-if="mode === 'register'" class="block">
            <span class="text-sm font-medium text-slate-700">이메일</span>
            <input v-model.trim="form.email" type="email" autocomplete="email" class="mt-2 w-full rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500" />
          </label>

          <label class="block">
            <span class="text-sm font-medium text-slate-700">비밀번호</span>
            <input v-model="form.password" required minlength="8" type="password" autocomplete="current-password" class="mt-2 w-full rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-blue-500" />
            <p v-if="mode === 'register'" class="mt-1 text-xs text-slate-500">8자 이상으로 입력하세요.</p>
          </label>
        </div>

        <p v-if="error" class="mt-4 rounded-lg border border-amber-100 bg-amber-50 p-3 text-sm font-semibold text-amber-800">
          {{ error }}
        </p>

        <button type="submit" :disabled="loading" class="mt-5 inline-flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 text-sm font-bold text-white transition hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60">
          <component :is="mode === 'login' ? LogIn : UserPlus" class="h-4 w-4" />
          {{ loading ? '처리 중' : mode === 'login' ? '로그인' : '회원가입' }}
        </button>

        <button type="button" class="mt-3 w-full rounded-lg border border-slate-200 px-4 py-2 text-sm font-bold text-slate-700" @click="mode = mode === 'login' ? 'register' : 'login'">
          {{ mode === 'login' ? '계정이 없으면 회원가입' : '이미 계정이 있으면 로그인' }}
        </button>
      </form>
    </template>
  </div>
</template>
