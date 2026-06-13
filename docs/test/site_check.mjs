import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(process.env.PLAYWRIGHT_REQUIRE_FROM || import.meta.url);
const { chromium } = require('playwright');

const baseUrl = process.argv[2] || 'https://renaissance-spend-twisted-seq.trycloudflare.com/';
const outDir = path.resolve('docs/test');
const screenshotDir = path.join(outDir, 'screenshots');
const startedAt = new Date();

await fs.mkdir(screenshotDir, { recursive: true });

const browserCandidates = [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
];

async function firstExisting(paths) {
  for (const candidate of paths) {
    try {
      await fs.access(candidate);
      return candidate;
    } catch {
      // keep looking
    }
  }
  return undefined;
}

const executablePath = await firstExisting(browserCandidates);
const browser = await chromium.launch({
  headless: true,
  executablePath,
});

const context = await browser.newContext({
  viewport: { width: 1440, height: 1100 },
  locale: 'ko-KR',
});
const page = await context.newPage();

const routes = [];
const screenshots = [];
const consoleMessages = [];
const pageErrors = [];
const failedRequests = [];
const httpErrors = [];
let currentArea = 'startup';

page.on('console', (message) => {
  if (['error', 'warning'].includes(message.type())) {
    consoleMessages.push({
      area: currentArea,
      type: message.type(),
      text: message.text(),
    });
  }
});

page.on('pageerror', (error) => {
  pageErrors.push({
    area: currentArea,
    message: error.message,
  });
});

page.on('requestfailed', (request) => {
  failedRequests.push({
    area: currentArea,
    method: request.method(),
    url: request.url(),
    failure: request.failure()?.errorText || 'unknown',
  });
});

page.on('response', (response) => {
  const status = response.status();
  if (status >= 400 && !response.url().includes('favicon')) {
    httpErrors.push({
      area: currentArea,
      status,
      url: response.url(),
    });
  }
});

function absoluteUrl(routePath) {
  return new URL(routePath, baseUrl).toString();
}

async function bodyTextSample() {
  const text = await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
  return text.replace(/\s+/g, ' ').trim().slice(0, 700);
}

async function saveScreenshot(fileName, fullPage = true) {
  const filePath = path.join(screenshotDir, fileName);
  await page.screenshot({ path: filePath, fullPage });
  const relative = path.relative(outDir, filePath).replaceAll('\\', '/');
  screenshots.push(relative);
  return relative;
}

async function visit(area, routePath, fileName, waitMs = 1200) {
  currentArea = area;
  const url = absoluteUrl(routePath);
  const started = Date.now();
  const entry = { area, url, routePath };
  try {
    const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(waitMs);
    entry.status = response?.status() || null;
    entry.title = await page.title().catch(() => '');
    entry.h1 = await page.locator('h1').first().textContent({ timeout: 2500 }).catch(() => '');
    entry.sample = await bodyTextSample();
    entry.elapsedMs = Date.now() - started;
    entry.screenshot = await saveScreenshot(fileName);
  } catch (error) {
    entry.error = error.message;
    entry.elapsedMs = Date.now() - started;
  }
  routes.push(entry);
  return entry;
}

function uniqueByUrl(items) {
  const seen = new Set();
  return items.filter((item) => {
    const key = `${item.status || item.failure || item.type || ''}:${item.url || item.text || item.message}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

await visit('dashboard', '/', '01_dashboard.png', 1800);

currentArea = 'global-search';
try {
  const searchInput = page.locator('input[placeholder*="검색"]').first();
  if (await searchInput.count()) {
    await searchInput.fill('대출');
    await page.waitForTimeout(1200);
    await saveScreenshot('02_global_search_loan.png');
    await searchInput.fill('정책');
    await page.waitForTimeout(1200);
    await saveScreenshot('03_global_search_policy.png');
  }
} catch (error) {
  routes.push({ area: 'global-search', error: error.message });
}

await visit('profile', '/profile', '04_profile.png', 1200);
const recommendation = await visit('recommendations', '/recommendations', '05_recommendations.png', 2500);

let noticePath = null;
let noticeId = null;
let noticeQuery = '';
try {
  const hrefs = await page.locator('a[href]').evaluateAll((links) =>
    links.map((link) => link.getAttribute('href')).filter(Boolean)
  );
  const found = hrefs.find((href) => /\/notices\/\d+/.test(href));
  if (found) {
    const noticeUrl = new URL(found, baseUrl);
    noticePath = `${noticeUrl.pathname}${noticeUrl.search}`;
    noticeId = noticeUrl.pathname.match(/\/notices\/(\d+)/)?.[1] || null;
    noticeQuery = noticeUrl.search || '';
  }
} catch (error) {
  routes.push({ area: 'recommendation-link-discovery', error: error.message });
}

if (noticePath) {
  await visit('notice-detail', noticePath, '06_notice_detail.png', 1800);
}

if (noticeId) {
  await visit('funding', `/funding/${noticeId}${noticeQuery}`, '07_funding.png', 1800);
  await visit('ai-coach', `/ai-coach/${noticeId}${noticeQuery}`, '08_ai_coach.png', 9000);
}

await visit('map', '/map', '09_map.png', 3000);
await visit('favorites', '/favorites', '10_favorites.png', 1200);
await visit('auth', '/auth', '11_auth.png', 1200);

currentArea = 'chatbot';
try {
  await visit('chatbot-base', '/', '12_chatbot_base.png', 1000);
  const aiButton = page.locator('button[title*="FirstHome"], .fixed.bottom-24 button, .fixed.bottom-6 button').last();
  if (await aiButton.count()) {
    await aiButton.click();
    await page.waitForTimeout(800);
    await saveScreenshot('13_chatbot_open.png');
  } else {
    routes.push({ area: 'chatbot', note: 'AI floating button not found by visible text.' });
  }
} catch (error) {
  routes.push({ area: 'chatbot', error: error.message });
}

currentArea = 'mobile-dashboard';
try {
  await page.setViewportSize({ width: 390, height: 844 });
  await visit('mobile-dashboard', '/', '14_mobile_dashboard.png', 1500);
} catch (error) {
  routes.push({ area: 'mobile-dashboard', error: error.message });
}

await browser.close();

const endedAt = new Date();
const cleanConsole = consoleMessages.filter((message) => !message.text.includes('favicon'));
const cleanHttpErrors = httpErrors.filter((item) => !item.url.includes('favicon'));
const result = {
  baseUrl,
  startedAt: startedAt.toISOString(),
  endedAt: endedAt.toISOString(),
  durationMs: endedAt.getTime() - startedAt.getTime(),
  browserExecutable: executablePath || 'playwright bundled browser',
  routes,
  screenshots,
  consoleMessages: cleanConsole,
  pageErrors,
  failedRequests: uniqueByUrl(failedRequests),
  httpErrors: uniqueByUrl(cleanHttpErrors),
};

function statusLabel(route) {
  if (route.error) return `실패: ${route.error}`;
  return route.status ? `${route.status}` : '응답 없음';
}

const issueLines = [];
for (const route of routes) {
  if (route.error) issueLines.push(`- ${route.area}: 화면 이동 실패 - ${route.error}`);
  if (route.sample?.includes('불러오지 못했습니다')) issueLines.push(`- ${route.area}: "불러오지 못했습니다" 안내가 화면에 표시됨`);
  if (route.sample?.includes('서버가 실행 중인지 확인하세요')) issueLines.push(`- ${route.area}: 서버 연결 실패 안내가 화면에 표시됨`);
}
if (pageErrors.length) issueLines.push(`- 브라우저 런타임 오류 ${pageErrors.length}건 감지`);
if (cleanConsole.length) issueLines.push(`- console warning/error ${cleanConsole.length}건 감지`);
if (failedRequests.length) issueLines.push(`- 실패한 네트워크 요청 ${failedRequests.length}건 감지`);
if (cleanHttpErrors.length) issueLines.push(`- HTTP 4xx/5xx 응답 ${cleanHttpErrors.length}건 감지`);

const report = `# Cloudflare 배포 사이트 실제 화면 점검

- 점검 대상: ${baseUrl}
- 점검 시간: ${startedAt.toLocaleString('ko-KR')} ~ ${endedAt.toLocaleString('ko-KR')}
- 브라우저: ${result.browserExecutable}
- 방식: 실제 공개 URL을 브라우저로 열어 주요 화면을 이동하고 스크린샷, 콘솔 오류, 실패 요청을 수집했습니다.

## 점검 범위

| 영역 | 경로 | 응답 | 대표 제목 | 캡처 |
| --- | --- | --- | --- | --- |
${routes
  .filter((route) => route.screenshot || route.status || route.error)
  .map((route) => `| ${route.area} | \`${route.routePath || route.url || '-'}\` | ${statusLabel(route)} | ${route.h1 || '-'} | ${route.screenshot ? `[${route.screenshot}](./${route.screenshot})` : '-'} |`)
  .join('\n')}

## 발견 사항

${issueLines.length ? issueLines.join('\n') : '- 자동 점검 범위에서는 치명적인 화면 이동 실패나 런타임 오류가 감지되지 않았습니다.'}

## 스크린샷

${screenshots.map((screenshot) => `- [${screenshot}](./${screenshot})`).join('\n')}

## 네트워크/콘솔 요약

- Console warning/error: ${cleanConsole.length}건
- Page error: ${pageErrors.length}건
- Request failed: ${failedRequests.length}건
- HTTP 4xx/5xx: ${cleanHttpErrors.length}건

상세 원본은 [site_check_result.json](./site_check_result.json)에 저장했습니다.

## 제한 사항

- 로그인 계정 생성이나 실제 유료 LLM 질문 전송처럼 서버 데이터를 변경하거나 비용이 발생할 수 있는 동작은 자동으로 수행하지 않았습니다.
- AI 코치 화면은 공개/현재 세션 상태에서 접근 가능한 범위까지 확인했습니다. 로그인 전용 심층 분석은 테스트 계정 기준으로 별도 점검하는 것이 좋습니다.
`;

await fs.writeFile(path.join(outDir, 'site_check_result.json'), JSON.stringify(result, null, 2), 'utf8');
await fs.writeFile(path.join(outDir, 'site_check_report.md'), report, 'utf8');

console.log(`Wrote ${path.join(outDir, 'site_check_report.md')}`);
