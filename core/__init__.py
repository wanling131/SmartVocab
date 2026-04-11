"""
通用导入工具
提供统一的路径设置和导入功能
"""

import os
import sys


def setup_project_path():
    """
    设置项目根目录到Python路径
    用于core目录下的模块导入
    """
    # 获取项目根目录（当前文件的3级父目录）
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    if project_root not in sys.path:
        sys.path.append(project_root)


# 自动设置路径
setup_project_path()
