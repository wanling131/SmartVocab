"""
WSGI 入口：供 Gunicorn / uWSGI 等生产级服务器加载。

用法示例::
    gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 wsgi:app
"""

import os
import sys

# 项目根目录加入路径
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config import configure_logging

configure_logging()

from api.api_launcher import create_api_launcher

_launcher = create_api_launcher()
app = _launcher.app
