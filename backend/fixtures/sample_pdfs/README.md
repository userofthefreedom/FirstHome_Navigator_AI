# Sample PDF Fixtures

이 폴더는 공식 공고문 분석, PDF discovery, 주택형 옵션 추출, 납부 일정 추출, 서비스 대상 필터링을 검증하기 위한 작은 샘플 파일을 보관합니다.

운영 중 다운로드되는 원문 PDF는 이 폴더가 아니라 `backend/.cache/official_pdfs` 아래에 캐시됩니다. 새로 다운로드한 대용량 PDF는 명확한 테스트 목적이 있을 때만 Git에 포함합니다.

## 주요 파일

| 파일 | 용도 |
|---|---|
| `lh_detail_page.html` | LH 상세 페이지에서 공식 PDF 링크를 찾는 discovery 회귀 테스트 |
| `manifest.json` | 샘플 PDF 목록과 메타데이터 |
| `expected.json` | 일부 샘플의 기대 추출 결과 |
| `public_sale_notice_611.pdf` | 공공분양 공고문 기본 추출 테스트 |
| `public_sale_ulsan_down2_a10_20251230.pdf` | 융자금과 마이너스 옵션 추출 검증 |
| `public_sale_incheon_yeongjong_a24_remaining_20260330.pdf` | 여러 차수 중도금과 융자금 컬럼 검증 |
| `public_sale_daejeon_daedong2_1_remaining_20260403.pdf` | 기본/일반공급 옵션 그룹이 있는 대형 잔여세대 표 검증 |
| `public_sale_cheongju_jibuk_b1_remaining_20260430.pdf` | 중도금 요구가 없는 잔여세대 공고 검증 |
| `public_sale_namyangju_wangsuk2_a3_corrected_20260430.pdf` | 정정 공고 형태와 표 구조 확장 검증 |
| `private_public_sale_wangsuk_atera_a1_20260430.pdf` | 민간참여 공공분양 공고문 검증 |
| `private_public_sale_wangsuk_prugio_b2_20250729.pdf` | 민간참여 공공분양 후보 문서 검증 |
| `newlywed_public_sale_siheung_hajung_a1_20260430.pdf` | 신혼희망타운 공공분양 표 구조 검증 |
| `newlywed_public_sale_incheon_gyeyang_a9_20260430.pdf` | 다른 표 레이아웃의 신혼희망타운 검증 |
| `newlywed_public_sale_namyangju_jinjeop2_a3_20251230.pdf` | 직접 다운로드한 신혼희망타운 공고 검증 |
| `newlywed_private_public_sale_wirye_xi_resupply_20240118.pdf` | 민간참여 신혼희망타운 재공급 공고 검증 |
| `rent_notice_506.pdf` | 임대 공고 exclusion/reference fixture |

## 관련 코드

- `backend/apps/notice_docs/services/pdf_parser.py`
- `backend/apps/notice_docs/services/extractors.py`
- `backend/apps/notice_docs/services/discovery_lh.py`
- `backend/apps/notice_docs/services/analysis.py`
- `backend/apps/notice_docs/tests.py`

## 관리 원칙

- 공식 PDF 분석 로직을 바꿀 때는 이 샘플들로 회귀 테스트를 확인합니다.
- 서비스 대상이 아닌 임대 공고는 추천 대상 필터링 검증용으로만 유지합니다.
- 샘플을 추가할 때는 파일명에 공고 유형, 지역/단지, 기준일을 알 수 있게 적습니다.
