import asyncio
from typing import Any

from sanic import Sanic

from enhancers.information_enhancer import InformationEnhancerFactory
from parsers import get_parser
from parsers.base_models import ChunkData


async def worker(app: Sanic) -> dict[str, Any]:
    # 使用工厂获取合适的解析器

    enhancer_factory = InformationEnhancerFactory()
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
        chunk_list = parse_result.texts + parse_result.tables + parse_result.images + parse_result.formulas
        # 控制并发数量，防止访问量过大导致失败
        SEMAPHORE_LIMIT = 10  # 可根据实际情况调整
        semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)

        async def enhance_with_semaphore(chunk: ChunkData, semaphore: asyncio.Semaphore) -> ChunkData:
            async with semaphore:
                return await enhancer_factory.enhance_information(chunk)

        # 并发增强每个信息
        enhanced_chunk_list = await asyncio.gather(
            *(enhance_with_semaphore(chunk, semaphore) for chunk in chunk_list)
        )
        parse_result.texts = enhanced_chunk_list[:len(parse_result.texts)]
        parse_result.tables = enhanced_chunk_list[len(parse_result.texts):len(parse_result.texts) + len(parse_result.tables)]
        parse_result.images = enhanced_chunk_list[len(parse_result.texts) + len(parse_result.tables):len(parse_result.texts) + len(parse_result.tables) + len(parse_result.images)]
        parse_result.formulas = enhanced_chunk_list[len(parse_result.texts) + len(parse_result.tables) + len(parse_result.images):]
        return parse_result.model_dump(mode="json")
