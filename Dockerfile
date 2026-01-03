# Stage 1: Tailwind CSS bauen
FROM node:20-alpine AS frontend
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY tailwind.config.cjs ./
COPY app/static_src ./app/static_src
COPY app/templates ./app/templates

RUN npm run build

# Stage 2: Python-App (Produktion)
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Systempakete für psycopg2-binary (Postgres-Treiber)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.prod.txt requirements.prod.txt
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.prod.txt

COPY app ./app
# Tailwind-Ergebnis übernehmen
COPY --from=frontend /app/app/static ./app/static

# Port in Container (für Info)
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
