# FirstHome Navigator AI Docs

이 폴더는 FirstHome Navigator AI의 기획, 설계, 제출 산출물, 보조 문서를 모아 둔 문서 공간입니다. 최신 실행 방법과 환경 변수는 프로젝트 루트의 `README.md`를 우선 확인합니다.

## 폴더 구조

| 위치 | 내용 |
|---|---|
| `history/` | 기획서, 확장 기획서, 과거 공유 문서, 참고 PDF 등 히스토리 자료 |
| `guide/` | API Key 발급/활용 가이드, 외부 서비스 연동 참고 문서 |
| `detail/` | 규칙 상세, ERD, Use Case, 와이어프레임, WBS 등 개발 상세 문서 |
| `submit/` | 최종 제출용 산출물, 화면 캡처, 제출 보조 문서 |

## 중요 문서

| 문서 | 설명 |
|---|---|
| `detail/rules_detail.txt` | 추천 점수, 자금 계산, 지역 매칭, 공고 분류, PDF 분석, 금융상품/정책/대출 추천, AI 안전 규칙 상세 |
| `submit/docs_submit/service_architecture.txt` | 전체 서비스 아키텍처 설명 |
| `submit/docs_submit/recommendation_algorithm_detail.txt` | 청약/주택형/금융상품/정책/대출 추천 알고리즘 상세 설계 |
| `submit/document_generation_prompt_guide.txt` | API 흐름도, Vue 구조도, ERD, 화면 설계도를 GPT에 요청하기 위한 프롬프트 가이드 |
| `submit/screenshots/README.md` | 실제 배포 주소 기준 화면 캡처 설명 |

## 제출 산출물

최종 제출 자료는 `submit/` 아래에 모았습니다.

```text
docs/submit/
  README.md
  document_generation_prompt_guide.txt
  docs_submit/
    service_architecture.txt
    recommendation_algorithm_detail.txt
    FirstHome Navigator API.yaml
    firsthome_api_flow_sequence_diagrams.pdf
    firsthome_vue_component_structure.pdf
    firsthome_db_erd.pdf
    firsthome_page_design.pdf
    FirstHome_Navigator_AI_상세_와이어프레임_기획용_최종.pdf
    청약네비_기획서_최종.docx
    ERD.png
    usecase.png
  screenshots/
    README.md
    capture-submit.mjs
    screenshot-manifest.json
    guest/
    member/
```

## 문서 관리 원칙

- 실행 방법은 루트 `README.md`를 기준으로 유지합니다.
- 백엔드 세부 실행은 `backend/README.md`, 프론트엔드 세부 실행은 `frontend/README.md`를 기준으로 유지합니다.
- 발표/제출용 문서는 `docs/submit/` 아래에 모읍니다.
- 테스트 또는 임시 산출물은 최종 제출 전에 `docs/test/`에 남기지 않습니다.
