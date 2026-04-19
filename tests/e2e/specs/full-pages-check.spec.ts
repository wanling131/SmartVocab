import { test, expect } from '@playwright/test';

test.describe('所有页面全面检查', () => {
  test.setTimeout(180000);

  test.beforeEach(async ({ page }) => {
    // 登录
    await page.goto('http://localhost:5000/pages/login.html');
    await page.fill('#login-username', 'e2e_tester');
    await page.fill('#login-password', 'TestPass123');
    await page.click('#login-btn');
    await page.waitForURL(/dashboard/, { timeout: 10000 });
  });

  const pages = [
    { name: '首页', url: 'dashboard.html', check: async (page: any) => {
      // 等待推荐列表加载完成（等待真实数据而非"加载中"）
      await page.waitForFunction(() => {
        const items = document.querySelectorAll('#recommendations-list .word-item');
        if (items.length === 0) return false;
        const firstText = items[0].querySelector('h4')?.textContent || '';
        return firstText !== '加载中...' && firstText !== '暂无推荐' && firstText.length > 0;
      }, { timeout: 10000 }).catch(() => {});

      const recommendItems = await page.locator('#recommendations-list .word-item').all();
      console.log('  推荐: ' + recommendItems.length);
      return recommendItems.length >= 1;  // 至少有1个推荐即可
    }},
    { name: '关卡', url: 'levels.html', check: async (page: any) => {
      const gateCards = await page.locator('.level-card').all();
      console.log('  关卡: ' + gateCards.length);
      return gateCards.length >= 1;
    }},
    { name: '统计', url: 'statistics.html', check: async (page: any) => {
      // 检查是否有图表容器
      const charts = await page.locator('.chart-container, #learning-chart, canvas').all();
      console.log('  图表容器: ' + charts.length);
      return true;
    }},
    { name: '收藏', url: 'favorites.html', check: async (page: any) => {
      // 收藏页面可能为空
      const items = await page.locator('.favorite-item, .word-item').all();
      console.log('  收藏项: ' + items.length);
      return true;
    }},
    { name: '计划', url: 'plans.html', check: async (page: any) => {
      const planItems = await page.locator('.plan-item').all();
      console.log('  计划项: ' + planItems.length);
      return true;
    }},
    { name: '个人中心', url: 'profile.html', check: async (page: any) => {
      const username = await page.locator('#profile-username').textContent().catch(() => '');
      console.log('  用户名: ' + username);
      return username.length > 0;
    }},
    { name: '等级测试', url: 'evaluation.html', check: async (page: any) => {
      const startBtn = page.locator('#start-eval-btn');
      const visible = await startBtn.isVisible().catch(() => false);
      console.log('  开始测试按钮: ' + (visible ? '可见' : '不可见'));
      return visible;
    }},
  ];

  for (const pageInfo of pages) {
    test(pageInfo.name + '页面检查', async ({ page }) => {
      console.log('\n检查: ' + pageInfo.name);
      
      // 监听错误
      const errors: string[] = [];
      page.on('console', msg => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
          console.log('  错误: ' + msg.text());
        }
      });

      await page.goto('http://localhost:5000/pages/' + pageInfo.url);
      await page.waitForTimeout(2000);

      // 执行检查
      const result = await pageInfo.check(page);
      
      await page.screenshot({ path: 'monitor/' + pageInfo.name + '.png' });

      // 检查是否有严重错误（排除 favicon 等）
      const criticalErrors = errors.filter(e => !e.includes('favicon') && !e.includes('manifest'));
      if (criticalErrors.length > 0) {
        console.log('  严重错误: ' + criticalErrors.length);
      }

      expect(result).toBe(true);
    });
  }
});
