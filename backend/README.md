# FirstHome Navigator AI Backend

Django REST Framework 기반 백엔드입니다. 청약 공고 수집, 공식 PDF 분석, 추천 점수 계산, 자금 로드맵, 금융상품/정책/대출 추천, 지도/장소 API, 커뮤니티, AI 코치 API를 제공합니다.

전체 프로젝트 실행 순서는 루트 `README.md`를 우선 확인합니다.

## 역할

| 영역 | 설명 |
|---|---|
| 인증/프로필 | 회원가입, 로그인, 로그아웃, 세션 인증, 사용자 조건, 계정 상태, 관심 저장 |
| 청약 공고 | LH 공고 수집, 공고 목록/상세, 지도 표시용 공고, fixture 보강 |
| 공식 PDF 분석 | PDF 발견/다운로드/파싱, 주택형 옵션, 납부 일정, 체크리스트, 분석 상태 |
| 추천 | 자격, 자금, 지역, 일정 점수 기반 청약 추천 |
| 자금 로드맵 | option_id 기준 계약금, 중도금, 잔금, 융자금, 부족액, 월 준비 목표 계산 |
| 금융상품 | 금융감독원 예적금 상품 수집, 기간별 금리 옵션, 가입 후보 저장 |
| 정책/대출 | 청년/주거 정책 추천, 주택 구입 목적 대출 후보 추천 |
| 경제 지표 | 부동산, 환율, 금, 시장 지표 데이터 제공 |
| 지도/장소 | Kakao Local REST API 기반 주변 은행/부동산 검색, 길찾기 URL 제공 |
| 커뮤니티 | 청약 아고라 게시글과 댓글 CRUD |
| AI | SSAFY GMS OpenAI 호환 API 기반 AI 코치, 전역 챗봇, LLM 보조 PDF 분석 |

## 기술 스택

- Python 3.11+
- Django 5.0.6
- Django REST Framework
- drf-spectacular
- SQLite 기본 DB
- pypdf, pdfplumber
- requests
- waitress
- SSAFY GMS OpenAI 호환 Chat Completions API

## 앱 구조

```text
backend/
  apps/
    profiles/          인증, 사용자 조건, 계정 상태, 관심 저장
    notices/           청약 공고 모델, LH 수집, 지도용 공고, fixture 보강
    notice_docs/       공식 PDF 분석, 주택형 옵션, 납부 일정, 체크리스트
    recommendations/   청약/금융상품/정책/대출 추천 API
    funding/           자금 로드맵 계산 API
    products/          금융상품, 기간별 금리 옵션, 가입 후보
    policies/          청년/주거 정책 수집과 추천
    market/            경제 NOW 지표
    places/            Kakao 장소 검색과 길찾기
    videos/            YouTube 영상 검색
    community/         청약 아고라 게시글/댓글
    ai_coach/          AI 코치, 전역 챗봇, 안전 필터
    rules/             추천/자금/지역/PDF/정책/상품 판단 규칙
    fixture_store.py   실제 데이터 부족분 보강용 fixture 로더
  config/              settings, urls, wsgi/asgi
  fixtures/            시연 보강 데이터와 sample PDFs
```

## 주요 API 그룹

| 그룹 | 대표 엔드포인트 |
|---|---|
| Auth / Account | `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` |
| Profile | `GET/PUT /api/profile`, `GET/PUT /api/account-state`, `/api/favorites` |
| Housing Notices | `GET /api/notices`, `GET /api/notices/{notice_id}`, `GET /api/notices/map` |
| Notice Documents | `POST /api/notices/{notice_id}/documents/analyze`, `GET /api/notices/{notice_id}/unit-options` |
| Recommendations | `GET /api/recommendations/housing`, `GET /api/recommendations/products`, `GET /api/recommendations/policies`, `GET /api/recommendations/loans` |
| Funding | `GET /api/recommendations/funding/{notice_id}?option_id={option_id}` |
| AI Coach | `POST /api/ai/coach-summary`, `GET /api/ai/coach-summary/latest`, `POST /api/ai/chat` |
| Financial Products | `GET /api/products`, `GET /api/products/{product_id}`, `POST /api/products/{product_id}/join` |
| Market | `GET /api/market/assets`, `GET /api/market/summary` |
| Places | `GET /api/places/search`, `GET /api/places/route` |
| Community | `GET/POST /api/agora/posts`, `PUT/DELETE /api/agora/posts/{post_id}` |
| Videos | `GET /api/videos/default`, `GET /api/videos/search` |

Swagger 문서:

```text
http://localhost:8000/api/docs
http://localhost:8000/api/schema
http://localhost:8000/api/redoc
```

## 환경 변수

`backend/.env.example`을 복사해 `backend/.env`를 만듭니다.

```bash
cd backend
cp .env.example .env
```

주요 값:

| 변수 | 설명 |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key |
| `DJANGO_DEBUG` | 개발 중 `true`, 시연/배포 시 상황에 맞게 조정 |
| `DJANGO_ALLOWED_HOSTS` | 고정 배포 도메인 추가 |
| `CORS_ALLOWED_ORIGINS` | 프론트엔드 origin 추가 |
| `CSRF_TRUSTED_ORIGINS` | 프론트엔드 origin 추가 |
| `DATA_GO_KR_SERVICE_KEY` | LH/공공데이터 API |
| `FINLIFE_API_KEY` | 금융감독원 금융상품 API |
| `YOUTH_POLICY_API_KEY` | 청년정책 API |
| `KAKAO_REST_API_KEY` | Kakao Local REST API |
| `YOUTUBE_API_KEY` | YouTube 검색 API |
| `GMS_API_KEY` | SSAFY GMS OpenAI 호환 API |
| `AI_PROVIDER` | 기본값 `gms_openai` |
| `FIRSTHOME_ENABLE_FIXTURE_SUPPLEMENT` | 실제 데이터 부족분 fixture 보강 여부 |
| `FIRSTHOME_MATERIALIZE_FIXTURE_ON_READ` | 조회 중 fixture DB 생성 여부. 시연 안정성상 `false` 권장 |

## 설치

프로젝트 루트에서 실행합니다.

```bash
python -m venv .venv
source .venv/Scripts/activate
python -m pip install --upgrade pip
pip install -r backend/requirements.txt
```

## 개발 서버 실행

```bash
cd backend
python manage.py check
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

## 시연 서버 실행

```bash
cd backend
waitress-serve --listen=127.0.0.1:8000 --threads=8 config.wsgi:application
```

## 데이터 준비 명령

Fixture 보강:

```bash
python manage.py sync_fixture_supplements
```

금융상품:

```bash
python manage.py import_finlife --dry-run
python manage.py import_finlife
python manage.py import_finlife --repair-only
```

청년정책:

```bash
python manage.py import_youthcenter --dry-run
python manage.py import_youthcenter
```

LH 공고:

```bash
python manage.py import_lh --dry-run
python manage.py import_lh
```

공식 PDF 분석:

```bash
python manage.py analyze_notice_documents --dry-run
python manage.py analyze_notice_documents
python manage.py analyze_notice_documents --force
```

지도 좌표 보강:

```bash
python manage.py geocode_notice_locations --dry-run
python manage.py geocode_notice_locations
```

아고라 샘플 데이터:

```bash
python manage.py seed_agora
```

## 테스트

```bash
cd backend
python manage.py test
```

필요 시 특정 앱만 실행합니다.

```bash
python manage.py test apps.recommendations apps.funding apps.products apps.ai_coach
```

## 규칙 문서

추천과 판단 규칙은 다음 두 위치를 함께 확인합니다.

- 실행 코드: `backend/apps/rules/`
- 설명 문서: `docs/detail/rules_detail.txt`
- 제출용 알고리즘 문서: `docs/submit/docs_submit/recommendation_algorithm_detail.txt`
