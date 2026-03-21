import sys
import os
import signal
import time
import logging
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(__file__))

# 导入配置和API
from config import APP_CONFIG, configure_logging
from api.api_launcher import create_api_launcher
from tools.database import test_connection, get_pool_status

configure_logging()
logger = logging.getLogger(__name__)

class SmartVocabApp:
    """
    智能词汇学习系统主应用类
    负责系统初始化、启动和关闭
    """
    
    def __init__(self):
        """
        初始化应用
        """
        self.api_launcher = None
        self.is_running = False
        self.start_time = None
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def initialize(self):
        """
        初始化系统
        """
        logger.info("=== SmartVocab 智能词汇学习系统 ===")
        logger.info("启动时间: %s", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        # 检查数据库连接
        logger.info("1. 检查数据库连接...")
        if not test_connection():
            logger.error("数据库连接失败，请检查数据库配置")
            return False
        
        # 显示连接池状态
        logger.info("2. 检查连接池状态...")
        pool_status = get_pool_status()
        logger.info("连接池状态: %s", pool_status)
        
        if pool_status.get('status') == 'active':
            logger.info("连接池已启用，系统性能优化")
        else:
            logger.info("连接池未启用，使用直连模式")
        logger.info("数据库连接正常")
        
        # 设置静默模式，避免后续模块重复打印连接信息
        # 注意：使用连接池时不需要手动管理连接计数
        
        # 初始化API启动器
        logger.info("3. 初始化API服务...")
        try:
            self.api_launcher = create_api_launcher()
            logger.info("API服务初始化成功")
        except Exception as e:
            logger.exception("API服务初始化失败: %s", e)
            return False
        
        logger.info("4. 系统初始化完成")
        return True
    
    def run(self):
        """
        运行应用
        """
        if not self.api_launcher:
            logger.error("系统未正确初始化，无法启动")
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        
        try:
            # 启动API服务
            self.api_launcher.launch(
                host=APP_CONFIG['host'],
                port=APP_CONFIG['port'],
                debug=APP_CONFIG.get('debug', True)
            )
        except KeyboardInterrupt:
            logger.info("收到停止信号...")
        except Exception as e:
            logger.exception("服务运行出错: %s", e)
        finally:
            self.shutdown()
    
    def shutdown(self):
        """
        关闭应用
        """
        if not self.is_running:
            return
        
        logger.info("正在关闭SmartVocab服务...")
        
        # 计算运行时间
        if self.start_time:
            run_time = datetime.now() - self.start_time
            logger.info("服务运行时间: %s", run_time)
        
        # 关闭API服务
        if self.api_launcher:
            try:
                self.api_launcher.shutdown()
            except Exception as e:
                logger.warning("关闭API服务时出错: %s", e)
        
        self.is_running = False
        logger.info("SmartVocab服务已完全关闭")
    
    def _signal_handler(self, signum, frame):
        """
        信号处理器
        """
        logger.info("收到信号 %s，正在关闭服务...", signum)
        self.shutdown()
        sys.exit(0)
    
    def get_status(self):
        """
        获取系统状态
        """
        return {
            'is_running': self.is_running,
            'start_time': self.start_time,
            'uptime': datetime.now() - self.start_time if self.start_time else None,
            'api_available': self.api_launcher is not None
        }

def main():
    """
    主函数
    """
    app = SmartVocabApp()
    
    # 初始化系统
    if not app.initialize():
        logger.error("系统初始化失败，程序退出")
        sys.exit(1)
    
    # 运行应用
    app.run()

if __name__ == "__main__":
    main()
