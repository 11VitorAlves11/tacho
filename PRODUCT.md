# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Confirmado (PRD v2, agosto 2026) — substitui a decisão delegada anterior:
app construída inteiramente de raiz, sem depender da API do Tandoor como
backend. Backend em Python + FastAPI (SQLAlchemy + Alembic para migrações);
PostgreSQL como base de dados; Redis + Celery worker para tarefas em
background (importação de receitas por URL, sem bloquear o pedido HTTP).
Frontend em React + TypeScript + Vite + Tailwind CSS, responsivo
mobile/desktop. Stack alinhada deliberadamente com o Securo (CT 209) — mesmo
padrão de containers em Docker Compose. Deploy: 5 containers (frontend,
backend, worker Celery, PostgreSQL, Redis) no Proxmox, acesso remoto via
Tailscale. Ver `PRD-app-receitas-v2.md` para o diagrama de arquitetura
completo.

## Users

O utilizador principal (Vítor) e a Mariana — agregado familiar único, as
mesmas pessoas que hoje usam o Tandoor (CT 202) para gerir receitas. Uso
tanto no telemóvel (na cozinha, possivelmente com as mãos ocupadas) como no
computador (a planear refeições com calma) — sem contexto claramente
dominante. Não é um produto multi-tenant/SaaS — é doméstico, self-hosted.

## Product Purpose

Uma app de receitas self-hosted, construída inteiramente de raiz, que
substitui o Tandoor Recipes (CT 202) e cobre também funcionalidades de
planeamento de refeições e lista de compras que o utilizador valorizava no
Mealie — serviço que já não corre no homelab (a CT 202 passou de Mealie a
Tandoor em 2026-07-26), mas cujas funcionalidades continuam a fazer falta.
Cobre: gestão de receitas com importação automática por URL, organização por
categorias/tags/cookbooks, planeamento semanal de refeições, lista de
compras gerada automaticamente a partir do plano, e um Modo Cozinha
dedicado.

## Positioning

Uma única aplicação própria — stack único, base de dados única, design
único — em vez de manter ferramentas de terceiros diferentes para cada
função (a gestão de receitas do Tandoor de um lado, o planeamento de
refeições que existia no Mealie do outro). Construído e controlado pelo
próprio utilizador, talhado ao fluxo real de cozinha e planeamento da
família, em vez de se adaptar às convenções de produtos de terceiros.

## Operating Context

Corre dentro do homelab pessoal (Proxmox + LXC/Docker), ao lado de outros
serviços self-hosted da família (Tandoor/CT202, Securo/CT209, Immich/CT204,
Authentik/CT208, etc.). Segue deliberadamente o mesmo padrão arquitetural do
Securo (FastAPI + PostgreSQL + Redis + Celery + Docker Compose), para manter
as convenções consistentes entre os dois projetos próprios do homelab.
Substitui diretamente o Tandoor — inclui um script de migração dos dados de
receitas existentes (export/JSON) antes de o desligar definitivamente. O
Mealie já não corre no homelab; não há dados a migrar dele, só
funcionalidades a replicar.

## Capabilities and Constraints

- Suporta vários utilizadores do mesmo agregado (Vítor + Mariana) através de
  um modelo de Workspace partilhado — não é single-user, mas também não é
  multi-tenant/SaaS.
- Deve funcionar bem tanto em ecrã de telemóvel como de computador
  (interface responsiva única, sem apps nativas).
- Autenticação própria via conta local; integração SSO com Authentik fica
  como possibilidade futura (v2), não é decisão da v1.
- Fora de âmbito na v1: leitura de códigos de barras, sincronização com
  Nextcloud/Dropbox, plugins de terceiros, multi-idioma além de PT-PT/EN,
  cálculo automático de nutrição a partir dos ingredientes, apps móveis
  nativas.
- Por decidir: o modelo de Workspace e a biblioteca de autenticação
  (`fastapi-users`) são descritos no PRD como "o mesmo padrão do Securo" —
  ainda não confirmado contra o código real do Securo, só por analogia.
  Também por decidir: como convidar a segunda pessoa para o Workspace, já
  que o PRD assume um convite por email e não existe infraestrutura de envio
  de email em nenhum outro serviço do homelab.
- ~~Gap identificado durante a construção (06-08): o modelo `Recipe` ainda não
  tem campo de imagem~~ — **resolvido em 07-08**: `Recipe.image_path`,
  upload pela UI, storage em disco. Ver TODO.md.

## Evidence on Hand

PRD detalhado em `PRD-app-receitas-v2.md` (raiz do projeto), com arquitetura
técnica, âmbito funcional completo e roadmap por fases. Backend v1.0 em
construção em `backend/` (FastAPI + PostgreSQL + Redis/Celery, CRUD de
receitas/categorias/tags testado ponta a ponta, importação por URL e script
de migração do Tandoor) — ver `backend/README.md` para o estado exato.
Frontend v1.0 construído em `frontend/` (Home, Detalhe, Modo Cozinha,
Adicionar receita) a partir do mundo visual da Secção 6 do PRD, formalizado
em `DESIGN.md` depois de uma revisão de finalização (Impeccable
`new-work`). O Tandoor (CT 202) serve de referência do que já funciona e do
que se quer substituir, mas não deve ser copiado ao nível visual — o Figma
ligado no PRD ainda reflete uma paleta anterior (creme/terracota) e precisa
de ser refeito antes de desenhar os ecrãs.

## Product Principles

1. Talhado ao fluxo real da família, não ao conjunto de funcionalidades
   genérico de um produto de terceiros.
2. Igualmente funcional em telemóvel (na cozinha) e computador (a
   planear) — nenhum dos dois é secundário.
3. Um único stack e uma única base de dados próprios, em vez de manter
   várias ferramentas de terceiros com abordagens diferentes entre si.
4. Vive dentro do ecossistema self-hosted existente do homelab, seguindo o
   mesmo padrão arquitetural já validado no Securo.
