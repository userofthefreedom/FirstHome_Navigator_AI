# Cloudflare 30명 동시 접속 스모크 테스트 보고서

- 프론트 주소: https://san-ultra-represents-pins.trycloudflare.com
- 백엔드 API 주소: https://dressed-wichita-aerospace-clay.trycloudflare.com
- 점검 시각: 2026-06-13 19:29~19:31 KST
- 테스트 방식: Node `fetch` 기반 동시 요청
- 테스트 스크립트: `docs/test/concurrent_smoke.mjs`

## 테스트 범위

AI 코치/OpenAI 요청은 비용과 지연이 커서 제외했습니다. 발표 중 여러 명이 일반 화면을 열고 추천/상세/자금 API를 조회하는 상황을 먼저 확인했습니다.

각 가상 사용자는 다음 요청을 동시에 수행했습니다.

- 프론트: `/`, `/recommendations`, `/map`, `/funding/1?option_id=285`
- 백엔드: `/api/dashboard`, `/api/notices?active=1`, `/api/recommendations/housing`, `/api/recommendations/funding/1?option_id=285`

## 30명 동시 접속 결과

- 총 요청: 240건
- 성공: 148건
- 실패: 92건
- p50: 1.0초
- p90: 1.1초
- p95: 8.0초
- 최대 응답 시간: 12.5초
- 최대 `Set-Cookie` 크기: 9,023 bytes

프론트 정적 페이지 요청은 모두 성공했습니다.

백엔드 API 요청은 다수 `502`가 발생했습니다.

| URL | 요청 | 실패 | 최대 응답 |
| --- | ---: | ---: | ---: |
| `/api/dashboard` | 30 | 25 | 12.5초 |
| `/api/notices?active=1` | 30 | 24 | 9.8초 |
| `/api/recommendations/housing` | 30 | 20 | 11.3초 |
| `/api/recommendations/funding/1?option_id=285` | 30 | 23 | 1.1초 |

## 10명 동시 접속 결과

- 총 요청: 80건
- 성공: 80건
- 실패: 0건
- p50: 0.19초
- p90: 16.7초
- p95: 17.2초
- 최대 응답 시간: 17.8초
- 최대 `Set-Cookie` 크기: 9,023 bytes

10명 수준에서는 실패는 없었지만 일부 백엔드 API가 14~18초까지 길어졌습니다.

## 핵심 문제

현재 백엔드는 세션을 쿠키에 직접 저장합니다.

```python
SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
```

그 결과 `/api/dashboard`, `/api/recommendations/housing` 같은 응답에서 약 9KB짜리 `sessionid` 쿠키가 내려옵니다. 일반적인 브라우저 쿠키 한도는 약 4KB라서, 실제 브라우저에서는 쿠키가 거부되거나 잘릴 수 있습니다.

발표 상황에서는 다음 문제가 생길 수 있습니다.

- 비로그인 사용자마다 큰 세션 쿠키가 계속 오감
- 요청/응답 헤더가 불필요하게 커짐
- Cloudflare 터널과 Django 개발 서버에 부담 증가
- 일부 브라우저에서 세션 유지 실패 가능
- 30명 동시 접속 시 API 502 발생 가능

## 판정

현재 Cloudflare Quick Tunnel + Django 개발 서버 조합은 30명 발표용 동시 조작 환경에 안정적이라고 보기 어렵습니다.

특히 30명이 동시에 추천, 대시보드, 자금 로드맵을 누르면 백엔드 API가 실패할 가능성이 있습니다.

## 권장 수정

1. 세션 엔진을 signed cookie에서 DB session으로 변경
2. `python manage.py migrate`로 `django_session` 테이블 준비
3. 추천 결과나 계정 상태처럼 큰 데이터는 세션 쿠키에 저장하지 않기
4. 자금 로드맵 옵션 비교 요청은 현재 보이는 옵션만 lazy-load
5. 발표 전에는 Django 개발 서버 대신 `waitress` 같은 WSGI 서버 사용 검토
6. AI 코치/OpenAI는 로그인/캐시 기반으로만 실행하고 발표 중 반복 호출 제한

## 재실행 방법

```bash
node docs/test/concurrent_smoke.mjs "https://san-ultra-represents-pins.trycloudflare.com" "https://dressed-wichita-aerospace-clay.trycloudflare.com" 30
```
