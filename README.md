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

## 테스트

```bash
cd backend
python manage.py test apps.recommendations
```

테스트는 대표 사용자 자금 계산, fixture 수량, 추천 점수 구조, 상품/정책 matcher 개인화 여부를 확인합니다.

관심 저장은 MVP 단계에서 세션 기반으로 동작하며 `관심목록` 화면에서 저장한 청약, 상품, 정책을 다시 확인할 수 있습니다. 로그인 기능을 붙이면 `Favorite` 모델을 사용자별 저장소로 전환할 수 있습니다.

## 주의사항

이 서비스의 추천 결과는 공개 데이터와 fixture 기반 참고 정보입니다. 청약 당첨, 정책 수급, 대출 승인, 금융상품 수익을 보장하지 않으며 실제 신청 전 공식 공고와 기관 기준을 반드시 확인해야 합니다.
