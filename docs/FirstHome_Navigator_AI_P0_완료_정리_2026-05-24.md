# FirstHome Navigator AI P0 완료 정리

작성일: 2026-05-24

## 현재 결론

P0는 기능, 샘플, 실제 API 연동 확인, 대표 시나리오 회귀 점검 기준으로 완료 상태다.

## 완료된 P0

- 대표 시나리오 완주 점검 명령 추가
  - `python manage.py check_representative_flow --report-json=reports/representative_flow.json`
  - 프로필 저장, 추천 조회, 공고 상세, 공식 분석 상태, 주택형 옵션, 옵션 기반 자금 계획, AI 질문 5개, 관심 저장까지 확인한다.
- PDF 샘플 회귀 점검 명령 추가
  - `python manage.py check_sample_pdf_regression --report-json=reports/sample_pdf_regression.json`
  - include 공공분양 PDF 3건과 exclude PDF 5건을 검증한다.
- 실제 LH API 연동 확인
  - `.env`의 `DATA_GO_KR_SERVICE_KEY` 기준으로 LH 공고 import dry-run 및 실제 update 확인.
  - 현재 최신 LH 10건은 모두 임대, 전세, 오피스텔, 잔여세대 계열로 MVP 범위 밖이며 정상 제외된다.
- LH 분석 준비도 리포트 명령 보강
  - `python manage.py analyze_notice_documents --dry-run --include-excluded --provider=LH --exclude-fixture --limit=30 --report-json=reports/lh_actual_readiness.json --report-md=reports/lh_actual_readiness.md`
- 공식 공고문 기반 분석 흐름 정리
  - 분석 상태 문구, 공식 확인 안내, mock/fallback 문구 정리.
  - PDF 검색 키워드와 LH 문서 discovery 키워드 정상화.
  - 천원 단위와 원 단위가 섞인 PDF 금액 추출 보강.
- AI 추천 질문 5개 연결
  - 플로팅 AI 코치에서 현재 route의 notice/option context를 우선 사용한다.
- P1 일부 반영
  - 주택형 옵션 관심 저장 지원.
  - Funding 화면에서 옵션 저장 가능.
  - Favorites 화면에서 저장한 주택형 옵션 표시 및 옵션 자금 페이지 이동 가능.

## 회귀 게이트

P0 마감 전 실행한 검증:

- `python manage.py makemigrations --check --dry-run`
- `python manage.py test`
- `npm run build`
- `python manage.py check_representative_flow --report-json=reports/representative_flow.json`
- `python manage.py check_sample_pdf_regression --report-json=reports/sample_pdf_regression.json`

최종 확인 결과:

- backend test: 44 tests 통과
- frontend build 통과
- sample PDF regression 통과
- representative flow 통과
- backend/frontend local server 응답 확인

## 산출물 처리 방침

- `.env` 파일은 commit 대상이 아니다.
- `backend/reports/`는 로컬 실행 산출물이므로 `.gitignore`에 추가했다.
- `backend/fixtures/sample_pdfs/expected.json`과 `manifest.json`은 회귀 기준 데이터이므로 유지한다.

## 다음 P1 후보

- 남은 주요 화면의 문구/UX 세부 정리
  - Home, Recommendation, NoticeDetail, AiCoach, Map 화면 중심.
- PDF 파서 고도화
  - 표 구조가 더 불규칙한 공고의 주택형/납부일정 추출률 개선.
- AI 답변 context 강화
  - 선택 옵션, evidence text, checklist를 더 정교하게 전달.
- 관심 저장 확장
  - 옵션 저장은 들어갔으므로, 이후 option memo 또는 비교 그룹 저장을 검토.
- 실제 LH 공공분양 공고가 API에 잡히는 시점에 10~30건 분석 성공률 재측정.
