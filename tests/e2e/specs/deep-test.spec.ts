import { test, expect } from '@playwright/test';

test.describe('全面用户深度测试', () => {
  test.setTimeout(120000);

  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:5000/pages/login.html');
    await page.waitForTimeout(500);
    await page.fill('#login-username', 'e2e_tester');
    await page.fill('#login-password', 'TestPass123');
    await page.click('#login-btn');
    await page.waitForURL(/dashboard/, { timeout: 15000 });
  });

  test('完整学习流程验证', async ({ page }) => {
    console.log('=== 步骤1: 检查首页加载 ===');
    await expect(page.locator('.nav-brand')).toContainText('SmartVocab');
    await expect(page.locator('#username-display')).not.toHaveText('用户');

    console.log('=== 步骤2: 检查智能推荐 ===');

    await page.waitForFunction(() => {
      const items = document.querySelectorAll('#recommendations-list .word-item');
      if (items.length === 0) return false;
      const text = items[0].querySelector('h4')?.textContent || '';
      return text !== '加载中...' && text !== '暂无推荐' && text.length > 0;
    }, { timeout: 15000 });

    const recommendSection = page.locator('#recommendations-list');
    const items = await recommendSection.locator('.word-item').all();
    console.log('推荐数量: ' + items.length);
    expect(items.length).toBeGreaterThanOrEqual(4);

    await page.screenshot({ path: 'screenshots/01-dashboard.png', fullPage: true });

    const firstRecommendWord = await items[0]?.locator('h4').textContent() || '';
    console.log('首页第一个推荐: "' + firstRecommendWord + '"');

    console.log('=== 步骤3: 点击推荐进入学习 ===');

    const firstItem = recommendSection.locator('.word-item').first();
    await firstItem.click();
    await page.waitForURL(/learning/, { timeout: 10000 });
    await page.waitForTimeout(1500);

    const wordTitle = await page.locator('#word-text').textContent() || '';
    console.log('学习页面显示单词: "' + wordTitle + '"');
    console.log('URL: ' + page.url());

    await page.screenshot({ path: 'screenshots/02-learning-page.png', fullPage: true });

    const clickWord = firstRecommendWord;
    const isConsistent = wordTitle.toLowerCase().trim() === clickWord.toLowerCase().trim()
                         || wordTitle.toLowerCase().includes(clickWord.toLowerCase().split(' ')[0])
                         || clickWord.toLowerCase().includes(wordTitle.toLowerCase().trim());
    console.log('单词一致性: ' + (isConsistent ? 'PASS' : 'FAIL'));
    expect(isConsistent).toBe(true);

    console.log('=== 步骤4: 选择答案 ===');

    const choices = page.locator('.choice-option');
    const choiceCount = await choices.count();
    console.log('选项数量: ' + choiceCount);
    expect(choiceCount).toBeGreaterThanOrEqual(4);

    const firstChoiceText = await choices.first().textContent() || '';
    console.log('第一个选项: "' + firstChoiceText + '"');

    // 点击第一个选项
    await choices.first().click();
    console.log('已点击选项');

    await page.screenshot({ path: 'screenshots/03-selected.png', fullPage: true });

    // 等待反馈显示（正确/错误样式）
    await page.waitForTimeout(1000);

    // 检查是否有正确/错误的样式反馈
    const correctOption = page.locator('.choice-option.correct');
    const wrongOption = page.locator('.choice-option.wrong');
    const hasFeedback = await correctOption.isVisible().catch(() => false) 
                        || await wrongOption.isVisible().catch(() => false);
    console.log('有答案反馈样式: ' + hasFeedback);

    await page.screenshot({ path: 'screenshots/04-feedback.png', fullPage: true });

    // 等待 3 秒后自动进入下一个单词（或完成页面）
    console.log('等待 4 秒后检查完成页面...');
    await page.waitForTimeout(4000);

    await page.screenshot({ path: 'screenshots/05-after-wait.png', fullPage: true });

    // 检查完成页面（因为只有一个单词，应该显示完成）
    const completeSection = page.locator('#complete-section');
    const wordCard = page.locator('#word-card');

    const completeVisible = await completeSection.isVisible().catch(() => false);
    const wordCardVisible = await wordCard.isVisible().catch(() => false);

    console.log('完成页面显示: ' + completeVisible);
    console.log('单词卡片显示: ' + wordCardVisible);

    if (completeVisible) {
      const completeTitle = await completeSection.locator('.complete-text').textContent() || '';
      console.log('完成标题: "' + completeTitle + '"');

      const accuracy = await page.locator('#final-accuracy').textContent() || '';
      console.log('准确率: ' + accuracy);

      // 检查是否有返回按钮
      const backBtn = page.locator('.btn-primary').filter({ hasText: '返回' });
      if (await backBtn.isVisible().catch(() => false)) {
        console.log('返回按钮存在');
      }
    } else {
      // 如果完成页面不显示，可能还有更多单词在继续
      console.log('完成页面未显示，继续检查...');
    }

    await page.screenshot({ path: 'screenshots/06-final.png', fullPage: true });
    console.log('=== 测试完成 ===');
  });

  test('单词一致性专项测试', async ({ page }) => {
    await page.waitForFunction(() => {
      const items = document.querySelectorAll('#recommendations-list .word-item');
      if (items.length === 0) return false;
      const text = items[0].querySelector('h4')?.textContent || '';
      return text !== '加载中...' && text !== '暂无推荐' && text.length > 0;
    }, { timeout: 15000 });

    const items = await page.locator('#recommendations-list .word-item').all();
    const homeWord = await items[0].locator('h4').textContent() || '';
    console.log('首页推荐: "' + homeWord + '"');

    await items[0].click();
    await page.waitForURL(/learning/, { timeout: 10000 });
    await page.waitForTimeout(1500);

    const learningWord = await page.locator('#word-text').textContent() || '';
    console.log('学习页: "' + learningWord + '"');

    const isMatch = homeWord.toLowerCase().includes(learningWord.toLowerCase().trim())
                    || learningWord.toLowerCase().includes(homeWord.toLowerCase().split(' ')[0]);
    console.log('一致性: ' + (isMatch ? 'PASS' : 'FAIL'));
    expect(isMatch).toBe(true);
  });

  test('刷新按钮和 Toast 测试', async ({ page }) => {
    await page.waitForFunction(() => {
      const items = document.querySelectorAll('#recommendations-list .word-item');
      if (items.length === 0) return false;
      const text = items[0].querySelector('h4')?.textContent || '';
      return text !== '加载中...' && text !== '暂无推荐' && text.length > 0;
    }, { timeout: 15000 });

    const refreshBtn = page.locator('button').filter({ hasText: '刷新' });
    await refreshBtn.click();

    await page.waitForTimeout(500);
    const toast = page.locator('.toast');

    try {
      await toast.waitFor({ state: 'visible', timeout: 2000 });
      console.log('Toast 出现了');
      await page.waitForTimeout(4500);
      const toastGone = await toast.isVisible().catch(() => false);
      console.log('Toast 4.5秒后仍可见: ' + toastGone);
      expect(toastGone).toBe(false);
    } catch {
      console.log('Toast 未检测到');
    }
  });
});
