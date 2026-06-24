# FirstHome Beta Test

이 폴더는 실제 사용자 관점 베타 테스트 산출물을 저장한다. 기존 시각 감사 산출물은 제거했고, 여기부터는 ngrok 공개 URL 기준으로 비로그인/회원가입/로그인/동시접속 시나리오를 검증한다.

## 전제

- 기본 대상 URL: `https://polka-kennel-decorated.ngrok-free.dev`
- 유료 ngrok 도메인을 사용하므로 별도 경고 페이지 우회 헤더 없이 실제 사용자 접속 조건으로 검증한다.
- 내부 회귀 테스트가 아니라 실제 화면을 열고 버튼, 폼, API 응답, 콘솔 오류, 로딩 시간, 스크린샷을 기록한다.

## 설치

```bash
cd docs/test
npm install
npx playwright install chromium
```

## 실행

```bash
# 확장 베타 점검: 시각 대비, hover, AI 맥락, 여러 사용자 조건 포함
npm run beta:complete -- https://polka-kennel-decorated.ngrok-free.dev

# 비로그인 + 실제 회원가입 + 로그인 사용자 플로우 점검
npm run beta:flow -- https://polka-kennel-decorated.ngrok-free.dev

# 30명 동시 접속 시연 부하 점검
npm run beta:load -- https://polka-kennel-decorated.ngrok-free.dev 30
```

## 결과물

각 실행은 `docs/test/results/<timestamp>/` 아래에 다음을 저장한다.

- `beta-flow-report.json`: 페이지별 로딩 시간, 콘솔/네트워크 오류, 수행 액션
- `beta-flow-report.md`: 사람이 읽는 요약 보고서
- `beta-complete-report.json`: 시각/상호작용/AI/시나리오 사용자 확장 점검
- `beta-complete-report.md`: 확장 베타 점검 요약
- `beta-load-report.json`: 30개 세션 동시 이용 결과
- `screenshots/`: 주요 화면 캡처

## 판정 기준

- P0: 화면 진입 불가, 회원가입/로그인 실패, 추천/상세/자금/AI 핵심 API 실패, 30인 부하에서 반복 500 발생
- P1: 버튼 동작 불가, 저장/해제 상태 불일치, 챗봇이 화면 맥락과 반대로 답변, 주요 화면 5초 초과
- P2: 일부 문구/디자인/로딩 표시 어색함, 보조 기능 지연, 경미한 콘솔 경고
