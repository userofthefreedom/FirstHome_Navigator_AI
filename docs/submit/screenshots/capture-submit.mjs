import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require(path.resolve('docs/test/node_modules/playwright'));

const baseUrl = normalizeBaseUrl(process.argv[2] || 'https://polka-kennel-decorated.ngrok-free.dev');
const outDir = path.resolve('docs/submit/screenshots');
const manifestPath = path.resolve('docs/submit/screenshot-manifest.json');
const readmePath = path.resolve('docs/submit/README.md');

const viewport = { width: 1440, height: 960 };
const themes = ['light', 'dark'];
const personas = ['guest', 'member'];
const noticeId = 101;
const optionId = 1001;

const routes = [
  { key: 'dashboard', path: '/' },
  { key: 'profile', path: '/profile' },
  { key: 'recommendations', path: '/recommendations' },
  { key: 'notice_detail', path: `/notices/${noticeId}?option_id=${optionId}` },
  { key: 'map', path: '/map', settleMs: 2500 },
  { key: 'funding', path: `/funding/${noticeId}?option_id=${optionId}`, settleMs: 1200 },
  { key: 'ai_coach', path: `/ai-coach/${noticeId}?option_id=${optionId}`, settleMs: 2000 },
  { key: 'favorites', path: '/favorites' },
  { key: 'finance_products', path: '/finance/products' },
  { key: 'finance_product_detail', path: '/finance/products/1' },
  { key: 'economy_now', path: '/finance/economy-now', settleMs: 1400 },
  { key: 'agora', path: '/finance/agora', settleMs: 1200 },
  { key: 'my_page', path: '/my-page', settleMs: 1200 },
  { key: 'auth', path: '/auth' },
];

const profile = {
  name: '오세진',
  birth_year: 1999,
  job_status: 'employed',
  annual_income: 50000000,
  asset: 8000000,
  debt: 3000000,
  monthly_saving: 800000,
  is_homeless: true,
  subscription_months: 36,
  special_conditions: [],
  preferred_regions: ['서울', '경기 남부', '인천'],
  preferred_supply_types: ['공공분양', '신혼희망타운 공공분양'],
  target_months: 18,
  desired_area_min_m2: 45,
  desired_area_max_m2: 85,
  desired_price_min: 0,
  desired_price_max: 700000000,
  max_down_payment: 10000000,
  monthly_payment_capacity: 800000,
};

const loadingPatterns = [
  '로딩',
  '불러오는 중',
  '계산하고 있습니다',
  '분석 준비',
  '읽고 있습니다',
  '처리 중',
  'Loading',
];

const manifest = {
  baseUrl,
  generatedAt: new Date().toISOString(),
  viewport,
  noticeId,
  optionId,
  screenshots: [],
  warnings: [],
};

function normalizeBaseUrl(value) {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

async function ensureDirs() {
  await fs.mkdir(outDir, { recursive: true });
}

async function createContext(browser) {
  return browser.newContext({
    viewport,
    extraHTTPHeaders: {
      'ngrok-skip-browser-warning': 'true',
    },
  });
}

async function setTheme(page, theme) {
  await page.addInitScript((value) => {
    localStorage.setItem('firsthome-theme', value);
    document.documentElement.dataset.theme = value;
  }, theme);
  await page.evaluate((value) => {
    localStorage.setItem('firsthome-theme', value);
    document.documentElement.dataset.theme = value;
  }, theme).catch(() => undefined);
}

async function waitUntilReady(page, route) {
  await page.waitForLoadState('domcontentloaded', { timeout: 45000 }).catch(() => undefined);
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => undefined);
  await page.waitForTimeout(route.settleMs ?? 900);

  for (let attempt = 0; attempt < 8; attempt += 1) {
    const text = await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
    const hasLoadingText = loadingPatterns.some((pattern) => text.includes(pattern));
    const busyCount = await page.locator('[aria-busy="true"], .loading, .spinner, [class*="animate-spin"]').count().catch(() => 0);
    if (!hasLoadingText && busyCount === 0) return { ready: true, text };
    await page.waitForTimeout(1000);
  }

  const text = await page.locator('body').innerText({ timeout: 5000 }).catch(() => '');
  return {
    ready: false,
    text,
    matchedPatterns: loadingPatterns.filter((pattern) => text.includes(pattern)),
  };
}

async function capture(page, persona, theme, route) {
  await setTheme(page, theme);
  const url = `${baseUrl}${route.path}`;
  const startedAt = Date.now();
  const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 }).catch((error) => {
    manifest.warnings.push({
      persona,
      theme,
      route: route.key,
      type: 'goto-failed',
      message: String(error.message || error),
    });
    return null;
  });

  const readiness = await waitUntilReady(page, route);
  await hideVolatileUi(page);

  const dir = path.join(outDir, persona, theme);
  await fs.mkdir(dir, { recursive: true });
  const fileName = `${String(manifest.screenshots.length + 1).padStart(2, '0')}_${route.key}.png`;
  const filePath = path.join(dir, fileName);
  await page.screenshot({ path: filePath, fullPage: true, animations: 'disabled' });

  const entry = {
    persona,
    theme,
    route: route.key,
    path: route.path,
    url,
    file: path.relative(path.resolve('docs/submit'), filePath).replaceAll('\\', '/'),
    status: response?.status?.() ?? null,
    elapsedMs: Date.now() - startedAt,
    ready: readiness.ready,
  };
  manifest.screenshots.push(entry);

  if (!readiness.ready) {
    manifest.warnings.push({
      persona,
      theme,
      route: route.key,
      type: 'possibly-loading',
      matchedPatterns: readiness.matchedPatterns ?? [],
    });
  }

  return entry;
}

async function hideVolatileUi(page) {
  await page.evaluate(() => {
    const selectors = [
      '[class*="fixed"][class*="bottom"]',
      '[class*="Floating"]',
      '[aria-live]',
    ];
    for (const selector of selectors) {
      for (const element of document.querySelectorAll(selector)) {
        const text = element.textContent || '';
        if (text.includes('AI') || text.includes('챗봇') || text.includes('궁금')) {
          element.style.visibility = 'hidden';
        }
      }
    }
  }).catch(() => undefined);
}

async function registerAndPrimeMember(page) {
  await page.goto(`${baseUrl}/`, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => undefined);
  const username = `submit_${Date.now()}_${Math.random().toString(16).slice(2, 6)}`;
  const password = 'submitpass123';

  await page.evaluate(async ({ username, password, profile, noticeId, optionId }) => {
    const jsonHeaders = { 'Content-Type': 'application/json', 'X-FirstHome-Client-Id': `submit-${username}` };
    const registerResponse = await fetch('/api/auth/register', {
      method: 'POST',
      headers: jsonHeaders,
      credentials: 'include',
      body: JSON.stringify({
        username,
        password,
        email: `${username}@example.com`,
        name: profile.name,
        birth_year: profile.birth_year,
      }),
    });
    if (!registerResponse.ok) {
      throw new Error(`register failed ${registerResponse.status}`);
    }

    const profileResponse = await fetch('/api/profile', {
      method: 'PUT',
      headers: jsonHeaders,
      credentials: 'include',
      body: JSON.stringify(profile),
    });
    if (!profileResponse.ok) {
      throw new Error(`profile failed ${profileResponse.status}`);
    }

    await fetch('/api/account-state', {
      method: 'PUT',
      headers: jsonHeaders,
      credentials: 'include',
      body: JSON.stringify({ current_notice_id: noticeId, current_option_id: optionId }),
    });

    for (const favorite of [
      { favorite_type: 'notice', object_id: noticeId },
      { favorite_type: 'option', object_id: optionId },
      { favorite_type: 'product', object_id: 1 },
    ]) {
      await fetch('/api/favorites', {
        method: 'POST',
        headers: jsonHeaders,
        credentials: 'include',
        body: JSON.stringify(favorite),
      }).catch(() => undefined);
    }

    localStorage.setItem('firsthome.current_selection', JSON.stringify({
      noticeId,
      optionId,
      updatedAt: new Date().toISOString(),
    }));
  }, { username, password, profile, noticeId, optionId });

  return { username, password };
}

async function run() {
  await ensureDirs();
  const browser = await chromium.launch({ headless: true });

  try {
    for (const persona of personas) {
      const context = await createContext(browser);
      const page = await context.newPage();
      if (persona === 'member') {
        const account = await registerAndPrimeMember(page);
        manifest.memberAccount = { username: account.username };
      }

      for (const theme of themes) {
        for (const route of routes) {
          await capture(page, persona, theme, route);
        }
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }

  await fs.writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`, 'utf8');
  await fs.writeFile(readmePath, renderReadme(), 'utf8');
  console.log(`saved ${manifest.screenshots.length} screenshots to ${outDir}`);
  if (manifest.warnings.length) {
    console.log(`warnings: ${manifest.warnings.length}`);
  }
}

function renderReadme() {
  const lines = [
    '# 제출용 실행 화면 캡처',
    '',
    `- 생성 시각: ${manifest.generatedAt}`,
    `- 대상 주소: ${manifest.baseUrl}`,
    `- 뷰포트: ${manifest.viewport.width}x${manifest.viewport.height}`,
    `- 캡처 수: ${manifest.screenshots.length}`,
    `- 테스트 계정: ${manifest.memberAccount?.username ?? '생성 실패 또는 없음'}`,
    '',
    '## 구성',
    '',
    '- `screenshots/guest/light`: 비회원 라이트 모드',
    '- `screenshots/guest/dark`: 비회원 다크 모드',
    '- `screenshots/member/light`: 회원 라이트 모드',
    '- `screenshots/member/dark`: 회원 다크 모드',
    '- `screenshot-manifest.json`: 캡처 URL, 경로, 준비 상태 기록',
    '',
    '## 캡처 목록',
    '',
    '| 상태 | 테마 | 화면 | 파일 | 준비 상태 |',
    '|---|---|---|---|---|',
  ];

  for (const shot of manifest.screenshots) {
    lines.push(`| ${shot.persona} | ${shot.theme} | ${shot.route} | \`${shot.file}\` | ${shot.ready ? 'OK' : '확인 필요'} |`);
  }

  if (manifest.warnings.length) {
    lines.push('', '## 확인 필요 경고', '');
    for (const warning of manifest.warnings) {
      lines.push(`- ${warning.persona}/${warning.theme}/${warning.route}: ${warning.type}`);
    }
  }

  return `${lines.join('\n')}\n`;
}

run().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
