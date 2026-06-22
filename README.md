# FirstHome Navigator AI

첫 주택 마련을 준비하는 사용자가 실제 LH 청약 공고와 공식 PDF 공고문을 바탕으로 추천 청약, 주택형 옵션, 분양가, 계약금/중도금/잔금 일정, 자금 부족분, 공식 근거, AI 코치 답변을 확인할 수 있는 서비스입니다.

팀 터미널 기본값은 bash이므로 모든 명령은 bash 기준입니다.

현재 프로젝트는 다음 방향으로 동작합니다.

- 실제 LH 공고/API 데이터를 우선 사용합니다.
- 금융상품, 청년정책, 청약 공고는 외부 API 또는 DB 데이터를 먼저 사용하고, fixture는 부족한 부분을 보충하는 안전망으로만 사용합니다.
- 청약 fixture는 17개 광역시·도별 활성 소유형 공고가 5개 미만일 때 부족분만 뒤에 보충합니다.
- fixture 공고는 공식 원문 링크 대신 `Fixture`로 표시되며, 추천 점수도 실제 공고보다 낮게 보정됩니다.
- AI 기본값은 `openai`입니다. AI 코치, 전역 챗봇, LLM 보조 PDF 분석을 사용하려면 `OPENAI_API_KEY`를 넣어야 합니다.
- HuggingFace/local model serving은 현재 단계의 PDF 해석 핵심 방식에서 제외했습니다. 현재 전략은 rule-first, 공식 PDF 구조 파싱, 필요 시 GPT 보조, template fallback입니다.
- 공식 PDF 분석 결과가 있으면 주택형별 납부 일정이 우선 사용됩니다.
- 중도금은 0회, 1회, 여러 회차, 10회 이상 모두 가능한 반복 일정으로 처리합니다.
- 추천 점수는 정책/상품을 제외하고 자격 35점, 자금 25점, 지역 30점, 일정 10점의 100점 만점으로 계산합니다.
- 청약 지도는 Kakao Map JavaScript SDK로 화면을 렌더링하고, Kakao Local REST API는 백엔드에서 위치 좌표 보강에 사용합니다.

---

## 1. 사전 준비

| 항목 | 권장 버전 / 기준 |
|---|---|
| Python | 3.11 이상 |
| Node.js | 20 이상 |
| npm | 10 이상 |
| 터미널 | bash 기준 |
| Frontend | Vue 3 + JavaScript + Vite |

아래 명령은 프로젝트 루트, 즉 `backend/`와 `frontend/` 폴더가 보이는 위치에서 시작한다고 가정합니다. 프로젝트를 다른 위치에 받은 경우 먼저 본인 환경의 프로젝트 루트로 이동한 뒤 실행합니다.

---

## 2. 기술 스택

### Backend

- Python 3.11+
- Django 5.0.6
- Django REST Framework
- SQLite 기본 사용
- pypdf, pdfplumber 기반 PDF 분석
- requests 기반 외부 API 수집

### Frontend

- Node.js 20+
- npm 10+
- Vue 3
- Vite
- Vue Router
- Pinia
- Axios
- Tailwind CSS v4

> 이 프로젝트는 Vue 3 + JavaScript를 Vite로 실행합니다. TypeScript는 사용하지 않습니다.

---

## 3. 폴더 구조

```text
backend/
  apps/
    profiles/          사용자 조건, 인증, 관심목록
    notices/           공고 모델, LH 수집
    notice_docs/       공식 PDF 분석, 주택형 옵션, 납부 일정
    recommendations/   추천 점수와 추천 API
    funding/           option_id 기반 자금 계획 계산
    rules/             분류, 점수, 자금, 신뢰도, 문서 추출 규칙 코드
    products/          금융상품
    policies/          청년정책
    ai_coach/          AI 코치
  config/              Django settings, urls
  fixtures/            시연 보조 fixture
  manage.py
  requirements.txt

frontend/
  public/              favicon, 공통 SVG 아이콘 등 정적 파일
  src/
    api/               Axios 기반 backend API wrapper
    components/        전역 챗봇 등 재사용 컴포넌트
    layouts/           사이드바, 상단바, 모바일 nav 공통 레이아웃
    pages/             대시보드, 조건 입력, 추천, 지도, 상세, 자금, AI 코치 화면
    router/            Vue Router 경로 정의
    stores/            Pinia 인증/프로필 상태
    utils/             금액 포맷, 분석 상태, 선택 공고/옵션 상태 유틸
    main.js            Vue 앱 진입점
  package.json         프론트 의존성 및 npm scripts
  vite.config.js       Vite 설정

docs/
  README.md
  history/             과거 MVP/확장 기획서 버전 문서
  guide/               실행 가이드, API Key 신청 가이드
  detail/              ERD, Use Case, 와이어프레임, WBS, 규칙 상세 설명 자료
```

서비스 판단 규칙의 상세 설명은 `docs/detail/rules_detail.txt`에 정리되어 있습니다. 실제 실행 코드는 `backend/apps/rules/`를 중심으로 두고, 이 문서는 발표와 유지보수를 위한 해설 자료로 관리합니다.

---

## 4. 환경 파일 준비

### Backend

```bash
cd backend
cp .env.example .env
```

`backend/.env` 주요 값:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
DJANGO_ALLOWED_HOSTS=
CORS_ALLOWED_ORIGINS=
CSRF_TRUSTED_ORIGINS=
CORS_ALLOW_ALL_ORIGINS=false

DATA_GO_KR_SERVICE_KEY=
FINLIFE_API_KEY=
YOUTH_POLICY_API_KEY=
KAKAO_REST_API_KEY=

FIRSTHOME_ENABLE_FIXTURE_SUPPLEMENT=true
FIRSTHOME_MIN_ACTIVE_SERVICE_NOTICES_PER_REGION=5

AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
AI_ENABLE_LLM_EXTRACTION=true
AI_ENABLE_LLM_CHAT=true
AI_REQUEST_TIMEOUT=30
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_CHAT_PATH=/chat/completions
```

API Key는 개인 정보이므로 Git, ZIP, 팀 채팅방, 문서에 공유하지 않습니다.

`KAKAO_REST_API_KEY`는 지도 화면을 직접 띄우는 키가 아니라 백엔드에서 공고 위치를 좌표로 보강할 때 사용하는 REST API 키입니다. Kakao Developers에서 REST API 키의 호출 허용 IP를 제한하는 경우 `http://localhost:5173` 같은 URL은 넣을 수 없습니다. 로컬 개발 중에는 IP 제한을 비워두거나 현재 PC의 외부 IPv4 주소를 등록합니다.

### Frontend

```bash
cd frontend
cp .env.example .env
```

`frontend/.env`:

```env
VITE_API_BASE_URL=/api
VITE_KAKAO_MAP_JS_KEY=
```

Vite에서는 브라우저 코드에서 사용할 환경 변수 이름이 `VITE_`로 시작해야 합니다.

로컬 개발과 ngrok 공유에서는 Vite dev server가 `/api` 요청을 `http://127.0.0.1:8000` 백엔드로 프록시합니다. 따라서 기본값은 `/api`를 유지합니다.

```env
VITE_API_BASE_URL=/api
```

`VITE_KAKAO_MAP_JS_KEY`는 Kakao Map JavaScript SDK용 키입니다. Kakao Developers의 JavaScript 키 설정에는 프론트 접속 도메인을 등록합니다.

개발 환경에서 주로 쓰는 도메인:

```text
http://localhost:5173
http://127.0.0.1:5173
```

도메인이나 키를 바꾼 뒤에는 프론트 서버를 재시작해야 합니다.

---

## 5. Backend 설치와 실행

처음 한 번만 프로젝트 루트에서 가상환경과 패키지를 준비합니다.

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

현재 프로젝트는 HuggingFace/local model serving을 사용하지 않으므로 별도 AI requirements 파일이 없습니다. AI 코치, 전역 챗봇, LLM 보조 PDF 분석은 `requirements.txt`의 기본 의존성과 OpenAI-compatible API 호출로 동작합니다.

DB를 준비하고 서버를 실행합니다.

```bash
cd backend
python manage.py check
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

위 명령은 개발용 실행입니다. ngrok으로 외부에 공유하거나 발표장에서 여러 명이 동시에 접속하는 경우에는 7.1의 `waitress` 실행 방식을 사용합니다.

확인 URL:

```text
http://localhost:8000/api/dashboard
http://localhost:8000/api/notices
http://localhost:8000/api/notices?active=1
http://localhost:8000/api/notices/map
http://localhost:8000/api/recommendations/housing
```

`/api/notices`는 전체 공고 목록이고, `/api/notices?active=1`은 접수 마감일이 오늘 이후인 현재 검토 가능 공고만 반환합니다. `/api/notices/map`은 지도 표시용 공고 목록입니다. 대시보드와 추천 후보는 마감 지난 공고를 기본 후보에서 제외합니다.

---

## 6. 실제 데이터와 Fixture 운영

이 프로젝트는 실제 데이터를 먼저 쓰고, 실제 데이터가 부족할 때만 fixture를 보충합니다. fixture는 발표 화면을 비우지 않기 위한 보조 데이터이며 실제 공고처럼 외부 원문 링크를 제공하지 않습니다.

데이터 사용 우선순위:

1. DB에 저장된 실제 LH 청약 공고, 금융상품, 청년정책을 먼저 사용합니다.
2. 활성 소유형 청약이 대한민국 17개 광역시·도별로 5개 미만이면 해당 지역에만 fixture 공고를 보충합니다.
3. fixture 공고는 `source_meta.fixture_id`를 갖고, 화면에서는 공식 원문/공식 출처 버튼 대신 `Fixture` 표시가 나옵니다.
4. fixture 공고는 추천 점수가 실제 공고보다 낮게 보정되어 같은 조건이면 실제 데이터가 먼저 보입니다.

| 상황 | 동작 |
|---|---|
| 실제 금융상품/정책이 DB에 있음 | 실제 DB 데이터를 추천에 사용 |
| 실제 금융상품/정책이 DB에 없음 | fixture 금융상품/정책을 사용해 화면이 비지 않게 함 |
| 특정 광역시·도 활성 소유형 공고가 5개 미만 | `FIRSTHOME_ENABLE_FIXTURE_SUPPLEMENT=true`이면 부족분만 fixture로 DB에 보충 |
| 실제 DB만 확인하고 싶음 | `FIRSTHOME_ENABLE_FIXTURE_SUPPLEMENT=false` 설정 후 Django 서버 재시작 |
| 발표용 fixture를 DB에 직접 넣고 싶음 | `load_firsthome_fixture`로 85개 fixture 공고와 분석 결과를 로드 |

fixture 보충 기준은 `backend/.env`에서 조정합니다.

```env
FIRSTHOME_ENABLE_FIXTURE_SUPPLEMENT=true
FIRSTHOME_MIN_ACTIVE_SERVICE_NOTICES_PER_REGION=5
```

시연용 고정 데이터를 DB에 직접 넣고 싶을 때만 아래 명령을 사용합니다. 이 명령은 기존 공고/상품/정책을 지운 뒤 fixture를 로드하므로, 실제 수집 데이터를 보존해야 하는 상황에서는 실행하지 않습니다.

```bash
cd backend
python manage.py load_firsthome_fixture
```

실제 DB 데이터만 확인하고 싶으면 `backend/.env`에서 아래처럼 바꾼 뒤 Django 서버를 재시작합니다.

```env
FIRSTHOME_ENABLE_FIXTURE_SUPPLEMENT=false
```

---

## 7. Frontend 실행

새 터미널에서 실행합니다.

```bash
cd frontend
npm ci
npm run dev
```

확인 URL:

```text
http://localhost:5173/
```

`127.0.0.1`로 접속하고 싶다면 host를 지정해 실행할 수 있습니다.

```bash
npm run dev -- --host 127.0.0.1
```

프론트엔드는 기본적으로 `http://localhost:8000/api`를 호출합니다. 주소를 바꾸려면 `frontend/.env`의 `VITE_API_BASE_URL`을 수정한 뒤 프론트 서버를 재시작합니다.

---

## 7.1 ngrok으로 임시 공개

발표나 외부 공유용으로 로컬 서버를 ngrok에 연결할 수 있습니다. 이 프로젝트의 기본 터미널은 Git Bash 기준입니다.

핵심만 먼저 정리하면 다음과 같습니다.

| 터미널 | 실행할 것 | 용도 |
|---|---|---|
| 1 | Waitress 백엔드 | 발표용 로컬 API 서버 |
| 2 | Vite 프론트 | 로컬 화면 서버와 `/api` 프록시 |
| 3 | 프론트 ngrok 터널 | 사람들에게 공유할 접속 주소 생성 |

중요한 구분:

- **공유 주소**: 프론트 ngrok 주소 하나만 외부 사용자에게 공유합니다.
- **API 주소**: `frontend/.env`의 `VITE_API_BASE_URL=/api`를 유지합니다.
- ngrok 무료 주소는 실행할 때마다 바뀔 수 있습니다. 주소가 바뀌면 Kakao Developers 사이트 도메인을 다시 확인합니다.

### 7.1.1 처음 한 번만 ngrok 설치/인식 확인

```bash
ngrok version
```

정상적으로 버전이 나오면 버전을 확인합니다. 무료 계정은 ngrok agent 최소 버전 요구사항이 있을 수 있으므로 `3.20.0`보다 낮으면 먼저 업데이트합니다.

```bash
ngrok update
ngrok version
```

`ngrok: command not found`가 나오면 아래 명령으로 설치합니다.

```bash
winget install --id Ngrok.Ngrok --accept-package-agreements --accept-source-agreements
```

설치 후에는 Git Bash를 완전히 닫고 새로 연 뒤 다시 확인합니다.

```bash
ngrok version
```

ngrok 계정을 처음 쓰는 PC라면 ngrok 대시보드에서 받은 authtoken을 한 번 등록합니다.

```bash
ngrok config add-authtoken 본인_NGROK_AUTHTOKEN
```

`ngrok http`만 입력하면 터널이 열리지 않고 사용법 안내만 출력됩니다. 반드시 아래처럼 포트까지 붙여 실행합니다.

```bash
ngrok http 5173
```

### 7.1.2 발표용 백엔드 실행

ngrok으로 외부에 공유할 때는 Django 개발 서버(`runserver`)보다 WSGI 서버인 `waitress`로 백엔드를 실행합니다. `runserver`는 개발 편의를 위한 서버라 자동 리로드와 동시 요청 처리에서 발표용으로 불안정할 수 있습니다. `waitress`는 같은 Django 앱을 더 안정적으로 HTTP 요청에 연결해 줍니다.

1. 첫 번째 터미널에서 가상환경을 켜고 백엔드를 실행합니다.

```bash
source .venv/Scripts/activate
cd backend
python manage.py migrate
waitress-serve --listen=127.0.0.1:8000 --threads=8 config.wsgi:application
```

`waitress-serve` 명령을 찾지 못하면 패키지를 다시 설치합니다.

```bash
pip install -r requirements.txt
```

급하게 개발 서버로만 확인해야 한다면 아래처럼 자동 리로드를 끄고 실행합니다. 다만 발표용으로는 `waitress`를 우선 사용합니다.

```bash
python manage.py runserver 127.0.0.1:8000 --noreload
```

2. `frontend/.env`는 다음 값을 유지합니다. 프론트 개발 서버가 `/api`를 로컬 백엔드로 프록시합니다.

```env
VITE_API_BASE_URL=/api
VITE_KAKAO_MAP_JS_KEY=본인_KAKAO_JAVASCRIPT_KEY
```

### 7.1.3 프론트 ngrok 주소 만들기

3. 두 번째 터미널에서 프론트를 실행합니다.

```bash
cd frontend
npm run dev
```

4. 세 번째 터미널에서 프론트 ngrok 터널을 실행합니다.

```bash
ngrok http 5173
```

5. 출력된 프론트 ngrok 주소를 공유합니다.

프론트 ngrok에서 아래처럼 주소가 출력되면 이 주소가 **사람들에게 공유할 서비스 주소**입니다.

```text
https://xyz-789.ngrok-free.app
```

6. Kakao Developers에 프론트 ngrok 주소를 등록합니다.

청약 지도는 Kakao Map JavaScript SDK를 사용하므로, 프론트 ngrok 주소를 Kakao Developers의 JavaScript 키 허용 도메인에 반드시 추가해야 합니다.

등록 위치:

```text
Kakao Developers > 내 애플리케이션 > 앱 설정 > 플랫폼 > Web > 사이트 도메인
```

예를 들어 프론트 ngrok 주소가 `https://xyz-789.ngrok-free.app`라면 사이트 도메인에 다음 값을 추가합니다.

```text
https://xyz-789.ngrok-free.app
```

등록 후 프론트 페이지를 새로고침합니다. Kakao 도메인 등록이 빠지면 서비스는 열려도 청약 지도 화면이 비어 있거나 Kakao 지도 로딩 오류가 날 수 있습니다.

### 7.1.4 backend/.env 설정

이 프로젝트는 ngrok을 프론트 하나만 열고 `/api`를 Vite 프록시로 처리합니다. 따라서 백엔드와 프론트가 브라우저 기준 같은 origin처럼 동작하므로, 로컬 기본 쿠키 설정을 사용할 수 있습니다. 여러 사용자가 같은 ngrok 주소에 접속해도 쿠키는 각 사용자 브라우저에 따로 저장되고, Django 세션 데이터는 서버 DB에 별도 세션으로 저장됩니다.

`backend/.env`의 쿠키 설정은 기본값을 권장합니다.

```env
SESSION_COOKIE_SAMESITE=Lax
SESSION_COOKIE_SECURE=false
CSRF_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SECURE=false
```

주의할 점:

- `frontend/.env`의 `VITE_API_BASE_URL`은 `/api`로 둡니다.
- 백엔드와 프론트 서버는 모두 켜져 있어야 합니다.
- 이 프로젝트는 ngrok 무료 경고 페이지 우회를 위해 API 요청에 `ngrok-skip-browser-warning` 헤더를 자동으로 붙입니다.

### 7.1.5 종료 방법

공유를 끝낼 때는 열어둔 3개 터미널을 각각 종료합니다.

| 터미널 | 종료 방법 |
|---|---|
| Waitress 백엔드 | `Ctrl + C` |
| Vite 프론트 | `Ctrl + C` |
| 프론트 ngrok 터널 | `Ctrl + C` |

ngrok 터널은 터미널을 종료하면 외부 주소도 더 이상 접속되지 않습니다. 다음에 다시 실행하면 프론트 ngrok 주소가 새로 발급될 수 있으므로 Kakao Developers 사이트 도메인을 다시 확인합니다.

주의할 점:

- 프론트 ngrok 주소도 서버를 다시 열 때마다 바뀔 수 있습니다.
- Kakao Developers의 사이트 도메인은 프론트 ngrok 주소가 바뀔 때마다 다시 추가해야 합니다.
- API가 실패하면 백엔드 `127.0.0.1:8000`, 프론트 `5173`, `frontend/.env`의 `VITE_API_BASE_URL=/api`를 먼저 확인합니다.

---

## 8. 다음부터 다시 실행할 때

가상환경, `node_modules`, DB가 이미 준비된 뒤에는 전체 설치 과정을 반복할 필요가 없습니다.

백엔드:

```bash
source .venv/Scripts/activate
cd backend
python manage.py runserver 127.0.0.1:8000
```

ngrok으로 발표/공유할 때는 백엔드를 다음처럼 실행합니다.

```bash
source .venv/Scripts/activate
cd backend
waitress-serve --listen=127.0.0.1:8000 --threads=8 config.wsgi:application
```

프론트엔드:

```bash
cd frontend
npm run dev
```

---

## 9. 실제 데이터 수집 순서

외부 API를 사용하려면 먼저 `backend/.env`에 API 키를 넣어야 합니다.

```env
DATA_GO_KR_SERVICE_KEY=공공데이터포털_LH_API_KEY
FINLIFE_API_KEY=금융감독원_금융상품_API_KEY
YOUTH_POLICY_API_KEY=온통청년_정책_API_KEY
```

권장 순서:

1. 금융상품과 주택담보대출 상품을 수집합니다.
2. 청년정책을 수집합니다.
3. LH 청약 공고를 수집합니다.
4. 실제 공고의 공식 PDF 분석을 실행합니다.
5. Kakao Local REST API로 지도 위치 좌표를 보강합니다.
6. 서버를 실행하고 추천/상세/지도 화면에서 실제 데이터와 fixture 보충 결과를 확인합니다.

### 9.1 금융상품/주택담보대출 수집

금융감독원 금융상품 API에서 예금, 적금, 주택담보대출 상품을 가져옵니다. 실제 DB에 저장하기 전에 `--dry-run`으로 API 키와 응답을 먼저 확인합니다.

```bash
cd backend
python manage.py import_finlife --dry-run
python manage.py import_finlife
python manage.py import_finlife --clear
```

기본값은 예금/적금/주택담보대출을 모두 수집합니다. `--clear`는 기존 금융상품과 대출상품을 지우고 새로 저장합니다. 특정 상품군만 점검해야 하는 개발 상황에서는 `--kind deposit`, `--kind saving`, `--kind mortgage`를 사용할 수 있지만, 일반 운영 루틴에서는 위 3개 명령만 사용하면 됩니다.

### 9.2 청년정책 수집

온통청년 정책 API에서 정책 후보를 가져옵니다. 정책 API는 검색어 필터가 기대와 다르게 동작할 수 있으므로 넓게 수집한 뒤 서비스 내부 matcher가 나이, 지역, 소득, 무주택 여부, 정책 카테고리 기준으로 정렬합니다.

```bash
python manage.py import_youthcenter --dry-run
python manage.py import_youthcenter
python manage.py import_youthcenter --clear
```

기본 수집은 50개씩 4페이지, 약 200개 정책 후보를 가져옵니다. `--dry-run`은 API 연결 확인용으로 20개만 확인합니다. 수집 후 서비스 내부 matcher가 청약/주거/대출/자금 관련 정책, 사용자 희망 지역, 나이, 소득, 무주택 여부를 기준으로 다시 걸러냅니다.

### 9.3 LH 청약 공고 수집

공공데이터포털 LH API에서 청약 공고를 가져옵니다. 현재 서비스는 소유형 청약을 대상으로 하므로 기본값으로 서비스 대상 공고만 저장하고, LH 공급정보 상세 API까지 조회해 주택형, 면적, 일부 분양가를 보강합니다.

```bash
python manage.py import_lh --dry-run
python manage.py import_lh
python manage.py import_lh --clear
```

기본 수집은 페이지당 250개씩 7페이지를 조회합니다. `--dry-run`은 API 연결 확인용으로 50개 1페이지만 확인합니다. `python manage.py import_lh`의 공급정보 상세 조회는 기본 75개 공고까지만 수행합니다. `--clear` 는 기존 공고를 지우고 다시 내려 받는 명령어 입니다.

| 옵션 | 설명 |
|---|---|
| `--page-size` | 한 페이지에서 가져올 공고 수입니다. 운영 기본값은 250개입니다. |
| `--max-pages` | 가져올 최대 페이지 수입니다. 운영 기본값은 7페이지이고, `0`이면 가능한 모든 페이지를 조회합니다. |
| `--supply-limit` | 공급정보 상세 조회 개수를 제한합니다. 운영 기본값은 75개이고, dry-run 기본값은 10개입니다. `0`을 넣으면 수집된 모든 공고를 대상으로 주택형/면적/가격 보강을 시도합니다. |
| `--include-excluded` | 임대/전세/상가 등 서비스 대상 밖 공고까지 DB에 저장해야 할 때만 사용합니다. |
| `--without-supply-info` | 공급정보 상세 API 호출을 건너뜁니다. |
| `--clear` | 기존 공고를 지우고 새로 저장합니다. 실제 수집 데이터를 보존해야 하면 사용하지 않습니다. |

### 9.4 공식 PDF 분석

LH 공고 수집 후 공식 PDF 분석을 실행하면 상세 화면과 자금 로드맵에서 PDF 기반 주택형 옵션, 계약금, 중도금, 잔금, 융자금 일정이 우선 사용됩니다.

```bash
python manage.py analyze_notice_documents --dry-run
python manage.py analyze_notice_documents
python manage.py analyze_notice_documents --force
```

기본 실행은 아직 분석되지 않은 서비스 대상 공고를 모두 분석합니다. `--dry-run`은 20개만 골라 분석 대상 목록을 보여주고, 실제 PDF 분석은 실행하지 않습니다. 이미 분석된 공고까지 다시 분석하려면 `--force`를 사용합니다. 필요하면 `--report-json`, `--report-md`로 분석 리포트를 남길 수 있습니다.

fixture 공고는 실제 PDF URL이 없으므로 외부 문서를 내려받지 않습니다. fixture의 분석 버튼은 미리 준비된 fixture 분석 결과를 같은 형식으로 반영합니다.

### 9.5 지도 위치 좌표 보강

청약 지도는 저장된 좌표가 있으면 그 좌표를 사용하고, 없으면 지역 기준 fallback 좌표를 사용합니다. 실제 단지 위치에 가깝게 표시하려면 `backend/.env`에 `KAKAO_REST_API_KEY`를 넣고 좌표 보강 명령을 실행합니다.

```bash
python manage.py geocode_notice_locations --dry-run
python manage.py geocode_notice_locations
python manage.py geocode_notice_locations --overwrite
```

`--dry-run`은 20개만 확인하고 DB를 바꾸지 않습니다. 기본 실행은 좌표가 비어 있는 모든 공고를 대상으로 Kakao Local REST API 좌표 보강을 시도합니다. 이미 좌표가 있는 공고까지 다시 보정해야 할 때만 `--overwrite`를 사용합니다.

주의할 점:

- Kakao REST API 키는 백엔드에서만 사용합니다.
- REST API 키의 호출 허용 IP는 URL이 아니라 IP 주소 기준입니다.
- LH 공고의 지구명만으로는 정확한 주소를 찾지 못할 수 있습니다. 이 경우 지도는 지역 fallback 좌표를 사용하고, 화면에는 위치 정확도 안내가 표시됩니다.
- fixture 공고는 실제 공식 주소가 없으므로 fixture에 들어 있는 보조 좌표를 사용합니다.

### 9.6 Fixture 보충 확인

실제 수집이 끝난 뒤 Django 서버를 실행하면 추천/상세 API 호출 시 부족한 지역의 fixture가 자동 보충됩니다. 기준은 `FIRSTHOME_MIN_ACTIVE_SERVICE_NOTICES_PER_REGION=5`입니다.

```bash
python manage.py runserver localhost:8000
```

확인할 API:

```text
http://localhost:8000/api/notices?active=1
http://localhost:8000/api/notices/map
http://localhost:8000/api/recommendations/housing
```

fixture 공고는 화면에 `Fixture`로 표시되고, 공식 원문/공식 출처 버튼이 나타나지 않습니다.

---

## 10. 테스트와 회귀 점검

### Backend

```bash
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py check_sample_pdf_regression --report-json=reports/sample_pdf_regression_review.json
python manage.py check_representative_flow --report-json=reports/representative_flow_review.json
python manage.py check_ai_chat_smoke --report-json=reports/ai_chat_smoke_review.json
```

### Frontend

```bash
cd frontend
npm run build
```

---

## 11. 기본 화면 확인 흐름

1. 홈 화면 접속
2. 조건 입력 화면에서 대표 사용자 조건 확인 또는 일부 값 수정
3. 조건 저장 후 추천 결과로 이동
4. 추천 카드에서 총점 100점 기준 정렬과 Top-N 주택형 옵션 확인
5. 청약 지도에서 실제/fixture 공고 위치, 지역 필터, 공급유형 필터, 지도 공고 목록 확인
6. 공고 상세에서 공식 문서 분석 상태, 체크리스트, 출처 페이지, 주택형 옵션 확인
7. 필요 시 공식 공고문 분석 실행. fixture 공고는 외부 원문 버튼 대신 `Fixture` 표시가 나오는지 확인
8. 자금 로드맵에서 선택 `option_id` 기준 계약금, 중도금, 입주잔금, 융자금, 부족액 확인
9. 자금 로드맵 또는 공고 상세에서 AI 코치로 이동해 선택 공고와 선택 옵션 기준의 다음 행동 확인
10. 전역 챗봇에서 현재 화면 이용 방법 또는 청약 관련 질문을 입력해 답변 확인
11. 관심 공고 또는 관심 주택형 옵션 저장
12. 관심목록에서 저장 공고와 저장 옵션 확인 및 삭제
13. 로그인 사용자는 새로고침 후 프로필, 선택 공고/옵션, 관심목록이 유지되는지 확인
14. 로그아웃 후 조건과 선택 상태가 초기화되는지 확인

대표 사용자 조건:

| 항목 | 값 |
|---|---|
| 출생연도 | 1999년 |
| 직업 상태 | 직장인 |
| 연소득 | 36,000,000원 |
| 보유 현금 | 8,000,000원 |
| 부채 | 3,000,000원 |
| 월 저축 가능액 | 800,000원 |
| 무주택 여부 | 무주택 |
| 청약통장 가입기간 | 24개월 |
| 관심 특별조건 | 생애최초, 청년 |
| 희망 지역 | 서울, 경기 남부 |
| 희망 면적 | 전용 49~59㎡ 중심 |
| 목표 준비기간 | 18개월 |

---

## 12. 주요 API

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/dashboard` | 대시보드 |
| GET | `/api/auth/me` | 현재 로그인 세션 |
| GET/PUT | `/api/profile` | 사용자 조건 조회/저장 |
| GET/PUT | `/api/account-state` | 로그인 사용자의 선택 공고, 선택 옵션, 추천 결과 상태 |
| POST | `/api/auth/register` | 회원가입 및 세션 로그인 |
| POST | `/api/auth/login` | 로그인 |
| POST | `/api/auth/logout` | 로그아웃 |
| GET/POST/DELETE | `/api/favorites` | 관심목록 |
| GET | `/api/notices` | 전체 공고 목록 |
| GET | `/api/notices?active=1` | 접수 마감일이 오늘 이후인 현재 검토 가능 공고 목록 |
| GET | `/api/notices/map` | 지도 표시용 공고 목록 |
| GET | `/api/notices/{noticeId}` | 공고 상세 |
| GET | `/api/notices/{noticeId}/documents/status` | 공식 문서 분석 상태 |
| POST | `/api/notices/{noticeId}/documents/analyze` | 공식 문서 분석 실행 |
| POST | `/api/notices/{noticeId}/documents/analyze?async=1` | 공식 문서 분석을 pending 상태로 시작 |
| GET | `/api/notices/{noticeId}/unit-options` | 주택형 옵션 |
| GET | `/api/notices/{noticeId}/eligibility-checklists` | 자격 체크리스트 |
| GET | `/api/recommendations/housing` | 추천 청약 |
| GET | `/api/recommendations/funding/{noticeId}?option_id={optionId}` | 선택 주택형 옵션 기준 자금 계획 |
| GET | `/api/recommendations/products` | 금융상품 추천 |
| GET | `/api/recommendations/policies` | 정책 추천 |
| POST | `/api/ai/coach-summary` | 선택 공고/옵션 기준 AI 코치 플랜 |
| POST | `/api/ai/chat` | 전역 챗봇 답변 |

---

## 13. AI 설정

기본값은 OpenAI-compatible Chat Completions API를 호출하는 `openai` 모드입니다. `backend/.env`에 `OPENAI_API_KEY`가 없으면 AI 코치와 전역 챗봇은 template fallback 또는 오류 안내로 내려갈 수 있습니다.

현재 AI 기능은 두 갈래입니다.

| 기능 | 역할 | LLM 사용 |
|---|---|---|
| 전역 챗봇 | 모든 화면에서 서비스 이용 방법, 현재 화면, 청약 관련 질문에 답변 | `AI_PROVIDER=openai`, `AI_ENABLE_LLM_CHAT=true`일 때 LLM 사용 |
| AI 코치 | 사용자가 선택한 공고와 주택형 옵션 기준으로 이번 주 할 일, 공식 확인 포인트, 선택 기준 정리 | `AI_PROVIDER=openai`, `AI_ENABLE_LLM_CHAT=true`일 때 LLM 사용, 로그인 사용자는 같은 입력에 대해 캐시 재사용 |
| PDF 구조 분석 | 공식 공고문에서 주택형, 금액, 일정, 융자금, 서류 근거 추출 | rule-first가 기본이며 `AI_ENABLE_LLM_EXTRACTION=true`일 때만 LLM 보조 |

```env
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
AI_ENABLE_LLM_EXTRACTION=true
AI_ENABLE_LLM_CHAT=true
AI_REQUEST_TIMEOUT=30
OPENAI_API_KEY=본인_API_KEY
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_CHAT_PATH=/chat/completions
```

외부 LLM 호출 없이 rule/template fallback만 확인하고 싶을 때는 아래처럼 바꾼 뒤 Django 서버를 재시작합니다.

```env
AI_PROVIDER=template
AI_ENABLE_LLM_EXTRACTION=false
AI_ENABLE_LLM_CHAT=false
```

HuggingFace/local model serving은 현재 단계에서 사용하지 않습니다. AI 답변은 참고 정보이며 청약 당첨, 신청 가능 여부, 대출 승인, 정책 수급을 확정하지 않습니다.

---

## 14. 자주 나는 문제

### `ModuleNotFoundError: No module named 'django'`

가상환경이 켜져 있지 않거나 패키지가 설치되지 않은 상태입니다.

```bash
source .venv/Scripts/activate
pip install -r backend/requirements.txt
```

### 프론트 화면은 뜨지만 API가 실패함

확인할 것:

- Django 서버가 `localhost:8000`에서 실행 중인지
- `frontend/.env`의 `VITE_API_BASE_URL`이 백엔드 주소를 가리키는지
- 프론트 접속 주소가 `http://localhost:5173/` 또는 `http://127.0.0.1:5173/`인지
- ngrok을 쓰는 경우 `frontend/.env`의 `VITE_API_BASE_URL=/api`인지
- 고정 배포 도메인을 쓰는 경우 `backend/.env`의 `DJANGO_ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`에 접속 주소가 포함되어 있는지
- Django 서버를 CORS 설정 변경 후 재시작했는지

### 청약 지도 화면이 비어 있거나 Kakao 지도가 뜨지 않음

확인할 것:

- `frontend/.env`에 `VITE_KAKAO_MAP_JS_KEY`가 있는지
- Kakao Developers의 JavaScript 키 설정에 `http://localhost:5173` 또는 실제 접속 도메인이 등록되어 있는지
- 프론트 서버를 `.env` 수정 후 재시작했는지
- `/api/notices/map`이 200으로 응답하는지

지도 화면은 Kakao Map JavaScript SDK 키를 사용합니다. 백엔드 `KAKAO_REST_API_KEY`만 넣어서는 브라우저 지도 화면이 뜨지 않습니다.

### Kakao REST API 키의 호출 허용 IP가 유효하지 않다고 나옴

REST API 키의 호출 허용 IP에는 URL을 넣을 수 없습니다. `http://localhost:5173`은 JavaScript 키 도메인에 넣고, REST API 키는 IP 제한을 비워두거나 현재 서버의 외부 IPv4 주소를 넣습니다.

### 지도 위치가 실제 단지보다 넓은 지역 중심으로 보임

LH 공고가 정확한 도로명 주소 없이 지구명만 제공하면 Kakao geocoding이 실패할 수 있습니다. 이 경우 서비스는 지역 fallback 좌표를 사용합니다. `geocode_notice_locations` 명령으로 좌표를 보강하고, 그래도 실패하는 공고는 지도 화면의 위치 정확도 안내를 기준으로 확인합니다.

### 실제 LH 공고가 너무 적게 보임

소유형 공공분양 공고 자체가 시점에 따라 적을 수 있습니다. 기본 설정은 실제 DB 공고를 먼저 보여주고, 17개 광역시·도별 활성 서비스 대상 공고가 `FIRSTHOME_MIN_ACTIVE_SERVICE_NOTICES_PER_REGION`보다 적으면 해당 지역에만 fixture를 보조로 붙입니다.

대시보드와 추천 후보는 접수 마감일이 오늘 이후인 공고만 사용합니다. 마감 지난 공고까지 포함해 목록을 확인하려면 `/api/notices`를, 현재 검토 가능 공고만 확인하려면 `/api/notices?active=1`을 사용합니다.

### AI가 외부 모델을 호출하지 않음

기본값은 `AI_PROVIDER=openai`입니다. `OPENAI_API_KEY`가 비어 있으면 LLM 호출이 실패하거나 template fallback으로 내려갈 수 있습니다. 키를 넣은 뒤 Django 서버를 재시작합니다.

---

## 15. 운영/보안 주의사항

- `.env`와 API Key는 Git, ZIP, 문서, 로그에 포함하지 않습니다.
- `backend/reports/`는 로컬 산출물이므로 공유 여부를 팀 기준으로 정합니다.
- AI prompt와 raw response에는 개인정보가 들어갈 수 있으므로 저장/마스킹 정책을 정해야 합니다.
- 소득, 자산, 부채, 월 저축 가능액은 본인만 접근하도록 인증/세션 정책을 확인합니다.
- 운영 배포 시 `DEBUG=false`, CORS, CSRF, 쿠키 `SameSite`/`Secure`, `ALLOWED_HOSTS`를 별도 점검합니다.
- 추천 결과, 자금 로드맵, AI 답변은 참고 정보이며 실제 신청 전 공식 공고와 기관 기준을 확인해야 합니다.
