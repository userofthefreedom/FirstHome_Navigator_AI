# FirstHome Navigator AI Backend

Django + Django REST Framework 기반 백엔드입니다. 실제 LH 공고, 공식 PDF 분석 결과, rule 기반 추천/자금 계산, 계정 상태, AI 코치/챗봇 API를 제공합니다.

이 문서는 `docs/history/FirstHome_Navigator_AI_개발공유용_확장기획서_v9.0.docx`와 현재 코드 구조를 기준으로 작성했습니다. 전체 프로젝트 실행 흐름은 루트 `README.md`를 우선 확인합니다.

## Backend Role

백엔드는 다음 책임을 갖습니다.

| Area | Responsibility |
|---|---|
| 공고 데이터 | LH 공고 수집, 소유형 공공분양 필터링, active 공고 조회, fixture 보충 |
| 공식 PDF 분석 | 공고문 PDF에서 주택형 옵션, 분양가, 계약금/중도금/잔금/융자금, 서류/자격 근거 추출 |
| Rule 판단 | 공고 분류, 추천 점수, 자금 계산, confidence, 문서 후보 우선순위, 안전 문구 관리 |
| 추천/자금 | 사용자 조건 기반 추천 후보, option_id 기반 자금 로드맵 계산 |
| 지도 | Kakao Local REST API로 좌표 보강, 지도 표시용 공고 API 제공 |
| 계정/상태 | 로그인, 프로필, 관심목록, 선택 공고/옵션 상태 저장 |
| AI | OpenAI-compatible LLM 호출, AI 코치 플랜 캐시, 전역 챗봇 응답, template fallback |

## Stack

- Python 3.11+
- Django 5.0.6
- Django REST Framework
- SQLite 기본 DB
- pypdf, pdfplumber 기반 PDF 파싱
- requests 기반 외부 API 연동
- OpenAI-compatible Chat Completions API

## Directory Map

```text
backend/
  apps/
    ai_coach/        AI client, AI 코치 플랜, 전역 챗봇, safety/smoke check
    funding/         선택 주택형 option_id 기준 자금 로드맵 계산
    notice_docs/     공식 PDF 분석, 주택형 옵션, 납부 일정, 체크리스트
    notices/         LH 공고 수집, 공고 API, 지도 API, 좌표 보강
    policies/        온통청년 정책 수집/추천
    products/        금융감독원 금융상품 수집/추천
    profiles/        사용자 조건, 인증, 관심목록, 계정 선택 상태
    recommendations/ 추천 점수, 후보 랭킹, 추천 API
    rules/           서비스 판단 규칙의 중앙 모듈
    fixture_store.py 실제 데이터 부족 시 fixture 보충 및 직렬화
  config/            Django settings, root urls, ASGI/WSGI
  fixtures/          발표/회귀용 fixture와 sample PDFs
  manage.py
  requirements.txt
```

## Main Apps And Relationships

| App/File | Main Files | Used By |
|---|---|---|
| `apps/rules` | `notice_classification.py`, `scoring.py`, `funding.py`, `confidence.py`, `document_extraction.py`, `document_discovery.py`, `retrieval.py`, `safety.py` | notices, notice_docs, recommendations, funding, ai_coach |
| `apps/notices` | `models.py`, `views.py`, `services/lh.py`, `services/map_locations.py`, `management/commands/import_lh.py`, `geocode_notice_locations.py` | recommendation list, detail page, map page |
| `apps/notice_docs` | `models.py`, `services/analysis.py`, `extractors.py`, `pdf_parser.py`, `validators.py`, `llm_extractors.py` | notice detail, funding, AI coach official checks |
| `apps/recommendations` | `services/ranking.py`, `services/scoring.py`, `views.py` | recommendation page, dashboard, map scoring |
| `apps/funding` | `services/calculator.py`, `views.py` | funding page, AI coach |
| `apps/profiles` | `models.py`, `services.py`, `views.py`, `authentication.py` | all personalized APIs, favorites, account-state |
| `apps/ai_coach` | `services/ai_client.py`, `prompt_templates.py`, `safety_filter.py`, `views.py` | AI coach page, global chatbot |
| `apps/fixture_store.py` | fixture loading, DB materialization, serializers | all public APIs when real data is insufficient |

## Data Flow

```text
External APIs / PDFs
  -> import_finlife / import_youthcenter / import_lh
  -> HousingNotice, Product, Policy DB rows
  -> analyze_notice_documents
  -> NoticeDocument, NoticeExtraction, HousingUnitOption, PaymentSchedule, EligibilityChecklist
  -> recommendations/funding/notices/map APIs
  -> frontend screens
  -> ai_coach/chat with selected notice, option, profile, official refs
```

Fixture는 실제 데이터가 부족한 지역만 보충합니다.

```text
DB actual notices
  -> current_notices()
  -> if active service notices by region < FIRSTHOME_MIN_ACTIVE_SERVICE_NOTICES_PER_REGION
  -> materialize fixture notices
  -> mark as data_source=fixture and hide official source buttons
```

## Environment Variables

`.env.example`을 `.env`로 복사한 뒤 값을 채웁니다.

```bash
cp .env.example .env
```

중요 변수:

| Variable | Purpose |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_DEBUG` | local 개발은 `true`, 배포는 `false` |
| `DATA_GO_KR_SERVICE_KEY` | LH 공고 수집용 공공데이터포털 API 키 |
| `FINLIFE_API_KEY` | 금융감독원 금융상품 API 키 |
| `YOUTH_POLICY_API_KEY` | 온통청년 정책 API 키 |
| `KAKAO_REST_API_KEY` | Kakao Local REST API 좌표 보강 키 |
| `OPENAI_API_KEY` | AI 코치/챗봇/LLM 보조 분석용 OpenAI API 키 |
| `FIRSTHOME_ENABLE_FIXTURE_SUPPLEMENT` | 지역별 fixture 보충 on/off |
| `FIRSTHOME_MIN_ACTIVE_SERVICE_NOTICES_PER_REGION` | 지역별 최소 활성 소유형 공고 수 |

기본 AI 설정:

```env
AI_PROVIDER=openai
AI_MODEL=gpt-4o-mini
AI_ENABLE_LLM_EXTRACTION=true
AI_ENABLE_LLM_CHAT=true
AI_REQUEST_TIMEOUT=30
```

HuggingFace/local model serving은 현재 단계에서 사용하지 않습니다.

## Install

프로젝트 루트에서 가상환경을 만들고 패키지를 설치합니다.

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

HuggingFace/local model serving을 사용하지 않으며, AI 기능은 기본 의존성과 OpenAI-compatible API 호출로 동작합니다.

## Run

```bash
cd backend
python manage.py check
python manage.py migrate
python manage.py runserver localhost:8000
```

확인 API:

```text
http://localhost:8000/api/dashboard
http://localhost:8000/api/notices?active=1
http://localhost:8000/api/notices/map
http://localhost:8000/api/recommendations/housing
```

## Data Commands

### Fixture

발표용 고정 데이터를 DB에 로드합니다. 기존 공고/상품/정책을 지우므로 실제 수집 데이터가 필요할 때는 주의합니다.

```bash
python manage.py load_firsthome_fixture
```

### Financial Products

```bash
python manage.py import_finlife --dry-run
python manage.py import_finlife --clear
```

### Youth Policies

```bash
python manage.py import_youthcenter --dry-run --display 20
python manage.py import_youthcenter --clear --page 1 --display 50
```

### LH Notices

```bash
python manage.py import_lh --dry-run --service-target-only --page-size 100 --max-pages 5 --with-supply-info --supply-limit 30
python manage.py import_lh --service-target-only --page-size 100 --max-pages 5 --with-supply-info --supply-limit 30
```

### PDF Analysis

```bash
python manage.py analyze_notice_documents --provider=LH --exclude-fixture --limit 20 --report-json=reports/lh_actual_readiness.json --report-md=reports/lh_actual_readiness.md
```

### Kakao Geocoding

```bash
python manage.py geocode_notice_locations --dry-run --limit 30
python manage.py geocode_notice_locations --limit 30
```

정확한 주소가 없는 LH 지구명은 Kakao geocoding이 실패할 수 있습니다. 이 경우 지도 API는 지역 fallback 좌표와 위치 정확도 안내를 사용합니다.

## API Groups

| Group | Endpoints |
|---|---|
| Auth/Profile | `GET /api/auth/me`, `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET/PUT /api/profile`, `GET/PUT /api/account-state` |
| Favorites | `GET/POST/DELETE /api/favorites` |
| Notices | `GET /api/notices`, `GET /api/notices/map`, `GET /api/notices/{noticeId}` |
| Notice Documents | `GET /api/notices/{noticeId}/documents/status`, `POST /api/notices/{noticeId}/documents/analyze`, `GET /api/notices/{noticeId}/unit-options`, `GET /api/notices/{noticeId}/eligibility-checklists` |
| Recommendations | `GET /api/recommendations/housing`, `GET /api/recommendations/products`, `GET /api/recommendations/policies` |
| Funding | `GET /api/recommendations/funding/{noticeId}?option_id={optionId}` |
| AI | `POST /api/ai/coach-summary`, `POST /api/ai/chat` |

## Tests And Checks

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Focused checks:

```bash
python manage.py test apps.ai_coach apps.notice_docs
python manage.py test apps.notices apps.recommendations apps.profiles apps.ai_coach
python manage.py check_sample_pdf_regression --report-json=reports/sample_pdf_regression_review.json
python manage.py check_representative_flow --report-json=reports/representative_flow_review.json
python manage.py check_ai_chat_smoke --report-json=reports/ai_chat_smoke_review.json
```

## Local Artifacts

- `db.sqlite3`: local DB
- `reports/`: 분석/회귀/AI smoke 결과
- PDF cache 또는 외부 API 결과물: 로컬 산출물로 취급

API keys, `.env`, raw AI response, 개인정보가 들어간 로그는 커밋하지 않습니다.
