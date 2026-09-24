# Omnia AIOS Dockerfile
# 多阶段构建，支持全平台

# ============ 构建阶段 ============
FROM python:3.11-slim as builder

WORKDIR /build

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    make \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
COPY pyproject.toml* ./

# 创建虚拟环境并安装依赖
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ============ 运行时阶段 ============
FROM python:3.11-slim as runtime

WORKDIR /app

# 安装运行时依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 创建非 root 用户
RUN groupadd -r omnia && useradd -r -g omnia omnia

# 创建数据目录
RUN mkdir -p /data /app/logs && \
    chown -R omnia:omnia /data /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 复制应用代码
COPY --chown=omnia:omnia src/omnia /app/omnia
COPY --chown=omnia:omnia config /app/config
COPY --chown=omnia:omnia skills /app/skills
COPY --chown=omnia:omnia personas /app/personas
COPY --chown=omnia:omnia scripts /app/scripts
COPY --chown=omnia:omnia omnia.yaml.example /app/omnia.yaml.example

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    OMNIA_HOME=/data \
    OMNIA_CONFIG=/data/omnia.yaml

# 切换到非 root 用户
USER omnia

# 暴露端口
EXPOSE 8765

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8765/health || exit 1

# 启动命令
ENTRYPOINT ["python", "-m", "omnia"]
CMD ["--config", "/data/omnia.yaml"]
