/**
 * 用户体验巡检 — 以真实用户视角浏览所有页面
 * 发现视觉问题、交互缺陷、加载状态异常
 */
import { test, expect } from '@playwright/test';

const BASE = 'http://localhost:5000';
const PAGES = `${BASE}/pages`;

test.describe('用户体验巡检', () => {

  // 统一登录：通过 API 拿 token 直接注入 localStorage
  test.beforeEach(async ({ page }) => {
    // 通过 API 登录获取 token
    const resp = await page.request.post(`${BASE}/api/auth/login`, {
      data: { username: 'e2e_tester', password: 'TestPass123' }
    });
    const body = await resp.json();
    const token = body.data?.token;

    // 注入 token 到 localStorage，然后访问页面时自动带上
    await page.goto(`${PAGES}/login.html`);
    await page.evaluate((t) => {
      localStorage.setItem('auth_token', t);
    }, token);
  });

  test('Dashboard — 首页体验', async ({ page }) => {
    await page.goto(`${PAGES}/dashboard.html`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'screenshots/ux-dashboard.png', fullPage: true });

    // 1. 导航栏存在
    const navbar = page.locator('.navbar');
    await expect(navbar).toBeVisible({ timeout: 8000 });

    // 2. 统计卡片
    const statCards = page.locator('.stat-card');
    await expect(statCards.first()).toBeVisible({ timeout: 8000 });
    const cardCount = await statCards.count();
    console.log(`Dashboard 统计卡片: ${cardCount}`);

    // 3. 推荐词汇列表
    const wordList = page.locator('#recommendations-list');
    await expect(wordList).toBeVisible({ timeout: 8000 });

    // 4. 无 "undefined" 显示文本（JS 代码中的 null 是正常的）
    const visibleText = await page.locator('body').innerText();
    expect(visibleText).not.toContain('undefined');

    await page.screenshot({ path: 'screenshots/ux-dashboard-loaded.png', fullPage: true });
  });

  test('Learning — 学习页面体验', async ({ page }) => {
    await page.goto(`${PAGES}/learning.html`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'screenshots/ux-learning.png', fullPage: true });

    const bodyText = await page.locator('body').textContent();
    expect(bodyText!.length).toBeGreaterThan(50);
  });

  test('Plans — 计划页面体验', async ({ page }) => {
    await page.goto(`${PAGES}/plans.html`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);
    await page.screenshot({ path: 'screenshots/ux-plans.png', fullPage: true });

    const activePlan = page.locator('#active-plan-display');
    await expect(activePlan).toBeVisible({ timeout: 8000 });

    const content = await activePlan.textContent();
    console.log(`计划区域内容: "${content?.substring(0, 80)}..."`);
    expect(content!.trim().length).toBeGreaterThan(5);

    await page.screenshot({ path: 'screenshots/ux-plans-loaded.png', fullPage: true });
  });

  test('Favorites — 收藏页面体验', async ({ page }) => {
    await page.goto(`${PAGES}/favorites.html`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);
    await page.screenshot({ path: 'screenshots/ux-favorites.png', fullPage: true });

    const grid = page.locator('#favorites-grid');
    const empty = page.locator('#favorites-empty');
    const gridVisible = await grid.isVisible().catch(() => false);
    const emptyVisible = await empty.isVisible().catch(() => false);
    expect(gridVisible || emptyVisible).toBeTruthy();
  });

  test('Levels — 闯关页面体验', async ({ page }) => {
    await page.goto(`${PAGES}/levels.html`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);
    await page.screenshot({ path: 'screenshots/ux-levels.png', fullPage: true });

    const levelsGrid = page.locator('#levels-grid');
    await expect(levelsGrid).toBeVisible({ timeout: 8000 });
  });

  test('Evaluation — 测试页面体验', async ({ page }) => {
    await page.goto(`${PAGES}/evaluation.html`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);
    await page.screenshot({ path: 'screenshots/ux-evaluation.png', fullPage: true });

    const startBtn = page.locator('#start-eval-btn');
    await expect(startBtn).toBeVisible({ timeout: 8000 });
  });

  test('Statistics — 统计页面体验', async ({ page }) => {
    await page.goto(`${PAGES}/statistics.html`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);
    await page.screenshot({ path: 'screenshots/ux-statistics.png', fullPage: true });

    const statWords = page.locator('#stat-words');
    await expect(statWords).toBeVisible({ timeout: 8000 });

    const canvases = page.locator('canvas');
    const canvasCount = await canvases.count();
    console.log(`统计页面 canvas 数量: ${canvasCount}`);

    await page.screenshot({ path: 'screenshots/ux-statistics-loaded.png', fullPage: true });
  });

  test('Profile — 个人页面体验', async ({ page }) => {
    await page.goto(`${PAGES}/profile.html`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);
    await page.screenshot({ path: 'screenshots/ux-profile.png', fullPage: true });

    const username = page.locator('#profile-username');
    await expect(username).toBeVisible({ timeout: 8000 });
    const usernameText = await username.textContent();
    expect(usernameText).not.toBe('加载中...');
    expect(usernameText!.trim().length).toBeGreaterThan(0);
    console.log(`用户名: "${usernameText}"`);
  });

  test('导航一致性检查', async ({ page }) => {
    await page.goto(`${PAGES}/dashboard.html`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(3000);

    const navLinks = page.locator('.nav-link');
    const count = await navLinks.count();
    console.log(`导航链接数量: ${count}`);

    for (let i = 0; i < Math.min(count, 7); i++) {
      const link = navLinks.nth(i);
      const href = await link.getAttribute('href');
      const text = await link.textContent();
      console.log(`导航 ${i}: ${text?.trim()} -> ${href}`);
    }
    expect(count).toBeGreaterThanOrEqual(7);
  });

  test('移动端响应式体验', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`${PAGES}/dashboard.html`);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(4000);
    await page.screenshot({ path: 'screenshots/ux-mobile-dashboard.png', fullPage: true });

    const navMenu = page.locator('.nav-menu');
    if (await navMenu.isVisible()) {
      console.log('移动端导航菜单可见');
    }

    const statCards = page.locator('.stat-card');
    const cardCount = await statCards.count();
    console.log(`移动端统计卡片数量: ${cardCount}`);
  });
});
