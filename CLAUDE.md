# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

SmartVocab 是一个智能英语词汇学习系统，集成 PyTorch 深度学习推荐。后端使用 Flask + MySQL，前端为多页原生 JS 应用，采用克莱因蓝 + 莫兰迪手绘风格设计体系。

## 常用命令

```bash
# 安装依赖
pip install -r requirements.txt

# 运行全部单元测试（pytest）
python -m pytest tests/ -v

# 运行单个测试文件 / 单个测试
python -m pytest tests/test_auth.py -v
python -m pytest tests/test_auth.py::TestJWTToken::test_generate_token -v

# 跳过深度学习模型加载运行测试（更快）
SMARTVOCAB_SKIP_DL_INIT=1 python -m pytest tests/ -v

# 运行 E2E 测试（Playwright）
cd tests/e2e && npx playwright test

# 运行单个 E2E 测试用例
cd tests/e2e && npx playwright test --grep "测试名称"

# 启动开发服务器
python main.py

# 数据库连接测试
python -c "from tools.database import test_connection; test_connection()"
```

### 一键启动脚本

- **双击 `start.bat`** - 启动服务器
- **双击 `test.bat`** - 运行测试
- **命令行 `python commands.py`** - 查看更多选项（run/test/test-fast/db）

## 架构

### 后端（`api/`）

Flask 应用在 `api_launcher.py` 中组装。每个 `*_api.py` 是一个蓝图：

| 蓝图 | 前缀 | 关键端点 |
|------|------|----------|
| `auth_api` | `/api/auth` | `/login`、`/register`、`/profile`（无参数，从 JWT 获取）、`/profile/<id>`、`/password/<id>` |
| `vocabulary_api` | `/api/vocabulary` | `/start-session`、`/current-word`、`/submit-answer`、`/import`、`/export`、`/words` CRUD（管理员）、`/mistakes/<uid>`、`/mistakes/<uid>/review`、`/mistakes/<uid>/word/<wid>/master` |
| `learning_api` | `/api/learning` | `/progress/<uid>`、`/records/<uid>`、`/review-words/<uid>`、`/forgetting-curve/<uid>` |
| `recommendation_api` | `/api/recommendations` | `/<uid>?limit=&algorithm=` |
| `plans_api` | `/api/plans` | `?user_id=`（GET 列表）、POST 创建、`/<id>/deactivate`、`/<id>/activate` |
| `evaluation_api` | `/api/evaluation` | `/start`、`/submit`、`/history/<uid>` |
| `levels_api` | `/api/levels` | `/gates`（公开）、`/gates/<uid>`（含进度）、`/progress/<uid>`、`/unlock` |
| `favorites_api` | `/api/favorites` | `/<uid>`、`/<uid>/ids`、`/<uid>/word/<wid>` |
| `achievements_api` | `/api/achievements` | `/<uid>`、`/<uid>/streak`、`/<uid>/reports` |
| `health_api` | `/api` | `/health`、`/health/db`、`/health/cache`、`/health/metrics` |

### 核心业务逻辑（`core/`）

- `auth/user_auth.py`：bcrypt 密码哈希，登录/注册
- `recommendation/recommendation_engine.py`：多算法动态权重推荐（6 种算法，权重配置在 `config.py`）
- `recommendation/recommendation_enhancements.py`：推荐增强模块，提供协同过滤、多样性控制（MMR）、冷启动策略、实时个性化
- `recommendation/deep_learning_recommender.py`：PyTorch 双塔神经网络，LayerNorm，25 维特征，交叉注意力机制。PyTorch 不可用时自动降级为传统推荐
- `learning/learning_record_manager.py`：学习记录 CRUD
- `forgetting_curve/forgetting_curve_manager.py`：艾宾浩斯遗忘曲线计算，复习调度
- `vocabulary/vocabulary_learning_manager.py`：学习会话、题目生成、答案提交
- `evaluation/`：测试试卷生成与评分

### 工具层（`tools/`）

- `database.py`：MySQL 连接池单例（`DatabaseManager`）。`get_database_context()` 返回上下文管理器
- `base_crud.py`：基类，提供 `execute_query()`、`execute_update()`、`execute_insert()`、`build_update_query(allowed_fields=)`（白名单过滤）
- `*_crud.py`：继承 `BaseCRUD` 的表级 CRUD 类
- `memory_cache.py`：TTL + LRU 缓存，`@cached(ttl_seconds)` 装饰器

### 前端（`frontend/`）

多页架构，克莱因蓝 + 莫兰迪手绘风格设计：

- `pages/`：9 个独立 HTML 页面（login、dashboard、learning、statistics、plans、levels、evaluation、favorites、profile）
- `styles/klein-morandi.css`：共享设计系统（CSS 变量、组件、动画）
- `js/api-client.js`：API 封装，含 JWT 处理、2 分钟 GET 缓存、请求去重。导出 `apiRequest()`、`fetchWithState()`、`userApi.*`
- `js/utils.js`：`escapeHtml()`、`showToast()`、`animateNumber()` 等工具函数
- `js/charts.js`：统计页图表渲染
- `js/page-common.js`：导航栏组件、用户初始化、页面共享功能
- `js/components/`：前端组件（如 `achievements.js` 成就徽章组件）
- `js/icons.js`：SVG 图标系统，stroke 风格，与克莱因蓝主题一致
- `js/worker-client.js` + `js/worker.js`：Web Worker 后台任务

所有页面统一使用 ES 模块从 `js/api-client.js` 和 `js/utils.js` 导入。

## 关键模式

### 认证
- JWT 令牌通过 `auth_middleware.py` 管理：`generate_token()`、`verify_token()`、`@require_auth` 装饰器
- `check_user_access(user_id)` 验证当前用户是否有权访问目标用户数据 —— 所有模块共享此函数，**不要**创建本地副本
- 前端将令牌存储在 `localStorage` 的 `auth_token` 中

### 权限
- 管理员操作（单词导入/导出/CRUD）由 `ADMIN_USERS` 环境变量控制（逗号分隔的用户名）
- 当 `ADMIN_USERS` 未设置时，管理员操作**默认拒绝**（安全默认值）

### SQL 安全
- 使用参数化查询：`execute_query(query, params)` —— 始终将用户输入作为参数传入，**禁止**字符串拼接
- `build_update_query()` 接受 `allowed_fields` 白名单 —— 使用它防止列名注入

### XSS 防护
- 模板字面量中显示用户内容时，**必须**使用 `escapeHtml()`
- 对于包含动态数据的 `onclick` 处理器，使用 `data-*` 属性 + 事件委托代替内联字符串
- 导入 `js/utils.js` 的页面可直接使用 `escapeHtml`；内联脚本的页面需自行定义

### 数据库初始化
1. 创建 MySQL 数据库（如 `smartvocab`）
2. 运行 `文档/数据库建表脚本.sql` 创建基础表结构
3. 运行 `文档/数据库升级迁移脚本.sql` 进行增量更新
4. 或使用 `python tools/migrate_db.py` 编程式迁移

### 前端设计体系
`klein-morandi.css` 中的 CSS 变量：
```css
--klein-blue: #002FA7;        /* 主品牌色 */
--klein-light: #1a4fd0;
--klein-rgb: 0, 47, 167;      /* 用于 rgba() */
--morandi-cream: #F5F0E8;     /* 温暖背景色（所有页面统一） */
--morandi-rose: #D4C4B5;      /* 边框色 */
--morandi-lavender: #B8B4C8;  /* 阴影、强调色 */
--accent-coral: #E07A5F;      /* 行动按钮、错误色 */
--accent-amber: #F2A03D;      /* 辅助强调 */
```

手绘风格元素：不对称 `border-radius`（如 `24px 14px`）、`dashed` 虚线边框、硬偏移 `box-shadow`（如 `3px 3px 0`）、Caveat 手写字体用于装饰文字。背景装饰字母统一 56px、opacity 0.08。

所有页面 Favicon 统一为内联 SVG：克莱因蓝圆角方块 + 白色 "SV" 文字。

### 推荐系统
- 6 种算法，权重在 `config.py` 的 `RECOMMENDATION_CONFIG` 中配置：
  - difficulty_based（0.25）、frequency_based（0.20）、learning_history（0.15）、deep_learning（0.20）、collaborative（0.05）、random_exploration（0.15）
- 新用户冷启动处理
- 用户积累 **15 条**学习记录后启用个性化权重
- 深度学习模型：用户积累 30 条记录后训练

### 数据库字段映射（重要）

前端与数据库字段名不完全一致，需注意：

| 表名 | 数据库字段 | 前端期望 | 处理方式 |
|------|-----------|---------|---------|
| `level_gates` | `gate_order` | `order` | API添加别名 |
| `level_gates` | `gate_name` | `name` | API添加别名 |
| `user_level_progress` | `level_gate_id` | `gate_id` | API中用`level_gate_id` |

修改相关代码时，优先在 API 层添加字段别名，保持前端兼容。

## 环境变量

`.env` 中必需：
- `DB_HOST`、`DB_USER`、`DB_PASSWORD`、`DB_NAME`：MySQL 连接
- `SECRET_KEY`：Flask 会话签名
- `JWT_SECRET_KEY`：JWT 签名

重要可选项：
- `SMARTVOCAB_SKIP_DL_INIT=1`：跳过 PyTorch 加载以加速测试
- `LOG_LEVEL`：DEBUG/INFO/WARNING/ERROR
- `ADMIN_USERS`：逗号分隔的管理员用户名（单词管理功能必需）

## E2E 测试

### 测试账号
固定账号 `e2e_tester` / `TestPass123`，需预先在数据库中创建。

### 测试文件
- `tests/e2e/specs/full-flow.spec.ts`：全功能端到端测试（真实API）
- `tests/e2e/specs/integration.spec.ts`：集成测试

### 关键验证点
测试应验证真实数据加载，而非仅检查元素存在：
```typescript
// 等待真实数据加载（不是占位符）
await page.waitForFunction(() => {
  const text = items[0].querySelector('h4')?.textContent || '';
  return text !== '加载中...' && text !== '暂无推荐';
});
```

## 常见问题排查

| 问题 | 解决方案 |
|------|----------|
| PyTorch 导入失败 | 系统自动降级为传统推荐算法 |
| 模型键不匹配 | 旧模型为 BatchNorm+20 维，新模型为 LayerNorm+25 维；删除旧 `.pth` 文件重新训练 |
| 测试导入错误 | 确保 `requirements.txt` 中包含 `werkzeug<3` |
| 前端页面空白 | 清除 localStorage，检查浏览器控制台 |
| E2E 测试账号问题 | 使用固定账号 `e2e_tester` / `TestPass123`，需预先在数据库中创建 |
| 关卡名称显示为空 | 检查API是否添加了字段别名（`gate_name`→`name`） |
| 复习词缺少单词详情 | `forgetting_curve_manager.py` 应调用 `_enrich_with_word_details()` |
| 等级测试无选项 | 确保 `evaluation_manager.py` 使用选择题格式（返回 `options` 字段） |

## CI/CD

项目使用 GitHub Actions 进行持续集成（`.github/workflows/ci.yml`）：
- 自动运行 pytest 单元测试（覆盖率报告）
- 自动运行代码质量检查（flake8、isort、black）
- E2E 测试在 CI 中暂未启用（需配置数据库后开启）

## 开发工具

### Swagger API 文档（仅开发模式）
启动服务后访问 `/api/docs` 可查看交互式 API 文档：
- 可视化展示所有 API 端点、参数、响应格式
- 直接在浏览器测试 API（无需 Postman）
- 答辩演示时可作为「接口规范文档」展示

生产环境自动禁用（`APP_ENV=production` 时不可访问）。
