# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# 先只複製 requirements，利用 Docker layer cache
# 只有 requirements 改變時才重新 pip install
COPY requirements.txt .

RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# 從 builder 複製已安裝的套件
COPY --from=builder /install /usr/local

# 複製專案程式碼
COPY fetchers/   ./fetchers/
COPY formatters/ ./formatters/
COPY notifiers/  ./notifiers/
COPY main_daily.py  .
COPY main_weekly.py .

# 不以 root 執行（安全最佳實踐）
RUN useradd -m appuser
USER appuser

# 預設執行每日任務（docker-compose.yml 可 override）
CMD ["python", "main_daily.py"]
