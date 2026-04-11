"""
Swagger/OpenAPI 文档配置
使用 Flasgger 自动生成 API 文档，无需修改现有蓝图
"""

# Swagger 配置模板
SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "apispec",
            "route": "/api/docs/apispec.json",
            "rule_filter": lambda rule: True,  # 包含所有路由
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/api/docs/static",
    "swagger_ui": True,
    "specs_route": "/api/docs",
}

# API 文档元信息
SWAGGER_TEMPLATE = {
    "swagger": "2.0",
    "info": {
        "title": "SmartVocab API",
        "description": """
智能英语词汇学习系统 API 文档

## 功能模块
- **认证**: 用户登录、注册、个人资料管理
- **词汇**: 学习会话、单词 CRUD、导入导出
- **学习**: 学习记录、进度跟踪、复习提醒
- **推荐**: 多算法智能推荐（难度/词频/深度学习）
- **计划**: 学习计划创建与管理
- **关卡**: 学习关卡解锁与进度
- **评测**: 测试试卷生成与评分
- **收藏**: 收藏单词管理
- **成就**: 成就徽章、连续学习天数
- **健康**: 系统状态、数据库连接检查

## 认证方式
使用 JWT Token 认证：
1. 登录获取 token
2. 在请求头添加: `Authorization: Bearer <token>`
""",
        "version": "1.0.0",
        "contact": {
            "name": "SmartVocab Team",
        },
    },
    "host": "localhost:5000",
    "basePath": "/api",
    "schemes": ["http", "https"],
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Token: Bearer <token>",
        }
    },
}

# API 标签定义（用于分组）
API_TAGS = [
    {"name": "认证", "description": "用户登录、注册、个人资料"},
    {"name": "词汇", "description": "学习会话、单词管理"},
    {"name": "学习", "description": "学习记录、进度跟踪"},
    {"name": "推荐", "description": "智能推荐算法"},
    {"name": "计划", "description": "学习计划管理"},
    {"name": "关卡", "description": "学习关卡系统"},
    {"name": "评测", "description": "测试与评分"},
    {"name": "收藏", "description": "收藏单词"},
    {"name": "成就", "description": "成就徽章系统"},
    {"name": "健康", "description": "系统健康检查"},
]
