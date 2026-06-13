const { test, expect } = require('@playwright/test');

const baseUrl = process.env.BASE_URL || 'https://postal-philadelphia-disciplinary-finds.trycloudflare.com';
const stamp = Date.now();
const user = {
  username: `e2e_${stamp}`,
  password: `Pw!${stamp}`,
  email: `e2e_${stamp}@example.com`,
  name: `테스터${String(stamp).slice(-4)}`,
};

function attachCollectors(page, logs) {
  page.on('console', (msg) => {
    if (['error', 'warning'].includes(msg.type())) logs.push(`[console:${msg.type()}] ${msg.text()}`);
  });
  page.on('pageerror', (err) => logs.push(`[pageerror] ${err.message}`));
  page.on('requestfailed', (req) => logs.push(`[requestfailed] ${req.method()} ${req.url()} ${req.failure()?.errorText}`));
  page.on('response', (res) => {
    if (res.status() >= 400) logs.push(`[response:${res.status()}] ${res.url()}`);
  });
}

async function clickNav(page, text) {
  await page.getByRole('link', { name: text }).first().click();
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
}

async function saveScreenshot(page, name) {
  await page.screenshot({ path: `docs/test/${name}.png`, fullPage: true });
}

test('deployed site user flow with auth and AI surfaces', async ({ page }) => {
  test.setTimeout(240000);
  const logs = [];
  attachCollectors(page, logs);

  await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 60000 });
  await expect(page.getByText('FirstHome').first()).toBeVisible();
  await saveScreenshot(page, 'cloudflare_01_dashboard_guest');

  for (const nav of ['조건 입력', '추천 청약', '청약 지도', '자금 로드맵', 'AI 코치', '관심목록']) {
    await clickNav(page, nav);
    await expect(page.locator('body')).toContainText(nav === '자금 로드맵' ? '자금' : nav.split(' ')[0]);
    await saveScreenshot(page, `cloudflare_nav_${nav.replace(/\s/g, '_')}`);
  }

  await page.goto(`${baseUrl}/auth`, { waitUntil: 'networkidle', timeout: 60000 });
  await saveScreenshot(page, 'cloudflare_02_auth');

  const authText = await page.locator('body').innerText();
  const inputs = page.locator('main input:not([type="search"])');
  const inputCount = await inputs.count();
  if (inputCount < 2) throw new Error(`Auth page has too few inputs: ${inputCount}\n${authText}`);

  await page.getByRole('button', { name: '계정이 없으면 회원가입' }).click({ force: true });
  await expect(page.getByRole('heading', { name: '회원가입' })).toBeVisible({ timeout: 10000 });

  const afterModeInputs = page.locator('main input:not([type="search"])');
  const values = [user.username, user.email, user.password];
  const count = Math.min(await afterModeInputs.count(), values.length);
  for (let i = 0; i < count; i += 1) {
    await afterModeInputs.nth(i).fill(values[i]);
  }

  const submit = page.locator('main button[type="submit"]').first();
  await submit.click({ force: true });
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await saveScreenshot(page, 'cloudflare_03_after_auth_submit');

  const bodyAfterAuth = await page.locator('body').innerText();
  if (/로그인|회원가입/.test(bodyAfterAuth) && !/로그아웃|계정 저장 중/.test(bodyAfterAuth)) {
    const loginTab = page.getByRole('button', { name: /로그인/ }).first();
    if (await loginTab.count()) await loginTab.click().catch(() => {});
    const loginInputs = page.locator('main input:not([type="search"])');
    await loginInputs.nth(0).fill(user.username);
    await loginInputs.nth(1).fill(user.password);
    await page.locator('main button[type="submit"]').first().click({ force: true });
    await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
    await page.waitForTimeout(1500);
  }
  await saveScreenshot(page, 'cloudflare_04_logged_in');

  await clickNav(page, '추천 청약');
  await expect(page.getByText('검토할 후보')).toBeVisible({ timeout: 30000 });
  await page.getByRole('link', { name: /공식 근거 보기|공고 상세|공식 근거/ }).first().click().catch(async () => {
    await page.getByText(/공식 근거 보기|공고 상세|공식 근거/).first().click();
  });
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
  await saveScreenshot(page, 'cloudflare_05_notice_detail');

  await page.getByRole('link', { name: /옵션 자금|자금 로드맵|자금 보기/ }).first().click().catch(async () => {
    await page.getByText(/옵션 자금|자금 로드맵|자금 보기/).first().click();
  });
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
  await saveScreenshot(page, 'cloudflare_06_funding');

  await page.getByRole('link', { name: /AI 코칭 받기|AI 코치/ }).first().click().catch(async () => {
    await clickNav(page, 'AI 코치');
  });
  await page.waitForLoadState('networkidle', { timeout: 30000 }).catch(() => {});
  await page.waitForTimeout(5000);
  await saveScreenshot(page, 'cloudflare_07_ai_coach');
  await expect(page.locator('body')).toContainText(/바로 처리할 일|AI|코치/);

  const chatbot = page.getByRole('button', { name: /AI|Q/ }).last();
  if (await chatbot.count()) {
    await chatbot.click();
    await page.waitForTimeout(500);
    const chatInput = page.locator('textarea, input[placeholder*="질문"], input[placeholder*="메시지"], input[placeholder*="입력"]').last();
    if (await chatInput.count()) {
      await chatInput.fill('이 서비스에서 추천 청약을 고른 다음 무엇을 확인해야 하나요?');
      await page.keyboard.press('Enter');
      await page.waitForTimeout(8000);
      await saveScreenshot(page, 'cloudflare_08_chatbot');
    }
  }

  if (logs.length) {
    console.log('COLLECTED_LOGS\n' + logs.join('\n'));
  }

  const seriousLogs = logs.filter((line) => !/favicon|kakao|ResizeObserver|net::ERR_ABORTED/i.test(line));
  expect(seriousLogs, seriousLogs.join('\n')).toHaveLength(0);
});
