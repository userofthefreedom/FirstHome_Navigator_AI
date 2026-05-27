import { defineStore } from 'pinia';
import { ref } from 'vue';
import { fetchAuthSession, loginToApi, logoutFromApi, registerToApi } from '../api/firsthome';
export const useAuthStore = defineStore('auth', () => {
    const user = ref({ is_authenticated: false });
    const loaded = ref(false);
    const error = ref('');
    async function hydrateAuth() {
        try {
            const session = await fetchAuthSession();
            user.value = session.user;
            error.value = '';
            return session;
        }
        catch {
            error.value = '로그인 상태를 확인하지 못했습니다.';
            user.value = { is_authenticated: false };
            return null;
        }
        finally {
            loaded.value = true;
        }
    }
    async function login(credentials) {
        const session = await loginToApi(credentials);
        user.value = session.user;
        error.value = '';
        loaded.value = true;
        return session;
    }
    async function register(credentials) {
        const session = await registerToApi(credentials);
        user.value = session.user;
        error.value = '';
        loaded.value = true;
        return session;
    }
    async function logout() {
        const session = await logoutFromApi();
        user.value = session.user;
        loaded.value = true;
        return session;
    }
    return { user, loaded, error, hydrateAuth, login, register, logout };
});
