# 제출용 화면 캡처

이 폴더는 실제 배포 주소에서 캡처한 제출용 화면 이미지를 보관합니다.

## 캡처 기준

| 항목 | 값 |
|---|---|
| 대상 주소 | `https://polka-kennel-decorated.ngrok-free.dev` |
| viewport | `1440x960` |
| 캡처 수 | 56장 |
| 사용자 상태 | 비회원, 회원 |
| 테마 | light, dark |
| 캡처 방식 | Playwright 자동화 |
| manifest | `screenshot-manifest.json` |

회원 화면 캡처에는 자동 생성한 제출용 테스트 계정을 사용했습니다. 계정명은 manifest의 `member.username`에서 확인할 수 있습니다.

## 폴더 구조

```text
screenshots/
  README.md
  capture-submit.mjs
  screenshot-manifest.json
  guest/
    light/
    dark/
  member/
    light/
    dark/
```

## 캡처 대상 화면

각 사용자 상태와 테마 조합별로 다음 14개 화면을 캡처했습니다.

| 화면 | 경로 |
|---|---|
| Dashboard | `/` |
| Profile | `/profile` |
| Recommendations | `/recommendations` |
| Notice Detail | `/notices/101?option_id=1001` |
| Map | `/map` |
| Funding | `/funding/101?option_id=1001` |
| AI Coach | `/ai-coach/101?option_id=1001` |
| Favorites | `/favorites` |
| Financial Products | `/finance/products` |
| Financial Product Detail | `/finance/products/1` |
| Economy NOW | `/finance/economy-now` |
| Agora | `/finance/agora` |
| MY PAGE | `/my-page` |
| Auth | `/auth` |

## 파일 번호 규칙

- `guest/light`: `01_` ~ `14_`
- `guest/dark`: `15_` ~ `28_`
- `member/light`: `29_` ~ `42_`
- `member/dark`: `43_` ~ `56_`

예시:

```text
guest/light/01_dashboard.png
member/light/33_map.png
member/dark/55_my_page.png
```

## 재캡처 방법

프로젝트 루트에서 실행합니다.

```bash
node docs/submit/screenshots/capture-submit.mjs https://polka-kennel-decorated.ngrok-free.dev
```

주의:
- backend와 frontend 배포 주소가 정상 동작해야 합니다.
- 중간 로딩 화면이 저장되지 않도록 스크립트는 route 이동 후 network idle과 화면 안정 상태를 기다립니다.
- ngrok 경고 페이지 회피를 위해 자동화 요청에는 `ngrok-skip-browser-warning` 헤더를 사용합니다.

