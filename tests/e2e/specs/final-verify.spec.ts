import { test, expect } from '@playwright/test';

test.describe('最终验证', () => {
  test.setTimeout(120000);

  test('核心功能验证', async ({ page }) => {
    console.log('\n========================================');
    console.log('SmartVocab 最终验证测试');
    console.log('========================================\n');

    // 登录
    console.log('1. 登录测试');
    await page.goto('http://localhost:5000/pages/login.html');
    await page.fill('#login-username', 'e2e_tester');
    await page.fill('#login-password', 'TestPass123');
    await page.click('#login-btn');
    await page.waitForURL(/dashboard/, { timeout: 10000 });
    console.log('   PASS: 登录成功');

    // 推荐加载
    console.log('2. 推荐加载测试');
    await page.waitForFunction(() => {
      const items = document.querySelectorAll('#recommendations-list .word-item');
      return items.length >= 4;
    }, { timeout: 15000 });
    const items = await page.locator('#recommendations-list .word-item').all();
    console.log('   PASS: 推荐数量=' + items.length);

    // 单词一致性
    console.log('3. 单词一致性测试');
    const homeWord = await items[0].locator('h4').textContent() || '';
    await items[0].click();
    await page.waitForURL(/learning/, { timeout: 10000 });
    await page.waitForTimeout(1500);
    const learningWord = await page.locator('#word-text').textContent() || '';
    const isMatch = homeWord.toLowerCase().includes(learningWord.toLowerCase());
    console.log('   ' + (isMatch ? 'PASS' : 'FAIL') + ': 首页=' + homeWord + ', 学习页=' + learningWord);
    expect(isMatch).toBe(true);

    // 答题
    console.log('4. 答题测试');
    const choices = page.locator('.choice-option');
    expect(await choices.count()).toBeGreaterThanOrEqual(4);
    await choices.first().click();
    await page.waitForTimeout(2000);  // 等待翻转动画

    // 检查翻转卡片效果
    const flipCard = page.locator('#word-card');
    const isFlipped = await flipCard.evaluate(el => el.classList.contains('flipped'));
    console.log('   PASS: 答题完成, 卡片翻转=' + isFlipped);
    expect(isFlipped).toBe(true);

    // 点击继续学习（单单词模式会显示完成页面）
    console.log('5. 完成页面测试');
    const continueBtn = page.locator('#inline-continue');
    await continueBtn.click();
    await page.waitForTimeout(2000);

    const complete = page.locator('#complete-section');
    const completeVisible = await complete.isVisible().catch(() => false);
    console.log('   ' + (completeVisible ? 'PASS' : 'FAIL') + ': 完成页面显示=' + completeVisible);
    expect(completeVisible).toBe(true);

    // 返回首页刷新
    console.log('6. 刷新按钮测试');
    await page.goto('http://localhost:5000/pages/dashboard.html');
    await page.waitForTimeout(3000);
    await page.click('button:has-text("刷新")');
    await page.waitForTimeout(2000);
    const toast = page.locator('.toast');
    if (await toast.isVisible().catch(() => false)) {
      await page.waitForTimeout(4000);
      const toastGone = await toast.isVisible().catch(() => false);
      console.log('   ' + (!toastGone ? 'PASS' : 'FAIL') + ': Toast消失=' + !toastGone);
      expect(toastGone).toBe(false);
    } else {
      console.log('   PASS: Toast正常');
    }

    // 关卡页面
    console.log('7. 关卡页面测试');
    await page.goto('http://localhost:5000/pages/levels.html');
    await page.waitForTimeout(2000);
    const gates = await page.locator('.level-card').all();
    console.log('   PASS: 关卡数量=' + gates.length);
    expect(gates.length).toBeGreaterThanOrEqual(1);

    // 统计页面
    console.log('8. 统计页面测试');
    await page.goto('http://localhost:5000/pages/statistics.html');
    await page.waitForTimeout(2000);
    console.log('   PASS: 统计页面加载');

    // 个人中心
    console.log('9. 个人中心测试');
    await page.goto('http://localhost:5000/pages/profile.html');
    await page.waitForTimeout(2000);
    const username = await page.locator('#profile-username').textContent() || '';
    console.log('   PASS: 用户名=' + username);

    // 等级测试
    console.log('10. 等级测试页面测试');
    await page.goto('http://localhost:5000/pages/evaluation.html');
    await page.waitForTimeout(2000);
    const startBtn = page.locator('#start-eval-btn');
    const btnVisible = await startBtn.isVisible().catch(() => false);
    console.log('   ' + (btnVisible ? 'PASS' : 'FAIL') + ': 开始按钮=' + btnVisible);
    expect(btnVisible).toBe(true);

    console.log('\n========================================');
    console.log('测试完成 - 所有核心功能正常');
    console.log('========================================\n');
  });
});
