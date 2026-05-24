# FirstHome Navigator AI

사회초년생이 청약 조건, 자금 상황, 희망 지역을 입력하면 청약 후보 TOP 3, 계약금 준비 로드맵, 예·적금/정책 후보, AI 코치 체크리스트를 확인할 수 있는 MVP 웹서비스입니다.

현재 버전은 **Django REST Framework 백엔드 + Vue 3 프론트엔드** 구조이며, 기본 실행은 `backend/fixtures/firsthome_mvp.json` fixture만으로도 가능합니다. API Key를 연결하면 금융상품, LH 공고, 청년정책 데이터를 실제 API에서 수집해 DB에 저장할 수 있습니다.

---

## 1. 주요 기능

- 대표 사용자 조건 입력 및 저장
- 청약/공공주택 추천 TOP 3 조회
- 공고 상세 확인
- 계약금 기준 자금 로드맵 계산
- 예·적금 상품 추천
- 청년/주거 정책 추천
- AI 코치 체크리스트 제공
- 관심 청약/상품/정책 저장 및 관심목록 확인
- fixture 기반 시연 데이터 로드
- 실제 API 기반 데이터 수집 명령 제공

---

## 2. 기술 스택

### Backend

- Python 3.11+
- Django 5.0.6
- Django REST Framework
- django-cors-headers
- drf-spectacular
- SQLite 기본 사용
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

---

## 3. 폴더 구조

```text
firsthome-navigator/
├─ backend/
│  ├─ apps/
│  │  ├─ profiles/             # 프로필, 관심목록
│  │  ├─ notices/              # 공고 모델, LH 수집 command
│  │  ├─ products/             # 금융상품 모델, Finlife 수집 command
│  │  ├─ policies/             # 청년정책 모델, 온통청년 수집 command
│  │  ├─ recommendations/      # 추천 점수, 랭킹, 추천 API
│  │  ├─ funding/              # 자금 계산
│  │  └─ ai_coach/             # AI 코치 템플릿, 안전 문구 필터
│  ├─ config/                  # Django settings, urls
│  ├─ fixtures/                # firsthome_mvp.json
│  ├─ manage.py
│  ├─ requirements.txt
│  └─ .env.example
├─ frontend/
│  ├─ src/
│  │  ├─ api/                  # Axios API wrapper
│  │  ├─ layouts/
│  │  ├─ pages/
│  │  ├─ router/
│  │  ├─ stores/
│  │  ├─ types/
│  │  └─ utils/
│  ├─ package.json
│  └─ vite.config.ts
└─ README.md
```

---

## 4. 환경 변수

백엔드는 `backend/.env`를 읽습니다. 처음 실행 전 `backend/.env.example`을 복사해 `backend/.env`를 만듭니다.

```bash
cd backend
cp .env.example .env
```

Windows PowerShell에서는 다음 명령을 사용할 수 있습니다.

```powershell
Copy-Item .env.example .env
```

`backend/.env` 예시는 아래와 같습니다.

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true

# 공공데이터포털 LH API 서비스 키
DATA_GO_KR_SERVICE_KEY=

# 금융감독원 금융상품통합비교공시 API 키
FINLIFE_API_KEY=

# 온통청년 Open API 키
YOUTH_POLICY_API_KEY=

# AI provider 설정
# 기본값 template은 API 키 없이 템플릿 응답과 규칙 기반 PDF 추출만 사용합니다.
AI_PROVIDER=template
AI_MODEL=gpt-4o-mini
AI_ENABLE_LLM_EXTRACTION=false
AI_ENABLE_LLM_CHAT=false
AI_REQUEST_TIMEOUT=30

# AI_PROVIDER=openai일 때 사용
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_CHAT_PATH=/chat/completions

# AI_PROVIDER=local일 때 사용
LOCAL_LLM_ENDPOINT=
```

> 주의: `backend/.env`에는 실제 API Key가 들어가므로 Git이나 ZIP에 포함하면 안 됩니다. 공유해야 하는 파일은 `.env`가 아니라 `.env.example`입니다.

프론트엔드는 필요하면 `frontend/.env`에 API 주소를 지정합니다.

```bash
cd ../frontend
cp .env.example .env
```

Windows PowerShell에서는 다음 명령을 사용할 수 있습니다.

```powershell
Set-Location ..\frontend
Copy-Item .env.example .env
```

`frontend/.env` 예시는 아래와 같습니다.

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

로그인 세션은 브라우저 쿠키를 사용하므로, 프론트를 `http://localhost:5173/`로 접속한다면 API도 `http://localhost:8000/api`로 맞추는 것을 권장합니다. `localhost`와 `127.0.0.1`을 섞으면 브라우저가 세션 쿠키를 같은 사이트로 취급하지 않아 새로고침 뒤 로그인이 풀린 것처럼 보일 수 있습니다.

---

## 5. 백엔드 실행

### 5-1. 가상환경 생성

프로젝트 루트에서 실행하는 방식을 권장합니다.

```bash
python -m venv .venv
```

Git Bash 기준 활성화:

```bash
source .venv/Scripts/activate
```

PowerShell 기준 활성화:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 5-2. 패키지 설치

```bash
pip install --upgrade pip
pip install -r backend/requirements.txt
```

### 5-3. Django 점검 및 DB 준비

```bash
cd backend
python manage.py check
python manage.py migrate
python manage.py load_firsthome_fixture
```

`load_firsthome_fixture`는 발표/개발용 기본 데이터를 DB에 적재합니다.

현재 fixture에는 아래 데이터가 포함됩니다.

- 청약/공공주택 공고 10건
- 금융상품 10건
- 청년/주거 정책 10건
- 대표 사용자 3명

### 5-4. 백엔드 서버 실행

```bash
python manage.py runserver localhost:8000
```

정상 확인 URL:

```text
http://localhost:8000/api/dashboard
http://localhost:8000/api/recommendations/housing
http://localhost:8000/api/notices
```

---

## 6. 프론트엔드 실행

백엔드 서버를 켜 둔 상태에서 새 터미널을 열고 실행합니다.

```bash
cd frontend
npm ci
npm run build
npm run dev
```

Git Bash 또는 Windows 환경에서 npm 실행이 막히면 `npm.cmd`를 사용합니다.

```bash
npm.cmd ci
npm.cmd run build
npm.cmd run dev
```

프론트 접속 URL:

```text
http://localhost:5173/
```

만약 `http://127.0.0.1:5173/`로 접속해야 하는 환경이라면 Vite를 아래처럼 IPv4 주소에 직접 바인딩합니다.

```bash
npm run dev -- --host 127.0.0.1
```

---

## 7. 기본 화면 확인 흐름

1. 홈 접속
2. 조건 입력/수정 페이지 이동
3. 대표 사용자 조건 저장
4. 추천 결과 TOP 3 확인
5. 추천 카드에서 공고 상세 확인
6. 자금 로드맵 확인
7. 예·적금 상품 및 청년정책 후보 확인
8. 관심 청약/상품/정책 저장
9. AI 코치 체크리스트 확인
10. 관심목록에서 저장 항목 확인/해제
11. 새로고침 후 저장 조건 유지 확인

관심목록은 브라우저 `localStorage`의 `firsthome_client_id`와 백엔드 `Favorite` DB 모델을 기준으로 저장됩니다. 같은 브라우저에서는 새로고침 후에도 저장 항목이 유지되지만, `localStorage`를 지우거나 다른 브라우저를 사용하면 기존 관심목록과 연결되지 않을 수 있습니다.

---

## 8. 대표 사용자 시나리오

- 1999년생 직장인
- 연소득 3,600만 원
- 보유 현금 800만 원
- 부채 300만 원
- 월 저축 가능액 80만 원
- 무주택
- 청약통장 가입 24개월
- 특별조건 관심: 생애최초, 청년
- 희망 지역: 서울, 경기 남부
- 선호 공급유형: 공공분양, 뉴홈, 청년 공공주택
- 목표 준비 기간: 18개월

대표 사용자 기준 1순위 공고의 자금 계산은 다음과 같이 고정됩니다.

- 분양가: 320,000,000원
- 계약금: 32,000,000원
- 준비 가능 현금: 8,000,000원
- 부족액: 24,000,000원
- 18개월 기준 월 저축 목표: 1,333,334원

MVP에서는 부채를 정밀 대출 심사에 쓰지 않고 참고 정보로만 보며, 준비 가능 현금은 `asset` 기준으로 계산합니다.

---

## 9. API Key 신청 대상

현재 코드에서 실제로 사용하는 API Key는 아래 3개입니다.

| 환경변수 | 신청처 | 사용 명령 | 용도 |
|---|---|---|---|
| `DATA_GO_KR_SERVICE_KEY` | 공공데이터포털 | `import_lh` | LH 분양임대공고 목록 및 공급정보 상세 수집 |
| `FINLIFE_API_KEY` | 금융감독원 금융상품통합비교공시 | `import_finlife` | 예금/적금 금융상품 수집 |
| `YOUTH_POLICY_API_KEY` | 온통청년 | `import_youthcenter` | 청년정책 수집 |



---

## 10. 실제 금융상품 데이터 수집

금융감독원 금융상품통합비교공시 API Key를 `backend/.env`의 `FINLIFE_API_KEY`에 넣으면 예금/적금 상품을 DB로 수집할 수 있습니다.

```bash
cd backend

# API 호출과 정규화만 확인하고 DB를 바꾸지 않음
python manage.py import_finlife --dry-run

# 기존 금융상품을 지운 뒤 예금/적금 데이터를 새로 저장
python manage.py import_finlife --clear

# 적금만 수집
python manage.py import_finlife --kind saving --clear

# 예금만 수집
python manage.py import_finlife --kind deposit --clear
```

확인 URL:

```text
http://127.0.0.1:8000/api/recommendations/products
```

참고:

- `--dry-run`은 DB를 변경하지 않습니다.
- `--clear`는 기존 금융상품을 삭제한 뒤 새로 저장합니다.
- 청약 공고와 청년정책 데이터는 건드리지 않습니다.
- 기본 금융권역 코드는 `020000`이며 은행권 기준입니다.

---

## 11. 실제 LH 공고 데이터 수집

공공데이터포털 서비스 키를 `backend/.env`의 `DATA_GO_KR_SERVICE_KEY`에 넣으면 LH 분양임대공고 목록을 DB로 수집할 수 있습니다.

```bash
cd backend

# 작게 테스트하고 DB 변경 없음
python manage.py import_lh --dry-run --page-size 20 --max-pages 2

# 목록 데이터를 DB에 저장
python manage.py import_lh --page-size 100 --max-pages 3

# 공급정보 상세 API까지 조회해 면적, 주택형, 일부 금액 보강
python manage.py import_lh --page-size 100 --max-pages 3 --with-supply-info --supply-limit 50

# 기존 청약 공고를 모두 지우고 LH 공고만 다시 저장
python manage.py import_lh --clear --page-size 100 --max-pages 3 --with-supply-info --supply-limit 50
```

확인 URL:

```text
http://127.0.0.1:8000/api/notices
http://127.0.0.1:8000/api/recommendations/housing
```

주의:

- `--clear`를 붙이면 기존 fixture 공고도 지워집니다.
- 발표용 기본 데이터를 유지하고 싶다면 `--clear` 없이 먼저 테스트하세요.
- LH 목록 API에는 가격, 계약일, 세부 자격이 빠진 공고가 많습니다.
- 가격이 확인되지 않는 공고는 서비스에서 자금 계산을 추정하지 않고 “공식 공고 확인 필요”로 표시합니다.
- `--with-supply-info`를 쓰려면 공공데이터포털에서 LH 분양임대공고별 공급정보 조회 서비스도 활용승인되어 있어야 합니다.

---

## 12. 실제 청년정책 데이터 수집

온통청년 OPEN API Key를 `backend/.env`의 `YOUTH_POLICY_API_KEY`에 넣으면 청년정책을 DB로 수집할 수 있습니다.

```bash
cd backend

# API 호출과 정규화만 확인하고 DB를 바꾸지 않음
python manage.py import_youthcenter --dry-run --display 20

# 청년정책 100건 기준 수집
python manage.py import_youthcenter --page 1 --display 50
python manage.py import_youthcenter --page 2 --display 50

# 검색어 제한 - 온통청년 API 응답 정책에 따라 기대처럼 필터링되지 않을 수 있음
python manage.py import_youthcenter --display 100 --query 청년주거
python manage.py import_youthcenter --display 100 --keyword 월세
```

확인 URL:

```text
http://127.0.0.1:8000/api/recommendations/policies
```

참고:

- 온통청년 키는 신청 후 담당자 심사를 거쳐 승인됩니다.
- 키가 아직 승인되지 않았다면 명령은 실패하거나 누락 안내를 출력합니다.
- 온통청년 testbed에서 청년정책 `apiSn=86`은 `https://www.youthcenter.go.kr/go/ythip/getPlcy`로 요청됩니다.
- 현재 코드의 인증 파라미터 이름은 `apiKeyNm`입니다.
- 현재 코드의 페이지 파라미터는 testbed JSON 응답 기준으로 `pageNum`, `pageSize`를 사용합니다.
- 여러 페이지를 수집하려면 `--page` 값을 바꿔 여러 번 실행합니다.
- `--query`, `--keyword`는 온통청년 testbed 프록시에서 기대처럼 필터링되지 않을 수 있으므로 수집 후 서비스 추천 점수로 걸러 보는 흐름을 권장합니다.

---

## 13. 추천 데이터 수집 순서

처음 팀원이 데이터를 가져올 때는 아래 순서를 권장합니다.

```bash
cd backend

# 1. 발표 안정용 기본 데이터 적재
python manage.py load_firsthome_fixture

# 2. 금융상품 API 연결 확인
python manage.py import_finlife --dry-run

# 3. 실제 금융상품 저장
python manage.py import_finlife --clear

# 4. 온통청년 API 연결 확인
python manage.py import_youthcenter --dry-run --display 20

# 5. 실제 청년정책 저장
python manage.py import_youthcenter --page 1 --display 50
python manage.py import_youthcenter --page 2 --display 50
python manage.py import_youthcenter --page 3 --display 50

# 6. LH 목록 API 연결 확인
python manage.py import_lh --dry-run --page-size 20 --max-pages 2

# 7. 실제 LH 공고 및 상세 보강 저장
python manage.py import_lh --page-size 100 --max-pages 3 --with-supply-info --supply-limit 50
```

---

## 14. API 라우트

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/dashboard` | 대시보드 데이터 |
| GET | `/api/auth/me` | 현재 로그인 사용자 확인 |
| POST | `/api/auth/register` | 회원가입 후 로그인 |
| POST | `/api/auth/login` | 로그인 |
| POST | `/api/auth/logout` | 로그아웃 |
| GET/PUT | `/api/profile` | 프로필 조회/저장 |
| GET/POST/DELETE | `/api/favorites` | 관심목록 조회/저장/삭제 |
| GET | `/api/notices` | 공고 목록 |
| GET | `/api/notices/{noticeId}` | 공고 상세 |
| GET | `/api/recommendations/housing` | 청약/공공주택 추천 TOP 3 |
| GET | `/api/recommendations/funding/{noticeId}` | 자금 로드맵. `option_id` query를 주면 주택형 옵션 납부 일정 기준으로 계산 |
| GET | `/api/recommendations/products` | 금융상품 추천 |
| GET | `/api/recommendations/policies` | 청년정책 추천 |
| POST | `/api/ai/coach-summary` | AI 코치 요약 |
| POST | `/api/ai/chat` | 템플릿 fallback 또는 LLM provider 기반 AI 코치 채팅 |

로그인 사용자의 `/api/profile`과 `/api/favorites`는 Django `User` 기준으로 DB에 저장됩니다. 비로그인 사용자는 기존 시연 흐름 유지를 위해 세션 프로필과 `firsthome_client_id` 기반 관심목록 fallback을 사용합니다. 비로그인 상태에서 저장한 관심목록은 로그인/회원가입 시 계정으로 병합됩니다.

### AI provider 동작

- `AI_PROVIDER=template`: 기본값입니다. 외부 API 없이 규칙 기반 PDF 파서와 템플릿 AI 코치 응답을 사용합니다.
- `AI_PROVIDER=openai`: OpenAI 호환 Chat Completions 엔드포인트를 호출합니다. `OPENAI_API_KEY`가 필요합니다.
- `AI_PROVIDER=local`: `LOCAL_LLM_ENDPOINT`에 지정한 로컬 OpenAI 호환 Chat Completions 서버를 호출합니다.
- `AI_ENABLE_LLM_EXTRACTION=true`: 규칙 기반 PDF 추출이 부족하거나 검증 경고가 있을 때 LLM structured output 추출을 시도합니다.
- `AI_ENABLE_LLM_CHAT=true`: `/api/ai/chat`에서 LLM 답변을 우선 사용하고 실패 시 템플릿 fallback을 사용합니다.

LLM 결과는 바로 확정값으로 사용하지 않고 `notice_docs` 검증 로직을 통과한 뒤 화면에 병합됩니다. 채팅 로그는 `AiChatLog`, 문서 추출 호출 로그는 `AiExtractionResult`에 저장됩니다.

화면과 API에서 확인할 수 있는 source 값은 아래처럼 해석합니다.

| Source | 의미 |
|---|---|
| `template_fallback` | 외부 LLM 없이 템플릿으로 생성한 AI 코치 응답 |
| `llm` | 설정된 LLM provider가 생성한 AI 코치 응답 |
| `mock-v1` / `mock` | PDF 원문 분석 전 시연용 fallback 추출 결과 |
| `rules-v1` / `rules` | 규칙 기반 PDF 텍스트 추출과 검증 결과 |
| `llm-v1` / `llm` | LLM structured output 추출 후 검증을 통과한 결과 |
| `llm_cache` | 같은 입력 해시의 이전 LLM 추출 로그를 재사용한 결과 |

AI 채팅 응답은 420자 이내로 잘리고, 당첨·신청 가능·대출 승인 같은 확정 표현은 서버에서 한 번 더 안전 문구로 치환됩니다. `/api/ai/chat` 응답의 `source`로 `llm` 또는 `template_fallback` 여부를 확인할 수 있습니다.

공고문 분석 버튼을 누른 뒤 DB 저장 상태는 아래 API로 확인합니다.

```text
GET /api/notices/{noticeId}/documents/status
GET /api/notices/{noticeId}/unit-options
```

`documents/status`의 `latest_extraction.schema_version`, `latest_extraction.source`, `latest_extraction.status`, `unit_option_count`를 보면 `rules-v1`, `llm-v1`, `mock-v1` 중 어떤 경로로 저장되었는지 확인할 수 있습니다.

---

## 15. 테스트

```bash
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py check_sample_pdf_regression --report-json=reports/sample_pdf_regression_review.json
python manage.py check_representative_flow --report-json=reports/representative_flow_review.json
python manage.py check_ai_chat_smoke --report-json=reports/ai_chat_smoke_review.json

cd ../frontend
npm run build
```

테스트는 아래 내용을 확인합니다.

- 대표 사용자 자금 계산
- fixture 수량
- 추천 점수 구조
- 상품/정책 matcher 개인화 여부
- `/api/ai/chat` fallback 응답, 길이 제한, 안전 문구 치환
- 공고문 분석 후 `NoticeExtraction`, `HousingUnitOption`, `PaymentSchedule` 저장 상태와 source 표시

DB 상태를 명확히 나누어 확인할 때는 아래 기준을 사용합니다.

```bash
cd backend

# 발표/개발용 fixture 상태로 되돌림
python manage.py load_firsthome_fixture --with-demo-analysis

# 실제 LH 수집 상태로 전환하거나 보강
python manage.py import_lh --page-size 100 --max-pages 3 --with-supply-info --supply-limit 50
python manage.py analyze_notice_documents --limit 10 --report-json=reports/lh_actual_readiness_review.json

# AI 채팅 LLM 연결까지 강제 확인하고 싶을 때
python manage.py check_ai_chat_smoke --require-llm --report-json=reports/ai_chat_smoke_review.json
```

`check_ai_chat_smoke`는 기본적으로 template fallback도 정상 smoke로 인정합니다. 실제 LLM 호출을 필수로 볼 때만 `--require-llm`을 붙입니다.

---

## 16. 자주 나는 문제

### 16-1. `ModuleNotFoundError: No module named 'django'`

가상환경이 활성화되지 않았거나 패키지가 설치되지 않은 상태입니다.

```bash
source .venv/Scripts/activate
pip install -r backend/requirements.txt
```

### 16-2. PowerShell에서 activate가 막힘

PowerShell 실행 정책 문제일 수 있습니다. Git Bash를 쓰거나 PowerShell에서 아래 명령을 실행합니다.

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 16-3. npm 명령이 막힘

Windows/Git Bash에서는 `npm.cmd`를 사용합니다.

```bash
npm.cmd run dev
```

### 16-4. CORS 오류

백엔드와 프론트는 기본적으로 `localhost` 기준으로 실행합니다. 다른 주소를 쓴다면 `backend/config/settings.py`의 `CORS_ALLOWED_ORIGINS`와 `frontend/.env`의 `VITE_API_BASE_URL`을 확인하세요. 로그인 세션을 테스트할 때는 프론트와 API의 호스트명을 `localhost` 또는 `127.0.0.1` 중 하나로 통일하세요.

브라우저 개발자도구 또는 Django 로그에서 `OPTIONS` 요청만 보이고 실제 `GET`/`POST`가 이어지지 않으면 CORS preflight 단계에서 막힌 것입니다. 관심목록 API는 `X-FirstHome-Client-Id` 헤더를 사용하므로 `x-firsthome-client-id`가 `CORS_ALLOW_HEADERS`에 포함되어 있어야 합니다. 설정을 바꾼 뒤에는 Django 서버를 재시작합니다.

### 16-5. API Key 오류

아래를 확인하세요.

- `backend/.env` 파일이 실제로 존재하는지
- 변수명이 정확한지
- 활용신청이 승인되었는지
- 공공데이터포털 키가 Encoding/Decoding 형식 중 어떤 형식으로 동작하는지
- 서버를 재시작했는지

### 16-6. 실제 API를 수집했는데 화면이 fixture처럼 보임

DB에 실제 데이터가 들어갔는지 먼저 확인하세요. 현재 서비스는 DB 데이터가 있으면 DB를 우선 사용하고, DB가 비어 있거나 준비되지 않았으면 fixture로 fallback합니다.

확인 URL:

```text
http://127.0.0.1:8000/api/notices
http://127.0.0.1:8000/api/recommendations/products
http://127.0.0.1:8000/api/recommendations/policies
```

---

## 17. 보안 및 공유 주의사항

아래 파일/폴더는 Git 또는 ZIP 공유 대상에서 제외해야 합니다.

```gitignore
backend/.env
backend/db.sqlite3
**/__pycache__/
.venv/
backend/.venv/
frontend/node_modules/
frontend/dist/
```

이미 API Key가 포함된 `.env`를 공유했다면 해당 키는 폐기하거나 재발급하는 것이 안전합니다.
