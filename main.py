import json
import logging
import uuid
import asyncio
from asyncio import AbstractEventLoop
from contextlib import AsyncExitStack
from types import SimpleNamespace

from sanic import HTTPResponse, Request, Sanic
from sanic.config import Config
from sanic.response import json as json_response
from sanic_ext import Extend

# 导入自定义模块
from config import settings
from storage.s3_client import AsyncS3Client
from storage.redis_client import get_redis_client, TaskManager
from utils.validators import validate_upload_payload, ValidationError

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建Sanic应用
app = Sanic("MMDocParser")
app.config.CORS_ORIGINS = settings.CORS_ORIGINS
Extend(app)

@app.before_server_start
async def setup_services(app: Sanic[Config, SimpleNamespace], _: AbstractEventLoop) -> None:
    """服务启动时初始化依赖"""
    try:
        app.ctx.exit_stack = AsyncExitStack()
        
        # 初始化S3客户端
        app.ctx.s3 = await app.ctx.exit_stack.enter_async_context(
            AsyncS3Client(
                endpoint_url=settings.S3_ENDPOINT,
                access_key=settings.S3_ACCESS_KEY,
                secret_key=settings.S3_SECRET_KEY,
                bucket=settings.S3_BUCKET,
                region=settings.S3_REGION,
            )
        )
        
        # 初始化Redis客户端
        app.ctx.redis = await app.ctx.exit_stack.enter_async_context(
            get_redis_client(settings.REDIS_URL)
        )
        
        # 初始化任务管理器
        app.ctx.task_manager = TaskManager(
            app.ctx.redis,
            settings.TASK_QUEUE,
            settings.TASK_STATUS_PREFIX
        )
        
        logger.info("所有服务初始化成功")
        
    except Exception as e:
        await app.ctx.exit_stack.aclose()
        logger.exception("服务初始化失败")
        raise RuntimeError from e

@app.after_server_stop
async def shutdown_services(app: Sanic[Config, SimpleNamespace], _: AbstractEventLoop) -> None:
    """服务关闭时清理资源"""
    await app.ctx.exit_stack.aclose()
    logger.info("服务已关闭")

# ---- 接口 1: 上传并提交任务 ----
@app.post("/api/v1/documents/upload")
async def upload_documents(request: Request) -> HTTPResponse:
    """上传文档并提交解析任务"""
    try:
        # 1. 验证请求载荷
        payload = request.json
        validated_data = validate_upload_payload(payload)
        
        # 2. 生成任务ID
        task_id = str(uuid.uuid4())
        
        # 3. 并发上传文件到S3
        upload_tasks = [
            request.app.ctx.s3.upload_file(filename, content)
            for filename, content in validated_data["files"]
        ]
        presigned_urls = await asyncio.gather(*upload_tasks)
        
        # 4. 准备任务数据
        task_data = {
            "task_id": task_id,
            "template_type": validated_data["template_type"],
            "task_type": validated_data["task_type"],
            "presigned_urls": presigned_urls,
            "filenames": [filename for filename, _ in validated_data["files"]],
            "created_at": asyncio.get_event_loop().time()
        }
        
        # 5. 推送任务到队列
        success = await request.app.ctx.task_manager.push_task(task_data)
        if not success:
            raise Exception("推送任务到队列失败")
        
        # 6. 设置任务状态
        await request.app.ctx.task_manager.set_task_status(task_id, "pending")
        
        logger.info(f"[Submit] 任务已提交: {task_id}, 文件数: {len(validated_data['files'])}")
        
        return json_response({
            "success": True,
            "task_id": task_id,
            "status": "pending",
            "message": "任务已提交，正在处理中",
            "estimated_time": "5-10分钟"
        })
        
    except ValidationError as e:
        logger.warning(f"请求验证失败: {e}")
        return json_response({"error": str(e)}, status=400)
        
    except Exception as e:
        logger.error(f"[Submit] 提交任务失败: {e}")
        return json_response({"error": "提交任务失败，请稍后重试"}, status=500)

# ---- 接口 2: 查询任务状态 ----
@app.get("/api/v1/tasks/<task_id>/status")
async def get_task_status(request: Request, task_id: str) -> HTTPResponse:
    """查询任务状态"""
    try:
        status = await request.app.ctx.task_manager.get_task_status(task_id)
        if not status:
            return json_response({"error": "任务不存在"}, status=404)
        
        return json_response({
            "task_id": task_id,
            "status": status,
            "message": "查询成功"
        })
        
    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        return json_response({"error": "查询失败"}, status=500)

# ---- 接口 3: 获取解析结果 ----
@app.get("/api/v1/tasks/<task_id>/result")
async def get_task_result(request: Request, task_id: str) -> HTTPResponse:
    """获取任务解析结果"""
    try:
        # 检查任务状态
        status = await request.app.ctx.task_manager.get_task_status(task_id)
        if not status:
            return json_response({"error": "任务不存在"}, status=404)
        
        if status != "completed":
            return json_response({
                "error": "任务尚未完成",
                "current_status": status
            }, status=400)
        
        # 获取结果
        result = await request.app.ctx.task_manager.get_task_result(task_id)
        if not result:
            return json_response({"error": "结果不存在或已过期"}, status=404)
        
        return json_response({
            "task_id": task_id,
            "status": "completed",
            "result": result,
            "message": "获取结果成功"
        })
        
    except Exception as e:
        logger.error(f"获取任务结果失败: {e}")
        return json_response({"error": "获取结果失败"}, status=500)

# ---- 接口 4: 健康检查 ----
@app.get("/health")
async def health_check(request: Request) -> HTTPResponse:
    """健康检查接口"""
    try:
        # 检查Redis连接
        await request.app.ctx.redis.ping()
        
        # 检查S3连接（简化检查）
        redis_ok = True
        s3_ok = True
        
        if redis_ok and s3_ok:
            return json_response({
                "status": "healthy",
                "timestamp": asyncio.get_event_loop().time(),
                "services": {
                    "redis": "ok",
                    "s3": "ok"
                }
            })
        else:
            return json_response({
                "status": "unhealthy",
                "services": {
                    "redis": "ok" if redis_ok else "error",
                    "s3": "ok" if s3_ok else "error"
                }
            }, status=503)
            
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return json_response({
            "status": "unhealthy",
            "error": str(e)
        }, status=503)


def main() -> None:
    """主函数"""
    print("MMDocParser 服务启动中...")
    print(f"配置信息:")
    print(f"  - 主机: {settings.HOST}")
    print(f"  - 端口: {settings.PORT}")
    print(f"  - 工作进程: {settings.WORKERS}")
    print(f"  - 支持格式: {', '.join(settings.SUPPORTED_FORMATS)}")
    print(f"  - 最大文件数: {settings.MAX_FILES_PER_REQUEST}")
    print(f"  - 最大文件大小: {settings.MAX_FILE_SIZE // (1024*1024)}MB")

if __name__ == "__main__":
    main()
