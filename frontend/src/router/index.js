import { createRouter, createWebHistory } from 'vue-router';
import RootLayout from '../layouts/RootLayout.vue';
import HomePage from '../pages/HomePage.vue';
import ProfileFormPage from '../pages/ProfileFormPage.vue';
import RecommendationPage from '../pages/RecommendationPage.vue';
import NoticeDetailPage from '../pages/NoticeDetailPage.vue';
import FundingPage from '../pages/FundingPage.vue';
import AiCoachPage from '../pages/AiCoachPage.vue';
import FavoritesPage from '../pages/FavoritesPage.vue';
import AuthPage from '../pages/AuthPage.vue';
import MapPage from '../pages/MapPage.vue';
export const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            component: RootLayout,
            children: [
                { path: '', name: 'home', component: HomePage },
                { path: 'profile', name: 'profile', component: ProfileFormPage },
                { path: 'recommendations', name: 'recommendations', component: RecommendationPage },
                { path: 'map', name: 'map', component: MapPage },
                { path: 'notices/:noticeId', name: 'notice-detail', component: NoticeDetailPage },
                { path: 'funding/:noticeId?', name: 'funding', component: FundingPage },
                { path: 'ai-coach/:noticeId?', name: 'ai-coach', component: AiCoachPage },
                { path: 'favorites', name: 'favorites', component: FavoritesPage },
                { path: 'auth', name: 'auth', component: AuthPage },
            ],
        },
    ],
});
