# Sample notice PDFs

LLM/API Key를 붙이기 전후 PDF 파싱, 규칙 기반 extraction, LLM structured output fallback을 검증하기 위한 로컬 샘플 보관 위치입니다.

- 실제 PDF 파일은 용량과 저작권/배포 범위 때문에 Git에 올리지 않습니다.
- 필요한 샘플은 이 폴더에 직접 내려받아 두고, `manifest.json`에 출처와 용도를 기록합니다.
- 권장 구성은 소유형 공공분양 2건, 제외 대상 임대형 1건입니다.
- 서비스 목록 조회에서는 PDF를 전부 다운로드하지 않고, 상세 페이지의 온디맨드 분석 흐름에서만 사용합니다.
- 기본 시연은 `AI_PROVIDER=template`과 규칙 기반 파서만으로 완주해야 합니다.
- LLM 추출을 검증할 때만 `AI_ENABLE_LLM_EXTRACTION=true`로 바꾸고, 실패 시 기존 분석 결과가 보존되는지 확인합니다.
