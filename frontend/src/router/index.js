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
import FinancialProductsPage from '../pages/FinancialProductsPage.vue';
import FinancialProductDetailPage from '../pages/FinancialProductDetailPage.vue';
import EconomyNowPage from '../pages/EconomyNowPage.vue';
import AgoraPage from '../pages/AgoraPage.vue';
import MyPage from '../pages/MyPage.vue';
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
                { path: 'finance/products', name: 'finance-products', component: FinancialProductsPage },
                { path: 'finance/products/:productId', name: 'finance-product-detail', component: FinancialProductDetailPage },
                { path: 'finance/economy-now', name: 'economy-now', component: EconomyNowPage },
                { path: 'finance/agora', name: 'agora', component: AgoraPage },
                { path: 'my-page', name: 'my-page', component: MyPage },
                { path: 'auth', name: 'auth', component: AuthPage },
            ],
        },
    ],
});
