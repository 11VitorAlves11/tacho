# tacho_app

**Tacho** — app de gestão de receitas e cozinha, feita à medida, para substituir
o Tandoor e o Mealie.

## Motivação

O homelab tem o Tandoor instalado (CT 202) e foi considerado também o Mealie.
Manter duas ferramentas de terceiros — cada uma com o seu design, API e stack —
é complexidade desnecessária para um agregado de duas pessoas, e nenhuma delas
está talhada ao fluxo real de cozinha e planeamento cá de casa.

O Tandoor **não tem receitas guardadas**, pelo que não há migração a fazer: o
Tacho arranca com a base de dados vazia e o Tandoor pode ser desligado assim que
o Tacho estiver implantado.

Documentos de referência:
- `PRD-app-receitas-v3.2.md` — âmbito, funcionalidades, roadmap, decisões pendentes
- `PRODUCT.md` — registo de decisões de produto
- `DESIGN.md` — tokens, componentes e mundo visual
- `TODO.md` — estado do trabalho, tarefa a tarefa

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python + FastAPI, SQLAlchemy + Alembic |
| Base de dados | PostgreSQL |
| Tarefas em background | Redis + Celery |
| Frontend | React + TypeScript + Vite + Tailwind CSS |
| Importação de receitas | `recipe-scrapers` (+ Gemini API como fallback, v1.1) |

Alinhado deliberadamente com o Securo (CT 209) do homelab — mesmas convenções
nos dois projetos. Racional completo em `PRODUCT.md` (secção Stack).

## Como correr

### Pré-requisitos
Docker e Docker Compose. (Nota: no CT 111, onde isto foi construído, não havia
Docker — os testes correram contra Postgres/Redis locais instalados via apt. O
`docker-compose.yml` **ainda não foi corrido de facto**; confirmar antes de
assumir que funciona tal e qual no homelab.)

### Arranque

```bash
cp .env.example .env    # editar valores (ver tabela abaixo)
docker compose up -d
docker compose exec backend alembic upgrade head
```

- Frontend: http://localhost:5173
- API + docs interativos (OpenAPI): http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `DATABASE_URL` | Ligação ao PostgreSQL |
| `REDIS_URL` | Ligação ao Redis (broker do Celery) |
| `CORS_ORIGINS` | Origens permitidas para o frontend |
| `GEMINI_API_KEY` | *Opcional.* Sem esta chave, o fallback de importação por URL e a importação por foto ficam indisponíveis; o resto da app funciona normalmente |
| `MEDIA_ROOT` | Pasta onde ficam as fotos das receitas (volume Docker, incluído nos backups) |

### Desenvolvimento sem Docker

```bash
# backend
cd backend && pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload

# worker Celery (terminal separado)
celery -A app.worker worker --loglevel=info

# frontend
cd frontend && npm install && npm run dev
```

## Esquema de dados

> ⚠️ Reconstruído a partir do estado documentado em `TODO.md` — **verificar
> contra `backend/app/models.py`** e atualizar se divergir.

```
Workspace ──┬──< Recipe ──┬──< Ingredient   (name, quantity, unit, is_header*)
            │             ├──< Step         (order, text, timer*)
            │             ├──>< Category    (M:N)
            │             └──>< Tag         (M:N)
            ├──< Category
            └──< Tag
```

Tudo pertence a um `Workspace` (o agregado). Hoje existe um Workspace único
semeado pela migração inicial da BD; contas de utilizador reais só chegam na
v1.2 — ver PRD Secção 5.6.

`*` — campos previstos no PRD mas ainda não implementados (`Ingredient.is_header`,
timers por passo, campo de imagem em `Recipe`).

## Estado

**v1.0 em construção.**

Feito:
- `backend/` — CRUD de receitas/categorias/tags, filtros, importação por URL via
  Celery, `/health`, CORS. Ver `backend/README.md`.
- `frontend/` — Home, Detalhe da receita, Modo Cozinha (com wake lock),
  Adicionar receita (por link ou à mão), Editar/Apagar, menu de utilizador.

Por testar (passou build + linter, sem verificação visual no browser):
- Editor manual de receitas (`AddRecipe.tsx` aba "À mão", `EditRecipe.tsx`,
  `RecipeForm.tsx`)
- Menu de utilizador (`UserMenu.tsx`)

Gaps conhecidos da v1.0 (ver critérios de aceitação, PRD Secção 11.1):
armazenamento e upload de imagens, cabeçalhos de secção nos ingredientes,
informação nutricional, deploy definitivo no homelab.

A seguir: planeamento de refeições + lista de compras (v1.1), multi-utilizador
real (v1.2). Roadmap completo no PRD Secção 11.

## Deploy

Ainda **não implantado** — corre só no CT 111 de desenvolvimento, fora do
`docker-compose.yml` principal do homelab. Falta decidir VMID/IP segundo a
convenção do `homelab/CLAUDE.md` (PRD, Decisão #4).

⚠️ **Enquanto não houver autenticação (v1.2), a app só pode estar acessível
dentro da tailnet** — nunca exposta à LAN de convidados nem à internet.