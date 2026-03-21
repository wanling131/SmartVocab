# SmartVocab API（生产建议配合外部 MySQL 与反向代理 HTTPS）
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV APP_ENV=production \
    APP_DEBUG=false \
    LOG_LEVEL=INFO

EXPOSE 5000

# 生产环境必须注入 SECRET_KEY、DB_* 等，见 .env.example
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "--timeout", "120", "wsgi:app"]
