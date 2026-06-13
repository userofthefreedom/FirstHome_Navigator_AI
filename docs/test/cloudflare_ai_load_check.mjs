import fs from 'node:fs/promises';
import path from 'node:path';
import { performance } from 'node:perf_hooks';

const frontendBase = (process.argv[2] || 'https://postal-philadelphia-disciplinary-finds.trycloudflare.com').replace(/\/$/, '');
const thirdArg = process.argv[3] || '';
const explicitApiBase = thirdArg && !/^\d+$/.test(thirdArg) ? thirdArg.replace(/\/$/, '') : '';
const users = Number((explicitApiBase ? process.argv[4] : process.argv[3]) || 30);
const outDir = path.resolve('docs/test');

const profile = {
  name: '동시접속테스터',
  birth_year: 1996,
  job_status: 'employed',
  annual_income: 50000000,
  cash_on_hand: 12000000,
  debt: 3000000,
  monthly_saving_capacity: 1200000,
  desired_price_min: 200000000,
  desired_price_max: 600000000,
  max_deposit_ready: 50000000,
  monthly_payment_limit: 1200000,
  preferred_area_min: 48,
  preferred_area_max: 84,
  is_homeless: true,
  subscription_months: 24,
  contract_saving_months: 18,
  special_conditions: ['청년'],
  preferred_regions: ['서울', '경기 남부', '경기 북부', '인천'],
  preferred_supply_types: ['public_sale', 'newlywed_public_sale', 'profit_sharing', 'public_participation'],
};

function timeoutSignal(ms) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  return { signal: controller.signal, clear: () => clearTimeout(timer) };
}

function normalizeApiBase(value) {
  const base = value.replace(/\/$/, '');
  return base.endsWith('/api') ? base : `${base}/api`;
}

async function discoverApiBase() {
  if (explicitApiBase) return normalizeApiBase(explicitApiBase);
  const htmlResponse = await fetch(frontendBase);
  const html = await htmlResponse.text();
  const assetPaths = [...html.matchAll(/src="([^"]+\.js)"/g)].map((match) => match[1]);
  for (const assetPath of assetPaths) {
    const assetUrl = new URL(assetPath, frontendBase).toString();
    const assetResponse = await fetch(assetUrl);
    const js = await assetResponse.text();
    const match = js.match(/https:\/\/[a-z0-9-]+\.trycloudflare\.com\/api/);
    if (match) return match[0].replace(/\/$/, '');
  }
  throw new Error('Unable to discover deployed API base URL from frontend assets.');
}

function cookieHeader(jar) {
  return Object.entries(jar)
    .map(([key, value]) => `${key}=${value}`)
    .join('; ');
}

function absorbSetCookie(jar, response) {
  const raw = response.headers.get('set-cookie');
  if (!raw) return 0;
  const cookies = raw.split(/,(?=\s*[^;,]+=)/);
  for (const cookie of cookies) {
    const [pair] = cookie.split(';');
    const index = pair.indexOf('=');
    if (index > 0) jar[pair.slice(0, index).trim()] = pair.slice(index + 1).trim();
  }
  return Buffer.byteLength(raw, 'utf8');
}

async function request(label, url, options = {}, jar = {}) {
  const started = performance.now();
  const timeout = timeoutSignal(options.timeoutMs || 120000);
  try {
    const headers = {
      Origin: frontendBase,
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(Object.keys(jar).length ? { Cookie: cookieHeader(jar) } : {}),
      ...(options.headers || {}),
    };
    const response = await fetch(url, {
      method: options.method || 'GET',
      body: options.body ? JSON.stringify(options.body) : undefined,
      signal: timeout.signal,
      headers,
    });
    const bytes = (await response.arrayBuffer()).byteLength;
    const setCookieBytes = absorbSetCookie(jar, response);
    return {
      label,
      url,
      ok: response.ok,
      status: response.status,
      ms: Math.round(performance.now() - started),
      bytes,
      setCookieBytes,
    };
  } catch (error) {
    return {
      label,
      url,
      ok: false,
      status: 0,
      ms: Math.round(performance.now() - started),
      bytes: 0,
      setCookieBytes: 0,
      error: error?.message || String(error),
    };
  } finally {
    timeout.clear();
  }
}

async function loadReference(apiBase) {
  const response = await fetch(`${apiBase}/recommendations/housing`, {
    headers: { Origin: frontendBase },
  });
  const recommendations = await response.json();
  const first = Array.isArray(recommendations) ? recommendations[0] : recommendations?.results?.[0];
  const option =
    first?.recommended_options?.[0] ||
    first?.options?.[0] ||
    first?.unit_options?.[0] ||
    first?.source_meta?.supply_summary?.unit_options?.[0] ||
    {};
  return {
    noticeId: first?.notice_id || first?.id || 1,
    optionId: option?.option_id || option?.id || null,
    title: first?.title || first?.notice_title || first?.name || '',
  };
}

async function virtualUser(index, apiBase, reference) {
  const jar = {};
  const suffix = `${Date.now()}_${index + 1}`;
  const credentials = {
    username: `load_${suffix}`,
    email: `load_${suffix}@example.com`,
    password: `Pw!${suffix}`,
  };
  const results = [];

  results.push(await request('frontend:home', `${frontendBase}/`, {}, jar));
  results.push(await request('frontend:recommendations', `${frontendBase}/recommendations`, {}, jar));
  results.push(await request('api:dashboard', `${apiBase}/dashboard`, {}, jar));
  results.push(await request('api:housing', `${apiBase}/recommendations/housing`, {}, jar));
  results.push(await request('api:map', `${apiBase}/notices/map`, {}, jar));
  results.push(await request('api:funding', `${apiBase}/recommendations/funding/${reference.noticeId}${reference.optionId ? `?option_id=${reference.optionId}` : ''}`, {}, jar));
  results.push(await request('auth:register', `${apiBase}/auth/register`, { method: 'POST', body: credentials }, jar));
  results.push(await request('auth:me', `${apiBase}/auth/me`, {}, jar));
  results.push(
    await request(
      'ai:chat',
      `${apiBase}/ai/chat`,
      {
        method: 'POST',
        body: {
          notice_id: reference.noticeId,
          option_id: reference.optionId,
          message: '추천 청약을 고른 뒤 바로 확인할 일을 짧게 알려줘.',
          profile,
          page_context: { page: 'concurrency-load-test', user: index + 1 },
        },
      },
      jar
    )
  );

  return { user: index + 1, results };
}

function percentile(values, p) {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const idx = Math.min(sorted.length - 1, Math.ceil((p / 100) * sorted.length) - 1);
  return sorted[idx];
}

const apiBase = await discoverApiBase();
const reference = await loadReference(apiBase);
const startedAt = new Date();
const started = performance.now();
const userResults = await Promise.all(Array.from({ length: users }, (_, index) => virtualUser(index, apiBase, reference)));
const endedAt = new Date();

const flat = userResults.flatMap((entry) => entry.results);
const failures = flat.filter((entry) => !entry.ok);
const durations = flat.map((entry) => entry.ms);
const byLabel = Object.values(
  flat.reduce((acc, entry) => {
    acc[entry.label] ||= { label: entry.label, count: 0, ok: 0, failed: 0, p50Ms: 0, p90Ms: 0, maxMs: 0, statuses: {} };
    const bucket = acc[entry.label];
    bucket.count += 1;
    bucket.ok += entry.ok ? 1 : 0;
    bucket.failed += entry.ok ? 0 : 1;
    bucket.statuses[entry.status] = (bucket.statuses[entry.status] || 0) + 1;
    bucket._durations ||= [];
    bucket._durations.push(entry.ms);
    return acc;
  }, {})
).map((bucket) => {
  const item = { ...bucket };
  item.p50Ms = percentile(item._durations, 50);
  item.p90Ms = percentile(item._durations, 90);
  item.maxMs = Math.max(...item._durations);
  delete item._durations;
  return item;
});

const result = {
  frontendBase,
  apiBase,
  users,
  reference,
  startedAt: startedAt.toISOString(),
  endedAt: endedAt.toISOString(),
  durationMs: Math.round(performance.now() - started),
  totalRequests: flat.length,
  successRequests: flat.length - failures.length,
  failedRequests: failures.length,
  p50Ms: percentile(durations, 50),
  p90Ms: percentile(durations, 90),
  p95Ms: percentile(durations, 95),
  maxMs: Math.max(...durations),
  byLabel,
  failedSamples: failures.slice(0, 30),
};

await fs.mkdir(outDir, { recursive: true });
await fs.writeFile(path.join(outDir, 'cloudflare_ai_load_result.json'), JSON.stringify(result, null, 2), 'utf8');

const status = failures.length ? '주의 필요' : '통과';
const lines = [
  '# Cloudflare AI 동시접속 점검',
  '',
  `- 점검 일시: ${endedAt.toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })}`,
  `- 프론트 주소: ${frontendBase}`,
  `- API 주소: ${apiBase}`,
  `- 가상 사용자: ${users}명`,
  `- 기준 공고: ${reference.title || reference.noticeId}`,
  `- 결과: ${status}`,
  '',
  '## 요약',
  '',
  `- 전체 요청: ${result.totalRequests}건`,
  `- 성공: ${result.successRequests}건`,
  `- 실패: ${result.failedRequests}건`,
  `- 총 소요: ${Math.round(result.durationMs / 1000)}초`,
  `- p50/p90/p95/max: ${result.p50Ms}ms / ${result.p90Ms}ms / ${result.p95Ms}ms / ${result.maxMs}ms`,
  '',
  '## 엔드포인트별 결과',
  '',
  '| 구분 | 요청 | 성공 | 실패 | p50 | p90 | 최대 | 상태 |',
  '|---|---:|---:|---:|---:|---:|---:|---|',
  ...byLabel.map((item) => `| ${item.label} | ${item.count} | ${item.ok} | ${item.failed} | ${item.p50Ms}ms | ${item.p90Ms}ms | ${item.maxMs}ms | ${Object.entries(item.statuses).map(([code, count]) => `${code}:${count}`).join(', ')} |`),
  '',
  '## 실패 샘플',
  '',
  failures.length
    ? '```json\n' + JSON.stringify(result.failedSamples, null, 2) + '\n```'
    : '실패 요청이 없습니다.',
  '',
  '## 해석',
  '',
  '- 이 점검은 30명의 사용자가 동시에 주요 화면/API를 열고, 회원가입 세션을 만든 뒤 AI 챗 요청을 보내는 상황을 HTTP 레벨에서 재현했습니다.',
  '- 브라우저 렌더링 전체 회귀는 `cloudflare_full_check.spec.js`에서 별도로 수행했습니다.',
].join('\n');

await fs.writeFile(path.join(outDir, 'cloudflare_ai_load_report.md'), lines, 'utf8');
console.log(JSON.stringify(result, null, 2));
