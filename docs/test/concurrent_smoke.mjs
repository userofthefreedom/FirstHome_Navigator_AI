import fs from 'node:fs/promises';
import path from 'node:path';
import { performance } from 'node:perf_hooks';

const frontendBase = (process.argv[2] || 'https://san-ultra-represents-pins.trycloudflare.com').replace(/\/$/, '');
const apiBase = (process.argv[3] || 'https://dressed-wichita-aerospace-clay.trycloudflare.com').replace(/\/$/, '');
const users = Number(process.argv[4] || 30);
const outDir = path.resolve('docs/test');

const frontendPaths = ['/', '/recommendations', '/map', '/funding/1?option_id=285'];
const apiPaths = [
  '/api/dashboard',
  '/api/notices?active=1',
  '/api/recommendations/housing',
  '/api/recommendations/funding/1?option_id=285',
];

function timeoutSignal(ms) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ms);
  return { signal: controller.signal, clear: () => clearTimeout(timer) };
}

async function request(url, options = {}) {
  const started = performance.now();
  const timeout = timeoutSignal(25000);
  try {
    const response = await fetch(url, {
      ...options,
      signal: timeout.signal,
      headers: {
        Origin: frontendBase,
        ...(options.headers || {}),
      },
    });
    const body = await response.arrayBuffer();
    const setCookie = response.headers.get('set-cookie') || '';
    return {
      ok: response.ok,
      status: response.status,
      ms: Math.round(performance.now() - started),
      bytes: body.byteLength,
      setCookieBytes: Buffer.byteLength(setCookie, 'utf8'),
      url,
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      ms: Math.round(performance.now() - started),
      bytes: 0,
      setCookieBytes: 0,
      url,
      error: error?.message || String(error),
    };
  } finally {
    timeout.clear();
  }
}

async function virtualUser(index) {
  const requests = [];
  for (const route of frontendPaths) {
    requests.push(request(`${frontendBase}${route}`));
  }
  for (const route of apiPaths) {
    requests.push(request(`${apiBase}${route}`));
  }
  const results = await Promise.all(requests);
  return { user: index + 1, results };
}

const startedAt = new Date();
const started = performance.now();
const userResults = await Promise.all(Array.from({ length: users }, (_, index) => virtualUser(index)));
const endedAt = new Date();

const flat = userResults.flatMap((entry) => entry.results);
const failed = flat.filter((entry) => !entry.ok);
const durations = flat.map((entry) => entry.ms).sort((a, b) => a - b);
const cookieMax = Math.max(...flat.map((entry) => entry.setCookieBytes));

function percentile(p) {
  if (!durations.length) return 0;
  const idx = Math.min(durations.length - 1, Math.ceil((p / 100) * durations.length) - 1);
  return durations[idx];
}

const result = {
  frontendBase,
  apiBase,
  users,
  startedAt: startedAt.toISOString(),
  endedAt: endedAt.toISOString(),
  durationMs: Math.round(performance.now() - started),
  totalRequests: flat.length,
  successRequests: flat.length - failed.length,
  failedRequests: failed.length,
  p50Ms: percentile(50),
  p90Ms: percentile(90),
  p95Ms: percentile(95),
  maxMs: durations.at(-1) || 0,
  maxSetCookieBytes: cookieMax,
  failedSamples: failed.slice(0, 20),
  perUrl: Object.values(
    flat.reduce((acc, entry) => {
      acc[entry.url] ||= { url: entry.url, count: 0, failures: 0, maxMs: 0, maxSetCookieBytes: 0 };
      acc[entry.url].count += 1;
      acc[entry.url].failures += entry.ok ? 0 : 1;
      acc[entry.url].maxMs = Math.max(acc[entry.url].maxMs, entry.ms);
      acc[entry.url].maxSetCookieBytes = Math.max(acc[entry.url].maxSetCookieBytes, entry.setCookieBytes);
      return acc;
    }, {})
  ),
};

await fs.mkdir(outDir, { recursive: true });
await fs.writeFile(path.join(outDir, 'concurrent_smoke_result.json'), JSON.stringify(result, null, 2), 'utf8');
await fs.writeFile(path.join(outDir, `concurrent_smoke_${users}_users_result.json`), JSON.stringify(result, null, 2), 'utf8');

console.log(JSON.stringify(result, null, 2));
