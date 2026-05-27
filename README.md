# FirstHome Navigator AI

첫 주택 마련을 준비하는 사용자가 실제 LH 청약 공고와 공식 PDF 공고문을 바탕으로 추천 청약, 주택형 옵션, 분양가, 계약금/중도금/잔금 일정, 자금 부족분, 공식 근거, AI 코치 답변을 확인할 수 있는 서비스입니다.

현재 프로젝트는 다음 방향으로 동작합니다.

- 실제 LH 공고/API 데이터를 우선 사용합니다.
- fixture는 실제 소유형 공고가 너무 적거나 시연 중 외부 API가 불안정할 때만 보조 데이터로 사용합니다.
- AI는 기본값으로 외부 LLM을 호출하지 않는 `template` 모드입니다.
- 공식 PDF 분석 결과가 있으면 주택형별 납부 일정이 우선 사용됩니다.
- 중도금은 0회, 1회, 여러 회차, 10회 이상 모두 가능한 반복 일정으로 처리합니다.
- 추천 점수는 정책을 제외하고 자격 35점, 자금 25점, 지역 30점, 일정 10점의 100점 만점으로 계산합니다.

---

## 1. 기술 스택

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

## 2. 폴더 구조

```text
backend/
  apps/
    profiles/          사용자 조건, 인증, 관심목록
    notices/           공고 모델, LH 수집
    notice_docs/       공식 PDF 분석, 주택형 옵션, 납부 일정
    recommendations/   추천 점수와 추천 API
    funding/           자금 계획 계산
    products/          금융상품
    policies/          청년정책
    ai_coach/          AI 코치
  config/              Django settings, urls
  fixtures/            시연 보조 fixture
  manage.py
  requirements.txt
  requirements-ai.txt

frontend/
  public/
  src/
    api/
    components/
    layouts/
    pages/
    router/
    stores/
    utils/
    main.js
  package.json
  vite.config.js
```

---

## 3. 환경 파일 준비

### Backend

```powershell
cd backend
Copy-Item .env.example .env
```

`backend/.env` 주요 값:

```env
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true

DATA_GO_KR_SERVICE_KEY=
FINLIFE_API_KEY=
YOUTH_POLICY_API_KEY=

FIRSTHOME_ENABLE_FIXTURE_SUPPLEMENT=true
FIRSTHOME_MIN_SERVICE_NOTICES=3

AI_PROVIDER=template
AI_MODEL=gpt-4o-mini
AI_ENABLE_LLM_EXTRACTION=false
AI_ENABLE_LLM_CHAT=false
AI_REQUEST_TIMEOUT=30
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_CHAT_PATH=/chat/completions
LOCAL_LLM_ENDPOINT=
```

### Frontend

```powershell
cd ..\frontend
Copy-Item .env.example .env
```

`frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

Vite에서는 브라우저 코드에서 사용할 환경 변수 이름이 `VITE_`로 시작해야 합니다.

---

## 4. Backend 실행

프로젝트 루트에서 가상환경을 만듭니다.

```powershell
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

현재 기본 기능 실행에는 `backend/requirements.txt`만 필요합니다. 추후 임베딩/로컬 AI 실험용 패키지가 필요하면 별도로 설치합니다.

```powershell
pip install -r backend/requirements-ai.txt
```

DB를 준비하고 서버를 실행합니다.

```powershell
cd backend
python manage.py check
python manage.py migrate
python manage.py runserver localhost:8000
```

확인 URL:

```text
http://localhost:8000/api/dashboard
http://localhost:8000/api/notices
http://localhost:8000/api/recommendations/housing
```

시연용 고정 데이터를 DB에 직접 넣고 싶을 때만 사용합니다.

```powershell
python manage.py load_firsthome_fixture --with-demo-analysis
```

기본 설정에서는 DB에 실제 공고가 부족할 때 fixture가 보조로 붙습니다. 실제 DB 데이터만 확인하고 싶으면 `backend/.env`에서 아래처럼 바꾼 뒤 Django 서버를 재시작합니다.

```env
FIRSTHOME_ENABLE_FIXTURE_SUPPLEMENT=false
```

---

## 5. Frontend 실행

새 터미널에서 실행합니다.

```powershell
cd frontend
npm ci
npm run dev
```

확인 URL:

```text
http://localhost:5173/
```

Windows PowerShell에서 `npm` 실행이 막히면 `npm.cmd`를 사용합니다.

```powershell
npm.cmd ci
npm.cmd run dev
```

프론트엔드는 기본적으로 `http://localhost:8000/api`를 호출합니다. 주소를 바꾸려면 `frontend/.env`의 `VITE_API_BASE_URL`을 수정한 뒤 프론트 서버를 재시작합니다.

---

## 6. 실제 데이터 수집

외부 API를 사용하려면 `backend/.env`에 API 키를 넣어야 합니다.

### LH 청약 공고 수집

```powershell
cd backend

# DB 변경 없이 수집 가능 여부 확인
python manage.py import_lh --dry-run --service-target-only --page-size 100 --max-pages 5 --with-supply-info --supply-limit 30

# 실제 DB 저장
python manage.py import_lh --service-target-only --page-size 100 --max-pages 5 --with-supply-info --supply-limit 30

# 기존 공고를 지우고 다시 수집
python manage.py import_lh --clear --service-target-only --page-size 100 --max-pages 5 --with-supply-info --supply-limit 30
```

### 공식 PDF 분석

```powershell
python manage.py analyze_notice_documents --provider=LH --limit 20 --report-json=reports/lh_actual_readiness.json --report-md=reports/lh_actual_readiness.md
```

### 금융상품 수집

```powershell
python manage.py import_finlife --dry-run
python manage.py import_finlife --clear
```

### 청년정책 수집

```powershell
python manage.py import_youthcenter --dry-run --display 20
python manage.py import_youthcenter --page 1 --display 50
python manage.py import_youthcenter --page 2 --display 50
```

---

## 7. 테스트

### Backend

```powershell
cd backend
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py check_sample_pdf_regression --report-json=reports/sample_pdf_regression_review.json
python manage.py check_representative_flow --report-json=reports/representative_flow_review.json
python manage.py check_ai_chat_smoke --report-json=reports/ai_chat_smoke_review.json
```

### Frontend

```powershell
cd frontend
npm run build
```

---

## 8. 주요 API

| Method | Endpoint | 설명 |
|---|---|---|
| GET | `/api/dashboard` | 대시보드 |
| GET/PUT | `/api/profile` | 사용자 조건 조회/저장 |
| GET/POST/DELETE | `/api/favorites` | 관심목록 |
| GET | `/api/notices` | 공고 목록 |
| GET | `/api/notices?active=1` | 접수 마감일이 오늘 이후인 현재 검토 가능 공고 목록 |
| GET | `/api/notices/{noticeId}` | 공고 상세 |
| GET | `/api/notices/{noticeId}/documents/status` | 공식 문서 분석 상태 |
| POST | `/api/notices/{noticeId}/documents/analyze` | 공식 문서 분석 실행 |
| GET | `/api/notices/{noticeId}/unit-options` | 주택형 옵션 |
| GET | `/api/notices/{noticeId}/eligibility-checklists` | 자격 체크리스트 |
| GET | `/api/recommendations/housing` | 추천 청약 |
| GET | `/api/recommendations/funding/{noticeId}` | 자금 계획 |
| GET | `/api/recommendations/products` | 금융상품 추천 |
| GET | `/api/recommendations/policies` | 정책 추천 |
| POST | `/api/ai/coach-summary` | AI 코치 요약 |
| POST | `/api/ai/chat` | AI 코치 채팅 |

---

## 9. 자주 나는 문제

### `ModuleNotFoundError: No module named 'django'`

가상환경이 켜져 있지 않거나 패키지가 설치되지 않은 상태입니다.

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
```

### PowerShell에서 npm이 막힘

`npm.cmd`를 사용합니다.

```powershell
npm.cmd run dev
```

### 프론트 화면은 뜨지만 API가 실패함

확인할 것:

- Django 서버가 `localhost:8000`에서 실행 중인지
- `frontend/.env`의 `VITE_API_BASE_URL`이 맞는지
- 프론트 접속 주소가 `http://localhost:5173/`인지
- Django 서버를 CORS 설정 변경 후 재시작했는지

### 실제 LH 공고가 너무 적게 보임

소유형 공공분양 공고 자체가 시점에 따라 적을 수 있습니다. 기본 설정은 실제 DB 공고를 먼저 보여주고, 서비스 대상 공고가 `FIRSTHOME_MIN_SERVICE_NOTICES`보다 적으면 fixture를 보조로 붙입니다.

대시보드와 추천 후보는 접수 마감일이 오늘 이후인 공고만 사용합니다. 마감 지난 공고까지 포함해 목록을 확인하려면 `/api/notices`를, 현재 검토 가능 공고만 확인하려면 `/api/notices?active=1`을 사용합니다.

### AI가 외부 모델을 호출하지 않음

기본값은 `AI_PROVIDER=template`입니다. 외부 LLM을 쓰려면 `AI_PROVIDER=openai`, `OPENAI_API_KEY`, `AI_ENABLE_LLM_CHAT=true` 또는 `AI_ENABLE_LLM_EXTRACTION=true`를 설정한 뒤 서버를 재시작합니다.
