import base64
import logging

from config import settings

logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """验证错误"""
    pass

def validate_file_info(file_info: dict) -> tuple[str, bytes]:
    """验证文件信息"""
    filename = file_info.get("name")
    content_base64 = file_info.get("content")

    if not filename:
        raise ValidationError("文件名不能为空")

    if not content_base64:
        raise ValidationError("文件内容不能为空")

    # 检查文件大小
    try:
        content = base64.b64decode(content_base64)
        if len(content) > settings.MAX_FILE_SIZE:
            raise ValidationError(f"文件大小超过限制: {len(content)} > {settings.MAX_FILE_SIZE}")
    except Exception as e:
        raise ValidationError("无效的base64编码") from e

    # 检查文件格式
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
    if file_ext not in [fmt.lstrip('.') for fmt in settings.SUPPORTED_FORMATS]:
        raise ValidationError(f"不支持的文件格式: {file_ext}")

    return filename, content

def validate_template_type(template_type: str) -> str:
    """验证模板类型"""
    valid_types = ["化学", "机械", "电学"]
    if template_type not in valid_types:
        raise ValidationError(f"无效的模板类型: {template_type}，支持的类型: {valid_types}")
    return template_type

def validate_task_type(task_type: str) -> str:
    """验证任务类型"""
    valid_types = ["document_analysis", "template_extraction"]
    if task_type not in valid_types:
        raise ValidationError(f"无效的任务类型: {task_type}，支持的类型: {valid_types}")
    return task_type

def validate_upload_payload(payload: dict) -> dict:
    """验证上传请求载荷"""
    if not payload:
        raise ValidationError("请求载荷不能为空")

    files = payload.get("files", [])
    if isinstance(files, dict):
        files = [files]
    if not files:
        raise ValidationError("文件列表不能为空")

    if len(files) > settings.MAX_FILES_PER_REQUEST:
        raise ValidationError(f"文件数量超过限制: {len(files)} > {settings.MAX_FILES_PER_REQUEST}")

    # 验证每个文件
    validated_files = []
    for file_info in files:
        try:
            filename, content = validate_file_info(file_info)
            validated_files.append((filename, content))
        except ValidationError as e:
            raise ValidationError(f"文件 {file_info.get('name', 'unknown')} 验证失败") from e

    return {
        "files": validated_files
    }
