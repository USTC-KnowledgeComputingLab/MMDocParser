import boto3
from botocore.client import Config

# MinIO 配置
endpoint_url = "http://localhost:9000"
access_key = "minio"
secret_key = "minio123"
bucket_name = "sci-assistant"
object_name = "my-uploaded-file.pdf"
file_path = "/home/lnp/Multimodal-Analysis/dataflow.drawio.pdf"

# 创建 S3 客户端
s3 = boto3.client(
    "s3",
    endpoint_url=endpoint_url,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1"
)

try:
    # 上传文件
    s3.upload_file(file_path, bucket_name, object_name)
    print(f"✅ 上传成功: {object_name}")

    # 生成预签名 URL（有效期 1 小时）
    presigned_url = s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket_name, "Key": object_name},
        ExpiresIn=3600  # 有效期（秒）
    )
    print(f"🔗 预签名下载链接（1小时有效）:\n{presigned_url}")

except Exception as e:
    print(f"❌ 上传失败: {e}")
