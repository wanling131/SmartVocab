#!/usr/bin/env python
"""
SmartVocab 命令工具
用法: python commands.py <命令>
"""

import subprocess
import sys


def main():
    commands = {
        "run": ["python", "main.py"],
        "test": ["python", "-m", "pytest", "tests/", "-v"],
        "test-fast": ["python", "-m", "pytest", "tests/", "-v"],
        "db": ["python", "-c", "from tools.database import test_connection; test_connection()"],
    }

    if len(sys.argv) < 2:
        print("用法: python commands.py <命令>")
        print("可用命令:")
        for cmd in commands:
            print(f"  {cmd}")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd not in commands:
        print(f"未知命令: {cmd}")
        print("可用命令:", ", ".join(commands.keys()))
        sys.exit(1)

    # 设置环境变量（快速测试跳过深度学习）
    if cmd == "test-fast":
        import os
        os.environ["SMARTVOCAB_SKIP_DL_INIT"] = "1"

    subprocess.run(commands[cmd])


if __name__ == "__main__":
    main()