export type Subscription = {
  id: number
  name: string
  district: string
  address: string
  supplyType: string
  housingType: string
  area: string
  price: string
  priceValue: number
  deposit: string
  competition: string
  deadline: string
  winnerDate: string
  moveIn: string
  matchScore: number
  commute: string
  tags: string[]
  strengths: string[]
  cautions: string[]
  position: {
    top: string
    left: string
  }
}

export type FinancialProduct = {
  id: number
  name: string
  provider: string
  category: '전세대출' | '주택담보대출' | '청약통장' | '적금'
  rate: string
  limit: string
  period: string
  matchScore: number
  tags: string[]
  reasons: string[]
  caution: string
}

export const profile = {
  name: '김싸피',
  region: '서울 강남권',
  household: '3인 가구',
  budget: '4.8억 이하',
  score: 84,
  subscriptionAccount: '8년 4개월',
  preferredAreas: ['강남', '송파', '성남', '마곡'],
  birth_year: 1993,
  job_status: 'employed',
  annual_income: 48000000,
  asset: 72000000,
  debt: 18000000,
  monthly_saving: 1400000,
  is_homeless: true,
  subscription_months: 28,
  special_conditions: ['first_home', 'youth'],
  preferred_regions: ['서울', '경기 남부'],
  preferred_supply_types: ['공공분양', '민영'],
  target_months: 10,
}

export const subscriptions: Subscription[] = [
  {
    id: 1,
    name: '서초 리트리오 포레',
    district: '서울 서초구',
    address: '서울특별시 서초구 반포대로 28길',
    supplyType: '민영',
    housingType: '아파트',
    area: '84㎡',
    price: '4억 6,800만원',
    priceValue: 468000000,
    deposit: '계약금 10%',
    competition: '12.4:1',
    deadline: '2026-05-23',
    winnerDate: '2026-06-03',
    moveIn: '2028년 2월',
    matchScore: 96,
    commute: '강남역 18분',
    tags: ['역세권', '초등학교 450m', '분양가 상한제'],
    strengths: ['예산 안에 들어오는 84㎡ 타입', '출퇴근 동선이 짧음', '가점 대비 경쟁률이 적정'],
    cautions: ['접수 마감이 임박함', '서류 발급 기준일 확인 필요'],
    position: { top: '42%', left: '56%' },
  },
  {
    id: 2,
    name: '송파 레이크 포레',
    district: '서울 송파구',
    address: '서울특별시 송파구 올림픽로 221',
    supplyType: '공공분양',
    housingType: '아파트',
    area: '74㎡',
    price: '3억 9,500만원',
    priceValue: 395000000,
    deposit: '계약금 15%',
    competition: '9.8:1',
    deadline: '2026-05-28',
    winnerDate: '2026-06-10',
    moveIn: '2027년 11월',
    matchScore: 91,
    commute: '잠실역 9분',
    tags: ['공원 인접', '대중교통', '신혼 특공'],
    strengths: ['공공분양 조건과 잘 맞음', '생활 인프라가 안정적', '초기 자금 부담이 낮음'],
    cautions: ['주차 대수와 커뮤니티 시설 확인 필요'],
    position: { top: '47%', left: '65%' },
  },
  {
    id: 3,
    name: '판교 테크밸리 포레',
    district: '경기 성남시',
    address: '경기도 성남시 분당구 판교역로 235',
    supplyType: '민영',
    housingType: '아파트',
    area: '98㎡',
    price: '5억 2,000만원',
    priceValue: 520000000,
    deposit: '계약금 10%',
    competition: '17.6:1',
    deadline: '2026-06-04',
    winnerDate: '2026-06-17',
    moveIn: '2028년 5월',
    matchScore: 86,
    commute: '판교역 12분',
    tags: ['직주근접', '중대형', 'IT 생활권'],
    strengths: ['직장 접근성이 좋음', '중대형 선호에 부합', '장기 거주 수요가 높음'],
    cautions: ['예산 초과 가능성', '경쟁률 상승 추세'],
    position: { top: '61%', left: '52%' },
  },
  {
    id: 4,
    name: '마곡 에코스퀘어',
    district: '서울 강서구',
    address: '서울특별시 강서구 마곡중앙로 76',
    supplyType: '공공분양',
    housingType: '오피스텔',
    area: '59㎡',
    price: '3억 1,700만원',
    priceValue: 317000000,
    deposit: '계약금 10%',
    competition: '6.3:1',
    deadline: '2026-06-12',
    winnerDate: '2026-06-25',
    moveIn: '2027년 8월',
    matchScore: 82,
    commute: '마곡역 6분',
    tags: ['낮은 분양가', '산업단지', '1순위 가능'],
    strengths: ['자금 부담이 낮음', '지하철 접근성이 좋음', '잔금 일정이 여유 있음'],
    cautions: ['선호 면적보다 작음'],
    position: { top: '39%', left: '31%' },
  },
]

export const documents = [
  '주민등록등본',
  '가족관계증명서',
  '청약통장 가입확인서',
  '소득금액증명원',
  '무주택 확인서',
]

export const financialProducts: FinancialProduct[] = [
  {
    id: 1,
    name: '청약 당첨 대비 전세 브릿지론',
    provider: 'SSAFY Bank',
    category: '전세대출',
    rate: '연 3.42%~',
    limit: '최대 2.8억',
    period: '24개월',
    matchScore: 94,
    tags: ['중도상환수수료 면제', '무주택 우대', '모바일 서류'],
    reasons: ['예상 계약금 일정과 맞음', '현재 소득 대비 DSR 여유', '입주 전 거주비 대응 가능'],
    caution: '당첨 후 계약서 제출 시 금리가 확정됩니다.',
  },
  {
    id: 2,
    name: '분양 잔금 안심 주택담보대출',
    provider: '하나로저축',
    category: '주택담보대출',
    rate: '연 3.88%~',
    limit: '분양가의 70%',
    period: '최대 35년',
    matchScore: 89,
    tags: ['고정혼합형', '거치 1년', '잔금 알림'],
    reasons: ['서초 후보 잔금 시점과 맞음', '장기 고정비 관리에 유리', '예산 상단 청약에 적합'],
    caution: '분양권 담보 인정 여부는 사업장별로 달라질 수 있습니다.',
  },
  {
    id: 3,
    name: '청약 가점 성장 적금',
    provider: '국민내일은행',
    category: '적금',
    rate: '연 4.10%',
    limit: '월 50만원',
    period: '12개월',
    matchScore: 86,
    tags: ['자동이체 우대', '청약통장 연동', '비상금 분리'],
    reasons: ['계약금 준비금을 별도 관리', '월 저축 여력과 맞음', '마감 전 현금 흐름 안정'],
    caution: '중도해지 시 우대금리가 적용되지 않을 수 있습니다.',
  },
]

export const housingRecommendations = subscriptions.map((item) => ({
  notice_id: item.id,
  title: item.name,
  provider: 'CheongYak Navi',
  region: item.district,
  district: item.address,
  supply_type: item.supplyType,
  price: item.priceValue,
  total_score: item.matchScore,
  source_url: '',
  reasons: item.strengths,
  score_detail: {
    eligibility: Math.min(100, item.matchScore + 1),
    funding: Math.max(60, item.matchScore - 7),
    location: Math.max(60, item.matchScore - 4),
    schedule: Math.max(60, item.matchScore - 2),
    policy_link: Math.max(60, item.matchScore - 10),
  },
}))

const primaryPrice = subscriptions[0].priceValue
const downPayment = Math.round(primaryPrice * 0.1)
const availableCash = profile.asset - profile.debt
const shortfall = Math.max(0, downPayment - availableCash)

export const fundingPlan = {
  notice_id: subscriptions[0].id,
  price: primaryPrice,
  down_payment: downPayment,
  available_cash: availableCash,
  shortfall,
  months_until_contract: profile.target_months,
  monthly_target: Math.ceil(shortfall / Math.max(profile.target_months, 1)),
  timeline: [
    { label: '접수 마감', date: subscriptions[0].deadline, amount: 0 },
    { label: '당첨자 발표', date: subscriptions[0].winnerDate, amount: 0 },
    { label: '계약금 납부', date: '2026-06-15', amount: downPayment },
    { label: '중도금 대출 검토', date: '2026-07-01', amount: Math.round(primaryPrice * 0.6) },
    { label: '잔금 계획', date: subscriptions[0].moveIn, amount: Math.round(primaryPrice * 0.3) },
  ],
}

export const aiCoach = {
  summary:
    '매칭률이 높은 청약을 우선 검토하고, 계약금 부족액과 서류 발급 일정을 함께 관리하는 흐름이 적합합니다.',
  todo_this_week: [
    '주민등록등본과 가족관계증명서 발급 기준일 확인',
    '공고문의 소득, 무주택, 청약통장 조건 재검토',
    '계약금 부족액 기준으로 대출 상품 한도 비교',
  ],
  official_checklist: ['신청 자격 조건', '접수 마감일과 당첨자 발표일', '분양가, 계약금, 중도금 일정'],
  warning:
    'AI 추천 결과는 참고용입니다. 실제 신청 전에는 반드시 공식 공고문을 기준으로 자격과 일정을 확인해야 합니다.',
}
