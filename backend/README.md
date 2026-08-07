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

- **Ingredientes não vêm separados.** O `recipe-scrapers` devolve uma linha
  de texto por ingrediente (ex.: `"500 g frango"`), não quantidade/unidade/
  nome separados. Guardamos a linha inteira em `Ingredient.name`, com
  `quantity`/`unit` a `null` — fica para o utilizador editar à mão, ou para
  uma iteração futura com um parser de ingredientes dedicado (não incluído
  aqui de propósito, para não somar um segundo risco não validado ao spike).
- **Alguns sites não expõem instruções, nem em modo genérico.** Ex.:
  `pingodoce.pt` devolve título/porções/tempo/ingredientes corretamente mas
  `instructions()` vem vazio, mesmo com fallback `wild_mode` (schema.org
  genérico) — as instruções desse site não estão em HTML estático acessível
  ao scraper. Nesse caso a receita fica sem passos e o utilizador tem de os
  escrever à mão.
- **Alguns sites devolvem passos com lixo.** Ex.:
  `mundodereceitasbimby.com.pt` devolve `instructions_list()` com entradas
  válidas misturadas com chaves cruas do JSON-LD (`"@type"`, `"position"`,
  `"name"`, `"text"`) — bug do scraper específico do site, não nosso. Não
  filtrámos isto automaticamente (haveria o risco de apagar passos legítimos
  por engano) — fica visível para o utilizador rever/apagar depois de
  importar.
- **Cobertura de sites PT confirmada:** `recipe-scrapers` 15.11.0 tem
  scraper dedicado para `pingodoce.pt`, `mundodereceitasbimby.com.pt` e
  `aldi.pt`, entre 583 sites — mais amplo do que fica óbvio à partida.

## Migração do Tandoor

`scripts/migrate_from_tandoor.py` lê um export "Default" do Tandoor
(Definições > Dados e Ferramentas > Exportar Dados) e importa para o
Workspace único. Uso:

```bash
.venv/bin/python -m scripts.migrate_from_tandoor caminho/export.zip --dry-run   # ver o resumo primeiro
.venv/bin/python -m scripts.migrate_from_tandoor caminho/export.zip             # importar a sério
```

O esquema JSON usado está **verificado contra o código-fonte real do
Tandoor** (GitHub, `cookbook/integration/default.py` +
`cookbook/serializer.py`), não adivinhado — mas nunca foi corrido contra um
export real desta instância (192.168.1.202 exige login Authentik, sem
acesso a partir desta máquina). Testado mecanicamente com um export
sintético fiel ao esquema real (2 receitas, ingredientes com/sem unidade,
cabeçalho de secção, keywords, foto) — confirma que o script não tem bugs
de parsing/inserção, não que bate certo com todas as particularidades da
tua coleção real. **Corre sempre `--dry-run` primeiro** contra o export
real e confirma visualmente os números antes de importar a sério.

Limitações: fotos são extraídas para `--images-dir` mas não ligadas a
nenhuma receita (o tacho_app ainda não tem armazenamento de imagens —
funcionalidade própria por construir, fora do âmbito desta migração);
"categorias" ficam vazias (o export do Tandoor só tem "keywords", mapeadas
para Tags); cabeçalhos de secção nos ingredientes são descartados;
deduplicação é só por título igual.

## Por fazer a seguir

- Frontend: passa primeiro pelo `new-work` do Impeccable, para o mundo visual
  da Secção 6 do PRD ficar decidido antes de existir qualquer ecrã.
- Armazenamento de imagens (upload próprio + campo no modelo `Recipe`) —
  falta no schema atual; necessário antes de ligar as fotos migradas do
  Tandoor.
- Planeamento de refeições + lista de compras (v1.1).
- Workspace multi-utilizador + autenticação real (v1.2) — confirmar primeiro,
  contra o código do Securo, se `fastapi-users` e o modelo "Workspace" são
  mesmo o padrão usado lá (ponto em aberto no `PRODUCT.md`).
