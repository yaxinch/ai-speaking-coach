FROM node:22.16.0-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12.11-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FRONTEND_DIST_DIR=/app/frontend/dist

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist
RUN chmod +x scripts/start_production.sh

EXPOSE 8000
CMD ["sh", "scripts/start_production.sh"]
