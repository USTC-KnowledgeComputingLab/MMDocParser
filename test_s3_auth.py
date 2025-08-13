import boto3
from botocore.exceptions import ClientError, NoCredentialsError

def test_s3_authentication():
    """测试S3认证"""
    
    # 配置信息
    endpoint_url = "https://s3.kclab.cloud"
    access_key = "B2sE0fKv1Y1lOpZtge5u"
    secret_key = "JRx4MbrMbfUfQjIEm7speT52kQgjt0zafvlAuYxW"
    bucket_name = "bucket-78134-shared"
    region = "us-east-1"
    
    print("=== S3认证测试 ===")
    print(f"端点: {endpoint_url}")
    print(f"存储桶: {bucket_name}")
    print(f"区域: {region}")
    print()
    
    try:
        # 创建S3客户端
        s3_client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        
        print("1. 测试列出存储桶...")
        response = s3_client.list_buckets()
        buckets = [b['Name'] for b in response['Buckets']]
        print(f"   可用存储桶: {buckets}")
        
        if bucket_name in buckets:
            print(f"\n2. 测试访问存储桶: {bucket_name}")
            try:
                response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=5)
                if 'Contents' in response:
                    print(f"   存储桶内容数量: {len(response['Contents'])}")
                    for obj in response['Contents'][:3]:
                        print(f"     - {obj['Key']} ({obj['Size']} bytes)")
                else:
                    print("   存储桶为空")
            except ClientError as e:
                print(f"   访问存储桶失败: {e}")
        
        print(f"\n3. 测试上传小文件...")
        test_content = b"Hello, S3 Test!"
        test_key = "test/connectivity_test.txt"
        
        try:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=test_key,
                Body=test_content,
                ContentType='text/plain'
            )
            print("   上传成功!")
            
            # 测试下载
            response = s3_client.get_object(Bucket=bucket_name, Key=test_key)
            downloaded_content = response['Body'].read()
            print(f"   下载成功: {downloaded_content}")
            
            # 清理测试文件
            s3_client.delete_object(Bucket=bucket_name, Key=test_key)
            print("   清理成功!")
            
        except ClientError as e:
            print(f"   上传/下载失败: {e}")
            
    except NoCredentialsError:
        print("错误: 无法找到AWS凭证")
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        print(f"错误: {error_code} - {error_message}")
    except Exception as e:
        print(f"未知错误: {e}")

if __name__ == "__main__":
    test_s3_authentication()
