import asyncio
from typing import Any

from sanic import Sanic

from enhancers.information_enhancer import InformationEnhancerFactory
from parsers.document_parser import DocumentData
from parsers.document_parser_factory import DocumentParserFactory


async def worker(app: Sanic) -> dict[str, Any]:
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
        parse_result = await parser_factory.parse_document(file_path)
        if not parse_result.success:
            continue
        chunk_list = parse_result.document
        # 控制并发数量，防止访问量过大导致失败
        SEMAPHORE_LIMIT = 10  # 可根据实际情况调整
        semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)

        async def enhance_with_semaphore(chunk: DocumentData, semaphore: asyncio.Semaphore) -> DocumentData:
            async with semaphore:
                return await enhancer_factory.enhance_information(chunk)

        # 并发增强每个信息
        enhanced_chunk_list = await asyncio.gather(
            *(enhance_with_semaphore(chunk, semaphore) for chunk in chunk_list)
        )
        parse_result.document = enhanced_chunk_list
        return parse_result.model_dump(mode="json")
