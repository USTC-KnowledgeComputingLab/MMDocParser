import os

import dotenv

dotenv.load_dotenv()

class Settings:
    """应用配置类"""
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    WORKERS: int = int(os.getenv("WORKERS", "4"))

    # CORS配置
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # 文件限制
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(100 * 1024 * 1024)))  # 100MB
    SUPPORTED_FORMATS: list[str] = ["pdf", "docx", "doc","xlsx"]

    # Redis配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    TASK_QUEUE: str = os.getenv("TASK_QUEUE", "document_parsing_queue")
    TASK_STATUS_PREFIX: str = os.getenv("TASK_STATUS_PREFIX", "task_status")

    # S3配置
    S3_ENDPOINT: str = os.getenv("S3_ENDPOINT", "http://localhost:9000")
    S3_ACCESS_KEY: str = os.getenv("S3_ACCESS_KEY", "minioadmin")
    S3_SECRET_KEY: str = os.getenv("S3_SECRET_KEY", "minioadmin")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "documents")
    S3_REGION: str = os.getenv("S3_REGION", "us-east-1")

    # 任务配置
    MAX_FILES_PER_REQUEST: int = int(os.getenv("MAX_FILES_PER_REQUEST", "20"))
    TASK_TIMEOUT: int = int(os.getenv("TASK_TIMEOUT", "3600"))  # 1小时

settings = Settings()
