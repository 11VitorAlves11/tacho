# Imagem de produção — backend + frontend compilado, um único processo/porta.
# Ver docker-compose.prod.yml. Para desenvolvimento local usa-se
# backend/Dockerfile + frontend/Dockerfile (vite dev) em docker-compose.yml.

FROM node:22-slim AS frontend-build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
# Vazio de propósito: o frontend e o backend passam a ser servidos na mesma
# origem (ver app/main.py), por isso os pedidos à API ficam relativos.
ENV VITE_API_URL=""
RUN npm run build

FROM python:3.14-slim
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

COPY backend/ .
COPY --from=frontend-build /app/dist ./frontend_dist
RUN chmod +x docker-entrypoint.sh

# Corre as migrações Alembic pendentes antes de arrancar — `alembic upgrade
# head` é idempotente (não faz nada se já estiver atualizado), por isso é
# seguro correr sempre, mesmo sem migração nova. Antes disto o passo era
# manual (`docker-compose exec web alembic upgrade head`), o que tornava
# perigoso qualquer atualização automática (ex.: botão do Telegram) — código
# novo podia arrancar contra esquema antigo.
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
