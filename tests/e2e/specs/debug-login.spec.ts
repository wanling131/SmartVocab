import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5000';

test.describe('Debug Login', () => {
  test('token inject and navigate', async ({ page }) => {
    // 1. Get token via API
    const resp = await page.request.post(`${BASE}/api/auth/login`, {
      data: { username: 'e2e_tester', password: 'TestPass123' }
    });
    const body = await resp.json();
    console.log('Login response:', body.success, body.data?.token?.substring(0, 30));
    const token = body.data?.token;
    expect(token).toBeTruthy();

    // 2. Set token in localStorage on the correct origin
    await page.goto(`${BASE}/frontend/pages/dashboard.html`);

    // Inject token
    await page.evaluate((t) => {
      localStorage.setItem('auth_token', t);
    }, token);

    // Verify token is set
    const stored = await page.evaluate(() => localStorage.getItem('auth_token'));
    console.log('Stored token:', stored?.substring(0, 30));

    // 3. Reload the page so it picks up the token
    await page.reload();
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(5000);

    // Check current URL
    console.log('Current URL:', page.url());

    // Check for JS errors
    page.on('console', msg => {
      if (msg.type() === 'error') console.log('CONSOLE ERROR:', msg.text());
    });

    // Check page content
    const bodyText = await page.locator('body').textContent();
    console.log('Body text (first 200):', bodyText?.substring(0, 200));

    // Check if navbar exists
    const navbar = page.locator('.navbar');
    const navCount = await navbar.count();
    console.log('Navbar count:', navCount);

    // Check if redirected to login
    const currentUrl = page.url();
    console.log('Final URL:', currentUrl);

    await page.screenshot({ path: 'screenshots/debug-dashboard.png', fullPage: true });
  });
});
