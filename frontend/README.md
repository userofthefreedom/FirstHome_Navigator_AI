# FirstHome Navigator AI Frontend

Vue 3 + JavaScript + Vite 기반 프론트엔드입니다. 사용자가 조건을 입력하고, 추천 청약을 비교하고, 지도에서 공고를 선택하고, 선택한 주택형 옵션의 자금 로드맵과 AI 코치 플랜을 확인하는 화면을 담당합니다.

이 문서는 `docs/history/FirstHome_Navigator_AI_개발공유용_확장기획서_v9.0.docx`와 현재 `frontend/src` 구조를 기준으로 작성했습니다. 전체 프로젝트 실행 순서는 루트 `README.md`를 우선 확인합니다.

## Frontend Role

프론트엔드는 다음 사용자 흐름을 화면으로 연결합니다.

```text
Home
  -> Profile Form
  -> Recommendations
  -> Notice Detail / Map
  -> Funding Roadmap
  -> AI Coach
  -> Favorites
```

전역 챗봇은 `RootLayout`에서 항상 렌더링되어, 로그인 여부와 관계없이 현재 화면 이용 방법과 청약 관련 질문을 돕습니다.

## Stack

- Vue 3
- JavaScript
- Vite
- Vue Router
- Pinia
- Axios
- Tailwind CSS v4
- lucide-vue-next
- Kakao Map JavaScript SDK

TypeScript는 사용하지 않습니다.

## Directory Map

```text
frontend/
  public/
    favicon.svg
    icons.svg
  src/
    api/
      firsthome.js          Axios client and backend API wrappers
    components/
      FloatingCoachChat.vue Global chatbot
    layouts/
      RootLayout.vue        Sidebar/topbar/mobile nav and shared layout
    pages/
      HomePage.vue          Dashboard and current selected candidate summary
      ProfileFormPage.vue   User condition input
      RecommendationPage.vue Housing recommendation list
      MapPage.vue           Kakao map based notice explorer
      NoticeDetailPage.vue  Notice detail, official checks, unit options
      FundingPage.vue       Option-based funding roadmap
      AiCoachPage.vue       Selected notice/option AI action plan
      FavoritesPage.vue     Saved notices and unit options
      AuthPage.vue          Login/register/logout helper
    router/
      index.js              Route definitions
    stores/
      authStore.js          Session state
      profileStore.js       Profile state
    utils/
      analysisStatus.js     Notice document status labels
      format.js             Money/date formatting
      globalSearch.js       Topbar search routing and keyword mapping
      selectionState.js     Current notice/option persistence
    App.vue
    main.js
    style.css
  index.html
  package.json
  vite.config.js
```

## Screen Responsibilities

| Screen | Route | Main Responsibility |
|---|---|---|
| Dashboard | `/` | 현재 추천 후보, 캘린더, 선택 후보 요약 |
| Profile | `/profile` | 사용자 자금/면적/지역/공급유형/청약 조건 입력 |
| Recommendations | `/recommendations` | 점수순/마감/분양가/계약금/부족액 기준 후보 정렬 |
| Map | `/map` | Kakao 지도에서 실제/fixture 공고 위치 탐색 |
| Notice Detail | `/notices/:noticeId` | 공고 상세, 주택형 옵션 그룹, 공식 확인 체크리스트 |
| Funding | `/funding/:noticeId?` | 선택 option_id 기준 계약금, 중도금, 잔금, 융자금, 부족액 계산 |
| AI Coach | `/ai-coach/:noticeId?` | 선택 공고/옵션 기준 이번 주 할 일과 공식 확인 포인트 |
| Favorites | `/favorites` | 저장한 공고와 주택형 옵션 재확인 |
| Auth | `/auth` | 회원가입, 로그인, 로그아웃 상태 확인 |

## State Model

상태는 세 층으로 나뉩니다.

| State | File | Persistence |
|---|---|---|
| Auth session | `stores/authStore.js` | Django session cookie |
| Profile | `stores/profileStore.js` | 로그인 사용자는 backend profile, 비로그인은 local/session fallback |
| Current selection | `utils/selectionState.js` | 로그인 사용자는 `/api/account-state`, 비로그인은 browser storage |

선택 상태 규칙:

- 아무 선택이 없으면 추천 점수 1등 공고와 해당 공고의 1등 옵션을 기본값으로 사용합니다.
- 공고만 선택하면 해당 공고 안의 기본/최고 옵션을 사용합니다.
- 공고와 옵션을 선택한 뒤에는 사용자가 바꾸기 전까지 임의로 리셋하지 않습니다.
- 로그아웃하면 프로필 임시 상태와 현재 선택 상태를 초기화하고 홈으로 이동합니다.

## Backend API Client

`src/api/firsthome.js`가 backend API를 감쌉니다.

주요 함수:

| Function | Backend API |
|---|---|
| `fetchAuthSession` | `GET /api/auth/me` |
| `fetchProfile`, `saveProfileToApi` | `GET/PUT /api/profile` |
| `fetchAccountState`, `saveAccountStateToApi` | `GET/PUT /api/account-state` |
| `fetchHousingRecommendations` | `GET /api/recommendations/housing` |
| `fetchMapNotices` | `GET /api/notices/map` |
| `fetchNotice` | `GET /api/notices/{noticeId}` |
| `analyzeNoticeDocument` | `POST /api/notices/{noticeId}/documents/analyze` |
| `fetchFundingPlan` | `GET /api/recommendations/funding/{noticeId}?option_id={optionId}` |
| `fetchCoachSummary` | `POST /api/ai/coach-summary` |
| `askCoachChat` | `POST /api/ai/chat` |
| `fetchFavorites`, `addFavorite`, `removeFavorite` | `/api/favorites` |

Axios는 `withCredentials: true`로 Django session cookie를 함께 보냅니다. 비로그인 관심목록 병합을 위해 `X-FirstHome-Client-Id` 헤더를 사용합니다.

## Environment Variables

`.env.example`을 `.env`로 복사합니다.

```bash
cp .env.example .env
```

```env
VITE_API_BASE_URL=http://localhost:8000/api
VITE_KAKAO_MAP_JS_KEY=
```

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Django API base URL |
| `VITE_KAKAO_MAP_JS_KEY` | Kakao Map JavaScript SDK key |

Vite에서 브라우저 코드에 노출되는 환경 변수는 `VITE_` 접두사가 필요합니다.

Kakao Developers의 JavaScript 키 설정에는 개발 중 접속하는 도메인을 등록합니다.

```text
http://localhost:5173
http://127.0.0.1:5173
```

## Install

```bash
cd frontend
npm ci
```

## Run

```bash
npm run dev
```

확인 URL:

```text
http://localhost:5173/
```

백엔드가 기본값인 `http://localhost:8000/api`에서 실행 중이어야 합니다.

## Build

```bash
npm run build
```

Vite preview:

```bash
npm run preview
```

## Kakao Map Notes

`MapPage.vue`는 Kakao Map JavaScript SDK를 동적으로 로드합니다.

- JS 키가 없으면 지도 대신 안내 문구를 표시합니다.
- `/api/notices/map`에서 받은 `location` 좌표로 marker를 표시합니다.
- 실제 주소가 없는 공고는 backend fallback 좌표를 사용할 수 있으므로 화면에 위치 정확도 안내를 제공합니다.
- 지도 목록은 페이지네이션으로 제한하여 긴 목록이 화면 높이를 늘리지 않게 합니다.

## AI UX Notes

AI 기능은 두 화면으로 분리되어 있습니다.

| UI | Component/Page | Role |
|---|---|---|
| Global chatbot | `components/FloatingCoachChat.vue` | 모든 화면에서 현재 맥락 질문, 서비스 이용 방법, 청약 질문 응답 |
| AI Coach page | `pages/AiCoachPage.vue` | 선택 공고/옵션 기준으로 앞으로 할 일, 공식 확인 포인트, 선택 기준 정리 |

채팅 기록은 새로고침, 로그인, 로그아웃 시 초기화됩니다. 새 메시지가 생기면 채팅 영역은 자동으로 최신 메시지로 스크롤됩니다.

## Development Checklist

프론트 변경 후 최소 확인:

```bash
npm run build
```

수동 확인 흐름:

1. `/profile`에서 조건 저장
2. `/recommendations`에서 추천 후보와 정렬 기준 확인
3. `/map`에서 지도 marker, 필터, 목록 페이지네이션 확인
4. `/notices/:noticeId`에서 옵션 선택
5. `/funding/:noticeId?option_id=...`에서 선택 옵션 자금 로드맵 확인
6. `/ai-coach/:noticeId?option_id=...`에서 같은 선택이 유지되는지 확인
7. 전역 챗봇에서 현재 화면 질문 입력
8. 로그인/로그아웃 후 선택 상태 초기화 또는 유지 규칙 확인

## Common Issues

### API 호출 실패

- Django 서버가 켜져 있는지 확인합니다.
- `VITE_API_BASE_URL`이 backend 주소와 맞는지 확인합니다.
- `.env` 수정 후 Vite dev server를 재시작합니다.
- backend CORS 설정에 현재 프론트 도메인이 들어 있는지 확인합니다.

### Kakao 지도 미표시

- `VITE_KAKAO_MAP_JS_KEY`가 비어 있지 않은지 확인합니다.
- Kakao Developers JavaScript 키 도메인에 `http://localhost:5173`이 등록되어 있는지 확인합니다.
- REST API 키는 backend geocoding용입니다. 프론트 지도 렌더링에는 JS 키가 필요합니다.

### AI 답변이 template fallback으로 보임

- backend `.env`의 `AI_PROVIDER`, `OPENAI_API_KEY`, `AI_ENABLE_LLM_CHAT` 값을 확인합니다.
- 로그인 사용자만 실제 AI 코치 LLM 분석을 받을 수 있습니다.
