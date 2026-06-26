# 제출용 산출물

이 폴더는 FirstHome Navigator AI 최종 제출과 발표 준비에 필요한 자료를 모아 둔 공간입니다.

## 구성

```text
docs/submit/
  README.md
  document_generation_prompt_guide.txt
  docs_submit/
  screenshots/
```

## 폴더별 설명

| 위치 | 내용 |
|---|---|
| `screenshots/` | 실제 배포 주소 기준 화면 캡처 56장, 캡처 스크립트, manifest, 캡처 설명 |
| `docs_submit/` | 제출용 설계 문서, 다이어그램, 와이어프레임, API 명세, 기획서 |
| `document_generation_prompt_guide.txt` | 추가 산출물을 GPT에 요청할 때 사용할 프롬프트 작성 가이드 |

## docs_submit 주요 파일

| 파일 | 설명 |
|---|---|
| `service_architecture.txt` | 전체 서비스 아키텍처 설명 |
| `recommendation_algorithm_detail.txt` | 청약/주택형/금융상품/정책/대출 추천 알고리즘 상세 설계 |
| `FirstHome Navigator API.yaml` | OpenAPI/Swagger API 명세 |
| `firsthome_api_flow_sequence_diagrams.pdf` | API 흐름도와 시퀀스 다이어그램 |
| `firsthome_vue_component_structure.pdf` | Vue 컴포넌트 구조도 |
| `firsthome_db_erd.pdf` | DB 모델링 ERD |
| `firsthome_page_design.pdf` | 페이지 설계 또는 화면 설계도 |
| `FirstHome_Navigator_AI_상세_와이어프레임_기획용_최종.pdf` | 상세 와이어프레임 문서 |
| `청약네비_기획서_최종.docx` | 최종 기획서 |
| `ERD.png` | ERD 이미지 |
| `usecase.png` | Use Case 이미지 |

## screenshots 주요 파일

| 파일/폴더 | 설명 |
|---|---|
| `screenshots/README.md` | 캡처 기준과 재캡처 방법 |
| `screenshots/capture-submit.mjs` | Playwright 기반 캡처 실행 스크립트 |
| `screenshots/screenshot-manifest.json` | 캡처 URL, 파일 경로, ready 상태 기록 |
| `screenshots/guest/` | 비회원 light/dark 화면 캡처 |
| `screenshots/member/` | 회원 light/dark 화면 캡처 |

## 제출 전 확인

- 루트 `README.md`의 제출용 산출물 위치 섹션과 이 폴더 구성이 일치하는지 확인합니다.
- 캡처 화면에 중간 로딩 화면이나 ngrok 경고 페이지가 들어가지 않았는지 확인합니다.
- API 명세는 최신 backend schema에서 생성한 파일인지 확인합니다.
- 발표자료에 넣을 다이어그램은 PDF와 이미지 중 더 잘 보이는 형식을 선택합니다.
