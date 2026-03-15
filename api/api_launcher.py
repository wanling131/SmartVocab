"""
API服务启动器
负责启动和管理API服务
"""

from flask import Flask
from flask_cors import CORS

# 导入所有API模块
from .auth_api import auth_bp
from .vocabulary_api import vocabulary_bp
from .learning_api import learning_bp
from .recommendation_api import recommendation_bp
from .utils import APIResponse

class APILauncher:
    """
    API服务启动器类
    负责启动和管理API服务
    """
    
    def __init__(self):
        """初始化API启动器"""
        self.app = Flask(__name__, static_folder='../frontend', static_url_path='/')
        CORS(self.app)  # 允许跨域请求
        
        # 注册所有蓝图
        self._register_all_blueprints()
        
        # 注册错误处理器
        self._register_error_handlers()
    
    def _register_all_blueprints(self):
        """注册所有API蓝图"""
        # 按模块顺序注册蓝图
        self.app.register_blueprint(auth_bp)           # 1. 用户认证模块
        self.app.register_blueprint(vocabulary_bp)    # 2. 词汇学习模块
        self.app.register_blueprint(learning_bp)      # 3. 学习记录模块
        self.app.register_blueprint(recommendation_bp) # 4. 推荐系统模块
        
        # 根路径
        @self.app.route('/')
        def index():
            return self.app.send_static_file('index.html')
    
    def _register_error_handlers(self):
        """注册错误处理器"""
        
        @self.app.errorhandler(404)
        def not_found(error):
            return APIResponse.error('接口不存在', 404)
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return APIResponse.error('服务器内部错误', 500)
    
    def launch(self, host='0.0.0.0', port=5000, debug=True):
        """启动API服务"""
        print(f"启动API服务: http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)
    
    def shutdown(self):
        """关闭API服务"""
        try:
            print("API服务已关闭")
        except Exception as e:
            print(f"关闭API服务时出错: {e}")

def create_api_launcher():
    """创建API启动器实例"""
    return APILauncher()
