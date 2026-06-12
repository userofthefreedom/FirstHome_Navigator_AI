const PAGE_TARGETS = [
    {
        title: '대시보드',
        description: '추천 후보, 달력, 이번 주 할 일을 한 번에 봅니다.',
        route: '/',
        keywords: ['홈', '대시보드', '현황', '준비', '캘린더', '달력'],
    },
    {
        title: '조건 입력',
        description: '희망 지역, 자금, 면적 조건을 수정합니다.',
        route: '/profile',
        keywords: ['조건', '입력', '프로필', '자금', '지역', '면적', '평수'],
    },
    {
        title: '추천 청약',
        description: '입력 조건에 맞는 청약 후보를 다시 봅니다.',
        route: '/recommendations',
        keywords: ['추천', '청약', '후보', '점수', '순위'],
    },
    {
        title: '청약 지도',
        description: '공고 위치를 지도에서 확인합니다.',
        route: '/map',
        keywords: ['지도', '위치', '지역', '카카오', '맵'],
    },
    {
        title: '관심목록',
        description: '저장한 공고와 주택형 옵션을 확인합니다.',
        route: '/favorites',
        keywords: ['관심', '저장', '북마크', '목록'],
    },
];

const QUICK_ACTIONS = [
    {
        title: '선택 공고 자금 로드맵',
        description: '현재 선택한 공고와 주택형의 계약금·납부 일정·대출 후보를 봅니다.',
        basePath: '/funding',
        keywords: ['자금', '로드맵', '계약금', '납부', '중도금', '잔금', '부족액', '대출', '주담대', '주택담보대출', '금융', '금리', '한도'],
    },
    {
        title: '선택 공고 AI 코치',
        description: '현재 선택한 공고 기준으로 다음 할 일을 정리합니다.',
        basePath: '/ai-coach',
        keywords: ['ai', '코치', '할일', '서류', '분석', '체크', '확인'],
    },
];

const CONCEPT_TARGETS = [
    {
        title: '구입자금 대출 후보',
        description: '선택 공고의 자금 로드맵에서 주택 구입 목적 대출 후보를 확인합니다.',
        basePath: '/funding',
        keywords: ['대출', '주담대', '주택담보대출', '구입자금', '디딤돌', '보금자리론', '금리', '한도', 'ltv'],
    },
    {
        title: '지원정책 후보',
        description: '자금 로드맵에서 청약·주거·금융 관련 지원정책 후보를 확인합니다.',
        basePath: '/funding',
        keywords: ['정책', '지원', '지원정책', '주거지원', '청년정책', '청약정책', '보조금', '복지'],
    },
    {
        title: '필수 서류와 공식 확인 항목',
        description: '공고 상세에서 제출 서류와 공식 공고문 확인 항목을 봅니다.',
        basePath: '/notices',
        keywords: ['서류', '제출', '신분증', '주민등록', '소득', '자산', '공고문', '공식'],
    },
    {
        title: 'AI 코치로 다음 할 일 정리',
        description: '선택 공고 기준으로 준비할 일과 확인할 조건을 정리합니다.',
        basePath: '/ai-coach',
        keywords: ['할일', '할 일', '다음', '준비', '체크리스트', '코칭', '코치'],
    },
];

function normalize(value) {
    return String(value ?? '').trim().toLowerCase().replace(/\s+/g, '');
}

function includesTerm(values, query) {
    const normalizedQuery = normalize(query);
    if (!normalizedQuery)
        return false;
    return values.some((value) => normalize(value).includes(normalizedQuery));
}

function selectionRoute(basePath, selection) {
    if (!selection?.noticeId) {
        if (basePath === '/funding' || basePath === '/notices' || basePath === '/ai-coach')
            return '/recommendations';
        return basePath;
    }
    if (basePath === '/notices') {
        const noticePath = `/notices/${selection.noticeId}`;
        return selection.optionId ? { path: noticePath, query: { option_id: selection.optionId } } : noticePath;
    }
    const path = `${basePath}/${selection.noticeId}`;
    return selection.optionId ? { path, query: { option_id: selection.optionId } } : path;
}

function optionIdForNotice(notice) {
    const option = notice?.best_option ?? notice?.top_options?.[0] ?? null;
    return option?.option_id ?? null;
}

function noticeRoute(notice) {
    const optionId = optionIdForNotice(notice);
    return optionId ? { path: `/notices/${notice.notice_id}`, query: { option_id: optionId } } : `/notices/${notice.notice_id}`;
}

function noticeScore(notice, query) {
    const normalizedQuery = normalize(query);
    const title = normalize(notice.title);
    const region = normalize(`${notice.region ?? ''} ${notice.district ?? ''}`);
    const supply = normalize(`${notice.supply_type ?? ''} ${notice.ownership_type ?? ''}`);
    const provider = normalize(notice.provider);
    let score = 0;
    if (title.includes(normalizedQuery))
        score += title.startsWith(normalizedQuery) ? 80 : 60;
    if (region.includes(normalizedQuery))
        score += 45;
    if (supply.includes(normalizedQuery))
        score += 30;
    if (provider.includes(normalizedQuery))
        score += 20;
    score += Math.min(10, Number(notice.total_score ?? 0) / 10);
    return score;
}

function noticeResults(query, recommendations) {
    return recommendations
        .map((notice) => ({ notice, score: noticeScore(notice, query) }))
        .filter((row) => row.score > 0)
        .sort((left, right) => right.score - left.score)
        .slice(0, 5)
        .map(({ notice }) => ({
            id: `notice-${notice.notice_id}`,
            type: '공고',
            title: notice.title,
            description: [notice.provider, notice.region, notice.district, notice.supply_type].filter(Boolean).join(' · '),
            meta: notice.application_deadline ? `마감 ${notice.application_deadline}` : '',
            route: noticeRoute(notice),
        }));
}

function pageResults(query) {
    return PAGE_TARGETS
        .filter((target) => includesTerm([target.title, target.description, ...target.keywords], query))
        .map((target) => ({
            id: `page-${target.route}`,
            type: '화면',
            title: target.title,
            description: target.description,
            route: target.route,
        }));
}

function quickActionResults(query, selection) {
    return QUICK_ACTIONS
        .filter((target) => includesTerm([target.title, target.description, ...target.keywords], query))
        .map((target) => ({
            id: `action-${target.basePath}`,
            type: '바로가기',
            title: target.title,
            description: selection?.noticeId ? target.description : '먼저 추천 청약에서 공고를 선택하면 바로 이동할 수 있습니다.',
            route: selectionRoute(target.basePath, selection),
        }));
}

function conceptResults(query, selection) {
    return CONCEPT_TARGETS
        .filter((target) => includesTerm([target.title, target.description, ...target.keywords], query))
        .map((target) => ({
            id: `concept-${target.basePath}-${target.title}`,
            type: '개념',
            title: target.title,
            description: selection?.noticeId ? target.description : '추천 청약에서 공고를 선택하면 해당 정보를 바로 확인할 수 있습니다.',
            route: selectionRoute(target.basePath, selection),
        }));
}

function mapResult(query) {
    const trimmed = String(query ?? '').trim();
    if (!trimmed)
        return [];
    return [
        {
            id: `map-search-${trimmed}`,
            type: '지도',
            title: `"${trimmed}" 지도에서 보기`,
            description: '청약 지도에서 공고명, 지역, 지구명으로 필터링합니다.',
            route: { path: '/map', query: { search: trimmed } },
        },
    ];
}

export function buildGlobalSearchResults({ query, recommendations = [], selection = {} }) {
    const trimmed = String(query ?? '').trim();
    if (!trimmed)
        return [];
    return [
        ...conceptResults(trimmed, selection),
        ...quickActionResults(trimmed, selection),
        ...pageResults(trimmed),
        ...noticeResults(trimmed, recommendations),
        ...mapResult(trimmed),
    ].slice(0, 8);
}
