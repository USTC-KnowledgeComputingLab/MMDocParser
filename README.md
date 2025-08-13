# MMDocParser

一个专业的文档解析服务，支持提取文档中的文字、图片、表格、公式等信息。

## 功能特性

- 🚀 **异步处理**：基于Sanic的高性能异步Web框架
- 📁 **多格式支持**：PDF、DOCX、XLSX等
- 🔄 **任务队列**：Redis任务队列，支持异步处理
- ☁️ **云存储**：S3兼容存储，支持大文件
- 📊 **状态跟踪**：实时查询任务状态和结果
- 🏥 **健康检查**：服务健康状态监控


## 快速开始

### 1. 环境要求

- Python 3.12+
- Redis 6.0+
- S3兼容存储（MinIO/AWS S3）

### 2. 安装依赖

```bash
# 使用uv安装
uv sync
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp .env.template .env

# 编辑配置
```

### 4. 启动服务

```bash
# 方式1：使用启动脚本
python run.py

# 方式2：直接运行
sanic main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API接口

### 1. 上传文档

```http
POST /api/v1/documents/upload
Content-Type: application/json

{
  "files": [
    {
      "name": "document.pdf",
      "content": "base64编码的文件内容"
    }
  ]
}
```

### 2. 查询任务状态

```http
GET /api/v1/tasks/{task_id}/status
```

### 3. 获取解析结果

```http
GET /api/v1/tasks/{task_id}/result
```

### 4. 健康检查

```http
GET /health
```

## 项目结构

```
MMDocParser/
├── main.py                 # 主应用文件
├── run.py                  # 启动脚本
├── config.py               # 配置管理
├── storage/                # 存储相关
│   ├── s3_client.py       # S3客户端
│   └── redis_client.py    # Redis客户端
├── parsers/                # 文档解析器
│   └── document_parser.py # 解析器基类和实现
├── utils/                  # 工具函数
│   └── validators.py      # 验证工具
└── pyproject.toml         # 项目配置
```

## 开发指南

### 添加新的文档格式支持

1. 在 `parsers/document_parser.py` 中创建新的解析器类
2. 继承 `DocumentParser` 基类
3. 实现 `parse()` 和 `can_parse()` 方法
4. 在 `DocumentParserFactory` 中注册新解析器

## 部署

### Docker部署

### 生产环境配置

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

