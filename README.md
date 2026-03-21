# SmartVocab - 智能英语词汇学习推荐系统

## 项目简介

SmartVocab 是一个基于深度学习的智能英语词汇学习推荐系统，旨在通过个性化推荐算法提升用户的学习效率和词汇掌握程度。系统采用双塔神经网络模型，结合用户学习历史与遗忘曲线理论，提供词汇学习、复习、评测、学习计划与闯关模式等功能。

## 主要功能

### 智能推荐与学习
- **深度学习推荐**：基于 PyTorch 的双塔神经网络模型（可选，不可用时回退传统推荐）
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
| 深度学习 | PyTorch（可选） |
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
│   └── api_router_backup.py # 旧版单文件路由备份（已弃用）
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
│   ├── index.html
│   ├── styles.css
│   ├── main.js              # 应用入口（ES module）
│   └── js/
│       └── api-client.js    # API 请求封装
├── tests/
│   ├── conftest.py
│   └── test_health.py       # 健康检查（需 pip install -r requirements.txt）
├── automation/              # 自动化自检脚本（可选，可整体删除）
│   ├── README.md
│   └── smoke_check.py
├── 文档/
│   ├── 数据库建表脚本.sql
│   ├── 数据库升级迁移脚本.sql
│   └── 开发与部署说明.md
├── config.py                # APP_CONFIG、学习参数；支持环境变量与 LOG_LEVEL
├── wsgi.py                  # Gunicorn 入口：`gunicorn wsgi:app`
├── Dockerfile               # 生产镜像（Gunicorn + APP_ENV=production）
├── docker-compose.yml       # MySQL + 应用（需配置 SECRET_KEY、DB_* 等）
├── .env.example             # 环境变量示例（复制为 .env）
├── main.py                  # 开发启动：configure_logging + 数据库检查 + API
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
- 执行 `文档/数据库建表脚本.sql` 与 `文档/数据库升级迁移脚本.sql`，或使用 `python tools/migrate_db.py`（若项目已提供）

3. **配置**
- 使用 `.env` 配置数据库与日志（见上表）

4. **启动**
```bash
python main.py
```

5. **访问**
- 浏览器打开 `http://localhost:5000`（端口以 `APP_PORT` 为准）

### 生产环境（Gunicorn）

安装依赖后使用 `wsgi.py` 作为入口（见 `requirements.txt` 中的 `gunicorn`）：

```bash
set APP_ENV=production
set SECRET_KEY=你的强随机密钥
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 wsgi:app
```

（Linux/macOS 可用 `export` 设置环境变量。）建议在反向代理（Nginx 等）后终止 **HTTPS**，并配置 `CORS_ORIGINS` 为实际前端域名。

### Docker Compose

1. 复制 `.env.example` 为 `.env`，设置 `SECRET_KEY`、`DB_*`（与 `docker-compose.yml` 中 MySQL 一致）。
2. **先**在数据库中执行建表与迁移脚本（见下文「数据库」），或使用已初始化的 MySQL 数据卷。
3. 在项目根目录执行：`docker compose up -d --build`

更完整的上线自检见 [文档/生产部署与商用检查清单.md](文档/生产部署与商用检查清单.md)。

## 开发说明

- **日志**：`main.py` 启动时调用 `configure_logging()`，业务代码请使用 `logging.getLogger(__name__)`，避免随意 `print`。
- **旧路由**：`api_router_backup.py` 仅作历史参考，新接口以 `api_launcher` 注册的 Blueprint 为准。
- **测试**：安装依赖后执行 `python -m pytest tests/ -v`（需已安装 Flask 等依赖）。
- **自动化自检**（可选）：`python automation/smoke_check.py --quick`（全量自检去掉 `--quick`，并含智能推荐模块自检）；不需要时删除 `automation/` 文件夹即可。若 `pip install` 后 `test_client` 报错，请确认已安装 `requirements.txt` 中的 `werkzeug<3`。
- **详细文档**：见 [文档/开发与部署说明.md](文档/开发与部署说明.md)、[文档/生产部署与商用检查清单.md](文档/生产部署与商用检查清单.md)。
- **功能与论文对照**：[文档/系统功能与实现对照.md](文档/系统功能与实现对照.md)（系统性与答辩口径说明）。

## 许可证

本项目仅用于学习与研究目的时，请遵守相应许可与学校规定。
