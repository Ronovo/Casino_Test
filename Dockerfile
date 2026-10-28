FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CASINO_DB=/app/data/casino.db \
    REPO_URL=https://github.com/Ronovo/Casino_Test.git \
    BUILD_CMD="pip install --no-cache-dir --user -q -r requirements.txt"

WORKDIR /app

COPY docker/git-sync.sh /usr/local/bin/git-sync
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/* \
    && sed -i 's/\r$//' /usr/local/bin/git-sync && chmod +x /usr/local/bin/git-sync

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# The database lives in /app/data so it can be mounted as a volume and survive rebuilds.
RUN useradd --create-home --uid 1000 casino \
    && mkdir -p /app/data \
    && chown -R casino:casino /app
USER casino

VOLUME ["/app/data"]
EXPOSE 8000

ENTRYPOINT ["git-sync"]
CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "8000"]
