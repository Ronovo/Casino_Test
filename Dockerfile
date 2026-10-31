# The coverage reports only show what the tests reach, so failing tests or low coverage still build the image.
FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159 AS python-coverage
WORKDIR /src
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
RUN python -m coverage run -m unittest discover -s Tests -t . ; \
    python -m coverage html --fail-under=0 ; mkdir -p coverage/python ; \
    sed -i 's/{run: false, exc: true, mis: true, par: true}/{run: true, exc: true, mis: true, par: true}/' coverage/python/coverage_html_cb_*.js ; \
    python -m coverage json --fail-under=0 -o coverage.json ; \
    python coverage-index/tools/functions.py coverage.json coverage/python/functions.json

FROM node:24-slim@sha256:c86ecead9e55a5210ac1727de38a4ca840bf03dcaf34dc9749addbf383b1920c AS js-coverage
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npx vitest run --coverage ; mkdir -p coverage/js ; cat coverage-index/istanbul.css >> coverage/js/base.css

FROM python:3.12-slim@sha256:aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CASINO_DB=/app/data/casino.db

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0

COPY main.py .
COPY casino casino
COPY Data Data
COPY coverage-index/index.html coverage/
COPY coverage-reports.json coverage/reports.json
COPY --from=python-coverage /src/coverage/python coverage/python
COPY --from=js-coverage /src/coverage/js coverage/js

# The database lives in /app/data so it can be mounted as a volume and survive rebuilds. Only that folder belongs to
# the app's user, so the app can't change its own code.
RUN useradd --create-home --uid 1000 casino \
    && mkdir -p /app/data \
    && chown casino:casino /app/data
USER casino

VOLUME ["/app/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/session', timeout=4)"]

# One worker: the floor keeps seated players and their locks in memory.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "8", "casino.web.server:create_app()"]
