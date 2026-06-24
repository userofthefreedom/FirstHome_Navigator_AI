import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const baseUrl = normalizeBaseUrl(process.argv[2] || 'https://polka-kennel-decorated.ngrok-free.dev');
const runId = new Date().toISOString().replace(/[:.]/g, '-');
const outDir = path.resolve('results', runId);
const shotDir = path.join(outDir, 'screenshots');

const routes = [
  { key: 'home', path: '/', budgetMs: 4500 },
  { key: 'profile', path: '/profile', budgetMs: 4500 },
  { key: 'recommendations', path: '/recommendations', budgetMs: 5000 },
  { key: 'map', path: '/map', budgetMs: 8500 },
  { key: 'funding', path: '/funding', budgetMs: 5500 },
  { key: 'ai_coach', path: '/ai-coach', budgetMs: 10000 },
  { key: 'favorites', path: '/favorites', budgetMs: 5000 },
  { key: 'products', path: '/finance/products', budgetMs: 5000 },
  { key: 'economy_now', path: '/finance/economy-now', budgetMs: 5500 },
  { key: 'agora', path: '/finance/agora', budgetMs: 5500 },
  { key: 'my_page', path: '/my-page', budgetMs: 5000 },
  { key: 'auth', path: '/auth', budgetMs: 4500 },
];

const scenarioUsers = [
  {
    key: 'seoul_cash_short',
    name: '서울부족',
    profile: {
      name: '서울부족',
      birth_year: 1999,
      is_homeless: true,
      subscription_months: 36,
      annual_income: 50000000,
      asset: 10000000,
      debt: 0,
      monthly_saving: 800000,
      target_months: 18,
      preferred_regions: ['서울', '경기 남부', '인천'],
      desired_area_min: 45,
      desired_area_max: 85,
      desired_area_min_m2: 45,
      desired_area_max_m2: 85,
      desired_price_min: 0,
      desired_price_max: 700000000,
      max_down_payment: 10000000,
      monthly_payment_capacity: 800000,
    },
    expectedRegions: ['서울', '경기', '인천'],
  },
  {
    key: 'incheon_stable',
    name: '인천안정',
    profile: {
      name: '인천안정',
      birth_year: 1994,
      is_homeless: true,
      subscription_months: 72,
      annual_income: 42000000,
      asset: 90000000,
      debt: 5000000,
      monthly_saving: 1200000,
      target_months: 12,
      preferred_regions: ['인천'],
      desired_area_min: 50,
      desired_area_max: 70,
      desired_area_min_m2: 50,
      desired_area_max_m2: 70,
      desired_price_min: 0,
      desired_price_max: 650000000,
      max_down_payment: 90000000,
      monthly_payment_capacity: 1200000,
    },
    expectedRegions: ['인천'],
  },
  {
    key: 'busan_low_budget',
    name: '부산예산',
    profile: {
      name: '부산예산',
      birth_year: 2001,
      is_homeless: true,
      subscription_months: 12,
      annual_income: 30000000,
      asset: 15000000,
      debt: 2000000,
      monthly_saving: 500000,
      target_months: 24,
      preferred_regions: ['부산', '경남'],
      desired_area_min: 40,
      desired_area_max: 60,
      desired_area_min_m2: 40,
      desired_area_max_m2: 60,
      desired_price_min: 0,
      desired_price_max: 500000000,
      max_down_payment: 15000000,
      monthly_payment_capacity: 500000,
    },
    expectedRegions: ['부산', '경남'],
  },
];

const aiChecks = [
  {
    key: 'agora',
    path: '/finance/agora',
    question: '이 화면은 어떻게 쓰면 돼?',
    expect: ['영상', '검색', '의견', '청약'],
    forbid: ['선택한 공고', '저장한 옵션', '분양 옵션을 비교'],
  },
  {
    key: 'map',
    path: '/map',
    question: '지도 화면은 어떻게 써?',
    expect: ['지도', '지역', '공고'],
    forbid: ['MY PAGE에서', '금융상품 가입'],
  },
  {
    key: 'my_page',
    path: '/my-page',
    question: 'MY PAGE에서는 뭘 할 수 있어?',
    expect: ['가입', '관심', '확인'],
    forbid: ['자산을 수정', '부채를 수정', '월 저축을 수정'],
  },
  {
    key: 'products',
    path: '/finance/products',
    question: '금융상품은 어떻게 비교해?',
    expect: ['금리', '기간', '상품'],
    forbid: ['청약 신청을 완료'],
  },
];

const report = {
  run_id: runId,
  base_url: baseUrl,
  started_at: new Date().toISOString(),
  mode: 'beta-complete',
  pages: [],
  actions: [],
  visual: [],
  hover: [],
  ai: [],
  scenarios: [],
  issues: [],
};

function normalizeBaseUrl(value) {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

function issue(severity, area, message, details = {}) {
  report.issues.push({ severity, area, message, details });
}

async function ensureDirs() {
  await fs.mkdir(shotDir, { recursive: true });
}

async function createBrowser() {
  return chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
}

async function newContext(browser, viewport = { width: 1440, height: 960 }) {
  return browser.newContext({
    viewport,
    extraHTTPHeaders: { 'ngrok-skip-browser-warning': 'true' },
  });
}

async function register(page, label = 'beta') {
  const username = `${label}_${Date.now()}_${Math.random().toString(16).slice(2, 6)}`;
  await page.goto(`${baseUrl}/auth`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.getByRole('button', { name: /계정이 없으면 회원가입/ }).click({ timeout: 8000 }).catch(() => undefined);
  await page.getByLabel('아이디').fill(username);
  await page.getByLabel('이메일').fill(`${username}@example.com`);
  await page.getByLabel('이름').fill('베타사용자');
  await page.getByLabel('출생년도').fill('1999');
  await page.getByLabel('비밀번호').fill('betapass123');
  await page.getByRole('button', { name: /^회원가입$/ }).click();
  await page.waitForURL(/\/profile/, { timeout: 12000 });
  return username;
}

async function saveProfile(page, profile) {
  await page.evaluate(async (payload) => {
    const response = await fetch('/api/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
      credentials: 'include',
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(`profile ${response.status}`);
  }, profile);
}

async function gotoPage(page, route, scenario) {
  const failedRequests = [];
  const pageErrors = [];
  const onFailed = (request) => {
    const url = request.url();
    const failure = request.failure()?.errorText || 'unknown';
    if (isIgnorableRequestFailure(url, failure)) return;
    failedRequests.push({ url, method: request.method(), failure });
  };
  const onPageError = (error) => pageErrors.push(String(error.message || error).slice(0, 500));
  page.on('requestfailed', onFailed);
  page.on('pageerror', onPageError);

  const started = Date.now();
  const response = await page.goto(`${baseUrl}${route.path}`, { waitUntil: 'domcontentloaded', timeout: 45000 }).catch((error) => {
    issue('P0', route.key, '페이지 진입 실패', { scenario, path: route.path, error: String(error.message || error) });
    return null;
  });
  await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => undefined);
  await page.waitForTimeout(route.key === 'map' ? 1800 : 800);
  const elapsedMs = Date.now() - started;
  const bodyText = await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
  const status = response?.status?.() ?? null;
  const screenshot = path.join(shotDir, `${scenario}_${route.key}.png`);
  await page.screenshot({ path: screenshot, fullPage: true }).catch(() => undefined);

  page.off('requestfailed', onFailed);
  page.off('pageerror', onPageError);

  if (bodyText.includes('ERR_NGROK_6024') || bodyText.includes('You are about to visit')) {
    issue('P0', route.key, 'ngrok 경고 페이지가 노출됨', { scenario, path: route.path });
  }
  if (!bodyText.trim()) {
    issue('P0', route.key, '본문 텍스트가 비어 있음', { scenario, path: route.path });
  }
  if (status && status >= 500) {
    issue('P0', route.key, `서버 오류 상태 코드 ${status}`, { scenario, path: route.path });
  }
  if (elapsedMs > route.budgetMs) {
    issue('P1', route.key, `로딩 예산 초과 ${elapsedMs}ms`, { scenario, budget_ms: route.budgetMs });
  }
  if (pageErrors.length) {
    issue('P0', route.key, '페이지 JS 예외 발생', { scenario, pageErrors });
  }
  if (failedRequests.length) {
    issue('P1', route.key, '네트워크 요청 실패', { scenario, failedRequests: failedRequests.slice(0, 8) });
  }

  const visual = await auditVisual(page, `${scenario}/${route.key}`);
  const hover = await auditHover(page, `${scenario}/${route.key}`);

  report.pages.push({
    scenario,
    key: route.key,
    path: route.path,
    status,
    elapsed_ms: elapsedMs,
    screenshot: path.relative(outDir, screenshot),
    failed_requests: failedRequests,
    page_errors: pageErrors,
  });
  report.visual.push(visual);
  report.hover.push(hover);
}

async function auditVisual(page, scope) {
  const result = await page.evaluate(() => {
    function parseRgb(value) {
      const match = String(value || '').match(/rgba?\(([^)]+)\)/);
      if (!match) return null;
      const parts = match[1].split(',').map((part) => Number.parseFloat(part.trim()));
      if (parts.length < 3) return null;
      return { r: parts[0], g: parts[1], b: parts[2], a: Number.isFinite(parts[3]) ? parts[3] : 1 };
    }
    function luminance({ r, g, b }) {
      const values = [r, g, b].map((v) => {
        const s = v / 255;
        return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
    }
    function contrast(fg, bg) {
      const l1 = luminance(fg);
      const l2 = luminance(bg);
      const high = Math.max(l1, l2);
      const low = Math.min(l1, l2);
      return (high + 0.05) / (low + 0.05);
    }
    function effectiveBackground(element) {
      let current = element;
      while (current && current !== document.documentElement) {
        const bg = parseRgb(getComputedStyle(current).backgroundColor);
        if (bg && bg.a > 0.2) return bg;
        current = current.parentElement;
      }
      return parseRgb(getComputedStyle(document.body).backgroundColor) || { r: 255, g: 255, b: 255, a: 1 };
    }
    function visible(element) {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return rect.width > 2 && rect.height > 2 && style.visibility !== 'hidden' && style.display !== 'none' && Number(style.opacity) > 0.05;
    }
    const nodes = [...document.querySelectorAll('body *')]
      .filter((element) => visible(element))
      .filter((element) => !element.closest('.leaflet-container, .leaflet-control, .leaflet-pane, .leaflet-map-pane, .leaflet-overlay-pane, .leaflet-marker-pane'))
      .filter((element) => {
        const own = [...element.childNodes].filter((node) => node.nodeType === Node.TEXT_NODE).map((node) => node.textContent.trim()).join(' ');
        return own.length >= 2;
      })
      .slice(0, 500);
    const lowContrast = [];
    const muddyFont = [];
    for (const element of nodes) {
      const style = getComputedStyle(element);
      const fg = parseRgb(style.color);
      const bg = effectiveBackground(element);
      if (!fg || !bg) continue;
      const text = element.innerText.trim().replace(/\s+/g, ' ').slice(0, 90);
      const fontSize = Number.parseFloat(style.fontSize || '0');
      const weight = Number.parseInt(style.fontWeight || '400', 10);
      const ratio = contrast(fg, bg);
      const required = fontSize >= 18 || (fontSize >= 14 && weight >= 700) ? 3 : 4.5;
      if (ratio < required) {
        lowContrast.push({ text, ratio: Math.round(ratio * 100) / 100, required, color: style.color, background: `rgb(${bg.r}, ${bg.g}, ${bg.b})` });
      }
      if (fontSize >= 15 && fontSize <= 22 && weight >= 800 && /[가-힣]/.test(text)) {
        muddyFont.push({ text, fontSize, weight, fontFamily: style.fontFamily.split(',')[0] });
      }
    }
    const controls = [...document.querySelectorAll('button, a, input, select, textarea')]
      .filter((element) => visible(element))
      .filter((element) => !element.closest('.leaflet-container, .leaflet-control, .leaflet-pane, .leaflet-map-pane, .leaflet-overlay-pane, .leaflet-marker-pane'));
    const tinyTargets = controls.filter((element) => {
      const rect = element.getBoundingClientRect();
      return rect.width < 32 || rect.height < 32;
    }).map((element) => ({
      text: (element.innerText || element.getAttribute('aria-label') || element.getAttribute('placeholder') || element.tagName).trim().slice(0, 60),
      width: Math.round(element.getBoundingClientRect().width),
      height: Math.round(element.getBoundingClientRect().height),
    }));
    return {
      lowContrast: lowContrast.slice(0, 20),
      muddyFont: muddyFont.slice(0, 20),
      tinyTargets: tinyTargets.slice(0, 20),
      checkedTextCount: nodes.length,
      checkedControlCount: controls.length,
    };
  });

  if (result.lowContrast.length) {
    issue('P1', 'visual', '낮은 텍스트 대비 후보 발견', { scope, examples: result.lowContrast.slice(0, 5) });
  }
  if (result.muddyFont.length >= 8) {
    issue('P2', 'visual', '중간 크기 고굵기 한글 폰트 뭉개짐 위험', { scope, examples: result.muddyFont.slice(0, 5) });
  }
  if (result.tinyTargets.length) {
    issue('P2', 'visual', '터치/클릭 목표 크기가 작은 요소 발견', { scope, examples: result.tinyTargets.slice(0, 5) });
  }
  return { scope, ...result };
}

async function auditHover(page, scope) {
  const handles = await page.locator('button:visible, a:visible, select:visible').elementHandles();
  const samples = handles.slice(0, 35);
  const noChange = [];
  for (const handle of samples) {
    const before = await handle.evaluate((element) => {
      const style = getComputedStyle(element);
      return {
        text: (element.innerText || element.getAttribute('aria-label') || element.getAttribute('title') || element.tagName).trim().slice(0, 80),
        color: style.color,
        background: style.backgroundColor,
        border: style.borderColor,
        boxShadow: style.boxShadow,
        transform: style.transform,
      };
    }).catch(() => null);
    if (!before) continue;
    await handle.hover({ timeout: 1500 }).catch(() => undefined);
    await page.waitForTimeout(90);
    const after = await handle.evaluate((element) => {
      const style = getComputedStyle(element);
      return {
        color: style.color,
        background: style.backgroundColor,
        border: style.borderColor,
        boxShadow: style.boxShadow,
        transform: style.transform,
      };
    }).catch(() => null);
    if (!after) continue;
    const changed = ['color', 'background', 'border', 'boxShadow', 'transform'].some((key) => before[key] !== after[key]);
    if (!changed && before.text && !['SELECT', 'OPTION'].includes(before.text)) {
      noChange.push(before.text);
    }
  }
  if (noChange.length >= 8) {
    issue('P2', 'hover', 'hover 반응이 없는 클릭 요소가 많음', { scope, examples: noChange.slice(0, 8) });
  }
  return { scope, sampled: samples.length, no_change: noChange.slice(0, 20) };
}

async function runGuestAndUserPages(browser) {
  const guestContext = await newContext(browser);
  const guestPage = await guestContext.newPage();
  for (const route of routes) {
    await gotoPage(guestPage, route, 'guest');
  }
  await guestContext.close();

  const userContext = await newContext(browser);
  const userPage = await userContext.newPage();
  const username = await register(userPage, 'complete');
  await saveProfile(userPage, scenarioUsers[0].profile);
  report.actions.push({ scenario: 'user', action: 'register_and_save_profile', username });
  for (const route of routes.filter((route) => route.key !== 'auth')) {
    await gotoPage(userPage, route, 'user');
  }
  await runInteractionMatrix(userPage);
  await runAiContextChecks(userPage);
  await userContext.close();
}

async function runInteractionMatrix(page) {
  await page.goto(`${baseUrl}/recommendations`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => undefined);
  const sort = page.locator('select').first();
  if (await sort.count()) {
    for (const value of ['deadline', 'price_low', 'contract_low', 'shortfall_low', 'score']) {
      await sort.selectOption(value).catch((error) => issue('P1', 'recommendations', '정렬 선택 실패', { value, error: String(error.message || error) }));
      await page.waitForTimeout(250);
    }
    report.actions.push({ scenario: 'user', action: 'recommendation_sort_options' });
  }
  await clickFirst(page, /조건 수정/, 'recommendations_profile_link');
  if (!page.url().includes('/profile')) issue('P1', 'recommendations', '조건 수정 버튼이 조건 입력으로 이동하지 않음', { url: page.url() });

  await page.goto(`${baseUrl}/finance/products`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => undefined);
  const selects = await page.locator('select').count();
  for (let i = 0; i < selects; i += 1) {
    const select = page.locator('select').nth(i);
    const values = await select.locator('option').evaluateAll((options) => options.slice(0, 2).map((option) => option.value));
    if (values[1] !== undefined) {
      await select.selectOption(values[1]).catch((error) => issue('P1', 'products', '금융상품 필터 선택 실패', { index: i, error: String(error.message || error) }));
      await page.waitForTimeout(350);
    }
  }
  const search = page.getByPlaceholder(/상품명 또는 은행 검색/);
  if (await search.count()) {
    await search.fill('NH');
    await page.waitForTimeout(700);
    report.actions.push({ scenario: 'user', action: 'product_search_filter' });
  } else {
    issue('P1', 'products', '금융상품 검색창을 찾지 못함');
  }

  await page.goto(`${baseUrl}/finance/agora`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => undefined);
  const videoSearch = page.getByPlaceholder(/관심 키워드 검색/);
  if (await videoSearch.count()) {
    await videoSearch.fill('청약 자금');
    await clickFirst(page, /^검색$/, 'agora_video_search');
  } else {
    issue('P1', 'agora', '영상 검색창을 찾지 못함');
  }
  for (const tab of ['청약', '금융상품', '자금준비', '자유 게시판', '전체']) {
    await clickFirst(page, new RegExp(`^${tab}$`), `agora_tab_${tab}`);
  }
  const title = `베타 글 ${Date.now()}`;
  await page.getByPlaceholder(/글 제목/).fill(title).catch(() => undefined);
  await page.getByPlaceholder('내용').fill('베타 테스트 작성 글입니다.').catch(() => undefined);
  await clickFirst(page, /글쓰기/, 'agora_create_post');
  await page.waitForTimeout(800);
  const body = await page.locator('body').innerText().catch(() => '');
  if (!body.includes(title)) issue('P1', 'agora', '게시글 작성 후 목록 반영 실패', { title });

  await page.goto(`${baseUrl}/map`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => undefined);
  for (const mode of ['청약', '부동산', '은행']) {
    await clickFirst(page, new RegExp(`^${mode}$`), `map_mode_${mode}`);
  }
  const mapSearch = page.getByPlaceholder(/청약명|지역|지구|검색/).first();
  if (await mapSearch.count()) {
    await mapSearch.fill('인천');
    await clickFirst(page, /검색/, 'map_search');
  }
}

async function runAiContextChecks(page) {
  for (const check of aiChecks) {
    await page.goto(`${baseUrl}${check.path}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => undefined);
    const answer = await askCoach(page, check.question);
    const hasExpected = check.expect.some((word) => answer.includes(word));
    const hasForbidden = check.forbid.some((word) => answer.includes(word));
    const row = { key: check.key, answer_excerpt: answer.slice(0, 400), has_expected: hasExpected, has_forbidden: hasForbidden };
    report.ai.push(row);
    if (!hasExpected) issue('P1', 'ai_chat', '챗봇 답변이 화면 기대 맥락을 충분히 포함하지 않음', { key: check.key, expect: check.expect, answer: row.answer_excerpt });
    if (hasForbidden) issue('P1', 'ai_chat', '챗봇 답변이 해당 화면에서 부적절한 기능을 안내함', { key: check.key, forbid: check.forbid, answer: row.answer_excerpt });
  }
}

async function askCoach(page, question) {
  await page.getByText('AI', { exact: true }).last().click({ timeout: 5000 }).catch(() => undefined);
  const input = page.getByPlaceholder(/궁금한 내용을 입력|질문/).last();
  if (!(await input.count())) {
    issue('P1', 'ai_chat', '챗봇 입력창을 찾지 못함', { question });
    return '';
  }
  const beforeAnswers = await assistantBubbleTexts(page);
  await input.fill(question);
  await input.press('Enter').catch(async () => {
    await page.getByRole('button', { name: /전송|send/i }).last().click({ timeout: 3000 }).catch(() => undefined);
  });
  await page.waitForFunction((count) => {
    const bubbles = [...document.querySelectorAll('.fixed.bottom-24 .justify-start .rounded-lg, .fixed.bottom-6 .justify-start .rounded-lg')];
    return bubbles.length > count && !document.body.innerText.includes('응답을 준비하고 있습니다');
  }, beforeAnswers.length, { timeout: 15000 }).catch(() => undefined);
  await page.waitForTimeout(600);
  const afterAnswers = await assistantBubbleTexts(page);
  return afterAnswers.slice(beforeAnswers.length).join('\n').trim() || afterAnswers.at(-1) || '';
}

async function assistantBubbleTexts(page) {
  return page.evaluate(() => {
    return [...document.querySelectorAll('.fixed.bottom-24 .justify-start .rounded-lg, .fixed.bottom-6 .justify-start .rounded-lg')]
      .map((element) => element.innerText.trim())
      .filter(Boolean);
  }).catch(() => []);
}

async function runScenarioUsers(browser) {
  for (const scenario of scenarioUsers) {
    const context = await newContext(browser, { width: 1366, height: 900 });
    const page = await context.newPage();
    const username = await register(page, scenario.key);
    await saveProfile(page, scenario.profile);
    await page.goto(`${baseUrl}/recommendations`, { waitUntil: 'domcontentloaded', timeout: 45000 });
    await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => undefined);
    await page.waitForTimeout(1200);
    const text = await page.locator('body').innerText().catch(() => '');
    const matched = scenario.expectedRegions.some((region) => text.includes(region));
    const hasRecommendations = /추천\s*1|검토할 후보|공고/.test(text);
    report.scenarios.push({ key: scenario.key, username, expectedRegions: scenario.expectedRegions, matched, hasRecommendations });
    if (!hasRecommendations) issue('P1', 'scenario', '시나리오 사용자 추천 결과가 비어 있거나 확인 어려움', { key: scenario.key });
    if (!matched) issue('P1', 'scenario', '추천 화면에서 희망 지역 관련 텍스트를 확인하지 못함', { key: scenario.key, expectedRegions: scenario.expectedRegions });
    await page.screenshot({ path: path.join(shotDir, `scenario_${scenario.key}.png`), fullPage: true }).catch(() => undefined);
    await context.close();
  }
}

async function clickFirst(page, namePattern, action) {
  const button = page.getByRole('button', { name: namePattern }).first();
  if (await button.count()) {
    await button.click({ timeout: 5000 }).catch((error) => issue('P1', action, '버튼 클릭 실패', { error: String(error.message || error) }));
    await page.waitForTimeout(450);
    report.actions.push({ scenario: 'user', action });
    return true;
  }
  const link = page.getByRole('link', { name: namePattern }).first();
  if (await link.count()) {
    await link.click({ timeout: 5000 }).catch((error) => issue('P1', action, '링크 클릭 실패', { error: String(error.message || error) }));
    await page.waitForTimeout(450);
    report.actions.push({ scenario: 'user', action });
    return true;
  }
  return false;
}

function isIgnorableRequestFailure(url, failure = '') {
  return /\.(woff2?|ttf|otf|eot|png|jpg|jpeg|webp|gif|svg)(\?|$)/i.test(url)
    || url.includes('fonts.gstatic.com')
    || url.includes('fonts.googleapis.com')
    || url.includes('cdn.jsdelivr.net')
    || url.includes('img.youtube.com')
    || (failure.includes('ERR_ABORTED') && url.includes('/api/ai/coach-summary'));
}

async function writeReports() {
  report.finished_at = new Date().toISOString();
  report.summary = {
    page_count: report.pages.length,
    action_count: report.actions.length,
    visual_pages: report.visual.length,
    ai_checks: report.ai.length,
    scenario_count: report.scenarios.length,
    issue_count: report.issues.length,
    p0: report.issues.filter((item) => item.severity === 'P0').length,
    p1: report.issues.filter((item) => item.severity === 'P1').length,
    p2: report.issues.filter((item) => item.severity === 'P2').length,
  };
  await fs.writeFile(path.join(outDir, 'beta-complete-report.json'), JSON.stringify(report, null, 2), 'utf8');
  await fs.writeFile(path.join(outDir, 'beta-complete-report.md'), renderMarkdown(report), 'utf8');
}

function renderMarkdown(data) {
  const lines = [
    '# Beta Complete Report',
    '',
    `- Run: ${data.run_id}`,
    `- URL: ${data.base_url}`,
    `- Pages: ${data.summary.page_count}`,
    `- Actions: ${data.summary.action_count}`,
    `- Visual pages: ${data.summary.visual_pages}`,
    `- AI checks: ${data.summary.ai_checks}`,
    `- Scenario users: ${data.summary.scenario_count}`,
    `- Issues: P0 ${data.summary.p0}, P1 ${data.summary.p1}, P2 ${data.summary.p2}`,
    '',
    '## Issues',
    '',
  ];
  if (!data.issues.length) {
    lines.push('- No issues detected by complete beta suite.');
  } else {
    for (const item of data.issues) {
      lines.push(`- **${item.severity}** ${item.area}: ${item.message}`);
    }
  }
  lines.push('', '## Slowest Pages', '');
  for (const page of [...data.pages].sort((a, b) => b.elapsed_ms - a.elapsed_ms).slice(0, 8)) {
    lines.push(`- ${page.scenario}/${page.key}: ${page.elapsed_ms}ms, status ${page.status ?? 'n/a'}`);
  }
  lines.push('', '## Scenario Users', '');
  for (const scenario of data.scenarios) {
    lines.push(`- ${scenario.key}: recommendations=${scenario.hasRecommendations}, region_match=${scenario.matched}`);
  }
  return `${lines.join('\n')}\n`;
}

await ensureDirs();
const browser = await createBrowser();
try {
  await runGuestAndUserPages(browser);
  await runScenarioUsers(browser);
} finally {
  await browser.close();
  await writeReports();
}

console.log(`Beta complete report written: ${path.join(outDir, 'beta-complete-report.md')}`);
if (report.summary?.p0 || report.summary?.p1) {
  process.exitCode = 1;
}
