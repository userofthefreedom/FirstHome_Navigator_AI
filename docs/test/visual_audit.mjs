import { createRequire } from 'node:module';
import fs from 'node:fs/promises';
import path from 'node:path';

const require = createRequire(process.env.PLAYWRIGHT_REQUIRE_FROM || import.meta.url);
const { chromium } = require('playwright');

const baseUrl = normalizeBaseUrl(process.argv[2] || 'http://127.0.0.1:5173');
const outDir = path.resolve('docs', 'test', 'visual_audit');
const shotDir = path.join(outDir, 'screenshots');

const routes = [
  { key: 'home', path: '/', wait: 1000 },
  { key: 'profile', path: '/profile', wait: 900 },
  { key: 'recommendations', path: '/recommendations', wait: 1400 },
  { key: 'notice_detail', path: '/notices/1', wait: 1300 },
  { key: 'funding', path: '/funding', wait: 1300 },
  { key: 'ai_coach', path: '/ai-coach', wait: 1600 },
  { key: 'map', path: '/map', wait: 3000 },
  { key: 'products', path: '/finance/products', wait: 1200 },
  { key: 'economy_now', path: '/finance/economy-now', wait: 1600 },
  { key: 'agora', path: '/finance/agora', wait: 1600 },
  { key: 'my_page', path: '/my-page', wait: 1400 },
  { key: 'auth', path: '/auth', wait: 900 },
];

const scenarios = [
  { key: 'guest', authenticated: false },
  { key: 'user', authenticated: true },
];

const browserCandidates = [
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
];

function normalizeBaseUrl(value) {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

async function firstExisting(candidates) {
  for (const candidate of candidates) {
    try {
      await fs.access(candidate);
      return candidate;
    } catch {
      // Keep looking.
    }
  }
  return undefined;
}

async function setTheme(context, theme) {
  await context.addInitScript((value) => {
    localStorage.setItem('firsthome-theme', value);
    document.documentElement.dataset.theme = value;
    document.documentElement.style.colorScheme = value;
  }, theme);
}

async function setupUserScenario(page) {
  await page.goto(baseUrl, { waitUntil: 'domcontentloaded', timeout: 45000 });
  await page.evaluate(async () => {
    const username = `visual_${Date.now()}_${Math.random().toString(16).slice(2, 8)}`;
    const headers = {
      'Content-Type': 'application/json',
      'ngrok-skip-browser-warning': 'true',
    };
    await fetch('/api/auth/register', {
      method: 'POST',
      headers,
      credentials: 'include',
      body: JSON.stringify({
        username,
        password: 'visualpass123',
        email: `${username}@example.com`,
      }),
    });
    await fetch('/api/profile', {
      method: 'PUT',
      headers,
      credentials: 'include',
      body: JSON.stringify({
        name: '시각점검',
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

    const productsResponse = await fetch('/api/products?ordering=fit', { credentials: 'include' });
    const productsPayload = await productsResponse.json().catch(() => ({ items: [] }));
    const products = Array.isArray(productsPayload.items) ? productsPayload.items.slice(0, 6) : [];
    for (const [index, product] of products.entries()) {
      const detailResponse = await fetch(`/api/products/${product.id}`, { credentials: 'include' });
      const detail = await detailResponse.json().catch(() => product);
      const options = Array.isArray(detail.options) ? detail.options : [];
      const selected = options
        .slice()
        .sort((left, right) => Number(left.save_trm || 0) - Number(right.save_trm || 0))[index % Math.max(options.length, 1)];
      await fetch(`/api/products/${product.id}/join`, {
        method: 'POST',
        headers,
        credentials: 'include',
        body: JSON.stringify({
          option_id: selected?.id,
          memo: index === 0 ? '시각 점검 메모' : '계약금 마련 후보',
        }),
      });
    }
  });
}

async function auditVisibleUi(page, theme) {
  return page.evaluate((activeTheme) => {
    const viewportHeight = window.innerHeight;

    function parseColor(value) {
      const match = value.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/);
      if (!match) return null;
      const alpha = value.includes('rgba') ? Number(value.match(/,\s*([0-9.]+)\)$/)?.[1] || 1) : 1;
      return { rgb: [Number(match[1]), Number(match[2]), Number(match[3])], alpha };
    }

    function parseRgb(value) {
      const parsed = parseColor(value);
      return parsed?.rgb || null;
    }

    function lum(rgb) {
      const values = rgb.map((v) => {
        const s = v / 255;
        return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
    }

    function contrast(fg, bg) {
      const a = lum(fg);
      const b = lum(bg);
      return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    }

    function effectiveBackground(element) {
      let current = element;
      while (current && current !== document.documentElement) {
        const color = getComputedStyle(current).backgroundColor;
        const parsed = parseColor(color);
        if (parsed) {
          if (parsed.alpha >= 0.72) return parsed.rgb;
        }
        current = current.parentElement;
      }
      return parseRgb(getComputedStyle(document.body).backgroundColor) || [255, 255, 255];
    }

    function shortText(element) {
      return element.innerText?.replace(/\s+/g, ' ').trim().slice(0, 90) || '';
    }

    const textIssues = [...document.querySelectorAll('body *')]
      .filter((el) => {
        const rect = el.getBoundingClientRect();
        const text = shortText(el);
        return text && rect.width > 10 && rect.height > 8 && rect.bottom > 0 && rect.top < viewportHeight * 1.8;
      })
      .map((el) => {
        const fg = parseRgb(getComputedStyle(el).color);
        const bg = fg ? effectiveBackground(el) : null;
        return {
          text: shortText(el),
          tag: el.tagName.toLowerCase(),
          className: String(el.className || '').slice(0, 180),
          contrast: fg && bg ? Number(contrast(fg, bg).toFixed(2)) : 99,
        };
      })
      .filter((entry, index, arr) => entry.contrast < 4.5 && arr.findIndex((candidate) => candidate.text === entry.text) === index)
      .slice(0, 30);

    const paleBoundaries = [...document.querySelectorAll('section, article, div, a, button')]
      .filter((el) => {
        const rect = el.getBoundingClientRect();
        if (rect.width < 120 || rect.height < 32 || rect.bottom < 0 || rect.top > viewportHeight * 1.6) return false;
        const style = getComputedStyle(el);
        const parsedBg = parseColor(style.backgroundColor);
        if (!parsedBg || parsedBg.alpha < 0.72) return false;
        const bg = parsedBg.rgb;
        const parentBg = el.parentElement ? effectiveBackground(el.parentElement) : null;
        const border = parseRgb(style.borderTopColor);
        if (!bg || !parentBg || !border) return false;
        const bgGap = Math.abs(lum(bg) - lum(parentBg));
        const borderGap = Math.abs(lum(border) - lum(bg));
        return bgGap < 0.018 && borderGap < 0.035 && style.borderTopWidth !== '0px';
      })
      .map((el) => ({
        text: shortText(el),
        tag: el.tagName.toLowerCase(),
        className: String(el.className || '').slice(0, 180),
      }))
      .slice(0, 30);

    const darkIslands = activeTheme === 'light'
      ? [...document.querySelectorAll('aside, header, section, article, div')]
        .filter((el) => {
          const rect = el.getBoundingClientRect();
          if (rect.width < 180 || rect.height < 60 || rect.bottom < 0 || rect.top > viewportHeight * 1.4) return false;
          const parsedBg = parseColor(getComputedStyle(el).backgroundColor);
          if (!parsedBg || parsedBg.alpha < 0.72) return false;
          const bg = parsedBg.rgb;
          return bg.every((value) => value <= 28);
        })
        .map((el) => ({
          text: shortText(el),
          tag: el.tagName.toLowerCase(),
          className: String(el.className || '').slice(0, 180),
        }))
        .slice(0, 30)
      : [];

    const tinyOrInvisibleText = [...document.querySelectorAll('body *')]
      .filter((el) => {
        const rect = el.getBoundingClientRect();
        const text = shortText(el);
        const style = getComputedStyle(el);
        return text && rect.width > 8 && rect.height > 8 && rect.bottom > 0 && rect.top < viewportHeight * 1.6 && Number.parseFloat(style.fontSize) <= 10;
      })
      .map((el) => ({
        text: shortText(el),
        tag: el.tagName.toLowerCase(),
        fontSize: getComputedStyle(el).fontSize,
        className: String(el.className || '').slice(0, 180),
      }))
      .slice(0, 30);

    return { textIssues, paleBoundaries, darkIslands, tinyOrInvisibleText };
  }, theme);
}

async function hoverAudit(page, theme, routeKey) {
  const candidates = await page.locator('button:visible, a:visible').evaluateAll((nodes) => nodes
    .map((node, index) => {
      const rect = node.getBoundingClientRect();
      const style = getComputedStyle(node);
      return {
        index,
        text: node.innerText?.replace(/\s+/g, ' ').trim().slice(0, 80) || node.getAttribute('title') || node.getAttribute('aria-label') || '',
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left,
        bg: style.backgroundColor,
        color: style.color,
        border: style.borderTopColor,
        shadow: style.boxShadow,
        transform: style.transform,
        opacity: style.opacity,
      };
    })
    .filter((item) => item.width >= 32 && item.height >= 24 && item.top >= 0 && item.top < window.innerHeight * 0.95)
    .slice(0, 12));

  const hoverIssues = [];
  const hoverShots = [];
  for (const candidate of candidates) {
    const locator = page.locator('button:visible, a:visible').nth(candidate.index);
    const before = await locator.evaluate((node) => {
      const style = getComputedStyle(node);
      return {
        bg: style.backgroundColor,
        color: style.color,
        border: style.borderTopColor,
        shadow: style.boxShadow,
        transform: style.transform,
        opacity: style.opacity,
        filter: style.filter,
      };
    }).catch(() => null);
    if (!before) continue;
    await locator.hover({ timeout: 2500 }).catch(() => {});
    await page.waitForTimeout(180);
    const after = await locator.evaluate((node) => {
      const style = getComputedStyle(node);
      return {
        bg: style.backgroundColor,
        color: style.color,
        border: style.borderTopColor,
        shadow: style.boxShadow,
        transform: style.transform,
        opacity: style.opacity,
        filter: style.filter,
      };
    }).catch(() => null);
    if (!after) continue;
    const changed = ['bg', 'color', 'border', 'shadow', 'transform', 'opacity', 'filter'].some((key) => before[key] !== after[key]);
    if (!changed && candidate.text) {
      hoverIssues.push({ text: candidate.text, index: candidate.index, before, after });
      if (hoverShots.length < 4) {
        const fileName = `${theme}_${routeKey}_hover_${hoverShots.length + 1}.png`;
        await page.screenshot({ path: path.join(shotDir, fileName), fullPage: false });
        hoverShots.push(fileName);
      }
    }
  }
  return { hoverIssues, hoverShots };
}

await fs.mkdir(shotDir, { recursive: true });

const executablePath = await firstExisting(browserCandidates);
const browser = await chromium.launch({ headless: true, executablePath });
const results = [];

for (const theme of ['dark', 'light']) {
  for (const scenario of scenarios) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, locale: 'ko-KR' });
    await setTheme(context, theme);
    const page = await context.newPage();
    page.on('pageerror', (error) => {
      results.push({ theme, scenario: scenario.key, route: 'pageerror', error: error.message });
    });

    if (scenario.authenticated) {
      await setupUserScenario(page).catch((error) => {
        results.push({ theme, scenario: scenario.key, route: 'setup', error: error.message });
      });
    }

    for (const route of routes) {
      const item = { theme, scenario: scenario.key, route: route.key, path: route.path };
      try {
        await page.goto(`${baseUrl}${route.path}`, { waitUntil: 'domcontentloaded', timeout: 45000 });
        await page.waitForLoadState('networkidle', { timeout: 9000 }).catch(() => {});
        await page.waitForTimeout(route.wait);
        item.h1 = await page.locator('h1').first().textContent({ timeout: 1200 }).catch(() => '');
        Object.assign(item, await auditVisibleUi(page, theme));
        Object.assign(item, await hoverAudit(page, theme, `${scenario.key}_${route.key}`));
        const fileName = `${theme}_${scenario.key}_${route.key}.png`;
        await page.screenshot({ path: path.join(shotDir, fileName), fullPage: true });
        item.screenshot = fileName;
      } catch (error) {
        item.error = error.message;
        const fileName = `${theme}_${scenario.key}_${route.key}_error.png`;
        await page.screenshot({ path: path.join(shotDir, fileName), fullPage: true }).catch(() => {});
        item.screenshot = fileName;
      }
      results.push(item);
    }

    await context.close();
  }
}

await browser.close();

const summary = {
  baseUrl,
  generatedAt: new Date().toISOString(),
  browserExecutable: executablePath || 'playwright bundled browser',
  routes,
  scenarios,
  results,
};

await fs.writeFile(path.join(outDir, 'visual_audit_result.json'), JSON.stringify(summary, null, 2), 'utf8');

const rows = results
  .filter((item) => item.route !== 'pageerror')
  .map((item) => ({
    theme: item.theme,
    route: item.scenario ? `${item.scenario}_${item.route}` : item.route,
    weak: item.textIssues?.length || 0,
    pale: item.paleBoundaries?.length || 0,
    dark: item.darkIslands?.length || 0,
    tiny: item.tinyOrInvisibleText?.length || 0,
    hover: item.hoverIssues?.length || 0,
    error: item.error || '',
  }));

await fs.writeFile(
  path.join(outDir, 'visual_audit_report.md'),
  [
    '# Visual Audit',
    '',
    `- Base URL: ${baseUrl}`,
    `- Generated: ${summary.generatedAt}`,
    `- Browser: ${summary.browserExecutable}`,
    '',
    '| Theme | Route | Weak Text | Pale Boundaries | Dark Islands | Tiny Text | Hover Issues | Error |',
    '| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |',
    ...rows.map((row) => `| ${row.theme} | ${row.route} | ${row.weak} | ${row.pale} | ${row.dark} | ${row.tiny} | ${row.hover} | ${row.error} |`),
  ].join('\n'),
  'utf8',
);

const totals = rows.reduce((acc, row) => {
  acc.weak += row.weak;
  acc.pale += row.pale;
  acc.dark += row.dark;
  acc.tiny += row.tiny;
  acc.hover += row.hover;
  return acc;
}, { weak: 0, pale: 0, dark: 0, tiny: 0, hover: 0 });

console.log(JSON.stringify({ outDir, screenshots: path.relative(process.cwd(), shotDir), totals }, null, 2));
