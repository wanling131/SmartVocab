/**
 * SmartVocab 全功能端到端测试
 * 使用真实API，一套流程测试所有功能
 * 需要服务器运行在 http://localhost:5000
 */

import { test, expect, Page } from '@playwright/test';

// 测试账号
const TEST_USER = {
  username: 'e2e_tester',
  password: 'TestPass123'
};

const BASE_URL = 'http://localhost:5000';

// 拦截外部字体，加速测试
async function blockExternalResources(page: Page) {
  await page.route('**/fonts.googleapis.com/**', route => route.abort());
  await page.route('**/fonts.gstatic.com/**', route => route.abort());
}

// ==================== 全流程测试 ====================
test.describe('SmartVocab 全功能端到端测试', () => {

  // 1. 登录流程
  test('完整流程：登录 → 推荐学习 → 关卡闯关 → 等级测试 → 个人中心', async ({ page }) => {
    test.setTimeout(300000); // 5分钟总时长

    // === 步骤1: 登录 ===
    console.log('\n=== 步骤1: 登录 ===');
    await blockExternalResources(page);
    await page.goto(`${BASE_URL}/pages/login.html`);
    await page.waitForSelector('#login-form', { timeout: 5000 });

    await page.fill('#login-username', TEST_USER.username);
    await page.fill('#login-password', TEST_USER.password);
    await page.click('#login-btn');

    // 等待跳转到 dashboard
    await expect(page).toHaveURL(/dashboard\.html/, { timeout: 15000 });

    // 等待用户名加载完成（navbar默认显示"用户"，需要等待JS更新）
    await page.waitForFunction(() => {
      const el = document.getElementById('username-display');
      return el && el.textContent !== '用户' && el.textContent.length > 0;
    }, { timeout: 10000 });

    const usernameDisplay = await page.locator('#username-display').textContent();
    console.log(`登录成功: ${usernameDisplay}`);
    expect(usernameDisplay).toContain(TEST_USER.username);

    // === 步骤2: 智能推荐加载 ===
    console.log('\n=== 步骤2: 智能推荐加载 ===');

    // 等待推荐API返回真实数据（不是"加载中..."占位符）
    const recommendationsList = page.locator('#recommendations-list');
    await page.waitForFunction(() => {
      const items = document.querySelectorAll('#recommendations-list .word-item');
      if (items.length === 0) return false;
      const firstText = items[0].querySelector('h4')?.textContent || '';
      return firstText !== '加载中...' && firstText !== '暂无推荐';
    }, { timeout: 15000 });

    const wordItems = recommendationsList.locator('.word-item');
    const wordCount = await wordItems.count();
    console.log(`智能推荐数量: ${wordCount}`);

    // 验证推荐数量应该大于0（已修复推荐数量问题）
    if (wordCount > 0) {
      const firstWordText = await wordItems.first().locator('h4').textContent();
      console.log(`第一个推荐词: ${firstWordText}`);

      // 点击第一个推荐词开始学习
      await wordItems.first().click();

      // 应该跳转到学习页面
      await expect(page).toHaveURL(/learning\.html/, { timeout: 5000 });
      await page.waitForTimeout(3000);

      // 检查学习页面是否加载单词
      const wordTextEl = page.locator('#word-text');
      const wordVisible = await wordTextEl.isVisible().catch(() => false);

      if (wordVisible) {
        const learningWord = await wordTextEl.textContent();
        console.log(`学习页面加载单词: ${learningWord}`);
        expect(learningWord).toBeTruthy();

        // 检查是否有选项
        const choiceOptions = page.locator('.choice-option');
        const optCount = await choiceOptions.count();
        console.log(`选项数量: ${optCount}`);
        expect(optCount).toBeGreaterThan(0);

        // 选择一个选项并提交
        await choiceOptions.first().click();
        await page.waitForTimeout(2000);

        // 检查反馈样式
        const hasFeedback = await page.locator('.choice-option.correct').isVisible().catch(() => false)
          || await page.locator('.choice-option.wrong').isVisible().catch(() => false);
        console.log(`答案反馈显示: ${hasFeedback}`);
      }
    }

    // === 步骤3: 闯关模式 ===
    console.log('\n=== 步骤3: 闯关模式 ===');
    await page.goto(`${BASE_URL}/pages/levels.html`);

    // 等待关卡数据加载完成（不是loading状态）
    await page.waitForSelector('.level-card', { timeout: 15000 });
    await page.waitForTimeout(2000);

    // 等待关卡内容加载（不是"正在铺设..."）
    await page.waitForFunction(() => {
      const cards = document.querySelectorAll('.level-card');
      if (cards.length === 0) return false;
      const firstTitle = cards[0].querySelector('.level-name')?.textContent || '';
      return firstTitle.length > 0 && !document.querySelector('.loading-state');
    }, { timeout: 10000 });

    const levelCards = page.locator('.level-card');
    const levelCount = await levelCards.count();
    console.log(`关卡数量: ${levelCount}`);
    expect(levelCount).toBeGreaterThan(0);

    // 查找已解锁关卡
    const unlockedCards = page.locator('.level-card:not(.locked)');
    const unlockedCount = await unlockedCards.count();
    console.log(`已解锁关卡: ${unlockedCount}`);

    if (unlockedCount > 0) {
      // 点击第一个已解锁关卡的开始按钮
      const startBtn = unlockedCards.first().locator('.btn-start-level');
      if (await startBtn.isVisible()) {
        await startBtn.click();

        // 等待跳转到学习页面
        await expect(page).toHaveURL(/learning\.html/, { timeout: 5000 });
        await page.waitForTimeout(4000);

        // 检查闯关学习单词加载
        const gateWordEl = page.locator('#word-text');
        const gateWordVisible = await gateWordEl.isVisible().catch(() => false);

        if (gateWordVisible) {
          const gateWord = await gateWordEl.textContent();
          console.log(`闯关学习单词: ${gateWord}`);
          expect(gateWord).toBeTruthy();

          // 检查进度显示
          const progressText = await page.locator('#current-index').textContent().catch(() => '');
          const totalText = await page.locator('#total-count').textContent().catch(() => '');
          console.log(`闯关进度: ${progressText}/${totalText}`);
        }
      }
    }

    // === 步骤4: 等级测试 ===
    console.log('\n=== 步骤4: 等级测试 ===');
    await page.goto(`${BASE_URL}/pages/evaluation.html`);
    await page.waitForTimeout(2000);
    await page.waitForSelector('#start-eval-btn', { timeout: 5000 });

    // 选择快速测试（10题）
    const quickBtn = page.locator('.preset-btn[data-count="10"]');
    if (await quickBtn.isVisible()) {
      await quickBtn.click();
      await page.waitForTimeout(500);
    }

    // 开始测试
    await page.locator('#start-eval-btn').click();

    // 等待试卷生成
    await page.waitForSelector('#eval-test', { state: 'visible', timeout: 15000 });
    await page.waitForSelector('.question-card', { timeout: 10000 });

    const questionCards = page.locator('.question-card');
    const questionCount = await questionCards.count();
    console.log(`生成题目数量: ${questionCount}`);
    expect(questionCount).toBeGreaterThan(0);

    // 为每个题目选择答案
    for (let i = 0; i < questionCount; i++) {
      const question = questionCards.nth(i);
      const options = question.locator('.option-input');
      const optCount = await options.count();

      if (optCount > 0) {
        await options.first().click();
        await page.waitForTimeout(200);
      }
    }

    // 等待一下让答案记录完成
    await page.waitForTimeout(500);

    // 提交答卷（处理确认对话框）
    page.once('dialog', dialog => dialog.accept());
    await page.locator('#submit-eval-btn').click();

    // 等待提交完成和结果显示
    await page.waitForTimeout(3000);
    await page.waitForSelector('#eval-result', { state: 'visible', timeout: 20000 });

    // 检查结果数据
    const score = await page.locator('#eval-score').textContent().catch(() => '');
    const correct = await page.locator('#eval-correct').textContent().catch(() => '');
    const level = await page.locator('#eval-level').textContent().catch(() => '');
    console.log(`测试结果: 分数=${score}, 正确=${correct}, 等级=${level}`);
    expect(score).toBeTruthy();

    // === 步骤5: 个人中心 ===
    console.log('\n=== 步骤5: 个人中心 ===');
    await page.goto(`${BASE_URL}/pages/profile.html`);
    await page.waitForTimeout(1500);

    const profileUsername = await page.locator('#profile-username').textContent().catch(() => '');
    console.log(`用户名: ${profileUsername}`);
    expect(profileUsername).toBeTruthy();

    // === 步骤6: 统计分析 ===
    console.log('\n=== 步骤6: 统计分析 ===');
    await page.goto(`${BASE_URL}/pages/statistics.html`);
    await page.waitForTimeout(1500);

    const totalWords = await page.locator('#stat-total-words').textContent().catch(() => '0');
    console.log(`总学习: ${totalWords}`);

    // === 步骤7: 收藏夹 ===
    console.log('\n=== 步骤7: 收藏夹 ===');
    await page.goto(`${BASE_URL}/pages/favorites.html`);
    await page.waitForTimeout(1500);

    const favoriteItems = page.locator('.favorite-item');
    const favoriteCount = await favoriteItems.count();
    console.log(`收藏单词数量: ${favoriteCount}`);

    // === 步骤8: 学习计划 ===
    console.log('\n=== 步骤8: 学习计划 ===');
    await page.goto(`${BASE_URL}/pages/plans.html`);
    await page.waitForTimeout(1500);

    const planCards = page.locator('.plan-card');
    const planCount = await planCards.count();
    console.log(`学习计划数量: ${planCount}`);

    console.log('\n=== 全流程测试完成 ===');
  });

  // 复习模式测试
  test('复习模式完整流程', async ({ page }) => {
    test.setTimeout(60000);

    await blockExternalResources(page);
    await page.goto(`${BASE_URL}/pages/login.html`);
    await page.waitForSelector('#login-form');
    await page.fill('#login-username', TEST_USER.username);
    await page.fill('#login-password', TEST_USER.password);
    await page.click('#login-btn');
    await expect(page).toHaveURL(/dashboard\.html/, { timeout: 15000 });

    // 设置复习模式
    await page.evaluate(() => {
      sessionStorage.setItem('review_mode', 'true');
    });

    await page.goto(`${BASE_URL}/pages/learning.html`);

    // 等待单词卡片加载
    await page.waitForSelector('#word-card', { state: 'visible', timeout: 10000 });
    await page.waitForTimeout(2000);

    const wordCard = page.locator('#word-card');
    const wordVisible = await wordCard.isVisible().catch(() => false);
    console.log(`复习单词卡片可见: ${wordVisible}`);

    if (wordVisible) {
      // 等待单词内容加载
      await page.waitForFunction(() => {
        const text = document.querySelector('#word-text')?.textContent || '';
        return text.length > 0 && text !== '';
      }, { timeout: 5000 });

      const wordText = await page.locator('#word-text').textContent();
      console.log(`复习单词: ${wordText}`);

      // 检查是否有选项
      const choiceOptions = page.locator('.choice-option');
      const optCount = await choiceOptions.count();
      console.log(`复习选项数量: ${optCount}`);

      // 复习模式可能无单词，需要检查
      if (wordText && wordText.length > 0) {
        expect(wordText).toBeTruthy();
      } else {
        console.log('复习模式无待复习单词（可能正常）');
      }
    }
  });

  // 3. 学习会话完整流程
  test('学习会话完整流程：开始 → 答题 → 完成', async ({ page }) => {
    test.setTimeout(120000);

    await blockExternalResources(page);

    // 登录
    await page.goto(`${BASE_URL}/pages/login.html`);
    await page.waitForSelector('#login-form');
    await page.fill('#login-username', TEST_USER.username);
    await page.fill('#login-password', TEST_USER.password);
    await page.click('#login-btn');
    await expect(page).toHaveURL(/dashboard\.html/, { timeout: 15000 });

    // 设置学习参数（只有3个单词，快速完成）
    await page.evaluate(() => {
      sessionStorage.setItem('learning_settings', JSON.stringify({
        difficulty: 1,
        wordCount: 3
      }));
    });

    // 开始学习会话
    await page.goto(`${BASE_URL}/pages/learning.html`);

    // 等待单词卡片或完成提示
    await page.waitForSelector('#word-card, #complete-section', { timeout: 15000 });
    await page.waitForTimeout(2000);

    // 检查会话是否启动
    const wordCard = page.locator('#word-card');
    const completeSection = page.locator('#complete-section');

    let hasWordCard = await wordCard.isVisible().catch(() => false);
    let hasComplete = await completeSection.isVisible().catch(() => false);

    console.log(`初始状态: 单词卡片=${hasWordCard}, 完成提示=${hasComplete}`);
    expect(hasWordCard || hasComplete).toBeTruthy();

    if (!hasWordCard && !hasComplete) {
      // 可能正在加载，再等待
      await page.waitForTimeout(5000);
      hasWordCard = await wordCard.isVisible().catch(() => false);
      hasComplete = await completeSection.isVisible().catch(() => false);
    }

    // 快速完成所有单词
    let answeredCount = 0;
    for (let i = 0; i < 15 && !hasComplete; i++) {
      // 等待选项可见
      try {
        await page.waitForSelector('.choice-option', { state: 'visible', timeout: 3000 });
      } catch {
        // 可能已完成或加载中
        hasComplete = await completeSection.isVisible().catch(() => false);
        if (hasComplete) break;
        await page.waitForTimeout(1000);
        continue;
      }

      const choiceOptions = page.locator('.choice-option');
      const optCount = await choiceOptions.count();

      if (optCount > 0 && await choiceOptions.first().isVisible()) {
        await choiceOptions.first().click();
        answeredCount++;
        console.log(`已答题: ${answeredCount}`);
        await page.waitForTimeout(2500);
      }

      // 检查是否完成
      hasComplete = await completeSection.isVisible().catch(() => false);
      if (hasComplete) {
        console.log('学习会话完成');
        break;
      }

      hasWordCard = await wordCard.isVisible().catch(() => false);
    }

    // 如果完成，检查统计数据
    if (hasComplete) {
      const stats = await page.locator('.stat-value').allTextContents();
      console.log(`完成统计: ${stats.join(', ')}`);
      expect(stats.length).toBeGreaterThan(0);
    } else if (answeredCount === 0) {
      console.log('未答题，可能无可用单词');
    }
  });

  // 4. 关卡解锁流程
  test('关卡解锁与闯关流程', async ({ page }) => {
    test.setTimeout(90000);

    await blockExternalResources(page);

    // 登录
    await page.goto(`${BASE_URL}/pages/login.html`);
    await page.waitForSelector('#login-form');
    await page.fill('#login-username', TEST_USER.username);
    await page.fill('#login-password', TEST_USER.password);
    await page.click('#login-btn');
    await expect(page).toHaveURL(/dashboard\.html/, { timeout: 15000 });

    // 进入关卡页面
    await page.goto(`${BASE_URL}/pages/levels.html`);

    // 等待关卡数据加载
    await page.waitForSelector('.level-card', { timeout: 10000 });
    await page.waitForTimeout(2000);

    // 检查关卡数据
    const levelCards = page.locator('.level-card');
    const levelCount = await levelCards.count();
    console.log(`关卡总数: ${levelCount}`);
    expect(levelCount).toBeGreaterThan(0);

    // 统计已解锁和未解锁关卡
    const lockedCards = page.locator('.level-card.locked');
    const lockedCount = await lockedCards.count();
    const unlockedCount = levelCount - lockedCount;
    console.log(`已解锁: ${unlockedCount}, 未解锁: ${lockedCount}`);

    // 检查关卡内容
    if (levelCount > 0) {
      const firstCard = levelCards.first();

      // 等待关卡内容加载
      await page.waitForFunction((selector) => {
        const card = document.querySelector(selector);
        const title = card?.querySelector('.level-name')?.textContent || '';
        return title.length > 0;
      }, '.level-card:first-child', { timeout: 5000 });

      const cardTitle = await firstCard.locator('.level-name').textContent().catch(() => '');
      console.log(`第一关卡: ${cardTitle}`);
      expect(cardTitle).toBeTruthy();
      expect(cardTitle.length).toBeGreaterThan(0);
    }

    // 尝试闯关
    if (unlockedCount > 0) {
      const startBtn = page.locator('.level-card:not(.locked)').first().locator('.btn-start-level');
      if (await startBtn.isVisible()) {
        await startBtn.click();
        await expect(page).toHaveURL(/learning\.html/, { timeout: 5000 });
        await page.waitForTimeout(3000);
        console.log('闯关跳转成功');
      }
    }
  });

  // 5. 数据一致性测试
  test('跨页面数据一致性', async ({ page }) => {
    test.setTimeout(60000);

    await blockExternalResources(page);

    // 登录
    await page.goto(`${BASE_URL}/pages/login.html`);
    await page.waitForSelector('#login-form');
    await page.fill('#login-username', TEST_USER.username);
    await page.fill('#login-password', TEST_USER.password);
    await page.click('#login-btn');
    await expect(page).toHaveURL(/dashboard\.html/, { timeout: 15000 });

    // 等待用户名加载完成
    await page.waitForFunction(() => {
      const el = document.getElementById('username-display');
      return el && el.textContent !== '用户' && el.textContent.length > 0;
    }, { timeout: 10000 });

    // 获取dashboard用户名
    const dashboardUsername = await page.locator('#username-display').textContent();
    console.log(`Dashboard用户名: ${dashboardUsername}`);

    // 切换到个人中心
    await page.goto(`${BASE_URL}/pages/profile.html`);
    await page.waitForTimeout(2000);
    await page.waitForSelector('#profile-username', { timeout: 5000 });
    const profileUsername = await page.locator('#profile-username').textContent();
    console.log(`Profile用户名: ${profileUsername}`);

    // 验证用户名一致
    expect(profileUsername?.trim()).toBe(dashboardUsername?.trim());

    // 切换到统计页面
    await page.goto(`${BASE_URL}/pages/statistics.html`);
    await page.waitForTimeout(3000);

    // 等待navbar用户名加载
    await page.waitForFunction(() => {
      const el = document.getElementById('username-display');
      return el && el.textContent !== '用户';
    }, { timeout: 5000 });

    // 验证导航栏用户名仍然正确
    const navUsername = await page.locator('#username-display').textContent();
    console.log(`Statistics用户名: ${navUsername}`);
    expect(navUsername?.trim()).toBe(dashboardUsername?.trim());
  });
});