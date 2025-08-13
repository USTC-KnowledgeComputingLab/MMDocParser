#!/usr/bin/env python3
"""
MMDocParser 服务启动脚本
"""

import logging

from config import settings
from main import app

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 启动服务
    app.run(
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        debug=False,
        access_log=True
    )
