# Handoff para Claude Code — Tacho 2.0

## Contexto

O objetivo é preparar este repositório para distribuição self-hosted e futura
abertura pública. O produto e futuro repositório devem chamar-se apenas
**Tacho**:

- remoto atual: `11VitorAlves11/tacho_app` (privado);
- remoto pretendido: `11VitorAlves11/tacho`;
- release de transição pretendida: `v2.0.0`;
- licença escolhida: AGPL-3.0;
- branch pretendida: `main`, mantendo `master` até a migração ser validada;
- imagem pretendida: `ghcr.io/11vitoralves11/tacho:<versão>`;
- apenas a última versão estável terá suporte;
- aliases Docker antigos devem ser mantidos por uma release de transição, sem
  apagar packages, tags ou releases existentes;
- infraestrutura real do homelab deve ficar num repositório privado separado;
- `vital` não deve ser usado como referência.

O utilizador aprovou a implementação, mas ainda não autorizou alterações
remotas no GitHub, mudança de visibilidade, renomeação remota, proteção de
branches ou eliminação de `master`.

## Estado do working tree

Já foram criados quatro commits locais nesta tarefa (não publicados). Antes
desta tarefa já existiam:

- `README.md` modificado pelo utilizador;
- `.mcp.json` não versionado — preservar e não adicionar ao Git.

As alterações atuais desta tarefa incluem segurança, Docker, documentação,
workflows, dependências e testes. Não fazer `reset`, `checkout` destrutivo nem
apagar alterações.

## Já implementado localmente

### Segurança e media

- `.dockerignore` na raiz, backend e frontend para excluir `.env`, uploads,
  virtualenvs, `node_modules`, caches e ficheiros locais.
- `backend/app/config.py` rejeita `AUTH_SECRET` default/fraco quando
  `ENVIRONMENT=production`.
- Foi removido o mount público global `/images`.
- Foi criado `backend/app/routers/media.py`, com media privada protegida por
  sessão e workspace.
- Foi criado endpoint público token-scoped:
  `/public/recipes/{token}/image`.
- Frontend privado usa `/media/...`; frontend de partilha usa o endpoint por
  token.
- Importação URL valida HTTP(S), resolve DNS e rejeita endereços locais/privados;
  redirects foram desativados no download direto de imagens.
- Atenção: fazer uma revisão de SSRF completa, incluindo redirects/scraping e
  DNS rebinding, antes de declarar isto resolvido.

### Docker

- `docker-compose.yml` foi convertido para configuração genérica de produção.
- `docker-compose.dev.yml` contém o ambiente de desenvolvimento com hot reload.
- A imagem única `ghcr.io/11vitoralves11/tacho` é usada por `web`, `worker` e
  `migrate` com comandos diferentes.
- `secrets-init` gera password PostgreSQL e `AUTH_SECRET` em volume persistente.
- Migrações correm num serviço one-shot antes de web/worker.
- Foram adicionados healthchecks e volumes persistentes.
- `docker-compose.prod.yml` ficou como wrapper com `include` por compatibilidade.
- `backend/docker-entrypoint.sh` passou a executar o comando recebido e já não
  força sempre Uvicorn.

### Dependências e testes

- Adicionados `backend/pyproject.toml`, `backend/uv.lock` e
  `backend/requirements.lock`.
- Dockerfiles instalam a lista exportada do lockfile.
- Adicionados testes backend:
  - `backend/tests/test_health.py`;
  - `backend/tests/test_security.py`.
- Adicionado teste frontend `frontend/src/lib/quantity.test.ts`.
- `vitest` foi adicionado e o lockfile npm atualizado.
- `npm audit --package-lock-only` foi executado; a vulnerabilidade transitiva de
  `nanoid` foi corrigida e o resultado final foi zero vulnerabilidades.

### GitHub Actions

- O workflow antigo `build-and-push.yml` foi substituído.
- `ci.yml`: backend, frontend, Compose, smoke test e dependency review
  condicional.
- `edge-image.yml`: publica `edge` e `sha-<commit>` apenas após CI verde na
  branch `main`.
- `release.yml`: tags `vX.Y.Z`, valida versão backend/frontend, build multiarch,
  tags semver + `latest`, e GitHub Release só depois do push da imagem.
- Actions estão fixadas por SHA, com comentários de versão.
- `.github/dependabot.yml`, templates de issues/PR e CODEOWNERS foram criados.

### Documentação/governança

- README principal reescrito para Tacho/self-hosted.
- README backend/frontend substituídos por documentação específica.
- Criados `docs/installation.md`, `configuration.md`, `upgrading.md`,
  `backup-restore.md`, `development.md`, `architecture.md`, `releasing.md` e
  `migration-from-tacho-app.md`.
- Criados `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md` e `LICENSE`
  (texto oficial AGPL-3.0).
- Criados `scripts/backup.sh` e `scripts/restore.sh`.
- Criado `docker-compose.override.example.yml` sanitizado.

## Tarefas obrigatórias antes de considerar concluído

1. **Corrigir e rever a implementação antes de commits**

   - Rever `docker-compose.yml`: confirmar que `include` no
     `docker-compose.prod.yml` é suportado pela versão mínima documentada.
   - Corrigir a regra `on.push.tags` em `release.yml` se necessário: GitHub
     Actions usa padrões glob, não regex completa; usar `v*.*.*` e validar
     estritamente no job.
   - Confirmar que o `CORS_ORIGINS` interpolado como JSON é aceite pelo
     pydantic-settings em Compose.
   - Confirmar a semântica de `secrets-init` com volume já existente e bases de
     dados existentes.
   - Rever `scripts/restore.sh` num ambiente descartável antes de o recomendar.
   - Adicionar permissões/restrições mínimas e verificar todas as Actions.

2. **Remover acoplamentos pessoais restantes**

   Fazer `git grep` por domínios, CTs, caminhos, homelab, Authentik, NPM,
   Tandoor/Mealie e `tacho_app`. Atualmente ainda existem referências pessoais
   em comentários/código, nomeadamente:

   - `backend/app/auth.py`;
   - `backend/app/config.py`;
   - `backend/app/nutrition.py`;
   - `backend/app/routers/auth.py`;
   - vários comentários frontend.

   Manter apenas referências genéricas a forward-auth. O default do header deve
   ser avaliado: `X-authentik-email` é específico; preferir um header genérico
   ou documentar explicitamente que é configurável. Não remover o suporte
   existente sem documentar a migração.

3. **Rever compatibilidade funcional da media**

   - Testar capa, galeria, duplicação, eliminação e modo cozinha.
   - Confirmar que partilhas públicas mostram a capa sem cookie.
   - Confirmar que export JSON-LD aponta para um URL apropriado.
   - Decidir se URLs antigos `/images/...` precisam de redirect temporário.

4. **Corrigir metadata e nomes**

   - Backend e frontend devem reportar `2.0.0` de forma coerente.
   - Atualizar manifest/PWA e `index.html` se ainda houver `frontend` ou
     `tacho_app` como identidade pública.
   - Remover a referência antiga do README apenas quando existir o guia de
     migração equivalente.

5. **Executar qualidade local**

   Ferramentas Docker não estavam disponíveis no ambiente original. Executar
   onde existam Docker Compose v2, Python 3.12 e Node:

   ```bash
   cd backend
   uv sync --frozen --all-groups
   uv run ruff check app tests
   uv run ruff format --check app tests
   uv run mypy app
   uv run pytest --cov=app --cov-report=term-missing
   uv run pip-audit

   cd ../frontend
   npm ci
   npm run lint
   npm test
   npm run build

   cd ..
   cp .env.example .env
   docker compose config --quiet
   docker compose up -d --wait
   curl --fail http://localhost:8000/health
   docker compose down --volumes
   ```

   Não declarar sucesso sem registar resultados. Corrigir todas as falhas
   reais, especialmente type checking e lint, antes de proteger a branch.

6. **Validar dados/migrações**

   - Testar BD vazia desde a migração inicial até `head`.
   - Testar upgrade de uma instalação representativa existente.
   - Confirmar uma única Alembic head (`5d7092e277e3` atualmente).
   - Testar backup e restore completos num stack descartável.
   - Confirmar que rollback documentado restaura BD, media e secrets.

7. **Dividir em commits**

   Sugestão:

   1. `security: harden image build context and private media`
   2. `build: add reproducible backend and frontend dependencies`
   3. `test: add health and security smoke coverage`
   4. `docker: provide generic production and development compose`
   5. `docs: document self-hosting operations and migration`
   6. `ci: separate checks, edge images and releases`
   7. `chore: prepare Tacho 2.0 identity and governance`

   Antes de cada commit, verificar que `.mcp.json`, `.env`, uploads, venvs e
   caches não entram no stage.

8. **Só depois preparar operações remotas**

   Não executar sem revisão final do utilizador:

   - renomeação do GitHub `tacho_app` → `tacho`;
   - mudança de default branch `master` → `main`;
   - branch protection/rulesets;
   - criação/verificação de packages GHCR novos;
   - eventual backfill de GitHub Releases;
   - mudança de visibilidade para público.

## Evidência do estado GitHub auditado

- Repositório atual: privado, `master`, sem proteção.
- Tags locais/remotas: `v1.0.0` até `v1.5.4`.
- Releases visíveis: apenas `v1.0.0`, `v1.1.0`, `v1.1.1`, `v1.1.2`.
- Packages antigos: `tacho_app-web` e `tacho_app-celery-worker`; acesso de
  leitura aos versions não estava disponível no token da auditoria.

## Restrições permanentes

- Não reescrever histórico.
- Não apagar tags, Releases, imagens ou packages antigos.
- Não tornar o repositório público sem aprovação final explícita.
- Não renomear o remoto automaticamente.
- Não alterar o homelab nem qualquer configuração externa nesta tarefa local.
- Não incluir domínios privados, IPs, nomes de containers, caminhos internos ou
  segredos no repositório público.
