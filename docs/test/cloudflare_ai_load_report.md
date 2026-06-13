# Cloudflare AI 동시접속 점검

- 점검 일시: 2026. 6. 14. 오전 1:02:14
- 프론트 주소: https://campaigns-singing-environments-undergraduate.trycloudflare.com
- API 주소: https://drawing-newest-definition-mud.trycloudflare.com/api
- 가상 사용자: 30명
- 기준 공고: e편한세상 분당 퍼스트빌리지(성남낙생 A-1BL) 신혼희망타운(공공분양) 입주자모집공고
- 결과: 통과

## 요약

- 전체 요청: 270건
- 성공: 270건
- 실패: 0건
- 총 소요: 151초
- p50/p90/p95/max: 11230ms / 36354ms / 41794ms / 52582ms

## 엔드포인트별 결과

| 구분 | 요청 | 성공 | 실패 | p50 | p90 | 최대 | 상태 |
|---|---:|---:|---:|---:|---:|---:|---|
| frontend:home | 30 | 30 | 0 | 821ms | 826ms | 829ms | 200:30 |
| frontend:recommendations | 30 | 30 | 0 | 286ms | 292ms | 294ms | 200:30 |
| api:dashboard | 30 | 30 | 0 | 14095ms | 24170ms | 26669ms | 200:30 |
| api:housing | 30 | 30 | 0 | 19462ms | 23180ms | 23779ms | 200:30 |
| api:map | 30 | 30 | 0 | 33921ms | 47721ms | 52582ms | 200:30 |
| api:funding | 30 | 30 | 0 | 27876ms | 41863ms | 43052ms | 200:30 |
| auth:register | 30 | 30 | 0 | 5517ms | 9960ms | 11466ms | 201:30 |
| auth:me | 30 | 30 | 0 | 1354ms | 18811ms | 36417ms | 200:30 |
| ai:chat | 30 | 30 | 0 | 21763ms | 36508ms | 37553ms | 200:30 |

## 실패 샘플

실패 요청이 없습니다.

## 해석

- 이 점검은 30명의 사용자가 동시에 주요 화면/API를 열고, 회원가입 세션을 만든 뒤 AI 챗 요청을 보내는 상황을 HTTP 레벨에서 재현했습니다.
- 브라우저 렌더링 전체 회귀는 `cloudflare_full_check.spec.js`에서 별도로 수행했습니다.