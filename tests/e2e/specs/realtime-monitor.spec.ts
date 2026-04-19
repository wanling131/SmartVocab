import { test, expect } from '@playwright/test';

test.describe('实时监控 - 真实用户操作模拟', () => {
  test.setTimeout(300000);

  test('完整用户流程实时监控', async ({ page }) => {
    // 监听控制台错误
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
        console.log('浏览器错误: ' + msg.text());
      }
    });

    // 监听页面错误
    page.on('pageerror', err => {
      consoleErrors.push(err.message);
      console.log('页面错误: ' + err.message);
    });

    // 监听网络请求失败
    const failedRequests: string[] = [];
    page.on('requestfailed', req => {
      failedRequests.push(req.url());
      console.log('请求失败: ' + req.url());
    });

    console.log('\n========================================');
    console.log('开始实时监控用户操作');
    console.log('========================================\n');

    // ===== 步骤1: 登录 =====
    console.log('步骤1: 用户访问登录页面');
    await page.goto('http://localhost:5000/pages/login.html');
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'monitor/01-login-page.png' });

    console.log('   用户输入用户名和密码');
    await page.fill('#login-username', 'e2e_tester');
    await page.fill('#login-password', 'TestPass123');
    await page.waitForTimeout(500);

    console.log('   用户点击登录按钮');
    await page.click('#login-btn');

    // 等待跳转
    try {
      await page.waitForURL(/dashboard/, { timeout: 10000 });
      console.log('登录成功，跳转到首页');
    } catch {
      console.log('登录失败，未跳转到首页');
      await page.screenshot({ path: 'monitor/error-login.png' });
    }

    await page.screenshot({ path: 'monitor/02-dashboard.png' });

    // ===== 步骤2: 首页浏览 =====
    console.log('\n步骤2: 用户浏览首页');
    await page.waitForTimeout(2000);

    // 检查推荐加载
    console.log('   等待智能推荐加载...');
    await page.waitForFunction(() => {
      const items = document.querySelectorAll('#recommendations-list .word-item');
      if (items.length === 0) return false;
      const text = items[0].querySelector('h4')?.textContent || '';
      return text !== '加载中...' && text !== '暂无推荐' && text.length > 0;
    }, { timeout: 15000 }).catch(() => {
      console.log('推荐加载超时');
    });

    const recommendItems = await page.locator('#recommendations-list .word-item').all();
    console.log('   推荐单词数量: ' + recommendItems.length);

    if (recommendItems.length > 0) {
      const firstWord = await recommendItems[0].locator('h4').textContent() || '';
      console.log('   第一个推荐: ' + firstWord);
    }

    // 检查复习数量
    const reviewCount = await page.locator('#review-count').textContent().catch(() => '0');
    console.log('   待复习单词: ' + reviewCount);

    await page.screenshot({ path: 'monitor/03-dashboard-full.png', fullPage: true });

    // ===== 步骤3: 点击推荐学习 =====
    console.log('\n步骤3: 用户点击推荐单词开始学习');

    if (recommendItems.length > 0) {
      const homeWord = await recommendItems[0].locator('h4').textContent() || '';
      console.log('   点击单词: ' + homeWord);

      await recommendItems[0].click();
      await page.waitForURL(/learning/, { timeout: 10000 });
      await page.waitForTimeout(1500);

      const learningWord = await page.locator('#word-text').textContent() || '';
      console.log('   学习页面显示: ' + learningWord);

      // 检查一致性
      const isMatch = homeWord.toLowerCase().includes(learningWord.toLowerCase())
                      || learningWord.toLowerCase().includes(homeWord.toLowerCase().split(' ')[0]);
      if (isMatch) {
        console.log('单词一致性检查通过');
      } else {
        console.log('单词不一致! 首页=' + homeWord + ', 学习页=' + learningWord);
      }

      await page.screenshot({ path: 'monitor/04-learning-page.png' });

      // ===== 步骤4: 选择答案 =====
      console.log('\n步骤4: 用户选择答案');

      const choices = page.locator('.choice-option');
      const choiceCount = await choices.count();
      console.log('   选项数量: ' + choiceCount);

      if (choiceCount >= 4) {
        // 模拟用户思考
        await page.waitForTimeout(1000);

        // 点击第一个选项
        console.log('   用户选择第一个选项');
        await choices.first().click();
        await page.waitForTimeout(500);

        await page.screenshot({ path: 'monitor/05-answer-selected.png' });

        // 检查反馈
        const correctOption = page.locator('.choice-option.correct');
        const wrongOption = page.locator('.choice-option.wrong');

        if (await correctOption.isVisible().catch(() => false)) {
          console.log('答案正确，显示绿色反馈');
        } else if (await wrongOption.isVisible().catch(() => false)) {
          console.log('答案错误，显示红色反馈');
        }

        // 等待自动切换
        console.log('   等待自动切换到完成页面...');
        await page.waitForTimeout(4000);

        await page.screenshot({ path: 'monitor/06-after-answer.png' });

        // 检查完成页面
        const completeSection = page.locator('#complete-section');
        if (await completeSection.isVisible().catch(() => false)) {
          console.log('学习完成，显示完成页面');
          const accuracy = await page.locator('#final-accuracy').textContent() || '';
          console.log('   准确率: ' + accuracy);
        } else {
          console.log('完成页面未显示（可能还有更多单词）');
        }
      }
    }

    // ===== 步骤5: 返回首页测试刷新 =====
    console.log('\n步骤5: 用户返回首页测试刷新');
    await page.goto('http://localhost:5000/pages/dashboard.html');
    await page.waitForTimeout(3000);

    // 点击刷新按钮
    const refreshBtn = page.locator('button').filter({ hasText: '刷新' });
    if (await refreshBtn.isVisible().catch(() => false)) {
      console.log('   用户点击刷新按钮');
      await refreshBtn.click();
      await page.waitForTimeout(2000);

      // 检查 Toast
      const toast = page.locator('.toast');
      if (await toast.isVisible().catch(() => false)) {
        console.log('Toast 显示');
        await page.waitForTimeout(4000);
        if (await toast.isVisible().catch(() => false)) {
          console.log('Toast 未消失');
        } else {
          console.log('Toast 正常消失');
        }
      }

      await page.screenshot({ path: 'monitor/07-after-refresh.png' });
    }

    // ===== 步骤6: 测试关卡页面 =====
    console.log('\n步骤6: 用户访问关卡页面');
    await page.goto('http://localhost:5000/pages/levels.html');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'monitor/08-levels.png' });

    const gates = await page.locator('.gate-card').all();
    console.log('   关卡数量: ' + gates.length);

    // ===== 步骤7: 测试统计页面 =====
    console.log('\n步骤7: 用户访问统计页面');
    await page.goto('http://localhost:5000/pages/statistics.html');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'monitor/09-statistics.png' });

    // ===== 步骤8: 测试个人中心 =====
    console.log('\n步骤8: 用户访问个人中心');
    await page.goto('http://localhost:5000/pages/profile.html');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'monitor/10-profile.png' });

    // ===== 步骤9: 测试收藏页面 =====
    console.log('\n步骤9: 用户访问收藏页面');
    await page.goto('http://localhost:5000/pages/favorites.html');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'monitor/11-favorites.png' });

    // ===== 步骤10: 测试计划页面 =====
    console.log('\n步骤10: 用户访问计划页面');
    await page.goto('http://localhost:5000/pages/plans.html');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'monitor/12-plans.png' });

    // ===== 最终报告 =====
    console.log('\n========================================');
    console.log('监控结束 - 错误汇总');
    console.log('========================================');

    if (consoleErrors.length > 0) {
      console.log('控制台错误 (' + consoleErrors.length + '):');
      consoleErrors.forEach(e => console.log('   - ' + e));
    } else {
      console.log('无控制台错误');
    }

    if (failedRequests.length > 0) {
      console.log('请求失败 (' + failedRequests.length + '):');
      failedRequests.forEach(r => console.log('   - ' + r));
    } else {
      console.log('无请求失败');
    }

    console.log('\n测试完成!');
  });
});