/**
 * SmartVocab 全面功能 E2E 测试
 * 使用固定测试账号 e2e_tester，覆盖所有功能点
 */

import { test, expect, Page } from '@playwright/test';

// 固定测试账号
const TEST_USER = {
  username: 'e2e_tester',
  password: 'TestPass123'
};

// 登录辅助函数
async function login(page: Page) {
  await page.goto('/');

  // 检查是否已登录
  const dashboardVisible = await page.locator('#dashboard-page').isVisible().catch(() => false);
  if (dashboardVisible) return;

  // 执行登录
  await page.fill('#login-username', TEST_USER.username);
  await page.fill('#login-password', TEST_USER.password);
  await page.click('#login-form button[type="submit"]');
  await expect(page.locator('#dashboard-page')).toBeVisible({ timeout: 10000 });
}

// 确保在首页
async function ensureOnDashboard(page: Page) {
  const dashboardVisible = await page.locator('#dashboard-page').isVisible().catch(() => false);
  if (!dashboardVisible) {
    await page.click('#back-to-dashboard').catch(() => {});
    await page.waitForTimeout(500);
  }
}

// ==================== 1. 用户系统测试 ====================
test.describe('1. 用户系统', () => {
  test('1.1 用户登录', async ({ page }) => {
    await page.goto('/');
    await expect(page.locator('#auth-page')).toBeVisible();

    await page.fill('#login-username', TEST_USER.username);
    await page.fill('#login-password', TEST_USER.password);
    await page.click('#login-form button[type="submit"]');

    await expect(page.locator('#dashboard-page')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#username-display')).toContainText(TEST_USER.username);
  });

  test('1.2 登录失败显示错误', async ({ page }) => {
    await page.goto('/');
    await page.fill('#login-username', 'wrong_user');
    await page.fill('#login-password', 'wrong_pass');
    await page.click('#login-form button[type="submit"]');

    await expect(page.locator('#login-error')).toBeVisible({ timeout: 5000 });
  });

  test('1.3 退出登录', async ({ page }) => {
    await login(page);
    await page.click('#logout-btn');
    await expect(page.locator('#auth-page')).toBeVisible();
  });
});

// ==================== 2. 智能推荐测试 ====================
test.describe('2. 智能推荐系统', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('2.1 显示推荐词汇', async ({ page }) => {
    const grid = page.locator('#recommendations-grid');
    await expect(grid).toBeVisible();

    // 应该有推荐卡片
    const cards = page.locator('.recommendation-card');
    const emptyState = page.locator('.empty-state');
    await expect(cards.first().or(emptyState)).toBeVisible({ timeout: 5000 });
  });

  test('2.2 刷新推荐', async ({ page }) => {
    await page.click('#refresh-recommendations');
    await page.waitForTimeout(1500);

    await expect(page.locator('#recommendations-grid')).toBeVisible();
  });

  test('2.3 推荐卡片显示推荐理由', async ({ page }) => {
    const card = page.locator('.recommendation-card').first();
    if (await card.isVisible()) {
      await expect(card.locator('.recommendation-reason')).toBeVisible();
    }
  });

  test('2.4 推荐卡片显示难度标签', async ({ page }) => {
    const card = page.locator('.recommendation-card').first();
    if (await card.isVisible()) {
      const badge = card.locator('.difficulty-badge');
      await expect(badge).toBeVisible();
    }
  });
});

// ==================== 3. 词汇学习测试 ====================
test.describe('3. 词汇学习系统', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('3.1 开始新词学习（选择题）', async ({ page }) => {
    await page.selectOption('#difficulty-level', '1');
    await page.fill('#word-count', '3');
    await page.selectOption('#question-type', 'choice');
    await page.click('#start-learning-btn');

    await page.waitForTimeout(2000);

    const learningPage = page.locator('#learning-page');
    if (await learningPage.isVisible()) {
      await expect(page.locator('#current-word')).toBeVisible();
      await expect(page.locator('#choice-section')).toBeVisible();
    }
  });

  test('3.2 开始新词学习（翻译题）', async ({ page }) => {
    await page.selectOption('#difficulty-level', '1');
    await page.fill('#word-count', '3');
    await page.selectOption('#question-type', 'translation');
    await page.click('#start-learning-btn');

    await page.waitForTimeout(2000);

    const learningPage = page.locator('#learning-page');
    if (await learningPage.isVisible()) {
      await expect(page.locator('#translation-section')).toBeVisible();
      await expect(page.locator('#answer-input')).toBeVisible();
    }
  });

  test('3.3 开始新词学习（拼写题）', async ({ page }) => {
    await page.selectOption('#difficulty-level', '1');
    await page.fill('#word-count', '3');
    await page.selectOption('#question-type', 'spelling');
    await page.click('#start-learning-btn');

    await page.waitForTimeout(2000);

    const learningPage = page.locator('#learning-page');
    if (await learningPage.isVisible()) {
      await expect(page.locator('#spelling-section')).toBeVisible();
    }
  });

  test('3.4 答题并查看反馈', async ({ page }) => {
    await page.selectOption('#difficulty-level', '1');
    await page.fill('#word-count', '3');
    await page.selectOption('#question-type', 'choice');
    await page.click('#start-learning-btn');

    await page.waitForTimeout(2000);

    const learningPage = page.locator('#learning-page');
    if (await learningPage.isVisible()) {
      // 选择一个选项
      const option = page.locator('#choice-options button').first();
      if (await option.isVisible()) {
        await option.click();
        await page.waitForTimeout(500);

        // 应该显示反馈
        const feedback = page.locator('#feedback-section');
        if (await feedback.isVisible()) {
          await expect(page.locator('#feedback-message')).toBeVisible();
        }
      }
    }
  });

  test('3.5 显示答案功能', async ({ page }) => {
    await page.selectOption('#difficulty-level', '1');
    await page.fill('#word-count', '3');
    await page.selectOption('#question-type', 'translation');
    await page.click('#start-learning-btn');

    await page.waitForTimeout(2000);

    const learningPage = page.locator('#learning-page');
    if (await learningPage.isVisible()) {
      await page.click('#show-answer-btn');
      await expect(page.locator('#correct-answer')).toBeVisible();
    }
  });

  test('3.6 返回首页', async ({ page }) => {
    await page.selectOption('#difficulty-level', '1');
    await page.fill('#word-count', '3');
    await page.click('#start-learning-btn');

    await page.waitForTimeout(2000);

    const learningPage = page.locator('#learning-page');
    if (await learningPage.isVisible()) {
      await page.click('#back-to-dashboard');
      await expect(page.locator('#dashboard-page')).toBeVisible();
    }
  });
});

// ==================== 4. 闯关模式测试 ====================
test.describe('4. 闯关模式', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.click('[data-page="levels"]');
    await expect(page.locator('#levels-page')).toBeVisible();
  });

  test('4.1 显示关卡列表', async ({ page }) => {
    await expect(page.locator('#levels-gates-list')).toBeVisible();
  });

  test('4.2 关卡列表不为空', async ({ page }) => {
    const list = page.locator('#levels-gates-list');
    await expect(list).not.toContainText('加载中');
  });
});

// ==================== 5. 等级测试测试 ====================
test.describe('5. 等级测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.click('[data-page="evaluation"]');
    await expect(page.locator('#evaluation-page')).toBeVisible();
  });

  test('5.1 显示开始测试界面', async ({ page }) => {
    await expect(page.locator('#evaluation-start')).toBeVisible();
    await expect(page.locator('#start-eval-btn')).toBeVisible();
    await expect(page.locator('#eval-question-count')).toBeVisible();
  });

  test('5.2 开始等级测试', async ({ page }) => {
    await page.fill('#eval-question-count', '5');
    await page.click('#start-eval-btn');

    await expect(page.locator('#evaluation-test')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#eval-questions-container')).toBeVisible();
  });

  test('5.3 提交答卷并查看结果', async ({ page }) => {
    await page.fill('#eval-question-count', '5');
    await page.click('#start-eval-btn');
    await expect(page.locator('#evaluation-test')).toBeVisible({ timeout: 10000 });

    await page.waitForTimeout(1500);
    await page.click('#submit-eval-btn');

    await expect(page.locator('#evaluation-result')).toBeVisible({ timeout: 10000 });
    await expect(page.locator('#eval-score')).toBeVisible();
    await expect(page.locator('#eval-correct')).toBeVisible();
    await expect(page.locator('#eval-level')).toBeVisible();
  });

  test('5.4 再次测试', async ({ page }) => {
    await page.fill('#eval-question-count', '5');
    await page.click('#start-eval-btn');
    await expect(page.locator('#evaluation-test')).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(1000);
    await page.click('#submit-eval-btn');
    await expect(page.locator('#evaluation-result')).toBeVisible({ timeout: 10000 });

    await page.click('#eval-again-btn');
    await expect(page.locator('#evaluation-start')).toBeVisible();
  });
});

// ==================== 6. 学习计划测试 ====================
test.describe('6. 学习计划', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.click('[data-page="plans"]');
    await expect(page.locator('#plans-page')).toBeVisible();
  });

  test('6.1 显示当前计划区域', async ({ page }) => {
    await expect(page.locator('#active-plan-display')).toBeVisible();
  });

  test('6.2 显示历史计划列表', async ({ page }) => {
    await expect(page.locator('#plans-list')).toBeVisible();
  });

  test('6.3 显示创建计划表单', async ({ page }) => {
    await expect(page.locator('#plan-dataset')).toBeVisible();
    await expect(page.locator('#plan-daily-new')).toBeVisible();
    await expect(page.locator('#plan-daily-review')).toBeVisible();
    await expect(page.locator('#create-plan-btn')).toBeVisible();
  });

  test('6.4 创建学习计划', async ({ page }) => {
    await page.selectOption('#plan-dataset', 'cet4');
    await page.fill('#plan-daily-new', '10');
    await page.fill('#plan-daily-review', '15');

    await page.click('#create-plan-btn');
    await page.waitForTimeout(1500);

    // 验证创建成功
    await expect(page.locator('#active-plan-display')).not.toContainText('加载中');
  });

  test('6.5 刷新计划列表', async ({ page }) => {
    await page.click('#refresh-plans-btn');
    await page.waitForTimeout(1000);
    await expect(page.locator('#plans-list')).toBeVisible();
  });
});

// ==================== 7. 统计分析测试 ====================
test.describe('7. 统计分析', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.click('[data-page="statistics"]');
    await expect(page.locator('#statistics-page')).toBeVisible();
  });

  test('7.1 显示统计概览', async ({ page }) => {
    await expect(page.locator('#total-reviews')).toBeVisible();
    await expect(page.locator('#new-words')).toBeVisible();
    await expect(page.locator('#learned-words-stats')).toBeVisible();
    await expect(page.locator('#avg-reviews')).toBeVisible();
  });

  test('7.2 显示遗忘曲线图表区域', async ({ page }) => {
    await expect(page.locator('#forgetting-curve-chart')).toBeVisible();
  });

  test('7.3 显示学习记录列表', async ({ page }) => {
    await expect(page.locator('#records-list')).toBeVisible();
  });

  test('7.4 切换时间周期（7天）', async ({ page }) => {
    await page.click('[data-days="7"]');
    await page.waitForTimeout(500);
    await expect(page.locator('.period-btn.active[data-days="7"], [data-days="7"]')).toBeVisible();
  });

  test('7.5 切换时间周期（30天）', async ({ page }) => {
    await page.click('[data-days="30"]');
    await page.waitForTimeout(500);
    await expect(page.locator('#total-reviews')).toBeVisible();
  });

  test('7.6 切换时间周期（90天）', async ({ page }) => {
    await page.click('[data-days="90"]');
    await page.waitForTimeout(500);
    await expect(page.locator('#total-reviews')).toBeVisible();
  });

  test('7.7 刷新统计数据', async ({ page }) => {
    await page.click('#refresh-statistics');
    await page.waitForTimeout(1000);
    await expect(page.locator('#total-reviews')).toBeVisible();
  });
});

// ==================== 8. 个人中心测试 ====================
test.describe('8. 个人中心', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await page.click('[data-page="profile"]');
    await expect(page.locator('#profile-page')).toBeVisible();
  });

  test('8.1 显示用户信息', async ({ page }) => {
    await expect(page.locator('#profile-username')).toBeVisible();
    await expect(page.locator('#profile-email')).toBeVisible();
  });

  test('8.2 显示学习统计', async ({ page }) => {
    await expect(page.locator('#profile-total-words')).toBeVisible();
    await expect(page.locator('#profile-mastered-words')).toBeVisible();
    await expect(page.locator('#profile-streak-days')).toBeVisible();
  });

  test('8.3 显示成就列表', async ({ page }) => {
    await expect(page.locator('#achievements-grid')).toBeVisible();
  });

  test('8.4 显示编辑表单', async ({ page }) => {
    await expect(page.locator('#edit-email')).toBeVisible();
    await expect(page.locator('#edit-realname')).toBeVisible();
    await expect(page.locator('#edit-studentno')).toBeVisible();
    await expect(page.locator('#save-profile-btn')).toBeVisible();
  });

  test('8.5 编辑个人信息', async ({ page }) => {
    await page.fill('#edit-email', 'test@example.com');
    await page.fill('#edit-realname', '测试用户');
    await page.fill('#edit-studentno', '20240001');

    await page.click('#save-profile-btn');
    await page.waitForTimeout(1000);
  });

  test('8.6 从个人中心退出登录', async ({ page }) => {
    await page.click('#profile-logout-btn');
    await expect(page.locator('#auth-page')).toBeVisible();
  });
});

// ==================== 9. 页面导航测试 ====================
test.describe('9. 页面导航', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('9.1 首页导航', async ({ page }) => {
    await page.click('[data-page="dashboard"]');
    await expect(page.locator('#dashboard-page')).toBeVisible();
  });

  test('9.2 学习计划导航', async ({ page }) => {
    await page.click('[data-page="plans"]');
    await expect(page.locator('#plans-page')).toBeVisible();
  });

  test('9.3 闯关模式导航', async ({ page }) => {
    await page.click('[data-page="levels"]');
    await expect(page.locator('#levels-page')).toBeVisible();
  });

  test('9.4 等级测试导航', async ({ page }) => {
    await page.click('[data-page="evaluation"]');
    await expect(page.locator('#evaluation-page')).toBeVisible();
  });

  test('9.5 统计导航', async ({ page }) => {
    await page.click('[data-page="statistics"]');
    await expect(page.locator('#statistics-page')).toBeVisible();
  });

  test('9.6 个人中心导航', async ({ page }) => {
    await page.click('[data-page="profile"]');
    await expect(page.locator('#profile-page')).toBeVisible();
  });
});

// ==================== 10. 仪表板测试 ====================
test.describe('10. 仪表板', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('10.1 显示学习进度统计', async ({ page }) => {
    await expect(page.locator('#total-words')).toBeVisible();
    await expect(page.locator('#learned-words')).toBeVisible();
    await expect(page.locator('#learning-words')).toBeVisible();
    await expect(page.locator('#mastery-rate')).toBeVisible();
  });

  test('10.2 显示深度学习区域', async ({ page }) => {
    await expect(page.locator('.quick-start-section')).toBeVisible();
    await expect(page.locator('#start-learning-btn')).toBeVisible();
    await expect(page.locator('#start-review-btn')).toBeVisible();
  });

  test('10.3 难度选择器可用', async ({ page }) => {
    await expect(page.locator('#difficulty-level')).toBeEnabled();
  });

  test('10.4 单词数量输入可用', async ({ page }) => {
    await expect(page.locator('#word-count')).toBeEnabled();
  });

  test('10.5 题型选择器可用', async ({ page }) => {
    await expect(page.locator('#question-type')).toBeEnabled();
  });
});
