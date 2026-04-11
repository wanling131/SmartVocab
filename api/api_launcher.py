"""
API服务启动器
负责启动和管理API服务（含生产环境安全基线）
"""

import logging
import os
import time
import uuid
from secrets import token_hex

from flask import Flask, g, request
from flask_cors import CORS

from config import APP_CONFIG
from .swagger_config import SWAGGER_CONFIG, SWAGGER_TEMPLATE

logger = logging.getLogger(__name__)

# 生产环境禁止使用的占位/弱密钥（与 docker-compose 等模板中的占位符对齐）
_KNOWN_INSECURE_SECRET_KEYS = frozenset(
    {
        "please-set-secret-key-in-production",
        "changeme",
        "secret",
        "your-secret-key",
    }
)

from .achievements_api import achievements_bp

# 导入所有API模块
from .auth_api import auth_bp
from .evaluation_api import evaluation_bp
from .favorites_api import favorites_bp
from .health_api import health_bp
from .learning_api import learning_bp
from .levels_api import levels_bp
from .plans_api import plans_bp
from .recommendation_api import recommendation_bp
from .utils import APIResponse
from .vocabulary_api import vocabulary_bp


class APILauncher:
    """
    API服务启动器类
    负责启动和管理API服务
    """

    def __init__(self):
        """初始化API启动器"""
        self.app = Flask(__name__, static_folder="../frontend", static_url_path="/")

        self._configure_app()
        self._configure_cors()

        # 注册所有蓝图
        self._register_all_blueprints()

        # 注册请求追踪中间件
        self._register_request_middleware()

        # 注册错误处理器与安全响应头
        self._register_error_handlers()
        self._register_security_headers()

    def _register_request_middleware(self):
        """注册请求追踪中间件"""

        @self.app.before_request
        def before_request():
            """请求开始前：生成请求ID、记录开始时间"""
            g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
            g.start_time = time.time()

            # 记录请求日志（排除静态文件和健康检查）
            if not request.path.startswith("/static") and request.path != "/api/health":
                logger.info("[%s] %s %s", g.request_id, request.method, request.path)

        @self.app.after_request
        def after_request(response):
            """请求结束后：添加请求ID头、记录响应时间"""
            # 添加请求ID到响应头
            if hasattr(g, "request_id"):
                response.headers["X-Request-ID"] = g.request_id

            # 记录响应时间
            if hasattr(g, "start_time"):
                elapsed_ms = (time.time() - g.start_time) * 1000
                response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"

                # 慢请求警告（>1秒）
                if elapsed_ms > 1000 and not request.path.startswith("/static"):
                    logger.warning(
                        "[%s] 慢请求: %s %s (%.2fms)",
                        g.request_id,
                        request.method,
                        request.path,
                        elapsed_ms,
                    )

            return response

    def _configure_app(self) -> None:
        """Flask 配置：密钥、请求体大小等（统一使用 strip 后的密钥，避免首尾空白通过校验却写入配置）"""
        secret = (os.environ.get("SECRET_KEY") or "").strip()
        if not secret:
            if APP_CONFIG.get("production"):
                raise RuntimeError(
                    "生产环境必须设置环境变量 SECRET_KEY（建议: openssl rand -hex 32）"
                )
            secret = "dev-" + token_hex(16)
            logger.warning("未设置 SECRET_KEY，已使用临时开发密钥；切勿用于生产")
        elif APP_CONFIG.get("production") and secret in _KNOWN_INSECURE_SECRET_KEYS:
            raise RuntimeError(
                "生产环境 SECRET_KEY 不能使用占位/弱密钥，请设置强随机值（例如 openssl rand -hex 32）"
            )

        self.app.config["SECRET_KEY"] = secret
        self.app.config["MAX_CONTENT_LENGTH"] = APP_CONFIG.get(
            "max_content_length", 16 * 1024 * 1024
        )
        # JSON 使用 UTF-8，避免中文乱码
        self.app.config["JSON_AS_ASCII"] = False

        # Swagger 配置（仅开发环境启用）
        if not APP_CONFIG.get("production"):
            self.app.config["SWAGGER"] = SWAGGER_CONFIG
            try:
                from flasgger import Swagger
                Swagger(self.app, template=SWAGGER_TEMPLATE)
                logger.info("Swagger UI 已启用: /api/docs")
            except ImportError:
                logger.warning("flasgger 未安装，Swagger UI 不可用")

    def _configure_cors(self) -> None:
        """跨域：生产环境请在 CORS_ORIGINS 中列出前端 Origin"""
        origins = APP_CONFIG.get("cors_origins") or ["*"]
        if origins == ["*"]:
            CORS(self.app)
        else:
            CORS(
                self.app,
                origins=origins,
                supports_credentials=True,
            )

    def _register_all_blueprints(self):
        """注册所有API蓝图"""
        self.app.register_blueprint(health_bp)
        self.app.register_blueprint(auth_bp)
        self.app.register_blueprint(vocabulary_bp)
        self.app.register_blueprint(learning_bp)
        self.app.register_blueprint(recommendation_bp)
        self.app.register_blueprint(plans_bp)
        self.app.register_blueprint(evaluation_bp)
        self.app.register_blueprint(levels_bp)
        self.app.register_blueprint(achievements_bp)
        self.app.register_blueprint(favorites_bp)

        @self.app.route("/")
        def index():
            return self.app.send_static_file("index.html")

    def _register_error_handlers(self):
        """注册错误处理器"""

        @self.app.errorhandler(404)
        def not_found(error):
            return APIResponse.error("接口不存在", 404)

        @self.app.errorhandler(500)
        def internal_error(error):
            return APIResponse.error("服务器内部错误", 500)

        @self.app.errorhandler(413)
        def request_entity_too_large(error):
            return APIResponse.error("请求体过大", 413)

        @self.app.errorhandler(Exception)
        def handle_exception(error):
            """全局异常处理"""
            logger.exception("[%s] 未处理异常: %s", getattr(g, "request_id", "N/A"), error)
            if APP_CONFIG.get("expose_error_details"):
                return APIResponse.error(f"服务器错误: {str(error)}", 500)
            return APIResponse.error("服务器内部错误，请稍后重试", 500)

    def _register_security_headers(self):
        """基础安全响应头（商用部署建议再配合 HTTPS 与反向代理）"""

        @self.app.after_request
        def add_security_headers(response):
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "DENY"
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
            response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
            # 仅在明确启用且生产模式下下发 HSTS（需站点全站 HTTPS）
            if APP_CONFIG.get("production") and os.getenv("ENABLE_HSTS", "").lower() in (
                "1",
                "true",
                "yes",
            ):
                response.headers["Strict-Transport-Security"] = (
                    "max-age=31536000; includeSubDomains"
                )
            return response

    def launch(self, host="0.0.0.0", port=5000, debug=True):
        """启动API服务"""
        logger.info("启动API服务: http://%s:%s (debug=%s)", host, port, debug)
        self.app.run(host=host, port=port, debug=debug)

    def shutdown(self):
        """关闭API服务"""
        try:
            logger.info("API服务已关闭")
        except Exception as e:
            logger.warning("关闭API服务时出错: %s", e)


def create_api_launcher():
    """创建API启动器实例"""
    return APILauncher()
