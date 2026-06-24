import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');

const baseUrl = normalizeBaseUrl(process.argv[2] || 'https://polka-kennel-decorated.ngrok-free.dev');
const users = Number(process.argv[3] || 30);
const runId = new Date().toISOString().replace(/[:.]/g, '-');
const outDir = path.resolve('results', runId);

const paths = ['/', '/profile', '/recommendations', '/finance/products', '/finance/economy-now', '/finance/agora', '/my-page'];
const stepBudgets = {
  'goto:/': 20000,
  'goto:/profile': 12000,
  'goto:/recommendations': 12000,
  'goto:/finance/products': 12000,
  'goto:/finance/economy-now': 12000,
  'goto:/finance/agora': 12000,
  'goto:/my-page': 12000,
  'api:recommendations': 8000,
  'api:chat': 30000,
};
const report = {
  run_id: runId,
  base_url: baseUrl,
  users,
  started_at: new Date().toISOString(),
  sessions: [],
  issues: [],
};

function normalizeBaseUrl(value) {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

async function timed(label, fn) {
  const started = Date.now();
  try {
    const result = await fn();
    return { label, ok: true, elapsed_ms: Date.now() - started, result };
  } catch (error) {
    return { label, ok: false, elapsed_ms: Date.now() - started, error: String(error.message || error) };
  }
}

async function runSession(browser, index) {
  const context = await browser.newContext({
    viewport: { width: 1280, height: 820 },
    extraHTTPHeaders: { 'ngrok-skip-browser-warning': 'true' },
  });
  const page = await context.newPage();
  const failures = [];
  page.on('pageerror', (error) => failures.push({ type: 'pageerror', message: String(error.message || error) }));
  page.on('requestfailed', (request) => {
    const url = request.url();
    const failure = request.failure()?.errorText || 'unknown';
    if (isIgnorableRequestFailure(url, failure)) return;
    failures.push({ type: 'requestfailed', url, message: failure });
  });

  const steps = [];
  for (const routePath of paths) {
    steps.push(await timed(`goto:${routePath}`, async () => {
      const response = await page.goto(`${baseUrl}${routePath}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await page.waitForLoadState('networkidle', { timeout: 10000 }).catch(() => undefined);
      const text = await page.locator('body').innerText({ timeout: 5000 });
      if (text.includes('ERR_NGROK_6024')) throw new Error('ngrok warning shown');
      const status = response?.status?.() ?? null;
      if (status && status >= 400) throw new Error(`http ${status}`);
      return { status, text_length: text.length };
    }));
  }

  steps.push(await timed('api:recommendations', () => page.evaluate(async () => {
    const response = await fetch('/api/recommendations/housing', { headers: { 'ngrok-skip-browser-warning': 'true' }, credentials: 'include' });
    if (!response.ok) throw new Error(`recommendations ${response.status}`);
    return response.status;
  })));

  steps.push(await timed('api:chat', () => page.evaluate(async () => {
    const response = await fetch('/api/ai/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
      credentials: 'include',
      body: JSON.stringify({
        message: '이 화면은 어떻게 쓰면 돼?',
        page_context: { page_type: 'home', page_title: '대시보드', is_authenticated: false },
      }),
    });
    if (!response.ok) throw new Error(`chat ${response.status}`);
    const payload = await response.json();
    return { status: response.status, reply_length: String(payload.reply || '').length };
  })));

  await context.close();
  const slowSteps = steps
    .filter((step) => step.ok)
    .filter((step) => Number(step.elapsed_ms || 0) > (stepBudgets[step.label] ?? 15000))
    .map((step) => ({
      label: step.label,
      elapsed_ms: step.elapsed_ms,
      budget_ms: stepBudgets[step.label] ?? 15000,
    }));
  return {
    index,
    ok: steps.every((step) => step.ok) && failures.length === 0 && slowSteps.length === 0,
    steps,
    failures,
    slow_steps: slowSteps,
  };
}

function percentile(values, ratio) {
  if (!values.length) return 0;
  const sorted = values.slice().sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.floor((sorted.length - 1) * ratio));
  return sorted[index];
}

function isIgnorableRequestFailure(url, failure = '') {
  return /\.(woff2?|ttf|otf|eot)(\?|$)/i.test(url)
    || url.includes('fonts.gstatic.com')
    || url.includes('fonts.googleapis.com')
    || url.includes('cdn.jsdelivr.net')
    || (failure.includes('ERR_ABORTED') && /\/api\/(profile|account-state|auth\/me|dashboard|notices\?active=1)/.test(url))
    || (failure.includes('ERR_ABORTED') && url.includes('/api/ai/coach-summary'));
}

function groupFailures(sessions) {
  const counts = new Map();
  for (const session of sessions) {
    for (const step of session.steps.filter((step) => !step.ok)) {
      const key = `${step.label}: ${String(step.error || '').split('\n')[0].slice(0, 180)}`;
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    for (const step of session.slow_steps || []) {
      const key = `${step.label}: slow ${step.elapsed_ms}ms > ${step.budget_ms}ms`;
      counts.set(key, (counts.get(key) || 0) + 1);
    }
    for (const failure of session.failures) {
      const key = `${failure.type}: ${failure.message} ${failure.url || ''}`.slice(0, 220);
      counts.set(key, (counts.get(key) || 0) + 1);
    }
  }
  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([name, count]) => ({ name, count }));
}

await fs.mkdir(outDir, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: process.env.PLAYWRIGHT_CHANNEL || undefined });
try {
  const sessions = await Promise.all(Array.from({ length: users }, (_value, index) => runSession(browser, index + 1)));
  report.sessions = sessions;
} finally {
  await browser.close();
}

const stepTimes = report.sessions.flatMap((session) => session.steps.map((step) => step.elapsed_ms));
report.finished_at = new Date().toISOString();
report.summary = {
  ok_sessions: report.sessions.filter((session) => session.ok).length,
  failed_sessions: report.sessions.filter((session) => !session.ok).length,
  total_steps: report.sessions.reduce((sum, session) => sum + session.steps.length, 0),
  failed_steps: report.sessions.flatMap((session) => session.steps).filter((step) => !step.ok).length,
  slow_steps: report.sessions.flatMap((session) => session.slow_steps || []).length,
  p50_ms: percentile(stepTimes, 0.5),
  p95_ms: percentile(stepTimes, 0.95),
  max_ms: Math.max(0, ...stepTimes),
};
report.failure_groups = groupFailures(report.sessions);

await fs.writeFile(path.join(outDir, 'beta-load-report.json'), JSON.stringify(report, null, 2), 'utf8');
await fs.writeFile(path.join(outDir, 'beta-load-report.md'), [
  '# Beta Load Report',
  '',
  `- URL: ${report.base_url}`,
  `- Sessions: ${report.users}`,
  `- OK sessions: ${report.summary.ok_sessions}`,
  `- Failed sessions: ${report.summary.failed_sessions}`,
  `- Failed steps: ${report.summary.failed_steps}`,
  `- Slow steps: ${report.summary.slow_steps}`,
  `- p50: ${report.summary.p50_ms}ms`,
  `- p95: ${report.summary.p95_ms}ms`,
  `- max: ${report.summary.max_ms}ms`,
  '',
  '## Failure Groups',
  '',
  ...(report.failure_groups.length
    ? report.failure_groups.map((item) => `- ${item.count}x ${item.name}`)
    : ['- None']),
  '',
].join('\n'), 'utf8');

console.log(`Beta load report written: ${path.join(outDir, 'beta-load-report.md')}`);
if (report.summary.failed_sessions || report.summary.failed_steps) {
  process.exitCode = 1;
}
