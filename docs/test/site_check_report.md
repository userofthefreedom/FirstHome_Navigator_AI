# Cloudflare 배포 전체 화면 점검 보고서

- 점검 주소: https://plastics-lightweight-chorus-wellington.trycloudflare.com/
- 점검 방식: Playwright 실제 브라우저 접속
- 점검 시각: 2026-06-13 16:13~16:15 KST
- 원본 결과: `docs/test/site_check_result.json`
- 스크린샷: `docs/test/screenshots/`

## 종합 판정

대시보드, 조건 입력, 추천 청약, 청약 상세, 자금 로드맵, AI 코치, 청약 지도, 관심목록, 로그인 화면, 전역 챗봇, 모바일 대시보드 화면은 모두 실제 배포 주소에서 렌더링되었습니다.

회원가입/로그인/프로필 저장/청약 저장/관심목록 유지/OpenAI 챗봇 응답은 별도 회원 E2E 점검에서 통과했습니다.

## 화면별 결과

| 화면 | 경로 | 결과 |
| --- | --- | --- |
| 대시보드 | `/` | 정상 렌더링 |
| 조건 입력 | `/profile` | 정상 렌더링 |
| 추천 청약 | `/recommendations` | 정상 렌더링 |
| 청약 상세 | `/notices/1?option_id=285` | 정상 렌더링 |
| 자금 로드맵 | `/funding/1?option_id=285` | 정상 렌더링 |
| AI 코치 | `/ai-coach/1?option_id=285` | 정상 렌더링 |
| 청약 지도 | `/map` | Kakao 지도와 공고 목록 렌더링 |
| 관심목록 | `/favorites` | 정상 렌더링 |
| 로그인/회원가입 | `/auth` | 정상 렌더링 |
| 전역 챗봇 | 대시보드 내 플로팅 버튼 | 패널 열림 확인 |
| 모바일 대시보드 | 390px 폭 | 모바일 폭 렌더링 확인 |

## 추가 확인

- `docs/test/screenshots/05_recommendations.png`: 추천 청약 목록 표시 확인
- `docs/test/screenshots/07_funding.png`: 자금 로드맵, 옵션 비교, 대출/금융/정책 후보 표시 확인
- `docs/test/screenshots/09_map.png`: 지도, 마커, 우측 공고 패널 표시 확인
- `docs/test/screenshots/13_chatbot_open.png`: 챗봇 패널 열림 확인
- `docs/test/screenshots/14_mobile_dashboard.png`: 모바일 폭 대시보드 표시 확인

## 관찰된 네트워크 신호

자동 점검에서 자금 로드맵 화면을 지나갈 때 옵션 비교용 백그라운드 요청 일부가 브라우저 콘솔에 CORS/`net::ERR_FAILED`로 기록되었습니다.

예시:

- `/api/recommendations/funding/1?option_id=304`
- `/api/recommendations/funding/1?option_id=285`

다만 같은 API를 `Origin: https://plastics-lightweight-chorus-wellington.trycloudflare.com` 헤더와 함께 직접 호출했을 때는 `200 OK`와 `Access-Control-Allow-Origin` 헤더가 정상 반환되었습니다. 따라서 현재 확인된 내용만으로는 CORS 환경변수 오류라기보다, 자동 점검이 다음 화면으로 이동하는 동안 다수의 옵션 비교 요청이 동시에 취소되며 발생한 신호일 가능성이 큽니다.

## 권장 보완

자금 로드맵에서 옵션이 많을 때 비교용 API 요청이 한 번에 많이 발생합니다. 실제 사용자 환경에서 콘솔 오류나 느려짐이 보이면 다음 순서로 개선하는 것이 좋습니다.

1. 현재 보이는 옵션 페이지에 대해서만 자금 계산 요청
2. 라우트 이동 시 진행 중인 요청을 `AbortController`로 취소
3. `notice_id + option_id` 단위 응답 캐시
4. 옵션 비교 요청 동시 실행 수 제한

## 회원/OpenAI 점검 보고서

회원 기능과 OpenAI 응답까지 포함한 별도 점검 결과는 다음 파일에 정리했습니다.

- `docs/test/member_e2e_report.md`
- `docs/test/member_e2e_result.json`
- `docs/test/member_screenshots/`
