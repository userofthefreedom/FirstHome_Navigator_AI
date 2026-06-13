import { createRequire } from 'module';
import fs from 'fs/promises';
import path from 'path';

const targetUrl = (process.argv[2] || 'https://bit-county-makers-utilize.trycloudflare.com/').replace(/\/$/, '');
const runStamp = new Date().toISOString().replace(/[:.]/g, '-');
const outDir = path.resolve('docs', 'test');
const shotDir = path.join(outDir, `live_auth_${runStamp}`);
const playwrightRequireFrom = process.env.PLAYWRIGHT_REQUIRE_FROM;
const { chromium } = playwrightRequireFrom
  ? createRequire(playwrightRequireFrom)('playwright')
  : createRequire(import.meta.url)('playwright');

await fs.mkdir(shotDir, { recursive: true });

const browser = await chromium.launch({
  headless: true,
  executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH || 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  args: ['--no-sandbox'],
});
const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
const page = await context.newPage();
const issues = [];
page.on('response', (res) => {
  if (res.status() >= 400 && !res.url().includes('favicon')) {
    issues.push({ type: 'http', status: res.status(), url: res.url() });
  }
});
page.on('pageerror', (error) => issues.push({ type: 'pageerror', text: error.message }));

const result = {
  targetUrl,
  runStamp,
  steps: [],
  issues,
};

async function record(label, fn) {
  const start = Date.now();
  try {
    await fn();
    result.steps.push({ label, ok: true, ms: Date.now() - start });
  } catch (error) {
    result.steps.push({ label, ok: false, ms: Date.now() - start, error: error.message });
  }
}

await record('open auth page', async () => {
  await page.goto(`${targetUrl}/auth`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.screenshot({ path: path.join(shotDir, '01_auth_initial.png'), fullPage: true });
});

await record('switch to register and submit', async () => {
  const form = page.locator('form').first();
  await form.locator('button[type="button"]').last().click();
  await page.waitForTimeout(500);
  const username = `codex_live_${Date.now()}`;
  const inputs = form.locator('input');
  await inputs.nth(0).fill(username);
  const count = await inputs.count();
  if (count >= 3) {
    await inputs.nth(1).fill(`${username}@example.com`);
    await inputs.nth(2).fill('Testpass123!');
  } else {
    throw new Error(`Register mode did not show expected 3 inputs. Input count=${count}`);
  }
  await page.screenshot({ path: path.join(shotDir, '02_register_filled.png'), fullPage: true });
  await form.locator('button[type="submit"]').click();
  await page.waitForURL(/profile|auth/, { timeout: 30000 }).catch(() => {});
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  await page.screenshot({ path: path.join(shotDir, '03_after_register.png'), fullPage: true });
  const url = page.url();
  const body = await page.locator('body').innerText();
  if (!url.includes('/profile') && !/조건 입력|첫 집 청약/.test(body)) {
    throw new Error(`Registration did not reach profile page. url=${url}, body=${body.slice(0, 300)}`);
  }
});

await record('logout if visible', async () => {
  await page.goto(`${targetUrl}/auth`, { waitUntil: 'domcontentloaded', timeout: 90000 });
  await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  const before = await page.locator('body').innerText();
  const logoutCandidate = page.locator('button').filter({ hasText: /로그아웃|濡/ }).first();
  if (await logoutCandidate.count()) {
    await logoutCandidate.click();
    await page.waitForTimeout(1500);
  }
  await page.screenshot({ path: path.join(shotDir, '04_after_logout.png'), fullPage: true });
  const after = await page.locator('body').innerText();
  result.logoutTextChanged = before !== after;
});

await browser.close();

const jsonPath = path.join(outDir, `live_auth_${runStamp}_result.json`);
const mdPath = path.join(outDir, `live_auth_${runStamp}_report.md`);
await fs.writeFile(jsonPath, JSON.stringify(result, null, 2), 'utf8');
const md = [
  '# Live Auth Mutation Check',
  '',
  `- Frontend: ${targetUrl}`,
  `- Run: ${runStamp}`,
  '',
  '| Step | Result | Time | Note |',
  '| --- | --- | ---: | --- |',
  ...result.steps.map((step) => `| ${step.label} | ${step.ok ? 'OK' : 'FAIL'} | ${(step.ms / 1000).toFixed(2)}s | ${(step.error || '').replace(/\|/g, '/')} |`),
  '',
  `Screenshots: \`${path.relative(outDir, shotDir).replace(/\\/g, '/')}\``,
  '',
  result.issues.length ? `Issues:\n${result.issues.map((issue) => `- ${issue.type} ${issue.status || ''} ${issue.url || issue.text || ''}`).join('\n')}` : 'Issues: none',
  '',
].join('\n');
await fs.writeFile(mdPath, md, 'utf8');
await fs.writeFile(path.join(outDir, 'live_auth_latest_result.json'), JSON.stringify(result, null, 2), 'utf8');
await fs.writeFile(path.join(outDir, 'live_auth_latest_report.md'), md, 'utf8');
console.log(md);
