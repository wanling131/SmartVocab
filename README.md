# SmartVocab - 智能英语词汇学习推荐系统

## 项目简介

SmartVocab 是一个基于深度学习的智能英语词汇学习推荐系统，旨在通过个性化推荐算法提升用户的学习效率和词汇掌握程度。系统采用双塔神经网络模型，结合用户学习历史与遗忘曲线理论，提供词汇学习、复习、评测、学习计划与闯关模式等功能。

## 主要功能

### 智能推荐与学习
- **深度学习推荐**：基于 PyTorch 的双塔神经网络模型（`requirements.txt` 含 **torch**；运行期若初始化失败或模型不可用则**回退**传统推荐，并非「可不安装 PyTorch」）
- **多算法融合**：难度、词频、学习历史、深度学习、随机探索等
- **多题型**：选择题、翻译题、拼写题；混合学习与复习会话

### 业务模块（REST API）
- **用户认证**：注册、登录、`/api/auth/profile` 个人信息
- **词汇**：学习会话、词库批量导入/导出（`/api/vocabulary/import`、`/api/vocabulary/export`）
- **学习记录与统计**：进度、记录、遗忘曲线 `/api/learning/forgetting-curve/<user_id>`
- **推荐**：`/api/recommendations/...`
- **学习计划**：`/api/plans`（CRUD、当前生效计划）
- **评测**：`/api/evaluation/start|submit|history`
- **闯关**：`/api/levels/gates|progress|unlock`
- **健康检查**：`/api/health`（便于部署与演示）

### 数据分析
- 学习统计、最近记录、未来多日复习计划柱状图（统计页）

## 技术架构

| 层级 | 技术 |
|------|------|
| Web | Flask + Blueprint，CORS |
| 数据库 | MySQL，连接池（`tools/database.py`） |
| 深度学习 | PyTorch（依赖已声明；失败时回退传统推荐） |
| 前端 | 原生 HTML/CSS/JS（`frontend/`），可按模块拆分 |

## 项目结构（节选）

```
SmartVocab/
├── api/
│   ├── api_launcher.py      # 主入口：注册全部蓝图与静态前端
│   ├── health_api.py        # GET /api/health、/api/health/db
│   ├── auth_api.py
│   ├── vocabulary_api.py
│   ├── learning_api.py
│   ├── recommendation_api.py
│   ├── plans_api.py
│   ├── evaluation_api.py
│   ├── levels_api.py
│   ├── achievements_api.py
│   └── favorites_api.py
├── core/
│   ├── auth/
│   ├── learning/
│   ├── vocabulary/
│   ├── forgetting_curve/
│   ├── evaluation/
│   └── recommendation/
├── tools/
│   ├── database.py
│   ├── migrate_db.py        # 数据库建表/升级迁移辅助
│   ├── base_crud.py
│   └── *_crud.py
├── frontend/
│   ├── index.html           # 首页入口
│   ├── pages/               # 多页 HTML
│   ├── styles/klein-morandi.css
│   └── js/
│       └── api-client.js    # API 请求封装
├── tests/
│   ├── conftest.py
│   ├── test_*.py            # pytest 单元测试
│   └── e2e/                 # Playwright E2E 测试
├── 文档/
│   ├── 数据库建表脚本.sql
│   ├── 数据库升级迁移脚本.sql
│   └── 开发与部署说明.md
├── config.py                # APP_CONFIG、学习参数
├── main.py                  # 开发启动入口
├── commands.bat             # Windows 常用命令快捷方式
├── CLAUDE.md                # Claude Code 开发指南
└── requirements.txt
```

## 环境变量

复制 [.env.example](.env.example) 为 `.env` 并按需修改：

| 变量 | 说明 |
|------|------|
| `APP_HOST` / `APP_PORT` / `APP_DEBUG` | 服务监听与调试 |
| `APP_ENV` / `APP_PRODUCTION` | `production`/`staging` 等表示生产模式（收紧默认行为） |
| `SECRET_KEY` | Flask 会话等签名；**生产必须**设置强随机值 |
| `LOG_LEVEL` | `DEBUG` / `INFO` / `WARNING` 等 |
| `CORS_ORIGINS` | 逗号分隔的前端 Origin；生产勿用 `*` |
| `EXPOSE_ERROR_DETAILS` | API 是否返回异常详情（生产建议 `false`） |
| `MAX_CONTENT_LENGTH_MB` | 请求体大小上限（默认 16） |
| `ENABLE_HSTS` | 全站 HTTPS 时在反向代理后可选启用 HSTS |
| `DB_HOST` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | MySQL（与 `tools/database.py` 一致） |

## 安装与运行

### 环境要求
- Python 3.8+
- MySQL 5.7+

### 步骤

1. **安装依赖**
```bash
pip install -r requirements.txt
```

2. **数据库**
- 创建数据库（如 `smartvocab`）
- 执行 `文档/数据库建表脚本.sql` 与 `文档/数据库升级迁移脚本.sql`

3. **配置**
- 复制 `.env.example` 为 `.env`，配置数据库连接

4. **启动**
```bash
python main.py
```

5. **访问**
- 浏览器打开 `http://localhost:5000`
- 开发模式下可访问 `/api/docs` 查看 Swagger API 文档

### Python Commands
```bash
python commands.py run        # Start server
python commands.py test       # Run unit tests
python commands.py test-fast  # Fast tests (skip deep learning)
python commands.py db         # Test database connection
```

## 开发说明

- **日志**：`main.py` 启动时调用 `configure_logging()`，业务代码使用 `logging.getLogger(__name__)`
- **API 路由**：所有接口以 `api_launcher.py` 注册的 Blueprint 为准
- **测试**：`python -m pytest tests/ -v`（单元测试），`cd tests/e2e && npx playwright test`（E2E）
- **API 文档**：开发模式下访问 `/api/docs` 查看 Swagger UI
- **详细文档**：见 [文档/开发与部署说明.md](文档/开发与部署说明.md)

## 许可证

本项目仅用于学习与研究目的时，请遵守相应许可与学校规定。
