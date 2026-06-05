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
    rules/             분류, 점수, 자금, 신뢰도, 문서 추출 규칙
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
VITE_API_BASE_URL=http://localhost:8000/api
VITE_KAKAO_MAP_JS_KEY=
```

Vite에서는 브라우저 코드에서 사용할 환경 변수 이름이 `VITE_`로 시작해야 합니다.

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

현재 기본 기능 실행에는 `backend/requirements.txt`만 필요합니다. 임베딩/로컬 AI 실험용 패키지가 필요할 때만 별도로 설치합니다.

```bash
pip install -r backend/requirements-ai.txt
```

DB를 준비하고 서버를 실행합니다.

```bash
cd backend
python manage.py check
python manage.py migrate
python manage.py runserver localhost:8000
```

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

## 8. 다음부터 다시 실행할 때

가상환경, `node_modules`, DB가 이미 준비된 뒤에는 전체 설치 과정을 반복할 필요가 없습니다.

백엔드:

```bash
source .venv/Scripts/activate
cd backend
python manage.py runserver localhost:8000
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

1. 금융상품을 수집합니다.
2. 청년정책을 수집합니다.
3. LH 청약 공고를 수집합니다.
4. 실제 공고의 공식 PDF 분석을 실행합니다.
5. Kakao Local REST API로 지도 위치 좌표를 보강합니다.
6. 서버를 실행하고 추천/상세/지도 화면에서 실제 데이터와 fixture 보충 결과를 확인합니다.

### 9.1 금융상품 수집

금융감독원 금융상품 API에서 예금/적금 상품을 가져옵니다. 실제 DB에 저장하기 전에 `--dry-run`으로 API 키와 응답을 먼저 확인합니다.

```bash
cd backend
python manage.py import_finlife --dry-run
python manage.py import_finlife --clear
```

`--clear`는 기존 금융상품을 지우고 새로 저장합니다.

### 9.2 청년정책 수집

온통청년 정책 API에서 정책 후보를 가져옵니다. 정책 API는 검색어 필터가 기대와 다르게 동작할 수 있으므로 넓게 수집한 뒤 서비스 내부 matcher가 나이, 지역, 소득, 무주택 여부, 정책 카테고리 기준으로 정렬합니다.

```bash
python manage.py import_youthcenter --dry-run --display 20
python manage.py import_youthcenter --clear --page 1 --display 50
python manage.py import_youthcenter --page 2 --display 50
```

### 9.3 LH 청약 공고 수집

공공데이터포털 LH API에서 청약 공고를 가져옵니다. 현재 서비스는 소유형 청약을 대상으로 하므로 `--service-target-only`를 권장합니다.

```bash
# DB 변경 없이 수집 가능 여부 확인
python manage.py import_lh --dry-run --service-target-only --page-size 100 --max-pages 5 --with-supply-info --supply-limit 30

# 실제 DB 저장
python manage.py import_lh --service-target-only --page-size 100 --max-pages 5 --with-supply-info --supply-limit 30
```

기존 공고를 지우고 다시 수집해야 할 때만 `--clear`를 사용합니다.

```bash
python manage.py import_lh --clear --service-target-only --page-size 100 --max-pages 5 --with-supply-info --supply-limit 30
```

주요 옵션:

| 옵션 | 설명 |
|---|---|
| `--service-target-only` | 공공분양/신혼희망타운/민간참여/잔여세대 공공분양 등 소유형 서비스 대상만 저장합니다. |
| `--page-size` | 한 페이지에서 가져올 공고 수입니다. |
| `--max-pages` | 가져올 최대 페이지 수입니다. `0`이면 가능한 모든 페이지를 조회합니다. |
| `--with-supply-info` | LH 공급정보 상세 API까지 조회해 주택형, 면적, 일부 분양가를 보강합니다. |
| `--supply-limit` | 공급정보 상세 조회 개수를 제한합니다. `0`이면 모든 수집 공고를 대상으로 조회합니다. |
| `--clear` | 기존 공고를 지우고 새로 저장합니다. 실제 수집 데이터를 보존해야 하면 사용하지 않습니다. |

### 9.4 공식 PDF 분석

LH 공고 수집 후 공식 PDF 분석을 실행하면 상세 화면과 자금 로드맵에서 PDF 기반 주택형 옵션, 계약금, 중도금, 잔금, 융자금 일정이 우선 사용됩니다.

```bash
python manage.py analyze_notice_documents --provider=LH --exclude-fixture --limit 20 --report-json=reports/lh_actual_readiness.json --report-md=reports/lh_actual_readiness.md
```

이미 분석된 공고까지 다시 분석하려면 `--force`를 추가합니다.

```bash
python manage.py analyze_notice_documents --provider=LH --exclude-fixture --force --limit 20
```

fixture 공고는 실제 PDF URL이 없으므로 외부 문서를 내려받지 않습니다. fixture의 분석 버튼은 미리 준비된 fixture 분석 결과를 같은 형식으로 반영합니다.

### 9.5 지도 위치 좌표 보강

청약 지도는 저장된 좌표가 있으면 그 좌표를 사용하고, 없으면 지역 기준 fallback 좌표를 사용합니다. 실제 단지 위치에 가깝게 표시하려면 `backend/.env`에 `KAKAO_REST_API_KEY`를 넣고 좌표 보강 명령을 실행합니다.

먼저 DB 변경 없이 결과를 확인합니다.

```bash
python manage.py geocode_notice_locations --dry-run --limit 30
```

문제가 없으면 실제 좌표를 저장합니다.

```bash
python manage.py geocode_notice_locations --limit 30
```

이미 좌표가 있는 공고까지 다시 보정해야 할 때만 `--overwrite`를 사용합니다.

```bash
python manage.py geocode_notice_locations --overwrite --limit 30
```

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
12. 관심목록에서 공고/옵션/상품/정책 저장 항목 확인 및 삭제
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
- `frontend/.env`의 `VITE_API_BASE_URL`이 맞는지
- 프론트 접속 주소가 `http://localhost:5173/` 또는 `http://127.0.0.1:5173/`인지
- `backend/config/settings.py`의 `CORS_ALLOWED_ORIGINS`에 접속 주소가 포함되어 있는지
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
