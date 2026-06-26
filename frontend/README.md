# FirstHome Navigator AI Frontend

Vue 3 + JavaScript + Vite 기반 프론트엔드입니다. 사용자가 조건을 입력하고, 추천 청약을 비교하고, 지도와 공고 상세를 확인하고, 자금 로드맵과 AI 코치를 이어서 보는 화면을 제공합니다. 금융상품, 경제 NOW, 청약 아고라, MY PAGE, light/dark mode도 이 프론트엔드에서 담당합니다.

전체 프로젝트 실행 순서는 루트 `README.md`를 우선 확인합니다.

## 기술 스택

- Vue 3
- JavaScript
- Vite
- Vue Router
- Pinia
- Axios
- Tailwind CSS v4
- lucide-vue-next
- Kakao Map JavaScript SDK

## 화면 구조

```text
frontend/
  public/
    favicon.svg
    icons.svg
  src/
    api/
      firsthome.js
    components/
      FloatingCoachChat.vue
    layouts/
      RootLayout.vue
    pages/
      HomePage.vue
      ProfileFormPage.vue
      RecommendationPage.vue
      NoticeDetailPage.vue
      FundingPage.vue
      AiCoachPage.vue
      FavoritesPage.vue
      MapPage.vue
      FinancialProductsPage.vue
      FinancialProductDetailPage.vue
      EconomyNowPage.vue
      AgoraPage.vue
      MyPage.vue
      AuthPage.vue
    router/
      index.js
    stores/
      authStore.js
      profileStore.js
    utils/
      analysisStatus.js
      format.js
      globalSearch.js
      selectionState.js
    App.vue
    main.js
    style.css
```

## 라우트

| 화면 | 경로 | 역할 |
|---|---|---|
| Dashboard | `/` | 현재 추천 후보, 선택 후보, 이번 주 할 일, 자금 상태 요약 |
| Profile | `/profile` | 사용자 조건 입력과 저장 |
| Recommendations | `/recommendations` | 추천 청약 목록, 점수, 우선 검토 주택형 옵션 |
| Map | `/map` | 청약 공고 지도, 주변 부동산/은행 검색, 길찾기 |
| Notice Detail | `/notices/:noticeId` | 공고 상세, 공식 PDF 분석, 주택형 옵션, 체크리스트 |
| Funding | `/funding/:noticeId?` | 선택 주택형 기준 자금 로드맵 |
| AI Coach | `/ai-coach/:noticeId?` | 선택 공고/옵션 기준 AI 준비 플랜 |
| Favorites | `/favorites` | 관심 공고와 관심 옵션 |
| Financial Products | `/finance/products` | 예적금 상품 목록, 필터, 정렬 |
| Product Detail | `/finance/products/:productId` | 기간별 금리 옵션과 가입 후보 저장 |
| Economy NOW | `/finance/economy-now` | 부동산/환율/금/시장 지표 시각화 |
| Agora | `/finance/agora` | 청약 영상 검색, 게시글, 댓글 |
| MY PAGE | `/my-page` | 프로필, 저장 내역, 가입 금융상품, 금리 그래프 |
| Auth | `/auth` | 로그인, 회원가입, 로그아웃 상태 확인 |

## 공통 레이아웃

`RootLayout.vue`가 좌측 사이드바, 상단 검색, 계정 영역, 테마 전환, 모바일 내비게이션, Floating AI 챗봇을 담당합니다.

`FloatingCoachChat.vue`는 현재 화면 맥락을 백엔드에 전달해 화면별 추천 질문과 답변을 제공합니다. 예를 들어 지도 화면에서는 지도 사용법, 청약 아고라에서는 청약 관련 영상/커뮤니티 사용법, MY PAGE에서는 저장 내역 확인 방법을 중심으로 답변합니다.

## 상태 관리

| 상태 | 파일 | 저장 방식 |
|---|---|---|
| 인증 세션 | `stores/authStore.js` | Django session cookie |
| 프로필 조건 | `stores/profileStore.js` | 회원은 backend profile, 비회원은 브라우저 상태 |
| 현재 선택 공고/옵션 | `utils/selectionState.js` | 회원은 `/api/account-state`, 비회원은 browser storage |
| API 캐시 | `api/firsthome.js` | 짧은 TTL의 GET 캐시와 중복 요청 병합 |

## API 클라이언트

`src/api/firsthome.js`가 백엔드 API 호출을 관리합니다.

대표 함수:

| 함수 | API |
|---|---|
| `fetchAuthSession` | `GET /api/auth/me` |
| `registerToApi`, `loginToApi`, `logoutFromApi` | `/api/auth/...` |
| `fetchProfile`, `saveProfileToApi` | `GET/PUT /api/profile` |
| `fetchAccountState`, `saveAccountStateToApi` | `GET/PUT /api/account-state` |
| `fetchHousingRecommendations` | `GET /api/recommendations/housing` |
| `fetchNotice`, `fetchNoticeUnitOptions` | `GET /api/notices/...` |
| `fetchFundingPlan` | `GET /api/recommendations/funding/{noticeId}` |
| `fetchCoachSummary`, `askCoachChat` | `/api/ai/...` |
| `fetchFinancialProducts`, `joinFinancialProduct` | `/api/products...` |
| `fetchMarketAssets` | `GET /api/market/assets` |
| `fetchAgoraPosts`, `createAgoraPost` | `/api/agora/posts` |
| `fetchFavorites`, `addFavorite`, `removeFavorite` | `/api/favorites` |

## 환경 변수

`frontend/.env.example`을 복사해 `frontend/.env`를 만듭니다.

```bash
cd frontend
cp .env.example .env
```

```env
VITE_API_BASE_URL=/api
VITE_KAKAO_MAP_JS_KEY=
```

| 변수 | 설명 |
|---|---|
| `VITE_API_BASE_URL` | Django API base URL. 개발/시연 기본값은 `/api` |
| `VITE_KAKAO_MAP_JS_KEY` | Kakao Map JavaScript SDK 키 |

Vite dev server는 `/api` 요청을 Django backend로 proxy합니다.

## 설치

```bash
cd frontend
npm ci
```

## 개발 서버 실행

```bash
cd frontend
npm run dev
```

기본 URL:

```text
http://localhost:5173/
```

## 빌드

```bash
cd frontend
npm run build
```

시연 안정성을 위해 Vite dev server 대신 빌드 산출물을 serve로 제공할 수 있습니다.

```bash
npm run build
npx serve -s dist -l 5173
```

## Kakao Map 확인

- Kakao Developers에서 JavaScript 키를 발급합니다.
- 허용 도메인에 개발/시연 주소를 등록합니다.
- `VITE_KAKAO_MAP_JS_KEY`에 JavaScript 키를 넣고 프론트엔드 서버를 재시작합니다.
- 지도 좌표 보강은 백엔드의 `KAKAO_REST_API_KEY`와 `geocode_notice_locations` 명령이 담당합니다.

## 개발 체크리스트

```bash
npm run build
```

수동 확인 흐름:

1. `/profile`에서 조건 저장
2. `/recommendations`에서 추천 후보 확인
3. `/notices/:noticeId`에서 공고 상세와 주택형 옵션 확인
4. `/funding/:noticeId?option_id=...`에서 자금 로드맵 확인
5. `/ai-coach/:noticeId?option_id=...`에서 AI 코치 확인
6. `/map`에서 지도, 필터, 주변 검색, 길찾기 확인
7. `/finance/products`와 `/finance/products/:productId`에서 상품 조회와 저장 확인
8. `/finance/economy-now`에서 차트 표시 확인
9. `/finance/agora`에서 영상 검색, 게시글, 댓글 확인
10. `/my-page`에서 저장 내역과 금리 그래프 확인
11. light/dark mode 모두 확인

## 자주 보는 문제

API 호출 실패:
- backend 서버가 켜져 있는지 확인합니다.
- `VITE_API_BASE_URL`이 `/api` 또는 올바른 backend 주소인지 확인합니다.
- backend CORS/CSRF 설정에 현재 프론트엔드 origin이 포함되어 있는지 확인합니다.

Kakao 지도 미표시:
- `VITE_KAKAO_MAP_JS_KEY`가 비어 있지 않은지 확인합니다.
- Kakao Developers JavaScript 키 허용 도메인에 현재 주소가 등록되어 있는지 확인합니다.

AI 답변이 fallback으로 보임:
- backend `.env`의 `AI_PROVIDER`, `GMS_API_KEY`, `AI_ENABLE_LLM_CHAT` 값을 확인합니다.
- backend 서버 로그에서 GMS/OpenAI 호출 경로를 확인합니다.
