import { test, expect } from '@playwright/test';

test.describe('关卡页面检查', () => {
  test.setTimeout(60000);

  test('关卡 API 和渲染检查', async ({ page }) => {
    // 监听网络请求
    const apiResults: { url: string; status: number; data: any }[] = [];
    page.on('response', async response => {
      if (response.url().includes('/api/levels/')) {
        try {
          const data = await response.json();
          apiResults.push({ url: response.url(), status: response.status(), data });
          console.log('API: ' + response.url() + ' => ' + response.status());
          if (data.data) {
            console.log('数据数量: ' + (Array.isArray(data.data) ? data.data.length : '非数组'));
          }
        } catch {}
      }
    });

    // 登录
    await page.goto('http://localhost:5000/pages/login.html');
    await page.fill('#login-username', 'e2e_tester');
    await page.fill('#login-password', 'TestPass123');
    await page.click('#login-btn');
    await page.waitForURL(/dashboard/, { timeout: 10000 });

    // 跳转到关卡页面
    console.log('\n访问关卡页面');
    await page.goto('http://localhost:5000/pages/levels.html');
    await page.waitForTimeout(3000);

    // 检查 API 结果
    console.log('\n关卡 API 结果:');
    apiResults.forEach(r => {
      console.log('  ' + r.url);
      console.log('  状态: ' + r.status);
      if (r.data && r.data.data) {
        console.log('  数据: ' + JSON.stringify(r.data.data).substring(0, 200));
      }
    });

    // 检查渲染的关卡卡片
    const gateCards = await page.locator('.level-card, .gate-card').all();
    console.log('\n渲染的关卡卡片数量: ' + gateCards.length);

    // 检查空状态
    const emptyState = page.locator('.empty-state');
    if (await emptyState.isVisible().catch(() => false)) {
      console.log('显示空状态');
    }

    await page.screenshot({ path: 'monitor/levels-check.png' });

    // 如果 API 返回了数据但渲染为空，说明有问题
    const levelsApi = apiResults.find(r => r.url.includes('/gates/'));
    if (levelsApi && levelsApi.data && levelsApi.data.data && levelsApi.data.data.length > 0) {
      if (gateCards.length === 0) {
        console.log('问题: API 返回数据但页面未渲染');
        // 检查是否有渲染错误
        const errorText = await page.locator('.error-message').textContent().catch(() => '');
        if (errorText) {
          console.log('错误消息: ' + errorText);
        }
      }
    }
  });
});
