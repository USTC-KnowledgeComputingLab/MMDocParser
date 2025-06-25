import asyncio
import aio_pika 
from aio_pika import Message, IncomingMessage
from src.message.parse.v1.pdf_parser_pb2 import PDFParserInput, PDFParserOutput
from src.message.common.v1.s3_pb2 import S3File
import logging
logging.basicConfig(level=logging.INFO)

AMQP_URI = "amqp://sci-assistant:sci-1234@localhost:5671/%2F?heartbeat=60"
INPUT_QUEUE = "PARSINGINPUT"
OUTPUT_QUEUE = "PARSINGOUTPUT"


async def send_task(channel, s3_key: str):
    message = PDFParserInput()
    message.file.CopyFrom(S3File(key=s3_key))
    body = message.SerializeToString()

    await channel.default_exchange.publish(
        Message(body=body, content_type="application/x-protobuf"),
        routing_key=INPUT_QUEUE
    )
    print(f"[SEND] Sent PDFParserInput with key: {s3_key}")


async def on_result(message: IncomingMessage):
    async with message.process():
        output = PDFParserOutput()
        output.ParseFromString(message.body)

        print(f"\n[RECEIVED] Output file key: {output.file.key}")
        print(f"Title: {output.metadata.title}")
        print(f"Segments ({len(output.segments)}):")
        for seg in output.segments[:5]:  # 打印前5个
            print(f"  ID: {seg.id}, Type: {seg.type}, Content: {seg.content[:100]}, Images: {seg.image}")


async def main():
    connection = await aio_pika.connect_robust(AMQP_URI)
    channel = await connection.channel()

    # 开始监听输出队列
    await channel.set_qos(prefetch_count=10)
    await channel.declare_queue(OUTPUT_QUEUE, durable=True)
    await channel.declare_queue(INPUT_QUEUE, durable=True)

    queue = await channel.declare_queue(OUTPUT_QUEUE, durable=True)
    await queue.consume(on_result)

    # 发送任务（替换成你需要解析的 PDF 文件 key）
    await send_task(channel, "my-uploaded-file.pdf")

    print(" [*] 等待解析结果。按 Ctrl+C 退出")
    await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
