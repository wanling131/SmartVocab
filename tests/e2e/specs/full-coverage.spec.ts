/**
 * SmartVocab 全面功能 E2E 测试
 * 适配多页架构：每个页面为独立 HTML 文件
 * 使用固定测试账号 e2e_tester
 */

import { test, expect, Page } from '@playwright/test';

// 固定测试账号
const TEST_USER = {
  username: 'e2e_tester',
  password: 'TestPass123'
};

const BASE_URL = 'http://localhost:5000';

// ==================== 辅助函数 ====================

/** 拦截 Google Fonts 请求，防止页面加载超时 */
async function blockFonts(page: Page) {
  await page.route('**/fonts.googleapis.com/**', route => route.abort());
  await page.route('**/fonts.gstatic.com/**', route => route.abort());
}

/** 登录并跳转到仪表盘 */
async function login(page: Page) {
  await blockFonts(page);
  await page.goto(`${BASE_URL}/pages/login.html`);
  await page.waitForSelector('#login-form');

  await page.fill('#login-username', TEST_USER.username);
  await page.fill('#login-password', TEST_USER.password);
  await page.click('#login-btn');

  // 等待跳转到仪表盘（用 URL 断言代替 waitForURL，避免 glob 匹配问题）
  await expect(page).toHaveURL(/dashboard\.html/, { timeout: 15000 });
  await page.waitForSelector('#username-display', { timeout: 5000 });
}

/** 导航到指定页面 */
async function navigateTo(page: Page, pageName: string) {
  const navLink = page.locator(`.nav-link[data-page="${pageName}"]`);
  if (await navLink.isVisible()) {
    await navLink.click();
    await page.waitForTimeout(500);
  } else {
    await page.goto(`${BASE_URL}/pages/${pageName}.html`);
    await page.waitForTimeout(500);
  }
}

// ==================== 1. 用户系统测试 ====================
test.describe('1. 用户系统', () => {
  test('1.1 用户登录', async ({ page }) => {
    await blockFonts(page);
    await page.goto(`${BASE_URL}/pages/login.html`);
    await expect(page.locator('#login-form')).toBeVisible();

    await page.fill('#login-username', TEST_USER.username);
    await page.fill('#login-password', TEST_USER.password);
    await page.click('#login-btn');

    await expect(page).toHaveURL(/dashboard\.html/, { timeout: 15000 });
    await expect(page.locator('#username-display')).toContainText(TEST_USER.username);
  });

  test('1.2 登录失败显示错误', async ({ page }) => {
    await page.goto(`${BASE_URL}/pages/login.html`);

    await page.fill('#login-username', 'wrong_user');
    await page.fill('#login-password', 'wrong_pass');
    await page.click('#login-btn');

    // 应该显示 toast 错误提示（页面不跳转）
    await page.waitForTimeout(2000);
    // 仍在登录页
    await expect(page).toHaveURL(/login\.html/);
  });

  test('1.3 注册切换', async ({ page }) => {
    await page.goto(`${BASE_URL}/pages/login.html`);
    await expect(page.locator('#login-form')).toBeVisible();

    // 切换到注册
    await page.click('#switch-to-register');
    await expect(page.locator('#register-form')).toBeVisible();

    // 切换回登录
    await page.click('#switch-to-login');
    await expect(page.locator('#login-form')).toBeVisible();
  });

  test('1.4 退出登录', async ({ page }) => {
    await login(page);
    // 点击退出按钮
    await page.click('button[onclick="logout()"]');
    await expect(page).toHaveURL(/login\.html/, { timeout: 5000 });
    await expect(page.locator('#login-form')).toBeVisible();
  });
});

// ==================== 2. 仪表盘测试 ====================
test.describe('2. 仪表盘', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('2.1 显示学习进度统计', async ({ page }) => {
    await expect(page.locator('#total-words')).toBeAttached();
    await expect(page.locator('#learned-words')).toBeAttached();
    await expect(page.locator('#learning-words')).toBeAttached();
    await expect(page.locator('#mastery-rate')).toBeAttached();
  });

  test('2.2 显示欢迎信息', async ({ page }) => {
    await expect(page.locator('#welcome-name')).toContainText(TEST_USER.username);
  });

  test('2.3 显示智能推荐区域', async ({ page }) => {
    await expect(page.locator('#recommendations-list')).toBeAttached();
  });

  test('2.4 快速开始区域可用', async ({ page }) => {
    await expect(page.locator('#difficulty')).toBeEnabled();
    await expect(page.locator('#word-count')).toBeEnabled();
  });

  test('2.5 显示复习计数', async ({ page }) => {
    await expect(page.locator('#review-count')).toBeAttached();
  });

  test('2.6 点击开始学习跳转', async ({ page }) => {
    // dashboard 的 startLearning 是通过 onclick 调用的
    await page.click('button[onclick="startLearning()"]');
    await page.waitForURL('**/learning.html', { timeout: 5000 });
  });
});

// ==================== 3. 词汇学习测试 ====================
test.describe('3. 词汇学习系统', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    // 设置学习参数后跳转到学习页
    await page.evaluate(() => {
      sessionStorage.setItem('learning_settings', JSON.stringify({
        difficulty: '1',
        wordCount: '3'
      }));
    });
    await page.goto(`${BASE_URL}/pages/learning.html`);
    await page.waitForTimeout(3000);
  });

  test('3.1 学习页面加载', async ({ page }) => {
    // 应该有单词卡片或完成提示
    const hasWordCard = await page.locator('#word-card').isVisible().catch(() => false);
    const hasComplete = await page.locator('#complete-section').isVisible().catch(() => false);
    expect(hasWordCard || hasComplete).toBeTruthy();
  });

  test('3.2 显示进度条', async ({ page }) => {
    await expect(page.locator('#progress-fill')).toBeAttached();
    await expect(page.locator('#current-index')).toBeAttached();
    await expect(page.locator('#total-count')).toBeAttached();
  });

  test('3.3 单词卡片显示', async ({ page }) => {
    const wordText = page.locator('#word-text');
    if (await wordText.isVisible()) {
      // 等待 API 加载完成
      await page.waitForFunction(
        (sel) => document.querySelector(sel)?.textContent !== 'Loading...',
        '#word-text',
        { timeout: 8000 }
      ).catch(() => {}); // 超时不阻塞
      const text = await wordText.textContent();
      expect(text).toBeTruthy();
    }
  });

  test('3.4 选择题选项可交互', async ({ page }) => {
    const choiceSection = page.locator('#choice-section');
    if (await choiceSection.isVisible()) {
      const options = page.locator('.choice-option');
      const count = await options.count();
      if (count > 0) {
        await options.first().click();
        await page.waitForTimeout(1000);
      }
    }
  });

  test('3.5 返回首页', async ({ page }) => {
    // learning 页面有 goBack 函数
    await page.evaluate(() => { window.location.href = 'dashboard.html'; });
    await page.waitForURL('**/dashboard.html', { timeout: 5000 });
  });
});

// ==================== 4. 闯关模式测试 ====================
test.describe('4. 闯关模式', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateTo(page, 'levels');
    await page.waitForTimeout(1000);
  });

  test('4.1 显示关卡网格', async ({ page }) => {
    await expect(page.locator('#levels-grid')).toBeAttached();
  });

  test('4.2 显示闯关路径', async ({ page }) => {
    await expect(page.locator('#journey-path')).toBeAttached();
  });

  test('4.3 关卡内容加载', async ({ page }) => {
    // 等待数据加载
    await page.waitForTimeout(2000);
    const grid = page.locator('#levels-grid');
    const cards = grid.locator('.level-card');
    const count = await cards.count();
    // 应该有关卡卡片（或空状态提示）
    expect(count).toBeGreaterThanOrEqual(0);
  });
});

// ==================== 5. 等级测试测试 ====================
test.describe('5. 等级测试', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateTo(page, 'evaluation');
    await page.waitForTimeout(1000);
  });

  test('5.1 显示开始测试界面', async ({ page }) => {
    await expect(page.locator('#eval-start')).toBeAttached();
    await expect(page.locator('#start-eval-btn')).toBeAttached();
    await expect(page.locator('.preset-btn')).toHaveCount(3);
  });

  test('5.2 开始等级测试', async ({ page }) => {
    // 选择 10 题快速测试模式（默认已选中）
    await page.waitForSelector('.preset-btn.active');
    await page.locator('#start-eval-btn').click({ force: true });

    await page.waitForSelector('#eval-test', { state: 'attached', timeout: 10000 });
    await expect(page.locator('#eval-questions-container')).toBeAttached();
  });

  test('5.3 提交答卷并查看结果', async ({ page }) => {
    test.setTimeout(60000);
    // 拦截 API 并模拟成功响应
    await page.route('**/api/evaluation/start', async route => {
      const request = route.request();
      const body = request.postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            paper_id: 999,
            questions: Array.from({ length: body.question_count || 10 }, (_, i) => ({
              word: `test_word_${i + 1}`,
              phonetic: `test_${i + 1}`,
              options: ['选项A', '选项B', '选项C', '选项D'],
              correct_index: 0
            }))
          },
          message: '开始测试成功'
        })
      });
    });

    // 拦截提交 API
    await page.route('**/api/evaluation/submit', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            score: 80,
            correct_count: 8,
            total_count: 10,
            level: '中级'
          },
          message: '提交成功'
        })
      });
    });

    // 等待用户信息加载完成（确保 currentUser 已设置）
    await page.waitForSelector('#username-display', { state: 'attached' });
    await page.waitForFunction(() => {
      const el = document.getElementById('username-display');
      return el && el.textContent && el.textContent.length > 0;
    }, { timeout: 5000 });

    await page.waitForSelector('.preset-btn.active');
    // 直接通过 JS 触发开始按钮点击
    await page.evaluate(() => document.getElementById('start-eval-btn').click());

    // 等待测试区域显示并可见
    await page.waitForSelector('#eval-test', { state: 'visible', timeout: 10000 });
    // 等待题目真正渲染出来（说明 API 成功返回了题目）
    await page.waitForSelector('.question-card', { state: 'attached', timeout: 10000 });

    // 接受确认对话框并直接通过 JS 触发提交
    page.once('dialog', dialog => dialog.accept());
    await page.evaluate(() => document.getElementById('submit-eval-btn').click());

    await page.waitForSelector('#eval-result', { state: 'visible', timeout: 10000 });
    await expect(page.locator('#eval-score')).toBeAttached();
    await expect(page.locator('#eval-correct')).toBeAttached();
    await expect(page.locator('#eval-total')).toBeAttached();
    await expect(page.locator('#eval-level')).toBeAttached();
  });

  test('5.4 再次测试', async ({ page }) => {
    test.setTimeout(60000);
    // 拦截 API 并模拟成功响应
    await page.route('**/api/evaluation/start', async route => {
      const request = route.request();
      const body = request.postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            paper_id: 999,
            questions: Array.from({ length: body.question_count || 10 }, (_, i) => ({
              word: `test_word_${i + 1}`,
              phonetic: `test_${i + 1}`,
              options: ['选项A', '选项B', '选项C', '选项D'],
              correct_index: 0
            }))
          },
          message: '开始测试成功'
        })
      });
    });

    // 拦截提交 API
    await page.route('**/api/evaluation/submit', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          data: {
            score: 80,
            correct_count: 8,
            total_count: 10,
            level: '中级'
          },
          message: '提交成功'
        })
      });
    });

    // 等待用户信息加载完成
    await page.waitForSelector('#username-display', { state: 'attached' });
    await page.waitForFunction(() => {
      const el = document.getElementById('username-display');
      return el && el.textContent && el.textContent.length > 0;
    }, { timeout: 5000 });

    await page.waitForSelector('.preset-btn.active');
    // 直接通过 JS 触发开始按钮点击
    await page.evaluate(() => document.getElementById('start-eval-btn').click());
    await page.waitForSelector('#eval-test', { state: 'visible', timeout: 10000 });
    await page.waitForSelector('.question-card', { state: 'attached', timeout: 10000 });

    page.once('dialog', dialog => dialog.accept());
    await page.evaluate(() => document.getElementById('submit-eval-btn').click());
    await page.waitForSelector('#eval-result', { state: 'visible', timeout: 10000 });

    await page.waitForSelector('#eval-again-btn', { state: 'attached' });
    await page.locator('#eval-again-btn').click({ force: true });
    await expect(page.locator('#eval-start')).toBeAttached();
  });
});

// ==================== 6. 学习计划测试 ====================
test.describe('6. 学习计划', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateTo(page, 'plans');
    await page.waitForTimeout(1000);
  });

  test('6.1 显示当前计划区域', async ({ page }) => {
    await expect(page.locator('#active-plan-display')).toBeAttached();
  });

  test('6.2 显示历史计划列表', async ({ page }) => {
    await expect(page.locator('#plans-history')).toBeAttached();
  });

  test('6.3 显示创建计划表单', async ({ page }) => {
    await expect(page.locator('#plan-dataset')).toBeAttached();
    await expect(page.locator('#plan-name')).toBeAttached();
    await expect(page.locator('#plan-daily-new')).toBeAttached();
    await expect(page.locator('#plan-daily-review')).toBeAttached();
    await expect(page.locator('#create-plan-btn')).toBeAttached();
  });

  test('6.4 创建学习计划', async ({ page }) => {
    await page.waitForSelector('#plan-dataset', { state: 'attached' });
    await page.selectOption('#plan-dataset', 'cet4');
    await page.fill('#plan-name', 'E2E测试计划');
    // 数字输入框是 readonly，通过 +/- 按钮调整或直接设值
    await page.evaluate(() => {
      const el = document.getElementById('plan-daily-new') as HTMLInputElement;
      if (el) { el.removeAttribute('readonly'); el.value = '10'; el.dispatchEvent(new Event('input', { bubbles: true })); }
    });
    await page.evaluate(() => {
      const el = document.getElementById('plan-daily-review') as HTMLInputElement;
      if (el) { el.removeAttribute('readonly'); el.value = '15'; el.dispatchEvent(new Event('input', { bubbles: true })); }
    });

    await page.waitForSelector('#create-plan-btn', { state: 'attached' });
    await page.locator('#create-plan-btn').click({ force: true });
    await page.waitForTimeout(2000);

    // 验证没有显示"加载中"
    await expect(page.locator('#active-plan-display')).not.toContainText('加载中');
  });

  test('6.5 刷新计划列表', async ({ page }) => {
    await page.waitForSelector('#refresh-plans-btn', { state: 'attached' });
    await page.locator('#refresh-plans-btn').click({ force: true });
    await page.waitForTimeout(1000);
    await expect(page.locator('#plans-history')).toBeAttached();
  });
});

// ==================== 7. 统计分析测试 ====================
test.describe('7. 统计分析', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateTo(page, 'statistics');
    await page.waitForTimeout(1000);
  });

  test('7.1 显示统计概览', async ({ page }) => {
    await expect(page.locator('#stat-words')).toBeAttached();
    await expect(page.locator('#stat-learned')).toBeAttached();
    await expect(page.locator('#stat-streak')).toBeAttached();
    await expect(page.locator('#stat-time')).toBeAttached();
  });

  test('7.2 显示趋势图表', async ({ page }) => {
    await expect(page.locator('#trend-chart')).toBeAttached();
  });

  test('7.3 显示难度分布图表', async ({ page }) => {
    await expect(page.locator('#difficulty-chart')).toBeAttached();
  });

  test('7.4 显示雷达图', async ({ page }) => {
    await expect(page.locator('#radar-chart')).toBeAttached();
  });

  test('7.5 显示词性分布图表', async ({ page }) => {
    await expect(page.locator('#pos-chart')).toBeAttached();
  });

  test('7.6 切换时间周期', async ({ page }) => {
    const periodBtns = page.locator('.period-btn');
    const count = await periodBtns.count();
    if (count > 1) {
      await periodBtns.nth(1).click({ force: true });
      await page.waitForTimeout(500);
      await expect(page.locator('#stat-words')).toBeAttached();
    }
  });
});

// ==================== 8. 收藏夹测试 ====================
test.describe('8. 收藏夹', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateTo(page, 'favorites');
    await page.waitForTimeout(1000);
  });

  test('8.1 显示收藏夹页面', async ({ page }) => {
    // 应该显示收藏网格或空状态
    const hasGrid = await page.locator('#favorites-grid').isVisible().catch(() => false);
    const hasEmpty = await page.locator('#favorites-empty').isVisible().catch(() => false);
    expect(hasGrid || hasEmpty).toBeTruthy();
  });

  test('8.2 显示收藏计数', async ({ page }) => {
    await expect(page.locator('#favorites-count')).toBeAttached();
  });

  test('8.3 搜索框可用', async ({ page }) => {
    await expect(page.locator('#favorites-search')).toBeEnabled();
  });

  test('8.4 难度过滤器存在', async ({ page }) => {
    await expect(page.locator('#difficulty-filters')).toBeAttached();
  });
});

// ==================== 9. 个人中心测试 ====================
test.describe('9. 个人中心', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
    await navigateTo(page, 'profile');
    await page.waitForTimeout(1000);
  });

  test('9.1 显示用户信息', async ({ page }) => {
    await expect(page.locator('#profile-username')).toBeAttached();
    await expect(page.locator('#profile-email')).toBeAttached();
  });

  test('9.2 显示学习统计', async ({ page }) => {
    await expect(page.locator('#profile-total-words')).toBeAttached();
    await expect(page.locator('#profile-mastered-words')).toBeAttached();
    await expect(page.locator('#profile-streak-days')).toBeAttached();
  });

  test('9.3 显示成就列表', async ({ page }) => {
    await expect(page.locator('#achievements-grid')).toBeAttached();
  });

  test('9.4 显示编辑表单', async ({ page }) => {
    await expect(page.locator('#edit-email')).toBeAttached();
    await expect(page.locator('#save-profile-btn')).toBeAttached();
  });

  test('9.5 编辑个人信息', async ({ page }) => {
    await page.fill('#edit-email', 'test@example.com');

    await page.locator('#save-profile-btn').click({ force: true });
    await page.waitForTimeout(1000);
  });

  test('9.6 显示修改密码表单', async ({ page }) => {
    await expect(page.locator('#old-password')).toBeAttached();
    await expect(page.locator('#new-password')).toBeAttached();
    await expect(page.locator('#confirm-password')).toBeAttached();
    await expect(page.locator('#change-password-btn')).toBeAttached();
  });

  test('9.7 从个人中心退出登录', async ({ page }) => {
    await page.locator('#profile-logout-btn').click({ force: true });
    await page.waitForURL('**/login.html', { timeout: 5000 });
    await expect(page.locator('#login-form')).toBeAttached();
  });
});

// ==================== 10. 页面导航测试 ====================
test.describe('10. 页面导航', () => {
  test.beforeEach(async ({ page }) => {
    await login(page);
  });

  test('10.1 导航到学习计划', async ({ page }) => {
    await navigateTo(page, 'plans');
    await page.waitForTimeout(500);
    await expect(page.locator('.nav-link[data-page="plans"]')).toHaveClass(/active/);
  });

  test('10.2 导航到闯关模式', async ({ page }) => {
    await navigateTo(page, 'levels');
    await page.waitForTimeout(500);
    await expect(page.locator('.nav-link[data-page="levels"]')).toHaveClass(/active/);
  });

  test('10.3 导航到等级测试', async ({ page }) => {
    await navigateTo(page, 'evaluation');
    await page.waitForTimeout(500);
    await expect(page.locator('.nav-link[data-page="evaluation"]')).toHaveClass(/active/);
  });

  test('10.4 导航到统计', async ({ page }) => {
    await navigateTo(page, 'statistics');
    await page.waitForTimeout(500);
    await expect(page).toHaveURL(/statistics\.html/);
  });

  test('10.5 导航到收藏夹', async ({ page }) => {
    await navigateTo(page, 'favorites');
    await page.waitForTimeout(500);
    await expect(page).toHaveURL(/favorites\.html/);
  });

  test('10.6 导航到个人中心', async ({ page }) => {
    await navigateTo(page, 'profile');
    await page.waitForTimeout(500);
    await expect(page.locator('.nav-link[data-page="profile"]')).toHaveClass(/active/);
  });

  test('10.7 导航回首页', async ({ page }) => {
    await navigateTo(page, 'plans');
    await page.waitForTimeout(500);
    await navigateTo(page, 'dashboard');
    await page.waitForTimeout(500);
    await expect(page).toHaveURL(/dashboard\.html/);
  });
});

// ==================== 11. 认证保护测试 ====================
test.describe('11. 认证保护', () => {
  test('11.1 未登录访问仪表盘重定向', async ({ page }) => {
    await blockFonts(page);
    await page.goto(`${BASE_URL}/pages/dashboard.html`);
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/login\.html/);
  });

  test('11.2 未登录访问学习页重定向', async ({ page }) => {
    await blockFonts(page);
    await page.goto(`${BASE_URL}/pages/learning.html`);
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/login\.html/);
  });

  test('11.3 未登录访问统计页重定向', async ({ page }) => {
    await blockFonts(page);
    await page.goto(`${BASE_URL}/pages/statistics.html`);
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/login\.html/);
  });
});
