const { test, expect } = require('@playwright/test');

const baseUrl = process.env.BASE_URL || 'https://postal-philadelphia-disciplinary-finds.trycloudflare.com';

test('auth mode switch probe', async ({ page }) => {
  await page.goto(`${baseUrl}/auth`, { waitUntil: 'networkidle', timeout: 60000 });
  await page.screenshot({ path: 'docs/test/cloudflare_auth_before_switch.png', fullPage: true });
  console.log(await page.locator('body').innerText());
  const toggle = page.getByRole('button', { name: '계정이 없으면 회원가입' });
  console.log('toggle count', await toggle.count());
  await toggle.click({ force: true });
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'docs/test/cloudflare_auth_after_switch.png', fullPage: true });
  console.log(await page.locator('body').innerText());
  await expect(page.getByRole('heading', { name: '회원가입' })).toBeVisible();
});
