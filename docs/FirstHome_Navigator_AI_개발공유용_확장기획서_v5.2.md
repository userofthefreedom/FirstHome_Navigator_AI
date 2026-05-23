# FirstHome Navigator AI 개발공유용 확장기획서 v5.2

작성일: 2026-05-23

참고 기준: v5.1을 주 기준으로 삼고, v4.1의 서비스 범위/AI 검색 로드맵을 복원 기준으로 참조한다. v5.0은 구현 흔적 확인용 보조 자료로만 참고한다.

## 0. v5.2 작성 목적

v5.2는 v5.1 이후 실제 프로젝트에 반영된 공고문 분석, 원격 PDF, 근거 표시, 옵션 비교, 분석 상태 운영 흐름을 정리하고 다음 개발 순서를 명확히 하기 위한 공유 문서다.

v4.1은 mock 분석 골격과 소유형 공공분양 서비스 범위를 정의했고, v5.1은 실제 Document Layer, LLM adapter, pypdf 기반 분석, option_id 기반 Funding, 임베딩/로컬 LLM 로드맵을 복원했다. v5.2는 그 다음 단계로, 현재 구현이 어디까지 안정화되었고 무엇이 아직 운영 품질에 부족한지를 기록한다.

## 1. 제품 한 줄 정의

사회초년생이 소유형 공공분양 청약 후보 중 희망 면적·예산 범위에 맞는 공고와 주택형 옵션을 찾고, 공식 공고문 기준 자금 로드맵·확인 체크리스트·AI 코치 답변을 받는 첫 집 소유 준비 웹서비스.

## 2. v4.1/v5.1 기준 핵심 방향

v4.1에서 유지해야 할 방향:

- 서비스 범위는 임대형 주택이 아니라 소유형 공공분양 중심이다.
- 추천은 공고 단위에서 끝나지 않고 주택형 옵션과 납부 일정까지 내려가야 한다.
- 공식 공고문 원문과 근거 페이지/문장을 화면과 AI 답변에 연결해야 한다.
- mock fallback은 데모 안정성을 위한 장치일 뿐 공식 분석 결과처럼 보이면 안 된다.

v5.1에서 유지해야 할 방향:

- PDF 분석은 rules, LLM, mock fallback의 단계형 파이프라인으로 운영한다.
- LLM은 전체 PDF를 한 번에 던지지 않고 후보 chunk 검색 결과를 기반으로 호출한다.
- OpenAI 외에도 local endpoint/경량 LLM 후보를 검증할 수 있게 provider switch 구조를 유지한다.
- 다음 병목은 원격 PDF 확보, 표/문단 검색 품질, LLM schema 실호출 검증, 옵션 단위 UX다.

## 3. v5.2 현재 구현 현황

### 3-1. 백엔드

완료된 항목:

- 원격 PDF 다운로드 및 캐시
  - `download_remote_pdf`로 HTTP PDF를 받아 `backend/.cache/official_pdfs`에 저장한다.
  - content-type과 `%PDF` 헤더를 확인하고, 기존 캐시가 있으면 재사용한다.
  - 분석 파이프라인이 `document_url` 또는 `source_url`에서 원격 PDF를 내려받아 로컬 파서에 연결한다.

- PDF 표 추출 보강
  - `pypdf` 텍스트 추출에 더해 `pdfplumber` 기반 table row 추출을 추가했다.
  - 표 행은 페이지 텍스트에 `[table n]` 블록으로 합쳐 rules/LLM 후보에 들어간다.

- 문서 후보 chunk 검색 레이어
  - `notice_docs/services/retrieval.py`를 추가했다.
  - 공급금액, 납부일정, 자격조건 후보를 paragraph/table chunk로 나누고 lexical Top-K로 우선순위를 계산한다.
  - 현재는 embedding이 아니라 결정론적 lexical ranking이다.

- 추출 근거 직렬화
  - `ExtractionEvidence`가 API 응답에 포함된다.
  - 주택형 옵션, 납부 일정, 체크리스트에 source/evidence 정보를 표시할 수 있다.

- 분석 상태 요약
  - `analysis_summary`를 추가해 공고 목록, 상세, 추천이 같은 상태 언어를 사용한다.
  - 상태 예시는 `공식 분석 완료`, `근거 검토 필요`, `임시 추정`, `분석 실패`, `분석 필요`다.
  - mock fallback은 `임시 추정`으로 구분된다.

- 배치 분석 명령
  - `python manage.py analyze_notice_documents --dry-run --limit=10`
  - `python manage.py analyze_notice_documents --limit=10 --include-failed`
  - 서비스 대상 공고를 순회하며 공식 문서 discovery와 분석을 실행할 수 있다.

- LH import 보강
  - LH import 시 `classify_notice_payload` 결과를 반영해 `ownership_type`, `is_service_target`, `exclude_reason`을 저장한다.

- 추천 고도화
  - 공고별 `top_options`를 내려주고, 가장 적합한 주택형만이 아니라 복수 옵션을 비교할 수 있다.
  - 옵션별 `fit_reasons`를 제공해 면적, 분양가, 계약금, 중도금 관점의 추천 이유를 설명한다.

### 3-2. 프론트엔드

완료된 항목:

- 공고 상세 화면
  - 공식 체크리스트, 추출 근거 문장, 주택형 옵션별 source/evidence를 표시한다.
  - 분석 상태와 다음 액션을 `analysis_summary` 기반으로 보여준다.
  - mock fallback은 `임시 추정`으로 분리 표시한다.

- 추천 화면
  - 추천 카드에 분석 상태 배지를 표시한다.
  - 추천 주택형 옵션을 Top-N으로 보여주고 옵션별 첫 번째 추천 이유를 표시한다.

- 자금 로드맵 화면
  - `option_id` 기준 FundingPlan을 불러온다.
  - 여러 주택형 옵션의 분양가, 계약금, 부족액, 준비율, 월 목표를 비교한다.
  - 공고문 납부 일정 기반인지 공고 대표값 기반인지 구분한다.

- 지도 화면
  - 지역별 공고 목록에 분석 상태와 다음 액션을 표시한다.

### 3-3. Fixture와 테스트 자산 정리

- 루트의 임시 파일을 `backend/fixtures/sample_pdfs`로 이동했다.
  - `lh_detail_page.html`
  - `public_sale_notice_611.pdf`
  - `rent_notice_506.pdf`
- 깨져 있던 fixture README/manifest를 현재 기준으로 재작성했다.
- 참조되지 않는 `docs/test.pdf`를 삭제했다.

## 4. 검증 현황

최근 검증 결과:

- `python manage.py test`: 40 tests OK
- `python manage.py makemigrations --check --dry-run`: No changes detected
- `npm.cmd run build`: 성공

검증 의미:

- 모델 변경 없이 API/서비스/화면 확장이 반영되었다.
- 공식 PDF 분석, 원격 PDF 캐시, table extraction, retrieval, evidence, recommendation option flow의 기본 회귀 테스트가 존재한다.
- 프론트 타입 검증과 production build가 통과했다.

주의:

- 실제 LH 운영 공고를 대상으로 한 대량 분석 성공률은 아직 별도 측정이 필요하다.
- OpenAI 또는 local LLM의 실 API 호출 품질/비용/실패율은 아직 운영 지표로 정리되지 않았다.

## 5. 현재 시스템 구조 요약

주요 백엔드 흐름:

1. LH API 또는 fixture에서 공고를 확보한다.
2. `classify_notice_payload`가 소유형 공공분양 서비스 대상 여부를 분류한다.
3. 공고 상세 또는 배치 명령이 `analyze_notice_document`를 호출한다.
4. LH detail HTML 또는 document URL에서 공식 PDF 후보를 찾는다.
5. 원격 PDF를 다운로드하거나 로컬 fixture PDF를 읽는다.
6. `pypdf`와 `pdfplumber`가 텍스트/표를 추출한다.
7. rules extractor가 주택형 옵션, 납부 일정, 체크리스트를 추출한다.
8. 추출값이 부족하거나 경고가 있으면 LLM structured extraction을 보조로 시도한다.
9. 실패 시 기존 결과를 보존하거나 mock fallback을 생성한다.
10. `analysis_summary`와 evidence가 화면/API로 전달된다.

주요 프론트 흐름:

1. Dashboard/Home: 추천 후보와 캘린더 중심으로 진입한다.
2. RecommendationPage: 공고 점수와 Top-N 주택형 옵션을 확인한다.
3. NoticeDetailPage: 공식 공고문 분석 상태, 체크리스트, 근거 문장, 옵션별 납부 일정을 확인한다.
4. FundingPage: 선택 주택형 기준으로 계약금 준비율과 부족액을 비교한다.
5. AI Coach: 프로필, 공고, 선택 옵션, 추출 근거를 기반으로 안내한다.

## 6. 남아 있는 주요 리스크

### 6-1. 데이터/공고 수집

- LH API 응답의 공고 유형/필드명이 변하면 분류 정확도가 흔들릴 수 있다.
- source URL이 detail HTML인지 직접 PDF인지, file_id 방식인지 공고마다 다를 수 있다.
- 실제 운영 공고 다수를 대상으로 한 성공률 리포트가 아직 없다.

### 6-2. PDF 분석 품질

- 현재 검색은 lexical ranking이다. v5.1에서 복원한 embedding 기반 의미 검색은 아직 미구현이다.
- 표 구조가 복잡하거나 병합 셀이 많은 공고문은 금액/일정 추출 오류 가능성이 있다.
- 계약금/중도금/잔금 날짜와 금액 검증은 더 많은 샘플이 필요하다.

### 6-3. LLM 운영

- OpenAI response_schema와 local LLM endpoint의 실제 호환성 검증이 더 필요하다.
- 비용, timeout, retry, cache hit ratio, 실패 로그 정책이 아직 운영 수준으로 정리되지 않았다.
- local LLM 후보는 구조만 고려되어 있고 품질 벤치마크는 아직 없다.

### 6-4. UX/문구 품질

- 일부 기존 파일에는 인코딩이 깨진 한글 문구가 남아 있다.
- 기능은 동작하더라도 발표/시연 화면에서 문구 신뢰도를 떨어뜨릴 수 있으므로 별도 문구 정리 작업이 필요하다.

### 6-5. 운영 구조

- 분석 요청은 현재 동기 API/관리 명령 중심이다.
- 실제 서비스에서는 비동기 job, 진행률, 재시도, 캐시 관리, 관리자 확인 화면이 필요하다.

## 7. 다음 작업 우선순위

### P0. 실제 LH 공고 E2E 분석 성공률 측정

목표:

- 최근 LH 공고를 import하고 서비스 대상 공고 10~30건을 대상으로 discovery, PDF download, parsing, extraction 성공률을 측정한다.

완료 기준:

- 공고별 상태표가 남는다.
- 각 공고의 실패 원인이 `HTML discovery`, `PDF download`, `parser`, `rules extraction`, `LLM extraction`, `validation` 중 하나로 분류된다.
- 성공/needs_review/mock/failed 비율이 기록된다.

추천 명령:

- `python manage.py import_lh --with-supply-info --supply-limit=30`
- `python manage.py analyze_notice_documents --dry-run --limit=30`
- `python manage.py analyze_notice_documents --limit=30 --include-failed`

### P0. 화면 문구/인코딩 정리

목표:

- 주요 페이지의 깨진 한글 문구를 정상 문구로 복구한다.

대상:

- `HomePage.vue`
- `MapPage.vue`
- `RecommendationPage.vue`
- `NoticeDetailPage.vue`
- `FundingPage.vue`
- 백엔드 메시지 일부

완료 기준:

- 추천, 지도, 상세, 자금, AI 코치 화면의 주요 사용자 문구가 모두 정상 한글로 보인다.
- `npm.cmd run build`가 통과한다.

### P1. PDF extraction QA 세트 확장

목표:

- 실제 공공분양 샘플 PDF를 최소 5건 이상 확보해 회귀 테스트 세트를 만든다.

완료 기준:

- 공공분양 include 샘플과 임대 exclude 샘플이 분리된다.
- 공급금액표, 납부일정표, 자격조건 문단별 expected 결과가 일부라도 정의된다.
- parser/rules/retrieval test가 샘플별로 통과한다.

### P1. embedding 검색 레이어 도입

목표:

- v5.1에서 복원한 의미 검색 로드맵을 실제 코드로 전환한다.

방식:

- 1차는 로컬 in-memory vector index 또는 SQLite 저장 방식으로 시작한다.
- chunk 단위는 page, block_type, purpose, text, score, source_hash를 갖는다.
- embedding provider는 OpenAI/local/template 구조와 유사하게 교체 가능하게 둔다.

완료 기준:

- 공급금액, 계약금, 중도금, 잔금, 소득, 자산, 무주택, 청약통장 질의에 대해 Top-K 후보가 반환된다.
- LLM extractor가 lexical + embedding 후보를 함께 사용할 수 있다.

### P1. LLM 실호출 검증과 비용 제어

목표:

- `AI_ENABLE_LLM_EXTRACTION=true` 환경에서 실제 structured output 추출을 검증한다.

완료 기준:

- OpenAI provider에서 JSON schema 응답이 정상 저장된다.
- local provider 후보 1개 이상이 동일 chunk 입력에서 비교된다.
- timeout, retry, cache hit, token/cost 추정 로그가 남는다.

### P2. 분석 job 운영화

목표:

- 분석 API를 실제 사용자 요청에 안정적으로 제공할 수 있게 만든다.

완료 기준:

- 분석 상태가 `queued/running/succeeded/needs_review/failed` 수준으로 확장된다.
- 같은 공고 중복 분석 요청을 제어한다.
- 실패한 공고는 관리자 또는 명령어로 재시도할 수 있다.

### P2. 관리자/검수 화면

목표:

- 추출값이 맞는지 사람이 확인하고 수정할 수 있는 최소 검수 흐름을 만든다.

완료 기준:

- 공고별 문서, extraction, evidence, 옵션, 납부 일정이 한 화면에서 확인된다.
- needs_review 항목을 사람이 승인/수정할 수 있다.

### P2. E2E 테스트와 발표 시나리오 고정

목표:

- 발표/시연에서 실패하지 않는 고정 루트를 만든다.

완료 기준:

- fixture 기반 demo route 1개와 실제 LH 기반 route 1개가 분리된다.
- 추천 -> 상세 분석 -> 근거 확인 -> 옵션 자금 비교 -> AI 코치 질문 흐름이 문서화된다.
- Playwright 또는 수동 QA 체크리스트가 남는다.

## 8. v5.2 기준 작업 체크리스트

백엔드:

- [x] 원격 PDF 다운로드/캐시
- [x] pdfplumber 표 추출
- [x] retrieval chunk layer
- [x] extraction evidence API
- [x] analysis_summary
- [x] batch analysis command
- [ ] 실제 LH 공고 10~30건 분석 리포트
- [ ] embedding retrieval
- [ ] LLM 실호출 비용/실패 로그
- [ ] 비동기 job 운영화

프론트엔드:

- [x] 상세 화면 근거/체크리스트 표시
- [x] 추천 화면 Top-N 옵션 표시
- [x] 자금 화면 옵션 비교
- [x] 분석 상태 배지
- [x] mock fallback 임시 추정 표시
- [ ] 깨진 한글 문구 정리
- [ ] 관리자/검수 화면
- [ ] 발표용 고정 시나리오 화면 점검

데이터/QA:

- [x] sample_pdfs fixture 폴더 정리
- [x] 백엔드 40개 테스트 통과
- [x] 프론트 build 통과
- [ ] 공공분양 PDF 샘플 5건 이상 추가
- [ ] 임대/비대상 negative sample 테스트
- [ ] E2E 테스트 또는 수동 QA 문서

## 9. 발표/시연 기준

v5.2 기준 발표에서 강조할 수 있는 점:

- 단순 공고 목록 추천이 아니라 공식 공고문 PDF에서 주택형 옵션과 납부 일정을 추출하는 구조로 진입했다.
- 사용자에게 추천 이유, 옵션별 계약금, 부족액, 공식 근거 문장을 함께 보여준다.
- 실패하거나 근거가 부족한 경우 mock fallback을 공식 결과처럼 숨기지 않고 `임시 추정`으로 분리한다.
- OpenAI/local/template provider 구조를 통해 외부 API와 로컬 LLM 양쪽을 검증할 수 있는 설계를 갖췄다.

발표 전 반드시 확인할 것:

- 화면의 깨진 한글 문구를 정리한다.
- demo fixture 공고 1개는 항상 분석 성공 상태로 준비한다.
- 실제 LH 공고 시연은 네트워크/API 상태에 따라 실패할 수 있으므로 backup route를 둔다.
- 공식 공고문 원문과 화면 추출값이 다를 경우 원문 우선이라는 안내를 명확히 둔다.

## 10. v5.3으로 넘길 수 있는 확장

- 본격적인 embedding 기반 RAG
- local LLM 품질 비교 리포트
- 관리자 검수/수정 workflow
- 사용자별 저장된 관심 주택형 옵션
- 알림/캘린더 연동
- 공고문 변경 감지
- 정책/금융상품 추천의 evidence 연결
- CI/CD와 배포 환경 운영 문서

