const { test } = require('@playwright/test');

const baseUrl = process.env.BASE_URL || 'https://postal-philadelphia-disciplinary-finds.trycloudflare.com';

test('probe deployed FirstHome page structure', async ({ page }) => {
  const logs = [];
  page.on('console', (msg) => {
    if (['error', 'warning'].includes(msg.type())) logs.push(`[console:${msg.type()}] ${msg.text()}`);
  });
  page.on('pageerror', (err) => logs.push(`[pageerror] ${err.message}`));
  page.on('requestfailed', (req) => logs.push(`[requestfailed] ${req.method()} ${req.url()} ${req.failure()?.errorText}`));
  page.on('response', (res) => {
    if (res.status() >= 400) logs.push(`[response:${res.status()}] ${res.url()}`);
  });

  await page.goto(baseUrl, { waitUntil: 'networkidle', timeout: 60000 });
  await page.screenshot({ path: 'docs/test/cloudflare_probe_home.png', fullPage: true });

  const bodyText = await page.locator('body').innerText({ timeout: 10000 });
  const buttons = await page.locator('button').evaluateAll((els) => els.slice(0, 80).map((el) => el.innerText.trim()).filter(Boolean));
  const links = await page.locator('a').evaluateAll((els) => els.slice(0, 80).map((el) => ({ text: el.innerText.trim(), href: el.href })).filter((x) => x.text || x.href));
  const inputs = await page.locator('input, select, textarea').evaluateAll((els) => els.slice(0, 80).map((el) => ({
    tag: el.tagName,
    type: el.getAttribute('type'),
    placeholder: el.getAttribute('placeholder'),
    value: el.value,
    name: el.getAttribute('name'),
    aria: el.getAttribute('aria-label'),
  })));

  console.log(JSON.stringify({
    title: await page.title(),
    url: page.url(),
    bodySnippet: bodyText.slice(0, 2000),
    buttons,
    links,
    inputs,
    logs,
  }, null, 2));
});
