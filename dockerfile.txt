# 阶段1：构建依赖（用完整Python镜像）
FROM python:3.11-slim as builder
WORKDIR /app
# 复制依赖文件
COPY requirements.txt .
# 安装依赖（国内源加速）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 阶段2：运行镜像（轻量化，只保留必要文件）
FROM python:3.11-slim
WORKDIR /app
# 从构建阶段复制依赖
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# 复制项目代码
COPY . /app
# 设置环境变量（避免Python缓存）
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
# 健康检查（云原生必备：检查服务是否存活）
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
# 暴露端口（和服务端口一致）
EXPOSE 8000
# 启动命令（生产环境用gunicorn，开发用uvicorn）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]