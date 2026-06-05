import { defineStore } from 'pinia';
import { ref, watch } from 'vue';
import { fetchProfile, saveProfileToApi } from '../api/firsthome';
const STORAGE_KEY = 'firsthome.profile';
export const emptyProfile = {
    name: '',
    birth_year: 1999,
    job_status: 'employed',
    annual_income: 0,
    asset: 0,
    debt: 0,
    monthly_saving: 0,
    is_homeless: true,
    subscription_months: 0,
    special_conditions: [],
    preferred_regions: [],
    preferred_supply_types: [],
    target_months: 18,
    desired_area_min_m2: 59,
    desired_area_max_m2: 84,
    desired_price_min: 0,
    desired_price_max: 0,
    max_down_payment: 0,
    monthly_payment_capacity: 0,
};
function readStoredProfile() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved ? { ...emptyProfile, ...JSON.parse(saved) } : { ...emptyProfile };
    }
    catch {
        return { ...emptyProfile };
    }
}
export const useProfileStore = defineStore('profile', () => {
    const profile = ref(readStoredProfile());
    const loaded = ref(false);
    const error = ref('');
    async function hydrateProfile() {
        try {
            profile.value = await fetchProfile();
            error.value = '';
        }
        catch {
            error.value = '백엔드 프로필 API에 연결하지 못했습니다.';
        }
        finally {
            loaded.value = true;
        }
    }
    async function saveProfile(nextProfile) {
        const savedProfile = await saveProfileToApi(nextProfile);
        profile.value = {
            ...savedProfile,
            special_conditions: [...savedProfile.special_conditions],
            preferred_regions: [...savedProfile.preferred_regions],
            preferred_supply_types: [...savedProfile.preferred_supply_types],
        };
    }
    function setLocalProfile(nextProfile) {
        profile.value = {
            ...nextProfile,
            special_conditions: [...nextProfile.special_conditions],
            preferred_regions: [...nextProfile.preferred_regions],
            preferred_supply_types: [...nextProfile.preferred_supply_types],
        };
    }
    function resetProfile() {
        profile.value = {
            ...emptyProfile,
            special_conditions: [],
            preferred_regions: [],
            preferred_supply_types: [],
        };
        loaded.value = true;
        error.value = '';
        localStorage.removeItem(STORAGE_KEY);
    }
    watch(profile, (value) => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(value));
    }, { deep: true });
    return { profile, loaded, error, hydrateProfile, saveProfile, setLocalProfile, resetProfile };
});
