"""
API接口模块（历史备份 / 已弃用）

说明：当前生产入口请使用 ``api_launcher.APILauncher``（见 ``main.py``），
本文件保留为旧版单文件路由参考，**不再随新接口维护**。
遗忘曲线、评测、学习计划等接口已迁移至各 Blueprint（learning_api、evaluation_api、plans_api 等）。
"""

# 导入配置常量
from config import LEARNING_PARAMS

from flask import Flask, request, jsonify
from flask_cors import CORS
from functools import wraps

# 导入核心模块
from core.auth.user_auth import UserAuth
from core.vocabulary.vocabulary_learning_manager import VocabularyLearningManager
from core.learning.learning_record_manager import LearningRecordManager
from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager
from core.recommendation.recommendation_engine import RecommendationEngine

class APIRouter:
    """
    API路由类
    提供完整的RESTful API服务
    """
    
    def __init__(self):
        """初始化API路由"""
        self.app = Flask(__name__, static_folder='../frontend', static_url_path='/')
        CORS(self.app)  # 允许跨域请求
        
        # 初始化核心模块
        self.user_auth = UserAuth()
        self.vocabulary_manager = VocabularyLearningManager()
        self.learning_record_manager = LearningRecordManager()
        self.forgetting_curve_manager = ForgettingCurveManager()
        self.recommendation_engine = RecommendationEngine()
        
        # 注册所有路由
        self._register_all_routes()
    
    def _create_response(self, success=True, data=None, message="操作成功", status_code=200):
        """创建统一API响应"""
        response = {
            'success': success,
            'message': message,
            'data': data
        }
        return jsonify(response), status_code
    
    def _handle_api_error(self, func):
        """API错误处理装饰器"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                return self._create_response(False, None, f'服务器错误: {str(e)}', 500)
        return wrapper
    
    def _register_all_routes(self):
        """注册所有API路由"""
        # 根路径
        @self.app.route('/')
        def index():
            return self.app.send_static_file('index.html')
        
        # 按模块顺序注册路由
        self._register_auth_routes()           # 1. 用户认证模块
        self._register_vocabulary_routes()    # 2. 词汇学习模块
        self._register_learning_routes()      # 3. 学习记录模块
        self._register_recommendation_routes() # 4. 推荐系统模块
        self._register_statistics_routes()     # 5. 统计模块
        
        # 错误处理
        self._register_error_handlers()
    
    # ==================== 1. 用户认证模块 ====================
    def _register_auth_routes(self):
        """用户认证相关路由"""
        
        @self.app.route('/api/auth/register', methods=['POST'])
        @self._handle_api_error
        def register():
            """用户注册"""
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            email = data.get('email')
            
            if not username or not password:
                return self._create_response(False, None, '用户名和密码不能为空', 400)
            
            result = self.user_auth.register(username, password, email)
            if result['success']:
                return self._create_response(True, result.get('user_id'), result['message'])
            else:
                return self._create_response(False, None, result['message'], 400)
        
        @self.app.route('/api/auth/login', methods=['POST'])
        @self._handle_api_error
        def login():
            """用户登录"""
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return self._create_response(False, None, '用户名和密码不能为空', 400)
            
            result = self.user_auth.login(username, password)
            if result['success']:
                return self._create_response(True, result.get('user_id'), result['message'])
            else:
                return self._create_response(False, None, result['message'], 401)
        
        # 用户管理API已移除 - 当前版本不需要用户信息管理功能
    
    # ==================== 2. 词汇学习模块 ====================
    def _register_vocabulary_routes(self):
        """词汇学习相关路由"""
        
        @self.app.route('/api/vocabulary/start-session', methods=['POST'])
        @self._handle_api_error
        def start_learning_session():
            """开始学习会话"""
            data = request.get_json()
            user_id = data.get('user_id')
            difficulty_level = data.get('difficulty_level')
            word_count = data.get('word_count', LEARNING_PARAMS["default_word_count"])
            
            if not user_id:
                return self._create_response(False, None, '用户ID不能为空', 400)
            
            result = self.vocabulary_manager.start_learning_session(user_id, difficulty_level, word_count)
            if result['success']:
                return self._create_response(True, result.get('session_info'), result['message'])
            else:
                return self._create_response(False, None, result['message'], 400)
        
        @self.app.route('/api/vocabulary/current-word', methods=['POST'])
        @self._handle_api_error
        def get_current_word():
            """获取当前学习的单词"""
            data = request.get_json()
            session_info = data.get('session_info')
            
            if not session_info:
                return self._create_response(False, None, '会话信息不能为空', 400)
            
            word_info = self.vocabulary_manager.get_current_word(session_info)
            if word_info:
                return self._create_response(True, word_info, "获取单词成功")
            else:
                return self._create_response(False, None, '没有更多单词', 404)
        
        @self.app.route('/api/vocabulary/submit-answer', methods=['POST'])
        @self._handle_api_error
        def submit_answer():
            """提交答案"""
            data = request.get_json()
            user_id = data.get('user_id')
            word_id = data.get('word_id')
            user_answer = data.get('user_answer')
            correct_answer = data.get('correct_answer')
            response_time = data.get('response_time', 0)
            question_type = data.get('question_type', 'translation')
            mastery_override = data.get('mastery_override')
            
            if not all([user_id, word_id, user_answer, correct_answer]):
                return self._create_response(False, None, '所有字段都不能为空', 400)
            
            result = self.vocabulary_manager.submit_answer(
                user_id, word_id, user_answer, correct_answer, response_time, question_type, mastery_override
            )
            if result['success']:
                return self._create_response(True, result, result['message'])
            else:
                return self._create_response(False, None, result['message'], 400)
        
        @self.app.route('/api/vocabulary/start-review-session', methods=['POST'])
        @self._handle_api_error
        def start_review_session():
            """开始复习会话"""
            data = request.get_json()
            user_id = data.get('user_id')
            word_count = data.get('word_count', LEARNING_PARAMS["default_word_count"])
            
            if not user_id:
                return self._create_response(False, None, '用户ID不能为空', 400)
            
            result = self.vocabulary_manager.start_review_session(user_id, word_count)
            if result['success']:
                return self._create_response(True, result.get('session_info'), result['message'])
            else:
                return self._create_response(False, None, result['message'], 400)
        
        # 测试和复习单词API已移除 - 当前版本使用start-review-session替代
    
    # ==================== 3. 学习记录模块 ====================
    def _register_learning_routes(self):
        """学习记录相关路由"""
        
        @self.app.route('/api/learning/progress/<int:user_id>', methods=['GET'])
        @self._handle_api_error
        def get_learning_progress(user_id):
            """获取学习进度"""
            progress = self.vocabulary_manager.get_learning_progress(user_id)
            return self._create_response(True, progress, "获取学习进度成功")
        
        @self.app.route('/api/learning/statistics/<int:user_id>', methods=['GET'])
        @self._handle_api_error
        def get_learning_statistics(user_id):
            """获取学习统计"""
            days = request.args.get('days', 7, type=int)
            statistics = self.vocabulary_manager.get_learning_statistics(user_id, days)
            return self._create_response(True, statistics, "获取学习统计成功")
        
        @self.app.route('/api/learning/records/<int:user_id>', methods=['GET'])
        @self._handle_api_error
        def get_learning_records(user_id):
            """获取学习记录"""
            limit = request.args.get('limit', type=int)
            offset = request.args.get('offset', 0, type=int)
            
            records = self.learning_record_manager.get_user_learning_records(user_id, limit, offset)
            return self._create_response(True, records, "获取学习记录成功")
    
    # ==================== 4. 推荐系统模块 ====================
    def _register_recommendation_routes(self):
        """推荐系统相关路由"""
        
        @self.app.route('/api/recommendations/<int:user_id>', methods=['GET'])
        @self._handle_api_error
        def get_recommendations(user_id):
            """获取推荐单词"""
            limit = request.args.get('limit', LEARNING_PARAMS["default_recommendation_limit"], type=int)
            algorithm = request.args.get('algorithm', 'mixed')
            
            recommendations = self.recommendation_engine.get_recommendations(user_id, limit, algorithm)
            return self._create_response(True, recommendations, "获取推荐成功")
        
        # 深度学习推荐API已移除 - 当前版本使用混合推荐算法
        # 如需深度学习功能，可在未来版本中重新添加
    
    # ==================== 5. 统计模块 ====================
    def _register_statistics_routes(self):
        """统计相关路由"""
        
        @self.app.route('/api/statistics/forgetting-curve/<int:user_id>', methods=['GET'])
        @self._handle_api_error
        def get_forgetting_curve_data(user_id):
            """获取遗忘曲线数据"""
            days = request.args.get('days', LEARNING_PARAMS["days_trend_analysis"], type=int)
            
            curve_data = self.forgetting_curve_manager.get_forgetting_curve_data(user_id, days)
            return self._create_response(True, curve_data, "获取遗忘曲线数据成功")
        
        # 记忆保持率预测API已移除 - 当前版本专注于遗忘曲线分析
    
    # ==================== 错误处理 ====================
    def _register_error_handlers(self):
        """注册错误处理器"""
        
        @self.app.errorhandler(404)
        def not_found(error):
            return self._create_response(False, None, '接口不存在', 404)
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return self._create_response(False, None, '服务器内部错误', 500)
    
    # ==================== 服务管理 ====================
    def run(self, host='0.0.0.0', port=5000, debug=True):
        """启动API服务"""
        self.app.run(host=host, port=port, debug=debug)
    
    def close(self):
        """关闭所有数据库连接"""
        try:
            print("所有数据库连接已关闭（连接池自动管理）")
        except Exception as e:
            print(f"关闭数据库连接时出错: {e}")

def main():
    """主函数 - 启动API服务"""
    print("=== SmartVocab API服务 ===")
    
    # 创建API路由器
    api_router = APIRouter()
    
    try:
        # 启动服务
        api_router.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        print("\n正在关闭服务...")
    finally:
        # 关闭所有连接
        api_router.close()

if __name__ == "__main__":
    main()