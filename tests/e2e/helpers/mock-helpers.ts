/**
 * E2E 测试 API Mock 辅助函数
 * 提供常用的 API 路由 mock，避免测试代码重复
 */

import type { Page } from '@playwright/test';

/**
 * Mock 评估测试 API
 * 模拟开始测试和提交答卷接口
 */
export async function mockEvaluationAPIs(page: Page) {
  // Mock 开始测试接口
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

  // Mock 提交答卷接口
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
}

/**
 * Mock 学习记录 API
 */
export async function mockLearningAPIs(page: Page) {
  await page.route('**/api/learning/records/*', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: [],
        message: '获取成功'
      })
    });
  });
}

/**
 * Mock 推荐词 API
 */
export async function mockRecommendationAPIs(page: Page) {
  await page.route('**/api/recommendations/*', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        success: true,
        data: Array.from({ length: 10 }, (_, i) => ({
          id: i + 1,
          word: `recommend_word_${i + 1}`,
          phonetic: `rec_${i + 1}`,
          translation: `推荐词${i + 1}`,
          difficulty_level: 2
        })),
        message: '获取推荐成功'
      })
    });
  });
}