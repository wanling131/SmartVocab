# SmartVocab 更新日志

## [2026-04-06] 代码质量优化与功能完善

### 新增功能
- **周月统计对比**
  - 统计页面新增本周/上周复习次数对比
  - 统计页面新增本周/上周新词学习对比
  - 趋势箭头显示（↑上升/↓下降/→持平）
- **API测试覆盖**
  - `/api/auth/register` 注册端点测试
  - `/api/auth/password/<user_id>` 密码修改测试
  - `/api/evaluation/result/<result_id>` 评估结果测试
  - `/api/evaluation/history/<user_id>` 评估历史测试

### 优化改进
- **代码重复消除**
  - `_check_user_access` 函数统一到 `auth_middleware.py`
  - 8个API文件改为导入公共函数
- **安全加固**
  - `record.word` 添加 `escapeHtml` 转义（XSS防护）
- **测试覆盖率**：171 → 177个测试 (+3.5%)

### 技术细节
- `frontend/main.js`: 新增 `updateTrendArrow()` 函数
- `frontend/main.js`: `loadStatistics()` 添加对比数据计算
- `tests/test_auth.py`: 新增 `TestAuthAPIEndpoints` 测试类
- `tests/test_learning.py`: 新增 `TestEvaluationResults` 测试类

---

## [2026-04-04] 系统架构升级与全面优化

### 新增功能
- **推荐算法增强模块** (`core/recommendation/recommendation_enhancements.py`)
  - 协同过滤（用户/物品相似度）
  - 动态权重调整（基于算法效果）
  - 多样性控制（MMR算法）
  - 冷启动策略（热门词+难度分级）
  - 实时个性化（会话跟踪+疲劳检测）
- **深度学习模型增强**
  - 特征维度扩展至25维
  - 注意力机制
  - LayerNorm替代BatchNorm
  - 门控融合机制
- **前端美化系统**
  - CSS变量系统（颜色、间距、阴影）
  - 微交互动画（波纹、悬浮、过渡）
  - 加载状态（骨架屏、进度条）
  - Toast通知系统
  - 表单验证反馈

### 优化改进
- **测试覆盖率**：47 → 112个测试 (+138%)
  - 新增 `test_recommendation.py` 推荐算法测试
  - 新增 `test_forgetting_curve.py` 遗忘曲线测试
  - 新增 `test_evaluation.py` 测评系统测试
- **安全加固**
  - XSS防护（`escapeHtml`函数）
  - 空答案处理bug修复
  - SQL注入白名单验证确认
- **代码规范**
  - 类型注解完善
  - docstring规范化
  - 未使用导入清理

### Bug修复
- 修复 `_check_answer` 空答案匹配bug
- 修复推荐引擎类型导入错误
- 修复测试权重断言适配新版算法

### 提交
- `feat: 推荐算法增强、前端美化、测试覆盖率提升`

---

## [2026-04-04] 项目优化与E2E测试

### 新增
- **E2E 测试框架**: Playwright 自动化测试，覆盖 48 个测试用例
- **前端美化**: 页面过渡动画、渐变效果、悬停动画、Toast 动画
- **CLAUDE.md**: 项目文档，帮助 AI 助手理解项目结构

### 优化
- **目录结构**: 图片移至 `文档/images/`，删除空目录
- **.gitignore**: 添加 E2E 测试相关忽略规则
- **数据库**: 清理 17 个测试用户

### 提交
- `2ce1f20` refactor: 项目结构优化、前端美化、E2E测试框架

---

## [2026-04-04] 系统体检与优化

### 新增
- **测试增强**: 新增 `tests/test_core.py`，增加16个核心业务测试用例
  - 遗忘曲线计算测试
  - 推荐引擎初始化与权重配置测试
  - 用户认证/密码哈希测试
  - 词汇学习管理器测试
  - 测评系统测试
  - API响应工具测试
  - 数据库连接池测试

### 优化
- **代码清理**: 移除 `frontend/main.js` 中6处 `console.log` 调试代码
- **测试数量**: 从31个提升至47个 (+51%)

### 安全确认
- JWT密钥生产环境强制校验 ✅
- SQL注入白名单防护 ✅
- API认证保护合理 ✅
- 密码bcrypt哈希 ✅

### 文档更新
- 确认"个人信息编辑"功能已实现（文档过时）
- 确认"计划编辑UI"功能已实现（文档过时）

---

## 历史版本

### [2026-04-03] 安全加固
- JWT认证保护
- API认证中间件
- 清理调试代码

### [2026-04-02] 功能完善
- 闯关模式完善
- 计划管理
- 个人中心
- 成就系统

### [2026-03-xx] 初始版本
- 核心学习闭环
- 评测系统
- 遗忘曲线
- 推荐系统
