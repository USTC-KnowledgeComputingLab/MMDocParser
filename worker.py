import asyncio
from typing import Any

from sanic import Sanic

from parsers import (
    get_parser,
    load_all_parsers,
)


async def worker(app: Sanic) -> dict[str, Any]:
    # 使用工厂获取合适的解析器
    load_all_parsers()
    redis = app.ctx.redis
    while True:
        task = await redis.get_task()
        if not task:
            await asyncio.sleep(1)
            continue
        file_path = task.get("file_path")
        parser = get_parser(file_path)
        if not parser:
            continue
        parse_result = await parser.parse(file_path)
        if not parse_result.success:
            continue
        return parse_result.model_dump(mode="json")
