# Contexto do projeto Tacho

## Visão geral

O **Tacho** é uma aplicação web self-hosted para gerir receitas e o dia a dia
da cozinha. Permite guardar e importar receitas, cozinhar passo a passo,
organizar coleções, planear refeições, manter a despensa e gerar uma lista de
compras partilhada.

O produto está na versão `2.0.0`, é distribuído sob a licença AGPL-3.0 e a
interface está atualmente escrita em português. O repositório oficial é
`11VitorAlves11/tacho` e a imagem de produção é publicada como
`ghcr.io/11vitoralves11/tacho`.

## Funcionalidades principais

- Criação, edição, pesquisa e eliminação de receitas.
- Categorias, etiquetas, favoritos, classificações e coleções de receitas.
- Importação através de URL, texto ou fotografia; a extração com Gemini é
  opcional.
- Fotografias de capa e galerias privadas.
- Modo de cozinha com passos, temporizadores, ajuste de doses e cache offline.
- Planeamento semanal de refeições, despensa e lista de compras.
- Links temporários para partilhar receitas publicamente.
- Vários utilizadores no mesmo agregado/workspace.
- Autenticação por cookie e integração opcional com forward-auth.
- PWA instalável, interface responsiva e modo escuro.

## Arquitetura

Este é um monorepo pequeno, composto por:

- `backend/`: API FastAPI em Python 3.12, SQLAlchemy, Alembic e Celery.
- `frontend/`: SPA React 19, TypeScript, Vite e Tailwind CSS.
- PostgreSQL: fonte de verdade para dados persistentes.
- Redis: broker e resultados transitórios das tarefas Celery.
- Volume de imagens: armazenamento persistente separado da base de dados.

Em produção, uma única imagem Docker contém o backend e o frontend
compilado. Essa imagem é usada por três serviços com comandos diferentes:

- `migrate` aplica as migrações Alembic e termina;
- `web` serve a API e a SPA pelo mesmo origin;
- `worker` executa as tarefas Celery.

Os dados de cada agregado pertencem a um `workspace`. As imagens privadas são
servidas por endpoints autenticados; uma partilha pública usa endpoints
limitados pelo token da partilha.

## Estrutura relevante

```text
backend/
  app/main.py          cria a aplicação e regista os routers
  app/models.py        modelos SQLAlchemy
  app/schemas.py       schemas de entrada e saída
  app/crud.py          operações de persistência
  app/config.py        configuração por variáveis de ambiente
  app/auth.py          autenticação e sessões
  app/routers/         endpoints por área funcional
  app/tasks.py         tarefas assíncronas
  alembic/versions/    histórico de migrações
  tests/               testes backend
frontend/
  src/api/             cliente HTTP e tipos da API
  src/auth/            contexto e fluxo de autenticação
  src/components/      componentes reutilizáveis
  src/pages/           páginas da aplicação
  src/App.tsx          rotas e gates de autenticação
docs/                  instalação, operação e arquitetura
scripts/               backup e restauro
.github/               CI, releases e configuração do GitHub
```

## Desenvolvimento local

O caminho recomendado usa Docker Compose:

```bash
cp .env.example .env
docker compose -f docker-compose.dev.yml up --build
```

- Frontend: <http://localhost:5173>
- API e documentação OpenAPI: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

Validações do backend:

```bash
cd backend
uv sync --frozen --all-groups
uv run ruff check app tests
uv run ruff format --check app tests
uv run mypy app
uv run pytest
```

Validações do frontend:

```bash
cd frontend
npm ci
npm run lint
npm test
npm run build
```

## Produção e persistência

O arranque normal é feito com `docker compose up -d`. Os volumes que devem ser
preservados em backups e atualizações são:

- `tacho_pgdata`: base de dados PostgreSQL;
- `tacho_images`: fotografias enviadas pelos utilizadores;
- `tacho_secrets`: password da base de dados e segredo das sessões.

Antes de expor a aplicação à Internet, deve existir HTTPS e
`AUTH_COOKIE_SECURE=true`. Consultar `docs/installation.md`,
`docs/configuration.md`, `docs/upgrading.md` e `docs/backup-restore.md` antes de
operar uma instalação com dados importantes.

## Configuração importante

- `DATABASE_URL` e `REDIS_URL`: ligações do backend.
- `AUTH_SECRET`: assina as sessões; em produção deve ter pelo menos 32
  caracteres e não pode usar o valor de desenvolvimento.
- `AUTH_COOKIE_SECURE`: ativa cookies apenas por HTTPS.
- `CORS_ORIGINS`: lista JSON das origens autorizadas.
- `PUBLIC_BASE_URL`: URL canónica privada usada, entre outros casos, nos
  exports schema.org.
- `SHARE_BASE_URL`: host público dos links e QR codes de partilha.
- `GEMINI_API_KEY`: ativa a extração opcional com Gemini.
- `TRUST_FORWARD_AUTH`, `FORWARD_AUTH_SECRET` e
  `FORWARD_AUTH_EMAIL_HEADER`: integração com um proxy de autenticação
  confiável.

No Compose de produção, os segredos essenciais são gerados automaticamente no
primeiro arranque e guardados no volume `tacho_secrets`.

## Convenções e cuidados ao alterar o projeto

- Uma alteração ao modelo de dados deve incluir uma migração Alembic revista
  e testada tanto numa base vazia como numa atualização.
- O frontend deve consumir a API através dos módulos em `frontend/src/api/`.
- Todas as consultas e alterações de dados privados devem respeitar o
  `workspace` do utilizador autenticado.
- Não voltar a expor o diretório de imagens como pasta estática pública.
- Importações por URL exigem cuidado com SSRF, redirects e resolução DNS.
- Não editar lockfiles manualmente; usar `uv` ou `npm` conforme o componente.
- Preservar alterações locais e ficheiros de configuração privados, em
  especial `.env` e `.mcp.json`.
- Para mudanças de comportamento, adicionar testes focados no caso alterado.

## Documentação complementar

- `README.md`: apresentação e início rápido.
- `docs/architecture.md`: resumo da arquitetura.
- `docs/development.md`: comandos e requisitos de desenvolvimento.
- `docs/configuration.md`: variáveis de ambiente.
- `docs/installation.md`: instalação self-hosted.
- `docs/upgrading.md`: atualização e rollback.
- `docs/backup-restore.md`: backup e restauro.
- `docs/releasing.md`: processo de release.
- `CONTRIBUTING.md`: regras para contribuições.

## Estado no momento da criação deste ficheiro

- Branch principal: `main`.
- Versão declarada no backend e frontend: `2.0.0`.
- Release `v2.0.0` já existe no histórico Git local.
- O working tree estava limpo antes da criação deste ficheiro.

Este documento deve ser atualizado quando a arquitetura, os comandos de
desenvolvimento, as regras de segurança ou o processo de distribuição mudarem.
