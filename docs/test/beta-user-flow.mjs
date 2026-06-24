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
  { key: 'map', path: '/map', budgetMs: 8000 },
  { key: 'funding', path: '/funding', budgetMs: 5000 },
  { key: 'ai_coach', path: '/ai-coach', budgetMs: 10000 },
  { key: 'products', path: '/finance/products', budgetMs: 5000 },
  { key: 'economy_now', path: '/finance/economy-now', budgetMs: 5000 },
  { key: 'agora', path: '/finance/agora', budgetMs: 5000 },
  { key: 'my_page', path: '/my-page', budgetMs: 5000 },
  { key: 'auth', path: '/auth', budgetMs: 4500 },
];

const report = {
  run_id: runId,
  base_url: baseUrl,
  started_at: new Date().toISOString(),
  mode: 'beta-user-flow',
  pages: [],
  actions: [],
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
  return chromium.launch({
    headless: true,
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
  });
}

async function newContext(browser) {
  return browser.newContext({
    viewport: { width: 1440, height: 960 },
    extraHTTPHeaders: {
      'ngrok-skip-browser-warning': 'true',
    },
  });
}

async function instrument(page, scope) {
  const consoleErrors = [];
  const pageErrors = [];
  const failedRequests = [];

  page.on('console', (message) => {
    if (['error', 'warning'].includes(message.type())) {
      consoleErrors.push({ type: message.type(), text: message.text().slice(0, 400) });
    }
  });
  page.on('pageerror', (error) => {
    pageErrors.push(String(error.message || error).slice(0, 500));
  });
  page.on('requestfailed', (request) => {
    failedRequests.push({
      url: request.url(),
      method: request.method(),
      failure: request.failure()?.errorText || 'unknown',
    });
  });

  return () => ({ scope, consoleErrors, pageErrors, failedRequests });
}

async function gotoAndAudit(page, route, scenario) {
  const collect = await instrument(page, `${scenario}:${route.key}`);
  const started = Date.now();
  const response = await page.goto(`${baseUrl}${route.path}`, { waitUntil: 'domcontentloaded', timeout: 45000 }).catch((error) => {
    issue('P0', route.key, `페이지 진입 실패: ${route.path}`, { error: String(error.message || error) });
    return null;
  });
  await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => undefined);
  await page.waitForTimeout(route.key === 'map' ? 1800 : 700);

  const elapsedMs = Date.now() - started;
  const title = await page.title().catch(() => '');
  const bodyText = await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
  const status = response?.status?.() ?? null;
  const shotPath = path.join(shotDir, `${scenario}_${route.key}.png`);
  await page.screenshot({ path: shotPath, fullPage: true }).catch(() => undefined);

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

  const diagnostics = collect();
  if (diagnostics.pageErrors.length) {
    issue('P0', route.key, '페이지 JS 예외 발생', { scenario, pageErrors: diagnostics.pageErrors });
  }
  const hardNetworkFailures = diagnostics.failedRequests.filter((entry) => !entry.url.includes('favicon') && !isIgnorableRequestFailure(entry.url, entry.failure));
  if (hardNetworkFailures.length) {
    issue('P1', route.key, '네트워크 요청 실패', { scenario, failedRequests: hardNetworkFailures.slice(0, 8) });
  }

  report.pages.push({
    scenario,
    key: route.key,
    path: route.path,
    status,
    title,
    elapsed_ms: elapsedMs,
    screenshot: path.relative(outDir, shotPath),
    console_errors: diagnostics.consoleErrors,
    page_errors: diagnostics.pageErrors,
    failed_requests: hardNetworkFailures,
  });
}

async function auditGuest(browser) {
  const context = await newContext(browser);
  const page = await context.newPage();
  for (const route of routes) {
    await gotoAndAudit(page, route, 'guest');
  }
  await askCoach(page, 'guest', '이 화면은 어떻게 쓰면 돼?');
  await context.close();
}

async function registerThroughUi(page) {
  const username = `beta_${Date.now()}_${Math.random().toString(16).slice(2, 7)}`;
  await page.goto(`${baseUrl}/auth`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.getByRole('button', { name: /계정이 없으면 회원가입/ }).click({ timeout: 8000 });
  await page.getByLabel('아이디').fill(username);
  await page.getByLabel('이메일').fill(`${username}@example.com`);
  await page.getByLabel('이름').fill('베타사용자');
  await page.getByLabel('출생년도').fill('1999');
  await page.getByLabel('비밀번호').fill('betapass123');
  await page.getByRole('button', { name: /^회원가입$/ }).click();
  await page.waitForURL(/\/profile/, { timeout: 12000 }).catch((error) => {
    issue('P0', 'auth', '회원가입 후 조건 입력 화면으로 이동하지 않음', { error: String(error.message || error) });
  });
  report.actions.push({ scenario: 'user', action: 'register_ui', username });
  return username;
}

async function saveProfileThroughApi(page) {
  await page.evaluate(async () => {
    const headers = {
      'Content-Type': 'application/json',
      'ngrok-skip-browser-warning': 'true',
    };
    const response = await fetch('/api/profile', {
      method: 'PUT',
      headers,
      credentials: 'include',
      body: JSON.stringify({
        name: '베타사용자',
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
        desired_price_min: 0,
        desired_price_max: 700000000,
      }),
    });
    if (!response.ok) throw new Error(`profile save failed: ${response.status}`);
  }).catch((error) => {
    issue('P0', 'profile', '프로필 API 저장 실패', { error: String(error.message || error) });
  });
  report.actions.push({ scenario: 'user', action: 'save_profile_api' });
}

async function exerciseCoreUserActions(page) {
  await page.goto(`${baseUrl}/recommendations`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => undefined);
  const firstNoticeLink = page.locator('a[href^="/notices/"]').first();
  if (await firstNoticeLink.count()) {
    await firstNoticeLink.click();
    await page.waitForURL(/\/notices\/\d+/, { timeout: 12000 }).catch(() => undefined);
    report.actions.push({ scenario: 'user', action: 'open_first_notice_detail' });
  } else {
    issue('P0', 'recommendations', '추천 공고 상세 링크를 찾지 못함');
  }

  await tryClick(page, /공고 저장|관심|저장/, 'save_notice_or_favorite');
  await tryClick(page, /공식 근거 보기|공식 출처|공고문 근거/, 'open_official_evidence');

  await page.goto(`${baseUrl}/finance/products`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForLoadState('networkidle', { timeout: 12000 }).catch(() => undefined);
  const productLink = page.locator('a[href^="/finance/products/"]').first();
  if (await productLink.count()) {
    await productLink.click();
    await page.waitForURL(/\/finance\/products\/\d+/, { timeout: 12000 }).catch(() => undefined);
    report.actions.push({ scenario: 'user', action: 'open_first_product_detail' });
    await tryClick(page, /가입상품으로 저장|로그인 후 가입 가능/, 'join_product');
  } else {
    issue('P1', 'products', '금융상품 상세 링크를 찾지 못함');
  }

  await askCoach(page, 'user', '이 화면에서 다음에 뭘 확인해야 해?');
}

async function tryClick(page, namePattern, actionName) {
  const candidate = page.getByRole('button', { name: namePattern }).first();
  if (await candidate.count()) {
    await candidate.click({ timeout: 5000 }).catch((error) => {
      issue('P1', actionName, '버튼 클릭 실패', { error: String(error.message || error) });
    });
    await page.waitForTimeout(500);
    report.actions.push({ scenario: 'user', action: actionName });
    return true;
  }
  return false;
}

async function askCoach(page, scenario, question) {
  const bodyText = await page.locator('body').innerText().catch(() => '');
  if (!bodyText.includes('AI')) {
    issue('P2', 'ai_chat', 'AI 챗봇 진입점 텍스트를 찾지 못함', { scenario });
    return;
  }
  await page.getByText('AI', { exact: true }).last().click({ timeout: 5000 }).catch(() => undefined);
  const input = page.getByPlaceholder(/궁금한 내용을 입력|질문/).last();
  if (!(await input.count())) {
    issue('P1', 'ai_chat', '챗봇 입력창을 찾지 못함', { scenario });
    return;
  }
  await input.fill(question);
  await input.press('Enter').catch(async () => {
    await page.getByRole('button', { name: /전송|send/i }).last().click({ timeout: 3000 }).catch(() => undefined);
  });
  await page.waitForTimeout(2500);
  const chatText = await page.locator('body').innerText().catch(() => '');
  if (!chatText.includes(question.slice(0, 8))) {
    issue('P2', 'ai_chat', '사용자 질문이 챗봇 영역에 남지 않음', { scenario, question });
  }
  if (!/공식|확인|화면|청약|자금|영상|지도|상품/.test(chatText)) {
    issue('P1', 'ai_chat', '챗봇 응답이 서비스 맥락 키워드를 포함하지 않음', { scenario, question });
  }
  report.actions.push({ scenario, action: 'ask_ai_chat', question });
}

async function auditUser(browser) {
  const context = await newContext(browser);
  const page = await context.newPage();
  await registerThroughUi(page);
  await saveProfileThroughApi(page);
  for (const route of routes.filter((item) => item.key !== 'auth')) {
    await gotoAndAudit(page, route, 'user');
  }
  await exerciseCoreUserActions(page);
  await context.close();
}

async function writeReports() {
  report.finished_at = new Date().toISOString();
  report.summary = {
    page_count: report.pages.length,
    action_count: report.actions.length,
    issue_count: report.issues.length,
    p0: report.issues.filter((item) => item.severity === 'P0').length,
    p1: report.issues.filter((item) => item.severity === 'P1').length,
    p2: report.issues.filter((item) => item.severity === 'P2').length,
  };
  await fs.writeFile(path.join(outDir, 'beta-flow-report.json'), JSON.stringify(report, null, 2), 'utf8');
  await fs.writeFile(path.join(outDir, 'beta-flow-report.md'), renderMarkdown(report), 'utf8');
}

function renderMarkdown(data) {
  const lines = [
    '# Beta User Flow Report',
    '',
    `- Run: ${data.run_id}`,
    `- URL: ${data.base_url}`,
    `- Pages: ${data.summary.page_count}`,
    `- Actions: ${data.summary.action_count}`,
    `- Issues: P0 ${data.summary.p0}, P1 ${data.summary.p1}, P2 ${data.summary.p2}`,
    '',
    '## Issues',
    '',
  ];
  if (!data.issues.length) {
    lines.push('- No issues detected by automated beta flow.');
  } else {
    for (const item of data.issues) {
      lines.push(`- **${item.severity}** ${item.area}: ${item.message}`);
    }
  }
  lines.push('', '## Page Timings', '');
  for (const page of data.pages) {
    lines.push(`- ${page.scenario}/${page.key}: ${page.elapsed_ms}ms, status ${page.status ?? 'n/a'}`);
  }
  return `${lines.join('\n')}\n`;
}

function isIgnorableRequestFailure(url, failure = '') {
  return /\.(woff2?|ttf|otf|eot)(\?|$)/i.test(url)
    || url.includes('fonts.gstatic.com')
    || url.includes('fonts.googleapis.com')
    || url.includes('cdn.jsdelivr.net')
    || (failure.includes('ERR_ABORTED') && url.includes('/api/ai/coach-summary'));
}

await ensureDirs();
const browser = await createBrowser();
try {
  await auditGuest(browser);
  await auditUser(browser);
} finally {
  await browser.close();
  await writeReports();
}

console.log(`Beta flow report written: ${path.join(outDir, 'beta-flow-report.md')}`);
if (report.summary?.p0 || report.summary?.p1) {
  process.exitCode = 1;
}
