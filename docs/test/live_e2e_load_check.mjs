import { createRequire } from 'module';
import fs from 'fs/promises';
import path from 'path';

const targetUrl = normalizeBaseUrl(process.argv[2] || 'https://bit-county-makers-utilize.trycloudflare.com/');
const concurrentUsers = Number(process.argv[3] || 30);
const runStamp = new Date().toISOString().replace(/[:.]/g, '-');
const outDir = path.resolve('docs', 'test');
const shotDir = path.join(outDir, `live_${runStamp}`);
const latestJson = path.join(outDir, 'live_latest_result.json');
const latestMd = path.join(outDir, 'live_latest_report.md');

function normalizeBaseUrl(value) {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

function nowMs() {
  return Number(process.hrtime.bigint() / 1000000n);
}

function msLabel(ms) {
  if (ms == null || Number.isNaN(ms)) return 'n/a';
  return `${(ms / 1000).toFixed(2)}s`;
}

function percentile(values, p) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1);
  return sorted[idx];
}

function tryRequirePlaywright() {
  const from = process.env.PLAYWRIGHT_REQUIRE_FROM;
  if (from) {
    return createRequire(from)('playwright');
  }
  return createRequire(import.meta.url)('playwright');
}

async function discoverApiBase(frontendBase) {
  const html = await fetchText(frontendBase);
  const scripts = [...html.matchAll(/<script[^>]+src="([^"]+\.js[^"]*)"/g)].map((m) => m[1]);
  for (const src of scripts.reverse()) {
    const jsUrl = src.startsWith('http') ? src : `${frontendBase}${src.startsWith('/') ? '' : '/'}${src}`;
    const js = await fetchText(jsUrl);
    const viteEnvApiBase = js.match(/"VITE_API_BASE_URL"\s*:\s*"([^"]+)"/);
    if (viteEnvApiBase?.[1]) {
      const raw = viteEnvApiBase[1].replace(/\\\//g, '/').replace(/\/$/, '');
      return raw.endsWith('/api') ? raw : `${raw}/api`;
    }
    const direct = js.match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com\/api/g);
    if (direct?.[0]) return direct[0].replace(/\/$/, '');
    const localhost = js.match(/http:\/\/127\.0\.0\.1:8000\/api|http:\/\/localhost:8000\/api/g);
    if (localhost?.[0]) return localhost[0].replace(/\/$/, '');
  }
  const viteApiModuleUrl = `${frontendBase}/src/api/firsthome.js`;
  const viteApiModule = await fetchText(viteApiModuleUrl).catch(() => '');
  const viteEnvApiBase = viteApiModule.match(/"VITE_API_BASE_URL"\s*:\s*"([^"]+)"/);
  if (viteEnvApiBase?.[1]) {
    const raw = viteEnvApiBase[1].replace(/\\\//g, '/').replace(/\/$/, '');
    return raw.endsWith('/api') ? raw : `${raw}/api`;
  }
  throw new Error('Could not discover API base URL from frontend bundle.');
}

async function fetchText(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: { 'User-Agent': 'FirstHome-live-check/1.0', ...(options.headers || {}) },
  });
  if (!res.ok) throw new Error(`GET ${url} failed: ${res.status}`);
  return res.text();
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    ...options,
    headers: {
      'User-Agent': 'FirstHome-live-check/1.0',
      Accept: 'application/json',
      ...(options.headers || {}),
    },
  });
  const text = await res.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {
    json = { raw: text.slice(0, 500) };
  }
  if (!res.ok) {
    throw new Error(`${options.method || 'GET'} ${url} failed: ${res.status} ${text.slice(0, 200)}`);
  }
  return json;
}

function pickArray(payload) {
  if (Array.isArray(payload)) return payload;
  return payload?.results || payload?.items || payload?.recommendations || payload?.data || [];
}

function pickFirstNotice(payload) {
  const list = pickArray(payload);
  const first = list[0] || {};
  const notice = first.notice || first;
  const options =
    first.recommended_options ||
    first.options ||
    notice.recommended_options ||
    notice.options ||
    notice.housing_options ||
    [];
  const option = options[0] || first.selected_option || first.representative_option || {};
  return {
    noticeId: notice.id || first.notice_id || first.id,
    optionId: option.id || option.option_id || first.option_id || first.selected_option_id,
    title: notice.title || first.title || '',
  };
}

async function waitForStablePage(page, label, expectedText, timeoutMs = 90000) {
  const start = nowMs();
  let loadingGoneMs = null;
  let expectedMs = null;
  const loadingPatterns = [
    /로딩/,
    /불러오는 중/,
    /준비 플랜을 정리하는 중/,
    /AI 코치가/,
    /분석 중/,
  ];
  const fatalPatterns = [
    /Django 서버가 실행 중인지 확인하세요/,
    /정보를 불러오지 못했습니다/,
    /Internal Server Error/,
    /Traceback/,
  ];

  while (nowMs() - start < timeoutMs) {
    const text = await page.locator('body').innerText({ timeout: 3000 }).catch(() => '');
    const hasLoading = loadingPatterns.some((pattern) => pattern.test(text));
    const hasExpected = expectedText ? expectedText.some((pattern) => pattern.test(text)) : text.trim().length > 200;
    const hasFatal = fatalPatterns.some((pattern) => pattern.test(text));
    if (!hasLoading && loadingGoneMs == null) loadingGoneMs = nowMs() - start;
    if (hasExpected && !hasLoading && !hasFatal) {
      expectedMs = nowMs() - start;
      return { label, ok: true, loadingGoneMs, readyMs: expectedMs };
    }
    await page.waitForTimeout(1000);
  }

  const text = await page.locator('body').innerText({ timeout: 3000 }).catch(() => '');
  return {
    label,
    ok: false,
    loadingGoneMs,
    readyMs: null,
    error: `Timed out waiting for ${label}`,
    bodySample: text.slice(0, 800),
  };
}

async function goAndCheck(page, route, label, expectedText, screenshotName, timeoutMs) {
  const started = nowMs();
  await page.goto(`${targetUrl}${route}`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  const result = await waitForStablePage(page, label, expectedText, timeoutMs);
  result.totalMs = nowMs() - started;
  await page.screenshot({ path: path.join(shotDir, screenshotName), fullPage: true }).catch(() => {});
  return result;
}

async function runBrowserFlow(apiBase, firstPick) {
  const { chromium } = tryRequirePlaywright();
  const executablePath = process.env.PLAYWRIGHT_EXECUTABLE_PATH || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
  const browser = await chromium.launch({
    headless: true,
    executablePath,
    args: ['--no-sandbox', '--disable-dev-shm-usage'],
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1100 },
    baseURL: targetUrl,
  });
  const page = await context.newPage();
  const browserIssues = [];
  page.on('console', (msg) => {
    if (['error', 'warning'].includes(msg.type())) browserIssues.push({ type: `console:${msg.type()}`, text: msg.text().slice(0, 500) });
  });
  page.on('pageerror', (err) => browserIssues.push({ type: 'pageerror', text: err.message.slice(0, 500) }));
  page.on('requestfailed', (req) => browserIssues.push({ type: 'requestfailed', url: req.url(), text: req.failure()?.errorText || '' }));
  page.on('response', (res) => {
    if (res.status() >= 400 && !res.url().includes('favicon')) {
      browserIssues.push({ type: 'http', status: res.status(), url: res.url() });
    }
  });

  const steps = [];
  steps.push(await goAndCheck(page, '/', 'dashboard', [/첫 집 준비 현황/, /대시보드/], '01_dashboard.png', 60000));
  steps.push(await goAndCheck(page, '/profile', 'profile input', [/첫 집 청약 추천 조건/, /조건 입력/], '02_profile.png', 60000));
  steps.push(await goAndCheck(page, '/recommendations', 'recommendations', [/검토할 후보 TOP/, /주택형 옵션 추천/], '03_recommendations.png', 60000));

  if (firstPick.noticeId) {
    const optionQuery = firstPick.optionId ? `?option_id=${firstPick.optionId}` : '';
    steps.push(await goAndCheck(page, `/notices/${firstPick.noticeId}${optionQuery}`, 'notice detail', [/공식 확인 체크리스트/, /주요 일정/], '04_notice_detail.png', 90000));
    steps.push(await goAndCheck(page, `/funding/${firstPick.noticeId}${optionQuery}`, 'funding roadmap', [/계약금과 납부 일정/, /납부 타임라인/], '05_funding.png', 90000));
    steps.push(await goAndCheck(page, `/ai-coach/${firstPick.noticeId}${optionQuery}`, 'ai coach', [/바로 처리할 일/, /무엇을 먼저 선택할지/, /공고문 심층 체크포인트/], '06_ai_coach.png', 180000));
  }

  steps.push(await goAndCheck(page, '/map', 'map', [/지도에서 공고를 직접 고르기/, /선택한 공고/], '07_map.png', 90000));
  steps.push(await goAndCheck(page, '/favorites', 'favorites', [/저장한 공고와 주택형/, /관심 목록/], '08_favorites.png', 60000));

  const authResult = await checkAuthFlow(page);
  steps.push(authResult);

  const chatResult = await checkChatbot(page);
  steps.push(chatResult);

  await browser.close();
  return { steps, browserIssues };
}

async function checkAuthFlow(page) {
  const label = 'signup/login screen';
  const started = nowMs();
  try {
    await page.goto(`${targetUrl}/auth`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    const body = await page.locator('body').innerText({ timeout: 5000 });
    const ok = /로그인|회원가입|계정/.test(body);
    await page.screenshot({ path: path.join(shotDir, '09_auth.png'), fullPage: true }).catch(() => {});
    return { label, ok, readyMs: nowMs() - started, totalMs: nowMs() - started, note: 'Auth page availability checked. Account mutation is intentionally not repeated in every load check.' };
  } catch (error) {
    return { label, ok: false, readyMs: null, totalMs: nowMs() - started, error: error.message };
  }
}

async function checkChatbot(page) {
  const label = 'chatbot open and response';
  const started = nowMs();
  try {
    await page.goto(`${targetUrl}/`, { waitUntil: 'domcontentloaded', timeout: 90000 });
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    const aiButton = page.locator('button').filter({ hasText: /^AI$|AI/ }).last();
    await aiButton.click({ timeout: 10000 });
    await page.waitForTimeout(1000);
    const input = page.locator('textarea, input[placeholder*="질문"], input[placeholder*="입력"]').last();
    await input.fill('청약 추천을 받으려면 어떤 순서로 이용하면 되나요?');
    await input.press('Enter').catch(async () => {
      await page.locator('button').last().click();
    });
    const ready = await waitForStablePage(page, label, [/조건 입력/, /추천 청약/, /자금 로드맵/, /AI 코치/, /청약/], 120000);
    ready.totalMs = nowMs() - started;
    await page.screenshot({ path: path.join(shotDir, '10_chatbot.png'), fullPage: true }).catch(() => {});
    return ready;
  } catch (error) {
    await page.screenshot({ path: path.join(shotDir, '10_chatbot_error.png'), fullPage: true }).catch(() => {});
    return { label, ok: false, readyMs: null, totalMs: nowMs() - started, error: error.message };
  }
}

async function timedFetch(label, url, options = {}) {
  const started = nowMs();
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), options.timeoutMs || 180000);
  try {
    const res = await fetch(url, {
      method: options.method || 'GET',
      body: options.body,
      signal: controller.signal,
    headers: {
      Origin: targetUrl,
      'User-Agent': `FirstHome-load-user/${options.userIndex ?? 0}`,
      Accept: options.accept || 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(options.headers || {}),
      },
    });
    const text = await res.text();
    clearTimeout(timer);
    return {
      label,
      ok: res.ok,
      status: res.status,
      ms: nowMs() - started,
      bytes: text.length,
      sample: res.ok ? undefined : text.slice(0, 300),
    };
  } catch (error) {
    clearTimeout(timer);
    return { label, ok: false, status: 0, ms: nowMs() - started, error: error.message };
  }
}

async function runVirtualUser(userIndex, apiBase, firstPick) {
  const suffix = firstPick.noticeId ? `/${firstPick.noticeId}${firstPick.optionId ? `?option_id=${firstPick.optionId}` : ''}` : '';
  const calls = [
    timedFetch('frontend:home', `${targetUrl}/`, { userIndex, accept: 'text/html' }),
    timedFetch('api:housing', `${apiBase}/recommendations/housing`, { userIndex }),
    timedFetch('api:notices-active', `${apiBase}/notices?active=1`, { userIndex }),
    timedFetch('api:map-notices', `${apiBase}/notices/map`, { userIndex }),
  ];
  if (firstPick.noticeId) {
    calls.push(timedFetch('api:notice-detail', `${apiBase}/notices/${firstPick.noticeId}`, { userIndex }));
    calls.push(timedFetch('api:funding', `${apiBase}/recommendations/funding${suffix}`, { userIndex }));
    calls.push(timedFetch('api:ai-coach', `${apiBase}/ai/coach-summary`, {
      userIndex,
      method: 'POST',
      timeoutMs: 240000,
      body: JSON.stringify({
        notice_id: firstPick.noticeId,
        option_id: firstPick.optionId,
        profile: {},
      }),
    }));
  }
  calls.push(timedFetch('api:chatbot', `${apiBase}/ai/chat`, {
    userIndex,
    method: 'POST',
    timeoutMs: 240000,
    body: JSON.stringify({
      message: '청약 추천과 자금 로드맵 이용 순서를 짧게 알려줘.',
      page: 'load-test',
      context: { userIndex },
    }),
  }));
  return Promise.all(calls);
}

async function runLoadCheck(apiBase, firstPick) {
  const started = nowMs();
  const users = Array.from({ length: concurrentUsers }, (_, i) => runVirtualUser(i + 1, apiBase, firstPick));
  const nested = await Promise.all(users);
  const flat = nested.flat();
  const byLabel = {};
  for (const row of flat) {
    byLabel[row.label] ||= [];
    byLabel[row.label].push(row);
  }
  const summary = Object.fromEntries(Object.entries(byLabel).map(([label, rows]) => {
    const times = rows.filter((r) => r.ok).map((r) => r.ms);
    return [label, {
      total: rows.length,
      ok: rows.filter((r) => r.ok).length,
      failed: rows.filter((r) => !r.ok).length,
      p50Ms: percentile(times, 50),
      p90Ms: percentile(times, 90),
      p95Ms: percentile(times, 95),
      maxMs: times.length ? Math.max(...times) : null,
      failures: rows.filter((r) => !r.ok).slice(0, 5),
    }];
  }));
  return { totalMs: nowMs() - started, summary, raw: flat };
}

function makeMarkdown(result) {
  const lines = [];
  lines.push(`# Live Cloudflare E2E And 30 User Load Check`);
  lines.push('');
  lines.push(`- Frontend: ${result.targetUrl}`);
  lines.push(`- API base: ${result.apiBase}`);
  lines.push(`- Run: ${result.runStamp}`);
  lines.push(`- Concurrent virtual users: ${result.concurrentUsers}`);
  lines.push('');
  lines.push(`## Browser E2E`);
  lines.push('');
  lines.push(`| Step | Result | Ready | Loading Gone | Total | Note |`);
  lines.push(`| --- | --- | ---: | ---: | ---: | --- |`);
  for (const step of result.browser.steps) {
    lines.push(`| ${step.label} | ${step.ok ? 'OK' : 'FAIL'} | ${msLabel(step.readyMs)} | ${msLabel(step.loadingGoneMs)} | ${msLabel(step.totalMs)} | ${(step.error || step.note || '').replace(/\|/g, '/')} |`);
  }
  lines.push('');
  lines.push(`## 30 User Scenario`);
  lines.push('');
  lines.push(`| Endpoint | OK/Total | p50 | p90 | p95 | Max |`);
  lines.push(`| --- | ---: | ---: | ---: | ---: | ---: |`);
  for (const [label, row] of Object.entries(result.load.summary)) {
    lines.push(`| ${label} | ${row.ok}/${row.total} | ${msLabel(row.p50Ms)} | ${msLabel(row.p90Ms)} | ${msLabel(row.p95Ms)} | ${msLabel(row.maxMs)} |`);
  }
  lines.push('');
  if (result.browser.browserIssues.length) {
    lines.push(`## Browser Issues`);
    lines.push('');
    for (const issue of result.browser.browserIssues.slice(0, 30)) {
      lines.push(`- ${issue.type}: ${issue.status || ''} ${issue.url || ''} ${issue.text || ''}`.trim());
    }
    lines.push('');
  }
  const failures = result.load.raw.filter((r) => !r.ok);
  if (failures.length) {
    lines.push(`## Load Failures`);
    lines.push('');
    for (const failure of failures.slice(0, 30)) {
      lines.push(`- ${failure.label}: status=${failure.status}, ms=${failure.ms}, ${failure.error || failure.sample || ''}`);
    }
    lines.push('');
  }
  lines.push(`## Screenshots`);
  lines.push('');
  lines.push(`Saved under \`${path.relative(outDir, shotDir).replace(/\\/g, '/')}\`.`);
  return `${lines.join('\n')}\n`;
}

await fs.mkdir(shotDir, { recursive: true });

const apiBase = await discoverApiBase(targetUrl);
const housing = await fetchJson(`${apiBase}/recommendations/housing`, { headers: { Origin: targetUrl } });
const firstPick = pickFirstNotice(housing);

const browser = await runBrowserFlow(apiBase, firstPick);
const load = await runLoadCheck(apiBase, firstPick);

const result = {
  targetUrl,
  apiBase,
  runStamp,
  concurrentUsers,
  firstPick,
  browser,
  load,
};

const jsonText = JSON.stringify(result, null, 2);
const mdText = makeMarkdown(result);
await fs.writeFile(path.join(outDir, `live_${runStamp}_result.json`), jsonText, 'utf8');
await fs.writeFile(path.join(outDir, `live_${runStamp}_report.md`), mdText, 'utf8');
await fs.writeFile(latestJson, jsonText, 'utf8');
await fs.writeFile(latestMd, mdText, 'utf8');

console.log(mdText);
