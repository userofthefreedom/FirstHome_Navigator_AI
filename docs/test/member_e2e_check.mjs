import fs from 'node:fs/promises';
import path from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(process.env.PLAYWRIGHT_REQUIRE_FROM || import.meta.url);
const { chromium } = require('playwright');

const baseUrl = process.argv[2] || 'https://cuisine-clothes-holes-helen.trycloudflare.com/';
const outDir = path.resolve('docs/test');
const screenshotDir = path.join(outDir, 'member_screenshots');
const startedAt = new Date();
const stamp = startedAt.toISOString().replace(/[^\d]/g, '').slice(0, 14);
const testAccount = {
  username: `codex_e2e_${stamp}`,
  email: `codex_e2e_${stamp}@example.com`,
  password: 'FirstHome!2026',
  displayName: `코덱스점검${stamp.slice(-4)}`,
};

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
const browser = await chromium.launch({ headless: true, executablePath });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1100 },
  locale: 'ko-KR',
});
const page = await context.newPage();

const steps = [];
const screenshots = [];
const consoleMessages = [];
const pageErrors = [];
const failedRequests = [];
const httpErrors = [];
let currentStep = 'startup';
let firstNotice = null;
let firstNoticePath = null;
let fundingPath = null;
let coachPath = null;

page.on('console', (message) => {
  if (['error', 'warning'].includes(message.type())) {
    consoleMessages.push({ step: currentStep, type: message.type(), text: message.text() });
  }
});

page.on('pageerror', (error) => {
  pageErrors.push({ step: currentStep, message: error.message });
});

page.on('requestfailed', (request) => {
  failedRequests.push({
    step: currentStep,
    method: request.method(),
    url: request.url(),
    failure: request.failure()?.errorText || 'unknown',
  });
});

page.on('response', (response) => {
  const status = response.status();
  if (status >= 400 && !response.url().includes('favicon')) {
    httpErrors.push({ step: currentStep, status, url: response.url() });
  }
});

function absoluteUrl(routePath) {
  return new URL(routePath, baseUrl).toString();
}

async function saveScreenshot(fileName, fullPage = true) {
  const filePath = path.join(screenshotDir, fileName);
  await page.screenshot({ path: filePath, fullPage });
  const relative = path.relative(outDir, filePath).replaceAll('\\', '/');
  screenshots.push(relative);
  return relative;
}

async function bodyTextSample(limit = 800) {
  const text = await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
  return text.replace(/\s+/g, ' ').trim().slice(0, limit);
}

async function go(routePath, waitMs = 1000) {
  const response = await page.goto(absoluteUrl(routePath), {
    waitUntil: 'domcontentloaded',
    timeout: 60000,
  });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(waitMs);
  return response;
}

async function recordStep(name, run) {
  currentStep = name;
  const started = Date.now();
  const entry = { name };
  try {
    const details = await run();
    entry.status = 'pass';
    Object.assign(entry, details || {});
  } catch (error) {
    entry.status = 'fail';
    entry.error = error.message;
    entry.screenshot = await saveScreenshot(`error_${steps.length + 1}_${name.replace(/[^\w-]+/g, '_')}.png`).catch(() => null);
  } finally {
    entry.elapsedMs = Date.now() - started;
    steps.push(entry);
  }
  return entry;
}

async function clickButtonByText(text, options = {}) {
  const locator = page.locator('button, a').filter({ hasText: text }).first();
  await locator.click({ timeout: options.timeout ?? 7000 });
}

async function fillProfileForm() {
  await page.locator('input[type="text"]').first().fill(testAccount.displayName);

  const numberInputs = page.locator('input[type="number"]');
  await numberInputs.nth(0).fill('1994');
  await numberInputs.nth(1).fill('36');
  await numberInputs.nth(2).fill('18');

  const selects = page.locator('select');
  if (await selects.count()) {
    await selects.nth(0).selectOption('employed').catch(async () => {
      await selects.nth(0).selectOption({ index: 0 });
    });
    await selects.nth(1).selectOption({ index: 0 }).catch(() => {});
  }

  const moneyInputs = page.locator('input[inputmode="numeric"]');
  const moneyValues = ['5200', '1200', '300', '120', '25000', '65000', '6000', '150'];
  for (let i = 0; i < moneyValues.length; i += 1) {
    await moneyInputs.nth(i).fill(moneyValues[i]);
  }

  const areaInputs = page.locator('input[inputmode="decimal"]');
  await areaInputs.nth(0).fill('48');
  await areaInputs.nth(1).fill('84');

  for (const label of ['청년', '신혼부부', '서울', '경기 남부', '인천', '공공분양', '신혼희망타운']) {
    await page.locator('button').filter({ hasText: label }).first().click({ timeout: 3000 }).catch(() => {});
  }
}

async function discoverFirstNotice() {
  const hrefs = await page.locator('a[href]').evaluateAll((links) =>
    links.map((link) => link.getAttribute('href')).filter(Boolean)
  );
  const found = hrefs.find((href) => /\/notices\/\d+/.test(href));
  if (!found) throw new Error('추천 목록에서 공고 상세 링크를 찾지 못했습니다.');
  const noticeUrl = new URL(found, baseUrl);
  const noticeId = noticeUrl.pathname.match(/\/notices\/(\d+)/)?.[1];
  firstNoticePath = `${noticeUrl.pathname}${noticeUrl.search}`;
  fundingPath = `/funding/${noticeId}${noticeUrl.search}`;
  coachPath = `/ai-coach/${noticeId}${noticeUrl.search}`;
  firstNotice = { noticeId, path: firstNoticePath, optionQuery: noticeUrl.search };
  return firstNotice;
}

async function sendChatbotMessage() {
  const openButton = page.locator('button[title*="FirstHome"], button[title*="챗봇"], .fixed.bottom-24 button, .fixed.bottom-6 button').last();
  await openButton.click({ timeout: 10000 });
  await page.waitForTimeout(800);

  const beforeText = await bodyTextSample(2000);
  const prompt = '선택한 공고와 옵션 기준으로 이번 주에 먼저 할 일을 3개만 알려줘.';
  await page.locator('textarea').last().fill(prompt);
  await page.locator('form button[type="submit"]').last().click();
  await page.waitForTimeout(45000);
  const afterText = await bodyTextSample(3000);
  const changed = afterText.length > beforeText.length + prompt.length;
  return { changed, prompt, sample: afterText.slice(-1000) };
}

await recordStep('auth-register', async () => {
  await go('/auth');
  await page.locator('form button[type="button"]').last().click();
  await page.locator('input[type="text"]').first().fill(testAccount.username);
  await page.locator('input[type="email"]').first().fill(testAccount.email);
  await page.locator('input[type="password"]').first().fill(testAccount.password);
  await page.locator('form button[type="submit"]').first().click();
  await page.waitForURL(/\/profile/, { timeout: 20000 });
  return {
    screenshot: await saveScreenshot('01_registered_profile.png'),
    sample: await bodyTextSample(),
  };
});

await recordStep('profile-save-and-recommend', async () => {
  await fillProfileForm();
  await page.locator('form button[type="submit"]').last().click();
  await page.waitForURL(/\/recommendations/, { timeout: 25000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(2500);
  await discoverFirstNotice();
  return {
    screenshot: await saveScreenshot('02_recommendations_after_profile.png'),
    firstNotice,
    sample: await bodyTextSample(),
  };
});

await recordStep('notice-detail-and-save', async () => {
  if (!firstNoticePath) throw new Error('공고 상세 경로가 없습니다.');
  await go(firstNoticePath, 1600);
  const saveButton = page.locator('button').filter({ hasText: /공고 저장|공고 저장됨/ }).first();
  if (await saveButton.count()) {
    await saveButton.click({ timeout: 5000 }).catch(() => {});
    await page.waitForTimeout(800);
  }
  return {
    screenshot: await saveScreenshot('03_notice_detail_saved.png'),
    sample: await bodyTextSample(),
  };
});

await recordStep('funding-page', async () => {
  if (!fundingPath) throw new Error('자금 로드맵 경로가 없습니다.');
  await go(fundingPath, 2200);
  return {
    screenshot: await saveScreenshot('04_funding_page.png'),
    sample: await bodyTextSample(),
  };
});

await recordStep('ai-coach-page', async () => {
  if (!coachPath) throw new Error('AI 코치 경로가 없습니다.');
  await go(coachPath, 2000);
  await page.waitForTimeout(60000);
  return {
    screenshot: await saveScreenshot('05_ai_coach_loaded.png'),
    sample: await bodyTextSample(1500),
  };
});

await recordStep('chatbot-openai-message', async () => {
  const chat = await sendChatbotMessage();
  return {
    screenshot: await saveScreenshot('06_chatbot_openai_message.png'),
    chatbotReplyChanged: chat.changed,
    prompt: chat.prompt,
    sample: chat.sample,
  };
});

await recordStep('favorites-after-save', async () => {
  await go('/favorites', 1500);
  return {
    screenshot: await saveScreenshot('07_favorites_after_save.png'),
    sample: await bodyTextSample(1500),
  };
});

await recordStep('logout', async () => {
  await go('/auth', 1000);
  await page.locator('button').filter({ hasText: /로그아웃|濡쒓렇/ }).last().click({ timeout: 10000 });
  await page.waitForURL(baseUrl.replace(/\/$/, '') + '/', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1000);
  return {
    screenshot: await saveScreenshot('08_after_logout_home.png'),
    sample: await bodyTextSample(),
  };
});

await recordStep('login-again-and-profile-persist', async () => {
  await go('/auth', 1000);
  await page.locator('input[type="text"]').first().fill(testAccount.username);
  await page.locator('input[type="password"]').first().fill(testAccount.password);
  await page.locator('form button[type="submit"]').first().click();
  await page.waitForURL(/\/profile/, { timeout: 20000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.waitForTimeout(1500);
  const sample = await bodyTextSample(1500);
  return {
    screenshot: await saveScreenshot('09_relogin_profile_persist.png'),
    profileNameFound: sample.includes(testAccount.displayName),
    sample,
  };
});

await recordStep('favorites-after-relogin', async () => {
  await go('/favorites', 1500);
  return {
    screenshot: await saveScreenshot('10_favorites_after_relogin.png'),
    sample: await bodyTextSample(1500),
  };
});

await browser.close();

const endedAt = new Date();
const result = {
  baseUrl,
  startedAt: startedAt.toISOString(),
  endedAt: endedAt.toISOString(),
  durationMs: endedAt.getTime() - startedAt.getTime(),
  browserExecutable: executablePath || 'playwright bundled browser',
  testAccount: {
    username: testAccount.username,
    email: testAccount.email,
    displayName: testAccount.displayName,
  },
  firstNotice,
  steps,
  screenshots,
  consoleMessages,
  pageErrors,
  failedRequests,
  httpErrors,
};

const failures = steps.filter((step) => step.status === 'fail');
const warnings = [];
if (consoleMessages.length) warnings.push(`console warning/error ${consoleMessages.length}건`);
if (pageErrors.length) warnings.push(`page error ${pageErrors.length}건`);
if (failedRequests.length) warnings.push(`request failed ${failedRequests.length}건`);
if (httpErrors.length) warnings.push(`HTTP 4xx/5xx ${httpErrors.length}건`);
const chatbotStep = steps.find((step) => step.name === 'chatbot-openai-message');
if (chatbotStep?.status === 'pass' && chatbotStep.chatbotReplyChanged === false) {
  warnings.push('챗봇 전송 후 응답 본문 증가를 명확히 감지하지 못했습니다.');
}
const persistStep = steps.find((step) => step.name === 'login-again-and-profile-persist');
if (persistStep?.status === 'pass' && persistStep.profileNameFound === false) {
  warnings.push('재로그인 후 프로필 화면에서 테스트 표시 이름을 찾지 못했습니다.');
}

const report = `# 회원/로그인/AI 메시지 배포 점검

- 점검 대상: ${baseUrl}
- 점검 시간: ${startedAt.toLocaleString('ko-KR')} ~ ${endedAt.toLocaleString('ko-KR')}
- 브라우저: ${result.browserExecutable}
- 테스트 계정: \`${testAccount.username}\` / \`${testAccount.email}\`
- 점검 방식: 실제 Cloudflare 공개 URL을 브라우저로 열고 회원가입, 조건 저장, 추천 확인, 공고 저장, 자금 로드맵, AI 코치, 챗봇 메시지 전송, 로그아웃, 재로그인을 수행했습니다.

## 결과 요약

${failures.length ? `- 실패 단계: ${failures.length}건` : '- 모든 핵심 단계가 실행 완료되었습니다.'}
${warnings.length ? warnings.map((warning) => `- 주의: ${warning}`).join('\n') : '- 자동 수집 기준의 치명적인 브라우저 오류는 없습니다.'}

## 단계별 결과

| 단계 | 결과 | 소요 | 캡쳐 | 메모 |
| --- | --- | ---: | --- | --- |
${steps.map((step) => {
  const memo = step.error
    ? step.error.replace(/\|/g, '/')
    : step.name === 'chatbot-openai-message'
      ? `응답 변화 감지: ${step.chatbotReplyChanged ? '예' : '불명확'}`
      : step.name === 'login-again-and-profile-persist'
        ? `표시 이름 유지: ${step.profileNameFound ? '예' : '불명확'}`
        : '';
  return `| ${step.name} | ${step.status} | ${step.elapsedMs}ms | ${step.screenshot ? `[보기](./${step.screenshot})` : '-'} | ${memo} |`;
}).join('\n')}

## 확인한 흐름

- 회원가입 후 프로필 입력 화면으로 이동
- 조건 입력 저장 후 추천 청약 목록 이동
- 추천 공고 상세 진입 및 공고 저장 시도
- 선택 공고/옵션 기준 자금 로드맵 확인
- 선택 공고/옵션 기준 AI 코치 화면 확인
- 전역 챗봇에서 실제 메시지 전송
- 관심목록에서 저장 상태 확인
- 로그아웃 후 홈으로 이동
- 같은 계정으로 재로그인 후 프로필/관심목록 유지 여부 확인

## 수집된 이상 신호

### Console

${consoleMessages.length ? consoleMessages.map((item) => `- [${item.step}] ${item.type}: ${item.text}`).join('\n') : '- 없음'}

### Page Error

${pageErrors.length ? pageErrors.map((item) => `- [${item.step}] ${item.message}`).join('\n') : '- 없음'}

### Failed Requests

${failedRequests.length ? failedRequests.map((item) => `- [${item.step}] ${item.method} ${item.url}: ${item.failure}`).join('\n') : '- 없음'}

### HTTP 4xx/5xx

${httpErrors.length ? httpErrors.map((item) => `- [${item.step}] ${item.status} ${item.url}`).join('\n') : '- 없음'}

## 스크린샷

${screenshots.map((screenshot) => `- [${screenshot}](./${screenshot})`).join('\n')}

상세 원본 데이터는 [member_e2e_result.json](./member_e2e_result.json)에 저장했습니다.
`;

await fs.writeFile(path.join(outDir, 'member_e2e_result.json'), JSON.stringify(result, null, 2), 'utf8');
await fs.writeFile(path.join(outDir, 'member_e2e_report.md'), report, 'utf8');

console.log(`Wrote ${path.join(outDir, 'member_e2e_report.md')}`);
