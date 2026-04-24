# syntax=docker/dockerfile:1.7

# ── Stage 1: builder — 使用 uv 解析并安装依赖到独立的虚拟环境 ──────────────
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

# 复制 uv 二进制（官方静态镜像），避免自行安装
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /usr/local/bin/

WORKDIR /app

# 先只复制 lock 与项目元数据以最大化 Docker 缓存命中
COPY pyproject.toml uv.lock README.md ./

# 创建仅含运行时依赖（不含 dev 组）的虚拟环境
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# 复制项目源码并安装本项目本身
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# ── Stage 2: runtime — 精简镜像，仅含虚拟环境与源码 ─────────────────────
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    APP_HOST=0.0.0.0 \
    APP_PORT=8000

# 创建非 root 用户
RUN groupadd --system --gid 1001 app \
    && useradd --system --uid 1001 --gid app --home /app --shell /usr/sbin/nologin app

WORKDIR /app

# 从 builder 拷贝虚拟环境与项目文件
COPY --from=builder --chown=app:app /app /app

USER app

EXPOSE 8000

# 简单健康检查（health 路由）
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys;\
        urllib.request.urlopen('http://127.0.0.1:${APP_PORT}/api/v1/health/live', timeout=3);\
        sys.exit(0)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
