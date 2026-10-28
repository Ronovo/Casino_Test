FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CASINO_DB=/app/data/casino.db

WORKDIR /app
COPY . .

# The database lives in /app/data so it can be mounted as a volume and survive rebuilds.
RUN useradd --create-home --uid 1000 casino \
    && mkdir -p /app/data \
    && chown -R casino:casino /app/data
USER casino

VOLUME ["/app/data"]
EXPOSE 8000

CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8000"]
