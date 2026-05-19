# FirstHome Navigator AI

사회초년생이 청약 조건, 자금 상황, 희망 지역을 입력하면 fixture 기반으로 청약 후보 TOP 3, 계약금 준비 로드맵, 예·적금/정책 후보, AI 코치 체크리스트를 확인하는 MVP입니다.

## 실행 환경

- Python 3.11+
- Node.js 20+
- npm 10+

## 백엔드 실행

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py check
python manage.py migrate
python manage.py load_firsthome_fixture
python manage.py runserver
```

백엔드 기본 주소는 `http://127.0.0.1:8000/api`입니다. 현재 MVP는 외부 API 없이 `backend/fixtures/firsthome_mvp.json`만으로 동작합니다.

실제 외부 API 키를 연결할 때는 `backend/.env.example`을 참고해 `backend/.env`를 만듭니다.

```bash
DJANGO_SECRET_KEY=change-me
DJANGO_DEBUG=true
DATA_GO_KR_SERVICE_KEY=
FINLIFE_API_KEY=
YOUTH_POLICY_API_KEY=
```

## 프론트엔드 실행

```bash
cd frontend
npm ci
npm run build
npm run dev
```

프론트엔드 개발 서버 기본 주소는 `http://localhost:5173`입니다. 다른 API 주소를 쓰려면 `frontend/.env`에 아래 값을 설정합니다.

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

## 대표 시나리오

1. 홈에서 `조건 수정` 또는 `첫 집 준비 시작하기` 흐름으로 이동합니다.
2. 대표 사용자 조건을 저장합니다.
   - 1999년생 직장인
   - 연소득 3,600만 원
   - 보유 현금 800만 원
   - 부채 300만 원
   - 월 저축 가능액 80만 원
   - 청약통장 24개월
   - 희망 지역 서울, 경기 남부
3. 추천 결과에서 TOP 3와 점수 구성, 추천 사유를 확인합니다.
4. 공고 상세에서 자격 조건, 필수 서류, 공식 확인 체크리스트를 확인하고 관심 공고로 저장합니다.
5. 자금 로드맵에서 계약금, 부족액, 월 저축 목표를 확인합니다.
6. 예·적금 상품과 지원정책 후보를 관심목록에 저장합니다.
7. AI 코치에서 이번 주 할 일과 공식 확인 항목을 확인합니다.
8. 관심목록에서 저장한 청약, 상품, 정책을 다시 확인하거나 해제합니다.

대표 사용자 기준 1순위 공고의 자금 계산은 다음과 같이 고정됩니다.

- 분양가: 320,000,000원
- 계약금: 32,000,000원
- 준비 가능 현금: 8,000,000원
- 부족액: 24,000,000원
- 18개월 기준 월 저축 목표: 1,333,334원

MVP에서는 부채를 정밀 대출 심사에 쓰지 않고 참고 정보로만 보며, 준비 가능 현금은 `asset` 기준으로 계산합니다.

## Fixture 구성

`backend/fixtures/firsthome_mvp.json`에는 발표용 샘플 데이터가 들어 있습니다.

- 청약 공고 10건
- 금융상품 10건
- 청년/주거 정책 10건
- 대표 사용자 3명

상품 추천은 목표 기간, 월 저축 가능액, 월 납입 한도, 예금자보호 여부를 기준으로 정렬합니다. 정책 추천은 나이, 희망 지역, 소득, 무주택 여부, 정책 카테고리를 기준으로 정렬합니다.

서비스 API는 DB에 데이터가 있으면 DB를 먼저 사용하고, DB가 비어 있거나 아직 준비되지 않았으면 fixture로 fallback합니다. 실제 API 수집 명령을 추가할 때도 화면 API는 이 조회 구조를 그대로 사용하면 됩니다.

## 실제 금융상품 데이터 수집

금융감독원 금융상품통합비교공시 API 키가 `backend/.env`의 `FINLIFE_API_KEY`에 있으면 예금/적금 상품을 DB로 수집할 수 있습니다.

```bash
cd backend
python manage.py import_finlife --dry-run
python manage.py import_finlife --clear
```

`--dry-run`은 API 호출과 정규화만 확인하고 DB를 바꾸지 않습니다. `--clear`는 기존 금융상품을 지운 뒤 금융감독원 예금/적금 데이터를 새로 저장합니다. 청약 공고와 청년정책 데이터는 건드리지 않습니다.

## 실제 LH 공고 데이터 수집

공공데이터포털 서비스 키가 `backend/.env`의 `DATA_GO_KR_SERVICE_KEY`에 있으면 LH 분양임대공고 목록을 DB로 수집할 수 있습니다.

```bash
cd backend
python manage.py import_lh --dry-run --page-size 20 --max-pages 2
python manage.py import_lh --page-size 100 --max-pages 3
python manage.py import_lh --page-size 100 --max-pages 3 --with-supply-info --supply-limit 50
```

LH 목록 API에는 가격, 계약일, 세부 자격이 빠진 공고가 많습니다. `--with-supply-info`를 붙이면 LH 공급정보 상세 API를 추가 조회해 면적, 주택형, 일부 금액을 보강하고 원본 조회 코드는 `source_meta`에 보관합니다. 그래도 가격이 확인되지 않는 공고는 서비스에서 자금 계산을 추정하지 않고 “공식 공고 확인 필요”로 표시하며, 추천 자금 점수는 보수적으로 반영합니다. `--clear`를 붙이면 기존 청약 공고를 지운 뒤 LH 공고만 저장하므로 발표용 fixture를 유지하려면 생략하는 편이 안전합니다.

## 실제 청년정책 데이터 수집

온통청년 OPEN API 키가 승인되어 `backend/.env`의 `YOUTH_POLICY_API_KEY`에 있으면 청년정책을 DB로 수집할 수 있습니다. 온통청년 공식 문서의 청년정책 목록 URL은 `https://www.youthcenter.go.kr/opi/youthPlcyList.do`이고 인증 파라미터는 `openApiVlak`입니다.

```bash
cd backend
python manage.py import_youthcenter --dry-run --display 20
python manage.py import_youthcenter --display 100
```

키가 아직 승인 전이면 명령은 DB를 건드리지 않고 누락 안내를 출력합니다.

## 테스트

```bash
cd backend
python manage.py test apps.recommendations
```

테스트는 대표 사용자 자금 계산, fixture 수량, 추천 점수 구조, 상품/정책 matcher 개인화 여부를 확인합니다.

관심 저장은 MVP 단계에서 세션 기반으로 동작하며 `관심목록` 화면에서 저장한 청약, 상품, 정책을 다시 확인할 수 있습니다. 로그인 기능을 붙이면 `Favorite` 모델을 사용자별 저장소로 전환할 수 있습니다.

## 주의사항

이 서비스의 추천 결과는 공개 데이터와 fixture 기반 참고 정보입니다. 청약 당첨, 정책 수급, 대출 승인, 금융상품 수익을 보장하지 않으며 실제 신청 전 공식 공고와 기관 기준을 반드시 확인해야 합니다.
