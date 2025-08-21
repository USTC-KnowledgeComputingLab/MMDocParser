import asyncio
from typing import Any

from sanic import Sanic

from enhancers import get_enhancer
from parsers import ChunkData, ChunkType, get_parser, load_all_parsers


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
        # 控制并发数量，防止访问量过大导致失败
        SEMAPHORE_LIMIT = 10
        semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)

        async def enhance_with_semaphore(chunk: ChunkData, semaphore: asyncio.Semaphore) -> ChunkData:
            async with semaphore:
                enhancer = get_enhancer(ChunkType(chunk.type))
                if not enhancer:
                    return chunk
                return await enhancer.enhance(chunk)

        text_tasks = [enhance_with_semaphore(chunk, semaphore) for chunk in parse_result.texts]
        table_tasks = [enhance_with_semaphore(chunk, semaphore) for chunk in parse_result.tables]
        image_tasks = [enhance_with_semaphore(chunk, semaphore) for chunk in parse_result.images]
        formula_tasks = [enhance_with_semaphore(chunk, semaphore) for chunk in parse_result.formulas]

        text_chunk_list = await asyncio.gather(*text_tasks)
        table_chunk_list = await asyncio.gather(*table_tasks)
        image_chunk_list = await asyncio.gather(*image_tasks)
        formula_chunk_list = await asyncio.gather(*formula_tasks)

        parse_result.texts = text_chunk_list
        parse_result.tables = table_chunk_list
        parse_result.images = image_chunk_list
        parse_result.formulas = formula_chunk_list
        return parse_result.model_dump(mode="json")
