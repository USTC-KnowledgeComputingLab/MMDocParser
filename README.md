# TriModalParser

## 添加依赖
```
pip imstall uv
```
```
uv pip install .
```
## 测试doc_parsing
1. 如果src没有message文件夹,那么请使用如下命令进行proto编译
```
python -m grpc_tools.protoc -Iproto --python_out=src/message --grpc_python_out=src/message proto/common/v1/s3.proto
python -m grpc_tools.protoc -Iproto --python_out=src/message --grpc_python_out=src/message proto/parse/v1/pdf_parser.proto
```
2. 运行tests/utils.py 上传需要解析的文件到s3，这一步需要保留key值
3. 运行tests/test_doc_parsing.py, 修改main函数中send_task函数的参数，将任务推入队列中，等待任务完成结果输出
