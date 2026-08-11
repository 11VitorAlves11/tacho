# tacho_app — backend

FastAPI + PostgreSQL + Redis/Celery. Ver `PRODUCT.md` e `PRD-app-receitas-v2.md`
na raiz do projeto para o contexto completo.

## Desenvolvimento local

```bash
docker compose up -d db redis
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp ../.env.example .env   # ajustar host para "localhost" fora do compose
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

Ou tudo dentro do compose: `docker compose up --build` (a partir da raiz do
projeto) sobe os 4 containers — `db`, `redis`, `backend`, `celery-worker`.

## Estado atual (v1.0, em construção)

- CRUD completo de receitas (`/recipes`), categorias (`/categories`) e tags
  (`/tags`), com filtro por categoria/tag/pesquisa de título.
- Todas as receitas/categorias/tags pertencem a um Workspace único, semeado
  pela migração `93c380aef9a6` (`app/constants.DEFAULT_WORKSPACE_ID`) — não
  há multi-utilizador real ainda; isso é v1.2 (ver `PRODUCT.md`).
- Importação de receitas por URL (`POST /recipes/import` + `GET
  /recipes/import/{task_id}`) via `recipe-scrapers`, a correr no worker
  Celery — o pedido HTTP volta de imediato, a receita aparece assim que o
  worker terminar. Testado com URLs reais (`pingodoce.pt`,
  `mundodereceitasbimby.com.pt`) e com um URL sem receita (falha reportada
  como `422`, não como sucesso silencioso).
- Testado manualmente ponta a ponta (migração, CRUD via HTTP, worker Celery,
  importação por URL) contra Postgres/Redis locais nesta máquina — sem
  Docker disponível aqui para correr o `docker-compose.yml` completo.

## Limitações conhecidas da importação por URL

Validadas com sites reais (spike do PRD, Secção 11 — risco técnico mais
alto identificado):

- **Ingredientes: separados quando há confiança, senão a linha fica intacta.**
  O `recipe-scrapers` devolve uma linha de texto por ingrediente (ex.:
  `"500 g de frango"`). `app/tasks.py::_parse_ingredient_line` separa
  quantidade/unidade/nome quando reconhece um padrão seguro (número no
  início + unidade PT conhecida); quando não tem a certeza — intervalos
  ("2-3 dentes"), frações mistas ("1 ½"), ou linhas sem quantidade no início
  ("Sal q.b.") — deixa a linha original intacta em `Ingredient.name` com
  `quantity`/`unit` a `null`, em vez de arriscar um split errado (mesma
  disciplina do filtro de passos abaixo: nunca uma heurística que possa
  destruir dado real).
- **Alguns sites não expõem instruções, nem em modo genérico.** Ex.:
  `pingodoce.pt` devolve título/porções/tempo/ingredientes corretamente mas
  `instructions()` vem vazio, mesmo com fallback `wild_mode` (schema.org
  genérico) — as instruções desse site não estão em HTML estático acessível
  ao scraper. Nesse caso a receita fica sem passos e o utilizador tem de os
  escrever à mão.
- **Alguns sites devolvem passos com lixo — filtrado.** Ex.:
  `mundodereceitasbimby.com.pt` (reproduzido em "Cheesecake de Bolacha -
  gelado sanduíche"): quando uma `HowToSection` do JSON-LD tem
  `itemListElement` como um dict solto em vez de uma lista, o
  `recipe-scrapers` itera as chaves desse dict como se fossem passos —
  devolve `"@type"`, `"position"`, `"name"`, `"text"` soltos no meio de
  passos reais. `app/tasks.py::_extract_steps` filtra essas correspondências
  exatas (não por comprimento — nunca arrisca apagar um passo real só por
  ser curto, ex. "Sirva.").
- **Cobertura de sites PT confirmada:** `recipe-scrapers` 15.11.0 tem
  scraper dedicado para `pingodoce.pt`, `mundodereceitasbimby.com.pt` e
  `aldi.pt`, entre 583 sites — mais amplo do que fica óbvio à partida.

## Por fazer a seguir

- Planeamento de refeições + lista de compras (v1.1).
- Workspace multi-utilizador + autenticação real (v1.2) — confirmar primeiro,
  contra o código do Securo, se `fastapi-users` e o modelo "Workspace" são
  mesmo o padrão usado lá (ponto em aberto no `PRODUCT.md`).
