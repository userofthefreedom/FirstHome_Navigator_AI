# Cloudflare 배포 회원 기능/OpenAI E2E 점검 보고서

- 점검 주소: https://plastics-lightweight-chorus-wellington.trycloudflare.com/
- 점검 시간: 2026년 6월 13일 16:03:32 ~ 16:06:09 KST
- 점검 방식: Playwright로 실제 Cloudflare 배포 주소에 접속하여 사용자 흐름 수행
- 브라우저: Microsoft Edge
- 테스트 계정: `codex_e2e_20260613070332`
- 원본 결과: [member_e2e_result.json](./member_e2e_result.json)
- 스크린샷 폴더: [member_screenshots](./member_screenshots/)

## 종합 판정

이번 배포 주소에서는 핵심 회원 시나리오가 모두 통과했습니다.

회원가입, 로그인 세션 유지, 조건 저장, 추천 청약 이동, 공고 저장, 자금 로드맵, AI 코치, 전역 챗봇 OpenAI 응답, 관심목록 저장, 로그아웃, 재로그인 후 프로필/관심목록 유지가 실제 브라우저 기준으로 정상 동작했습니다.

이전 점검에서 문제가 되었던 Cloudflare 배포 환경의 세션/CORS 문제는 이번 점검 기준으로 개선된 상태입니다.

## 단계별 결과

| 단계 | 결과 | 소요 시간 | 스크린샷 | 확인 내용 |
| --- | --- | ---: | --- | --- |
| 회원가입 | 통과 | 5.8초 | [01](./member_screenshots/01_registered_profile.png) | 회원가입 후 조건 입력 화면 진입 |
| 조건 저장 및 추천 이동 | 통과 | 3.2초 | [02](./member_screenshots/02_recommendations_after_profile.png) | 입력 조건 저장, 추천 목록 표시 |
| 공고 상세 및 저장 | 통과 | 5.1초 | [03](./member_screenshots/03_notice_detail_saved.png) | 상세 화면 진입, 공고 저장 |
| 자금 로드맵 | 통과 | 4.5초 | [04](./member_screenshots/04_funding_page.png) | 선택 공고/옵션 기준 자금 화면 표시 |
| AI 코치 | 통과 | 77.6초 | [05](./member_screenshots/05_ai_coach_loaded.png) | 로그인 상태에서 AI 코치 분석 화면 표시 |
| 챗봇 OpenAI 메시지 | 통과 | 46.0초 | [06](./member_screenshots/06_chatbot_openai_message.png) | 전역 챗봇 응답 변화 확인 |
| 관심목록 저장 확인 | 통과 | 4.9초 | [07](./member_screenshots/07_favorites_after_save.png) | 저장한 공고가 관심목록에 표시 |
| 로그아웃 | 통과 | 3.1초 | [08](./member_screenshots/08_after_logout_home.png) | 로그아웃 후 홈/비회원 상태로 이동 |
| 재로그인 후 프로필 유지 | 통과 | 3.9초 | [09](./member_screenshots/09_relogin_profile_persist.png) | 기존 입력 조건/계정 정보 유지 |
| 재로그인 후 관심목록 유지 | 통과 | 2.6초 | [10](./member_screenshots/10_favorites_after_relogin.png) | 저장 공고가 재로그인 후에도 유지 |

## 확인된 개선점

- Cloudflare 터널 환경에서 로그인 세션이 상세/자금/AI 코치 화면까지 유지됩니다.
- `CORS` 관련 콘솔 오류가 발생하지 않았습니다.
- `HTTP 4xx/5xx` 응답 오류가 발생하지 않았습니다.
- AI 코치 화면은 비회원 예시가 아니라 로그인 사용자 기준 화면으로 표시됩니다.
- 전역 챗봇은 실제 메시지 전송 후 응답 내용이 변경되는 것을 확인했습니다.
- 관심목록 저장 상태가 로그아웃 후 재로그인해도 유지됩니다.

## 관찰된 잔여 신호

점검 중 `net::ERR_ABORTED` 요청이 2건 기록되었습니다.

- `GET /api/notices?active=1`
- `GET /api/dashboard`

두 요청 모두 재로그인 직후 화면 이동 과정에서 브라우저가 이전 요청을 취소한 형태로 보입니다. HTTP 오류, 콘솔 오류, 페이지 오류가 없고 이후 화면이 정상 표시되었으므로 현재는 기능 실패로 보지 않습니다.

## 점검 로그 요약

- Console errors: 0건
- Page errors: 0건
- HTTP 4xx/5xx: 0건
- Failed requests: 2건, 모두 `net::ERR_ABORTED`

## 다음 확인 권장

- 발표 전 같은 Cloudflare 주소로 수동 회원가입/로그인 1회 재점검
- 터널 주소가 바뀌는 경우 `backend/.env`의 `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`와 Kakao JavaScript SDK 도메인 재확인
- AI 코치와 챗봇은 OpenAI 응답 시간이 길 수 있으므로 발표 환경에서 미리 한 번 캐시를 만들어두는 것을 권장
