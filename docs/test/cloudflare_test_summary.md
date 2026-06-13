# Cloudflare 배포 실사용 점검 요약

- 점검 일시: 2026-06-14 01:02 KST
- 프론트 배포 주소: https://campaigns-singing-environments-undergraduate.trycloudflare.com
- 확인된 API 주소: https://drawing-newest-definition-mud.trycloudflare.com/api
- 백엔드 실행 방식: `waitress-serve --listen=127.0.0.1:8000 config.wsgi:application`
- 점검 방식: 실제 배포 URL 접속, 브라우저 E2E, 회원가입/로그인, AI 코치, 챗봇, 30명 동시접속 HTTP 부하

## 1. 로그인/비로그인 전 과정 점검

결과: 통과

확인한 흐름:

- 비로그인 첫 화면 진입
- 조건 입력, 추천 청약, 청약 지도, 자금 로드맵, AI 코치, 관심목록 메뉴 이동
- 회원가입 화면 전환
- 신규 계정 생성 및 로그인 상태 확인
- 추천 청약 목록 진입
- 공고 상세 화면 진입
- 자금 로드맵 화면 진입
- AI 코치 화면 진입
- 전역 챗봇 질문 전송 및 답변 화면 확인

브라우저 점검 명령:

```bash
$env:BASE_URL='https://campaigns-singing-environments-undergraduate.trycloudflare.com'
npx.cmd playwright test docs/test/cloudflare_full_check.spec.js --reporter=line
```

결과:

- 1개 테스트 통과
- 소요 시간 약 27초
- 심각한 콘솔 오류나 4xx/5xx 응답 없음
- 화면 이동 중 `net::ERR_ABORTED`가 일부 발생했지만, 이는 라우트 전환 중 이전 요청이 취소되는 브라우저 동작으로 테스트 실패 대상에서 제외

주요 증빙 스크린샷:

- `cloudflare_01_dashboard_guest.png`
- `cloudflare_02_auth.png`
- `cloudflare_04_logged_in.png`
- `cloudflare_05_notice_detail.png`
- `cloudflare_06_funding.png`
- `cloudflare_07_ai_coach.png`
- `cloudflare_08_chatbot.png`

## 2. 30명 동시접속 점검

결과: 통과

점검 내용:

- 30명의 가상 사용자가 동시에 프론트 주요 페이지와 백엔드 핵심 API 요청
- 각 사용자별 회원가입 세션 생성
- 각 사용자별 AI 챗 요청 전송

부하 점검 명령:

```bash
node docs/test/cloudflare_ai_load_check.mjs https://campaigns-singing-environments-undergraduate.trycloudflare.com https://drawing-newest-definition-mud.trycloudflare.com/api 30
```

요약:

- 전체 요청: 270건
- 성공: 270건
- 실패: 0건
- AI 챗: 30건 모두 성공
- 회원가입: 30건 모두 성공
- 총 소요: 약 151초
- p50/p90/p95/max: 11.2초 / 36.4초 / 41.8초 / 52.6초

엔드포인트별 핵심 결과:

| 구분 | 성공 | 실패 | 최대 응답 |
|---|---:|---:|---:|
| 프론트 홈 | 30 | 0 | 829ms |
| 프론트 추천 페이지 | 30 | 0 | 294ms |
| 대시보드 API | 30 | 0 | 26.7초 |
| 추천 API | 30 | 0 | 23.8초 |
| 지도 API | 30 | 0 | 52.6초 |
| 자금 API | 30 | 0 | 43.1초 |
| 회원가입 | 30 | 0 | 11.5초 |
| 로그인 세션 확인 | 30 | 0 | 36.4초 |
| AI 챗 | 30 | 0 | 37.6초 |

## 해석

`waitress`로 백엔드를 실행한 뒤에는 이전 `runserver` 기반 테스트에서 발생했던 `/api/dashboard` 502가 재현되지 않았습니다. 실제 화면 기준 주요 흐름과 30명 동시접속 + AI 호출이 모두 성공했으므로, 발표용 실행 방식으로 `waitress`를 사용하는 판단은 타당합니다.

다만 지도 API, 자금 API, AI 챗은 동시 요청 시 최대 수십 초까지 걸릴 수 있습니다. 발표 중에는 데이터 수집, PDF 분석, 대량 AI 요청을 동시에 수행하지 말고, 주요 화면은 발표 전에 한 번씩 열어 캐시를 데워두는 것이 좋습니다.

## 발표 전 권장 조치

- 백엔드는 `waitress-serve --listen=127.0.0.1:8000 config.wsgi:application`으로 실행
- 백엔드 Cloudflare 터널은 `localhost` 대신 `127.0.0.1`로 연결
- 발표 전에는 `python manage.py import_*` 계열 데이터 수집 작업과 PDF 분석 작업을 끝내기
- 발표 시작 전 대시보드, 추천 청약, 지도, 자금 로드맵, AI 코치 화면을 한 번씩 열어두기
- 30명이 동시에 AI 챗을 누르면 응답은 가능하지만 지연될 수 있으므로, 발표 중 AI 기능 시연은 순서를 나눠 진행하기

## 결과 파일

- 상세 브라우저 테스트: `cloudflare_full_check.spec.js`
- 동시접속 테스트 스크립트: `cloudflare_ai_load_check.mjs`
- 동시접속 상세 JSON: `cloudflare_ai_load_result.json`
- 동시접속 상세 Markdown: `cloudflare_ai_load_report.md`
