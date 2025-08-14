from typing import Any
from enhancers.information_enhancer import InformationEnhancerFactory
import asyncio
from sanic import Sanic
from parsers.document_parser import DocumentParserFactory
from config import settings

async def worker(app: Sanic) -> list[dict[str, Any]]:
    # 使用工厂获取合适的解析器
    parser_factory = DocumentParserFactory()
    enhancer_factory = InformationEnhancerFactory()
    redis = app.ctx.redis
    while True:
        task = await redis.get_task()
        if not task:
            await asyncio.sleep(1)
            continue
        file_path = task.get("file_path")
        information_list = await parser_factory.parse_document(file_path)
        # 控制并发数量，防止访问量过大导致失败
        SEMAPHORE_LIMIT = 10  # 可根据实际情况调整
        semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)

        async def enhance_with_semaphore(info):
            async with semaphore:
                return await enhancer_factory.enhance_information(info)

        # 并发增强每个信息
        enhanced_information_list = await asyncio.gather(
            *(enhance_with_semaphore(info) for info in information_list)
        )
        return enhanced_information_list