export type Subscription = {
  id: number;
  name: string;
  district: string;
  address: string;
  supplyType: string;
  housingType: string;
  area: string;
  price: string;
  deposit: string;
  competition: string;
  deadline: string;
  winnerDate: string;
  moveIn: string;
  matchScore: number;
  commute: string;
  tags: string[];
  strengths: string[];
  cautions: string[];
  position: {
    top: string;
    left: string;
  };
};

export type FinancialProduct = {
  id: number;
  name: string;
  provider: string;
  category: "전세대출" | "주택담보대출" | "청약통장" | "적금";
  rate: string;
  limit: string;
  period: string;
  matchScore: number;
  tags: string[];
  reasons: string[];
  caution: string;
};

export type CommunityPost = {
  id: number;
  category: "후기" | "질문" | "꿀팁" | "동네정보";
  title: string;
  author: string;
  district: string;
  summary: string;
  replies: number;
  likes: number;
  createdAt: string;
  tags: string[];
};

export const profile = {
  name: "김싸피",
  region: "서울 강남권",
  household: "3인 가구",
  budget: "4.8억 이하",
  score: 84,
  subscriptionAccount: "8년 4개월",
  preferredAreas: ["강남", "송파", "성남", "마곡"],
};

export const subscriptions: Subscription[] = [
  {
    id: 1,
    name: "서초 센트럴 라움",
    district: "서울 서초구",
    address: "서울특별시 서초구 반포대로 28길",
    supplyType: "민영",
    housingType: "아파트",
    area: "84㎡",
    price: "4억 6,800만",
    deposit: "계약금 10%",
    competition: "12.4:1",
    deadline: "2026-05-23",
    winnerDate: "2026-06-03",
    moveIn: "2028년 2월",
    matchScore: 96,
    commute: "강남역 18분",
    tags: ["역세권", "초등학교 450m", "분양가 상한제"],
    strengths: ["예산 안에 들어오는 84㎡", "출퇴근 동선 우수", "가점 경쟁력 높음"],
    cautions: ["접수 마감 임박", "서류 제출 기간 짧음"],
    position: { top: "42%", left: "56%" },
  },
  {
    id: 2,
    name: "송파 레이크 포레",
    district: "서울 송파구",
    address: "서울특별시 송파구 올림픽로 221",
    supplyType: "공공분양",
    housingType: "아파트",
    area: "74㎡",
    price: "3억 9,500만",
    deposit: "계약금 15%",
    competition: "9.8:1",
    deadline: "2026-05-28",
    winnerDate: "2026-06-10",
    moveIn: "2027년 11월",
    matchScore: 91,
    commute: "잠실역 9분",
    tags: ["공원 인접", "대중교통", "신혼 특공"],
    strengths: ["특별공급 조건 적합", "생활 인프라 밀집", "전매 제한 짧음"],
    cautions: ["주차 대수 확인 필요"],
    position: { top: "47%", left: "65%" },
  },
  {
    id: 3,
    name: "판교 테크노밸리 포레",
    district: "경기 성남시",
    address: "경기도 성남시 분당구 판교역로 235",
    supplyType: "민영",
    housingType: "아파트",
    area: "98㎡",
    price: "5억 2,000만",
    deposit: "계약금 10%",
    competition: "17.6:1",
    deadline: "2026-06-04",
    winnerDate: "2026-06-17",
    moveIn: "2028년 5월",
    matchScore: 86,
    commute: "판교역 12분",
    tags: ["직주근접", "중대형", "IT 단지"],
    strengths: ["직장 접근성 우수", "중대형 희소성", "학군 선호 높음"],
    cautions: ["예산 초과 가능성", "경쟁률 상승 추세"],
    position: { top: "61%", left: "52%" },
  },
  {
    id: 4,
    name: "마곡 에코스퀘어",
    district: "서울 강서구",
    address: "서울특별시 강서구 마곡중앙로 76",
    supplyType: "공공분양",
    housingType: "오피스텔",
    area: "59㎡",
    price: "3억 1,700만",
    deposit: "계약금 10%",
    competition: "6.3:1",
    deadline: "2026-06-12",
    winnerDate: "2026-06-25",
    moveIn: "2027년 8월",
    matchScore: 82,
    commute: "마곡역 6분",
    tags: ["낮은 분양가", "산업단지", "1순위 가능"],
    strengths: ["자금 부담 낮음", "지하철 접근성 좋음", "잔여 일정 여유"],
    cautions: ["선호 면적보다 작음"],
    position: { top: "39%", left: "31%" },
  },
];

export const dashboardStats = [
  { label: "맞춤 추천", value: "12건", tone: "blue", change: "+3" },
  { label: "마감 임박", value: "4건", tone: "amber", change: "D-8" },
  { label: "신청 진행", value: "2건", tone: "teal", change: "접수중" },
  { label: "자격 점수", value: `${profile.score}점`, tone: "rose", change: "상위 18%" },
];

export const timeline = [
  { date: "05.23", title: "서초 센트럴 라움 1순위 접수 마감", type: "deadline" },
  { date: "05.28", title: "송파 레이크 포레 공공분양 접수 종료", type: "deadline" },
  { date: "06.03", title: "서초 센트럴 라움 당첨자 발표", type: "winner" },
  { date: "06.10", title: "송파 레이크 포레 당첨자 발표", type: "winner" },
];

export const documents = [
  "주민등록등본",
  "가족관계증명서",
  "청약통장 가입확인서",
  "소득금액증명원",
  "무주택 확인서",
];

export const financialProducts: FinancialProduct[] = [
  {
    id: 1,
    name: "청약 당첨 대비 전세 브릿지론",
    provider: "SSAFY Bank",
    category: "전세대출",
    rate: "연 3.42%~",
    limit: "최대 2.8억",
    period: "24개월",
    matchScore: 94,
    tags: ["중도상환수수료 면제", "무주택 우대", "모바일 서류"],
    reasons: ["예상 계약금 일정과 맞음", "현재 소득 대비 DSR 여유", "입주 전 임시 거주비 대응"],
    caution: "당첨 후 계약서 제출 시 우대금리가 확정됩니다.",
  },
  {
    id: 2,
    name: "분양 잔금 안심 주택담보대출",
    provider: "하나로저축",
    category: "주택담보대출",
    rate: "연 3.88%~",
    limit: "분양가의 70%",
    period: "최대 35년",
    matchScore: 89,
    tags: ["고정혼합형", "거치 1년", "잔금일 알림"],
    reasons: ["서초 센트럴 라움 잔금 시점과 맞음", "장기 고정비 관리에 유리", "예산 상단 청약에 적합"],
    caution: "분양권 담보 인정 여부는 단지별 협약에 따라 달라집니다.",
  },
  {
    id: 3,
    name: "청약 가점 성장 적금",
    provider: "국민내일은행",
    category: "적금",
    rate: "연 4.10%",
    limit: "월 50만원",
    period: "12개월",
    matchScore: 86,
    tags: ["자동이체 우대", "청약통장 연동", "비상금 분리"],
    reasons: ["계약금 준비금을 별도 관리", "월 저축 여력에 맞음", "마감 임박 청약 전 현금흐름 안정"],
    caution: "중도해지 시 우대금리가 적용되지 않을 수 있습니다.",
  },
  {
    id: 4,
    name: "청년 주거래 청약통장",
    provider: "우리동네은행",
    category: "청약통장",
    rate: "연 2.80%",
    limit: "월 20만원",
    period: "자유",
    matchScore: 81,
    tags: ["소득공제", "납입 인정", "자동 리포트"],
    reasons: ["납입 회차 유지에 도움", "세액 혜택 확인 가능", "장기 청약 준비에 적합"],
    caution: "기존 통장 전환 가능 여부를 먼저 확인해야 합니다.",
  },
];

export const communityPosts: CommunityPost[] = [
  {
    id: 1,
    category: "후기",
    title: "서초 센트럴 라움 모델하우스 다녀온 후기",
    author: "반포입성",
    district: "서울 서초구",
    summary: "84㎡ 타입 수납은 괜찮았고, 출퇴근 동선은 강남권 직장인에게 확실히 좋아 보였습니다.",
    replies: 18,
    likes: 42,
    createdAt: "2시간 전",
    tags: ["모델하우스", "84㎡", "서초"],
  },
  {
    id: 2,
    category: "질문",
    title: "공공분양 신혼 특공 소득 기준 계산이 헷갈려요",
    author: "첫청약러",
    district: "서울 송파구",
    summary: "맞벌이 3인 가구 기준으로 월평균 소득을 어디까지 넣어야 하는지 궁금합니다.",
    replies: 27,
    likes: 31,
    createdAt: "4시간 전",
    tags: ["신혼특공", "소득기준", "송파"],
  },
  {
    id: 3,
    category: "꿀팁",
    title: "청약 서류 발급일 기준 체크리스트 공유",
    author: "서류마스터",
    district: "전국",
    summary: "주민등록등본, 가족관계증명서, 소득금액증명원은 공고일 이후 발급본인지 꼭 확인하세요.",
    replies: 9,
    likes: 58,
    createdAt: "어제",
    tags: ["서류", "체크리스트", "실수방지"],
  },
  {
    id: 4,
    category: "동네정보",
    title: "마곡역 주변 실거주 장단점 정리",
    author: "마곡직장인",
    district: "서울 강서구",
    summary: "평일 출퇴근은 편하지만 주말 상권은 단지별로 체감 차이가 커서 현장 방문을 추천합니다.",
    replies: 12,
    likes: 24,
    createdAt: "2일 전",
    tags: ["마곡", "실거주", "교통"],
  },
];
