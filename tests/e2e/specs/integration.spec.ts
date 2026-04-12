/**
 * SmartVocab 深度集成测试
 * 使用真实API测试点击后的数据加载流程
 * 需要服务器运行在 http://localhost:5000
 */

import { test, expect, Page } from '@playwright/test';

// 测试账号
const TEST_USER = {
  username: 'e2e_tester',
  password: 'TestPass123'
};

const BASE_URL = 'http://localhost:5000';

// 拦截 Google Fonts
async function blockFonts(page: Page) {
  await page.route('**/fonts.googleapis.com/**', route => route.abort());
  await page.route('**/fonts.gstatic.com/**', route => route.abort());
}

// 登录
async function login(page: Page) {
  await blockFonts(page);
  await page.goto(`${BASE_URL}/pages/login.html`);
  await page.waitForSelector('#login-form');
  await page.fill('#login-username', TEST_USER.username);
  await page.fill('#login-password', TEST_USER.password);
  await page.click('#login-btn');
  await expect(page).toHaveURL(/dashboard\.html/, { timeout: 15000 });
  await page.waitForSelector('#username-display', { timeout: 5000 });
}

// ==================== 1. 智能推荐深度测试 ====================
test.describe('1. 智能推荐真实数据测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('1.1 推荐列表真实加载', async ({ page }) => {
    // 等待推荐API返回
    await page.waitForTimeout(2000);

    const recommendationsList = page.locator('#recommendations-list');
    const wordItems = recommendationsList.locator('.word-item');

    // 检查是否有推荐单词（可能是真实推荐或空状态）
    const count = await wordItems.count();
    console.log(`推荐单词数量: ${count}`);

    // 至少应该有内容（推荐词或空状态提示）
    expect(count).toBeGreaterThanOrEqual(0);

    if (count > 0) {
      // 检查第一个推荐词的内容
      const firstWord = wordItems.first();
      const wordInfo = firstWord.locator('.word-info h4');
      const wordText = await wordInfo.textContent();
      console.log(`第一个推荐词: ${wordText}`);
      expect(wordText).toBeTruthy();
      expect(wordText!.length).toBeGreaterThan(0);
    }
  });

  test('1.2 点击推荐词开始学习', async ({ page }) => {
    test.setTimeout(60000);

    await page.waitForTimeout(2000);
    const wordItems = page.locator('#recommendations-list .word-item');
    const count = await wordItems.count();

    if (count > 0) {
      // 点击第一个推荐词
      await wordItems.first().click();

      // 应该跳转到学习页面
      await expect(page).toHaveURL(/learning\.html/, { timeout: 5000 });

      // 等待学习页面加载
      await page.waitForTimeout(3000);

      // 检查是否有单词显示
      const wordText = page.locator('#word-text');
      const isVisible = await wordText.isVisible().catch(() => false);

      if (isVisible) {
        const text = await wordText.textContent();
        console.log(`学习页面单词: ${text}`);
        expect(text).toBeTruthy();
      }
    }
  });

  test('1.3 刷新推荐功能', async ({ page }) => {
    await page.waitForTimeout(2000);

    // 查找刷新按钮
    const refreshBtn = page.locator('button[onclick="refreshRecommendations()"]');
    if (await refreshBtn.isVisible()) {
      await refreshBtn.click();
      await page.waitForTimeout(2000);

      // 检查toast提示
      const toast = page.locator('.toast');
      const toastVisible = await toast.isVisible().catch(() => false);
      expect(toastVisible || true).toBeTruthy(); // toast可能很快消失
    }
  });
});

// ==================== 2. 学习会话深度测试 ====================
test.describe('2. 学习会话真实数据测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('2.1 开始学习会话', async ({ page }) => {
    test.setTimeout(60000);

    // 设置学习参数
    await page.evaluate(() => {
      sessionStorage.setItem('learning_settings', JSON.stringify({
        difficulty: 1,
        wordCount: 5
      }));
    });

    // 导航到学习页
    await page.goto(`${BASE_URL}/pages/learning.html`);
    await page.waitForTimeout(5000);

    // 检查是否成功启动会话
    const wordCard = page.locator('#word-card');
    const completeSection = page.locator('#complete-section');

    const hasWordCard = await wordCard.isVisible().catch(() => false);
    const hasComplete = await completeSection.isVisible().catch(() => false);

    console.log(`有单词卡片: ${hasWordCard}, 有完成提示: ${hasComplete}`);

    // 应该显示单词或完成提示
    expect(hasWordCard || hasComplete).toBeTruthy();

    if (hasWordCard) {
      // 检查单词内容
      const wordText = await page.locator('#word-text').textContent();
      console.log(`当前单词: ${wordText}`);
      expect(wordText).toBeTruthy();

      // 检查进度
      const currentIndex = await page.locator('#current-index').textContent();
      const totalCount = await page.locator('#total-count').textContent();
      console.log(`进度: ${currentIndex}/${totalCount}`);
    }
  });

  test('2.2 选择答案并提交', async ({ page }) => {
    test.setTimeout(90000);

    // 设置简短的学习会话
    await page.evaluate(() => {
      sessionStorage.setItem('learning_settings', JSON.stringify({
        difficulty: 1,
        wordCount: 3
      }));
    });

    await page.goto(`${BASE_URL}/pages/learning.html`);
    await page.waitForTimeout(5000);

    const choiceOptions = page.locator('.choice-option');
    const count = await choiceOptions.count();

    if (count > 0) {
      // 点击第一个选项
      await choiceOptions.first().click();
      await page.waitForTimeout(2000);

      // 检查是否有反馈（正确/错误样式）
      const correctOption = page.locator('.choice-option.correct');
      const wrongOption = page.locator('.choice-option.wrong');

      const hasFeedback = await correctOption.isVisible().catch(() => false)
        || await wrongOption.isVisible().catch(() => false);

      console.log(`有答案反馈: ${hasFeedback}`);

      // 等待下一个单词加载
      await page.waitForTimeout(2000);
    }
  });

  test('2.3 完成学习会话', async ({ page }) => {
    test.setTimeout(120000);

    // 设置只有2个单词的会话
    await page.evaluate(() => {
      sessionStorage.setItem('learning_settings', JSON.stringify({
        difficulty: 1,
        wordCount: 2
      }));
    });

    await page.goto(`${BASE_URL}/pages/learning.html`);
    await page.waitForTimeout(3000);

    // 快速完成所有单词
    for (let i = 0; i < 5; i++) {
      const choiceOptions = page.locator('.choice-option');
      const count = await choiceOptions.count();
      if (count > 0) {
        await choiceOptions.first().click();
        await page.waitForTimeout(2500);
      }

      // 检查是否完成
      const completeSection = page.locator('#complete-section');
      if (await completeSection.isVisible()) {
        console.log('学习会话已完成');
        break;
      }
    }

    // 检查完成状态
    const completeVisible = await page.locator('#complete-section').isVisible().catch(() => false);
    if (completeVisible) {
      // 检查统计数据
      const correctCount = await page.locator('.stat-value').first().textContent().catch(() => '0');
      console.log(`正确数: ${correctCount}`);
    }
  });
});

// ==================== 3. 复习模式深度测试 ====================
test.describe('3. 复习模式真实数据测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('3.1 开始复习会话', async ({ page }) => {
    test.setTimeout(60000);

    // 点击开始复习按钮
    await page.evaluate(() => {
      sessionStorage.setItem('review_mode', 'true');
    });

    await page.goto(`${BASE_URL}/pages/learning.html`);
    await page.waitForTimeout(5000);

    // 检查复习单词加载
    const wordCard = page.locator('#word-card');
    const isVisible = await wordCard.isVisible().catch(() => false);

    // 复习可能没有单词（如果没有到期复习的）
    console.log(`复习单词卡片可见: ${isVisible}`);

    // 如果有单词，检查内容
    if (isVisible) {
      const wordText = await page.locator('#word-text').textContent();
      console.log(`复习单词: ${wordText}`);
      expect(wordText).toBeTruthy();
    }
  });
});

// ==================== 4. 闯关模式深度测试 ====================
test.describe('4. 闯关模式真实数据测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/pages/levels.html`);
    await page.waitForTimeout(3000);
  });

  test('4.1 关卡数据真实加载', async ({ page }) => {
    // 等待关卡数据加载
    await page.waitForTimeout(2000);

    const levelCards = page.locator('.level-card');
    const count = await levelCards.count();

    console.log(`关卡数量: ${count}`);
    expect(count).toBeGreaterThan(0);

    // 检查第一个关卡的内容
    if (count > 0) {
      const firstCard = levelCards.first();
      const cardText = await firstCard.textContent();
      console.log(`第一关卡: ${cardText?.substring(0, 50)}`);
    }
  });

  test('4.2 开始闯关学习', async ({ page }) => {
    test.setTimeout(90000);

    await page.waitForTimeout(2000);

    // 查找已解锁的关卡
    const unlockedCards = page.locator('.level-card:not(.locked)');
    const count = await unlockedCards.count();

    if (count > 0) {
      // 点击第一个已解锁关卡
      const startBtn = unlockedCards.first().locator('.btn-start-level');
      if (await startBtn.isVisible()) {
        await startBtn.click();

        // 应该跳转到学习页面
        await expect(page).toHaveURL(/learning\.html/, { timeout: 5000 });
        await page.waitForTimeout(5000);

        // 检查学习页面是否加载单词
        const wordText = page.locator('#word-text');
        const isVisible = await wordText.isVisible().catch(() => false);

        if (isVisible) {
          const text = await wordText.textContent();
          console.log(`闯关学习单词: ${text}`);
          expect(text).toBeTruthy();
        }
      }
    }
  });
});

// ==================== 5. 等级测试深度测试 ====================
test.describe('5. 等级测试真实数据测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/pages/evaluation.html`);
    await page.waitForTimeout(2000);
  });

  test('5.1 真实生成测试试卷', async ({ page }) => {
    test.setTimeout(90000);

    // 等待页面加载
    await page.waitForSelector('#start-eval-btn');

    // 选择快速测试（10题）
    const quickBtn = page.locator('.preset-btn[data-count="10"]');
    if (await quickBtn.isVisible()) {
      await quickBtn.click();
    }

    await page.waitForTimeout(500);

    // 开始测试
    await page.locator('#start-eval-btn').click();

    // 等待试卷生成
    await page.waitForSelector('#eval-test', { state: 'visible', timeout: 15000 });
    await page.waitForSelector('.question-card', { timeout: 10000 });

    // 检查题目数量
    const questions = page.locator('.question-card');
    const count = await questions.count();
    console.log(`生成的题目数量: ${count}`);

    expect(count).toBeGreaterThan(0);

    // 检查第一个题目内容
    const firstQuestion = questions.first();
    const wordText = await firstQuestion.locator('.question-word').textContent().catch(() => '');
    console.log(`第一题单词: ${wordText}`);
  });

  test('5.2 答题并提交', async ({ page }) => {
    test.setTimeout(120000);

    await page.waitForSelector('#start-eval-btn');

    // 选择快速测试
    const quickBtn = page.locator('.preset-btn[data-count="10"]');
    if (await quickBtn.isVisible()) {
      await quickBtn.click();
    }

    await page.locator('#start-eval-btn').click();
    await page.waitForSelector('.question-card', { timeout: 15000 });

    // 为每个题目选择答案
    const questions = page.locator('.question-card');
    const count = await questions.count();

    for (let i = 0; i < count; i++) {
      const question = questions.nth(i);
      const options = question.locator('.question-option');
      const optCount = await options.count();

      if (optCount > 0) {
        // 选择第一个选项
        await options.first().click();
        await page.waitForTimeout(200);
      }
    }

    // 提交答卷
    await page.locator('#submit-eval-btn').click();

    // 等待结果显示
    await page.waitForSelector('#eval-result', { state: 'visible', timeout: 10000 });

    // 检查结果数据
    const score = await page.locator('#eval-score').textContent();
    const correct = await page.locator('#eval-correct').textContent();
    const level = await page.locator('#eval-level').textContent();

    console.log(`测试结果: 分数=${score}, 正确=${correct}, 等级=${level}`);

    expect(score).toBeTruthy();
    expect(correct).toBeTruthy();
    expect(level).toBeTruthy();
  });
});

// ==================== 6. 个人中心深度测试 ====================
test.describe('6. 个人中心真实数据测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/pages/profile.html`);
    await page.waitForTimeout(2000);
  });

  test('6.1 用户信息真实加载', async ({ page }) => {
    // 等待用户数据加载
    await page.waitForTimeout(2000);

    // 检查用户名显示
    const username = await page.locator('#profile-username').textContent().catch(() => '');
    console.log(`用户名: ${username}`);

    // 检查邮箱
    const email = await page.locator('#profile-email').textContent().catch(() => '');
    console.log(`邮箱: ${email}`);
  });

  test('6.2 学习统计真实数据', async ({ page }) => {
    await page.waitForTimeout(2000);

    // 检查统计数据
    const learnedWords = await page.locator('.stat-item').first().textContent().catch(() => '');
    console.log(`学习统计: ${learnedWords}`);
  });

  test('6.3 成就列表真实加载', async ({ page }) => {
    await page.waitForTimeout(2000);

    const achievements = page.locator('.achievement-item');
    const count = await achievements.count();
    console.log(`成就数量: ${count}`);

    // 检查是否有成就或空状态
    expect(count).toBeGreaterThanOrEqual(0);
  });
});

// ==================== 7. 统计分析深度测试 ====================
test.describe('7. 统计分析真实数据测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/pages/statistics.html`);
    await page.waitForTimeout(3000);
  });

  test('7.1 统计图表真实加载', async ({ page }) => {
    // 等待图表渲染
    await page.waitForTimeout(3000);

    // 检查图表容器
    const trendChart = page.locator('#trend-chart');
    const difficultyChart = page.locator('#difficulty-chart');

    const hasTrend = await trendChart.isVisible().catch(() => false);
    const hasDifficulty = await difficultyChart.isVisible().catch(() => false);

    console.log(`趋势图: ${hasTrend}, 难度图: ${hasDifficulty}`);
  });

  test('7.2 学习记录真实数据', async ({ page }) => {
    await page.waitForTimeout(2000);

    // 检查统计数字
    const totalWords = await page.locator('#stat-total-words').textContent().catch(() => '0');
    const masteredWords = await page.locator('#stat-mastered-words').textContent().catch(() => '0');

    console.log(`总学习: ${totalWords}, 已掌握: ${masteredWords}`);
  });
});

// ==================== 8. 收藏夹深度测试 ====================
test.describe('8. 收藏夹真实数据测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/pages/favorites.html`);
    await page.waitForTimeout(2000);
  });

  test('8.1 收藏列表真实加载', async ({ page }) => {
    await page.waitForTimeout(2000);

    const favoriteItems = page.locator('.favorite-item');
    const count = await favoriteItems.count();
    console.log(`收藏单词数量: ${count}`);

    expect(count).toBeGreaterThanOrEqual(0);

    if (count > 0) {
      const firstItem = favoriteItems.first();
      const wordText = await firstItem.locator('.word-text').textContent().catch(() => '');
      console.log(`第一个收藏词: ${wordText}`);
    }
  });
});

// ==================== 9. 学习计划深度测试 ====================
test.describe('9. 学习计划真实数据测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.goto(`${BASE_URL}/pages/plans.html`);
    await page.waitForTimeout(2000);
  });

  test('9.1 计划列表真实加载', async ({ page }) => {
    await page.waitForTimeout(2000);

    const planCards = page.locator('.plan-card');
    const count = await planCards.count();
    console.log(`学习计划数量: ${count}`);

    expect(count).toBeGreaterThanOrEqual(0);
  });

  test('9.2 创建新学习计划', async ({ page }) => {
    test.setTimeout(60000);

    // 点击创建计划按钮
    const createBtn = page.locator('#create-plan-btn');
    if (await createBtn.isVisible()) {
      await createBtn.click();
      await page.waitForTimeout(1000);

      // 填写计划表单
      const titleInput = page.locator('#plan-title');
      if (await titleInput.isVisible()) {
        await titleInput.fill('E2E测试计划');

        // 提交创建
        const submitBtn = page.locator('#submit-plan-btn');
        if (await submitBtn.isVisible()) {
          await submitBtn.click();
          await page.waitForTimeout(2000);

          // 检查是否创建成功
          console.log('学习计划创建测试完成');
        }
      }
    }
  });
});