#!/usr/bin/env python3
"""
DJI 模块入口
直接运行此模块以启动诊断工具
"""

import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.dji_tool import main

if __name__ == '__main__':
    main()
