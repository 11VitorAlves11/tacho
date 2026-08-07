# PRD — Tacho (App de Receitas de raiz)

**Autor:** Vítor Alves
**Data:** Agosto 2026
**Estado:** Rascunho v2 — substitui a v1
**Ficheiro de design:** [Figma — Receitas App Design Revamp](https://www.figma.com/design/cOvlbDp3d0osvTcPT6TFSR)

> **Mudança face à v1:** a v1 assumia um frontend novo consumindo a API do Tandoor como backend. Esta versão muda de direção: a app é construída **inteiramente de raiz** (backend, base de dados e frontend próprios), com o objetivo de replicar as funcionalidades essenciais do **Tandoor Recipes** e do **Mealie**, permitindo desligar ambos após a migração.

---

## 1. Contexto e problema

O homelab corre atualmente o Tandoor (gestão de receitas, nutrição, shopping list) e foi considerado também o Mealie (meal planning mais simples e elegante). Manter/integrar dois serviços diferentes, cada um com o seu design, API e stack (Tandoor: Django + Postgres + Nginx; Mealie: FastAPI + Vue), implica complexidade operacional desnecessária para um único agregado familiar.

Em vez de construir um frontend sobre um dos dois (abordagem da v1), a decisão é consolidar as funcionalidades de ambos numa **única aplicação própria**, com um único stack, uma única base de dados, e o design já definido no Figma.

## 2. Objetivo

Construir o **Tacho**, uma web app de receitas self-hosted, de raiz, que substitua completamente o Tandoor e o Mealie, cobrindo:
- Gestão de receitas (com importação automática por URL)
- Planeamento de refeições (meal planner semanal)
- Lista de compras (gerada automaticamente a partir do plano)
- Modo Cozinha dedicado
- Suporte multi-utilizador para o agregado (Vítor + Mariana)

## 3. Utilizador-alvo

Utilizador doméstico (Vítor e Mariana), self-hosted no Proxmox, com acesso remoto via Tailscale. Não é um produto multi-tenant/SaaS.

## 4. Âmbito — funcionalidades v1

Lista consolidada a partir das funcionalidades centrais do Tandoor e do Mealie:

### 4.1 Gestão de receitas
- CRUD completo (criar, editar, apagar, duplicar receitas)
- Editor de passos e ingredientes, com unidades e conversão de porções (escalar receita)
- Fotos por receita (upload próprio)
- **Importação automática por URL** — scraping de sites de receitas (reutilizar biblioteca open-source de parsing, ex.: `recipe-scrapers`, em vez de reinventar o parser)
- Informação nutricional por receita (entrada manual na v1; cálculo automático a partir dos ingredientes fica em v2)
- Notas privadas por receita

### 4.2 Organização e pesquisa
- Categorias e tags
- Cookbooks / coleções temáticas (ex. "Jantares rápidos", "Sobremesas de Natal")
- Pesquisa full-text com filtros combinados (categoria + tag + tempo de preparo)

### 4.3 Planeamento de refeições
- Calendário semanal/mensal com slots: pequeno-almoço, almoço, jantar, lanche
- Drag & drop de receitas para o plano
- Regras de plano (ex. "só receitas rápidas às terças-feiras")
- Sugestão aleatória de receita para um slot

### 4.4 Lista de compras
- Geração automática a partir do plano de refeições da semana
- Agrupamento por secção/corredor de supermercado
- Itens manuais (não ligados a receita)
- Marcar item como comprado, desfazer
- Consolidação de ingredientes repetidos entre receitas

### 4.5 Modo Cozinha
- Ecrã full-screen, passo a passo, sem bloqueio automático do ecrã
- Timers por passo quando aplicável
- Navegação Anterior/Seguinte

### 4.6 Multi-utilizador
- Papéis: viewer / editor / admin
- Agregado partilhado via **Workspace** (mesmo modelo do Securo) — Vítor e Mariana pertencem ao mesmo Workspace e veem/editam o mesmo plano e lista de compras
- **Fluxo:** cada pessoa tem a sua própria conta (login/password próprios via `fastapi-users`); o dono cria o Workspace e convida a segunda pessoa por email; depois de aceite, ambas as contas ficam associadas ao mesmo Workspace e passam a ver/editar os mesmos dados — não há separação entre "receitas do Vítor" e "receitas da Mariana", é tudo do agregado
- Cada conta pode, no futuro, pertencer a mais do que um Workspace (ex. um workspace pessoal separado do partilhado) — não necessário para a v1, mas o modelo já suporta sem alterações estruturais

### 4.7 Social leve
- Comentários e avaliação (estrelas) por receita

### 4.8 Dados e integrações
- Exportação/backup dos dados (para não repetir o erro de ficar preso a uma app que desaparece)
- API REST própria, para integrações futuras (ex. Home Assistant, atalhos iOS)
- Script de **migração** para importar as receitas já existentes no Tandoor (via export/JSON) para a nova base de dados

## 5. Fora de âmbito (v1)
- Leitura de códigos de barras
- Sincronização com Nextcloud/Dropbox
- Arquitetura de plugins de terceiros
- Suporte multi-idioma (apenas PT-PT / EN)
- Apps móveis nativas (só web responsiva mobile+desktop)
- Cálculo automático de nutrição a partir dos ingredientes (v2)

## 6. Design

> **Nota:** esta secção substitui a direção de design anterior (creme/terracota, já prototipada no Figma). A nova paleta segue referências de apps de nutrição/saúde recolhidas pelo Vítor — o ficheiro Figma existente fica desatualizado e terá de ser refeito segundo esta direção antes de avançar para a implementação dos ecrãs.

### 6.1 Racional

As referências recolhidas (apps de nutrição/meal tracking) partilham um padrão comum: **fundo claro em tom sage/verde muito suave**, cards brancos bem destacados, um **verde floresta profundo** reservado para ações principais (CTAs, headers de destaque) e um **verde-folha mais vivo** como acento secundário. Este padrão comunica "saudável, fresco, natural" de forma muito mais direta do que a paleta quente creme/terracota anteriormente escolhida — e encaixa melhor num produto que também vai lidar com planeamento de refeições e informação nutricional (Secção 4.3–4.4), não só com receitas isoladas.

Decisões-chave:
- **Verde como cor de marca**, não como mais uma tag de categoria — inverte a lógica anterior, em que o laranja era o acento único e o verde só sinalizava "vegetariano"
- **Fundo sage muito claro** em vez de creme quente — mais alinhado com "nutrição/bem-estar" do que com "comida caseira/artesanal"
- **Laranja mantém-se**, mas passa a papel secundário — útil para dados nutricionais (ex. hidratos de carbono, como nas referências) e para o Modo Cozinha, onde ainda faz sentido um contraste de "modo ativo"
- Cards continuam brancos e muito destacados do fundo — esse princípio mantém-se da direção anterior, porque funciona bem em ambas as paletas

### 6.2 Mini design system

**Cores**

| Token | Uso | Hex |
|---|---|---|
| `bg-sage` | Fundo principal da app | `#EAF0E7` |
| `bg-sage-deep` | Headers/heroes com gradiente (variante mais escura do fundo) | `#1F3D2B` → `#2D6A4F` (gradiente) |
| `card-white` | Fundo dos cards | `#FFFFFF` |
| `primary-forest` | CTA principal, elementos ativos, botão "Iniciar Modo Cozinha" | `#2D5F3F` |
| `accent-leaf` | Acento secundário, ícones, progress bars | `#4CAF50` |
| `accent-orange` | Dados nutricionais (calorias/hidratos), badges de aviso | `#F2994A` |
| `text-primary` | Texto principal | `#1C2B1F` |
| `text-secondary` | Metadata, legendas | `#5C6B5E` |

**Tipografia**
- Família: Inter (mantém-se)
- Números/métricas em destaque (ex. calorias, tempo): peso Bold, tamanho grande (24–56px conforme contexto) — inspirado nos "hero numbers" das referências (ex. "456 kcal over", "62.7 Nutrition Score")
- Títulos de secção: Semi Bold, 16–20px
- Corpo/metadata: Regular, 13–14px

**Componentes**
- Cards com cantos arredondados (16–20px), sombra suave, sempre brancos sobre o fundo sage
- Barra de pesquisa em pill, fundo branco ou sage-claro, ícone à esquerda
- Progress bars horizontais para macros/progresso (padrão claro nas 3 referências) — reutilizável para progresso do plano semanal
- Bottom nav (mobile) em pill flutuante com 4–5 ícones, item ativo destacado a verde-floresta
- Headers de secção/hero podem usar o gradiente `bg-sage-deep` como nas referências, para dar profundidade sem sair da paleta

### 6.3 Estado dos ecrãs
Os ecrãs desenhados no Figma (Home, Detalhe da Receita, Modo Cozinha) usam a paleta creme/terracota anterior e **precisam de ser refeitos** com esta nova direção verde. Em falta desenhar, já na paleta nova: Planeamento de refeições e Lista de Compras.

## 7. Arquitetura técnica

```
┌────────────────────┐     REST/JSON    ┌─────────────────────┐
│  Frontend            │ ───────────────▶ │  Backend (novo)       │
│  React + TS + Vite     │ ◀─────────────── │  FastAPI               │
│  CT Docker             │                  │  CT Docker             │
└────────────────────┘                  └─────────┬───────────┘
                                                      │
                              ┌───────────────────────┼───────────────────────┐
                              │                        │                        │
                    ┌─────────▼───────────┐  ┌─────────▼───────────┐ ┌─────────▼───────────┐
                    │  PostgreSQL           │  │  Redis                 │ │  Celery worker         │
                    │  CT Docker             │  │  CT Docker             │ │  (importação de       │
                    │  (dados por Workspace) │  │  (fila de tarefas)     │ │  receitas por URL)    │
                    └──────────────────────┘  └──────────────────────┘ └──────────────────────┘
```

- **Backend:** Python + FastAPI, SQLAlchemy + Alembic para migrações — mesmo padrão do Securo
- **Autenticação:** `fastapi-users` (mesma biblioteca do Securo), em vez de sistema de login próprio ou dependência exclusiva do Authentik — mantém os dois projetos do homelab com o mesmo modelo de utilizadores/sessões. Integração com Authentik SSO fica como possibilidade futura (v2), não como decisão da v1
- **Multi-tenancy / agregado familiar:** modelo de **Workspaces**, tal como no Securo — todas as receitas, planos e listas de compras pertencem a um Workspace (o agregado Vítor+Mariana), com pedidos à API sempre com o scope definido por um header `X-Workspace-Id`. Isto substitui a descrição solta de "household" da Secção 4.6 por um padrão técnico já validado no outro projeto
- **Fila de tarefas em background:** **Redis + Celery**, replicando o padrão do Securo (lá usado para sincronização bancária). Aqui o worker Celery trata da **importação de receitas por URL** (scraping), que não deve bloquear o pedido HTTP — o utilizador cola o link, o pedido volta de imediato, e a receita aparece assim que o worker terminar o parsing
- **Base de dados:** PostgreSQL (dados próprios, exportáveis, sem lock-in)
- **Scraper de receitas:** biblioteca open-source existente, corrida dentro do worker Celery (não construir parser de raiz — alto risco/baixo retorno)
- **Frontend:** React + TypeScript + Vite + Tailwind CSS, responsivo mobile/desktop, consumindo a API própria — alinhado deliberadamente com o stack do Securo (mesmas convenções nos dois projetos do homelab, e o Claude Code mantém-se "afinado" ao mesmo estilo em ambos)
- **Deploy:** Docker Compose (5 containers: frontend, backend, worker Celery, PostgreSQL, Redis), correndo no Proxmox ao lado dos restantes CTs
- **Acesso remoto:** via Tailscale, como o resto do stack

### 7.1 Migração
Script único de migração: exportar dados do Tandoor (formato JSON/backup) → transformar → importar para o schema novo. Corre uma vez, antes de desligar o Tandoor definitivamente.

## 8. Requisitos não-funcionais
- Stack completo (frontend + backend + worker Celery + PostgreSQL + Redis) deve correr confortavelmente no Mini PC N200/12GB atual, junto aos restantes CTs — Redis e o worker Celery são processos leves em repouso, só ativos durante importações de receitas
- Tempo de resposta da API < 200ms em rede local para operações comuns (listar receitas, obter detalhe)
- Interface responsiva única para mobile e desktop (não apps separadas)
- Dados sempre exportáveis, sem dependência de serviço externo

## 9. Métricas de sucesso
- Tandoor e Mealie podem ser desligados sem perda de funcionalidade
- Todas as receitas migradas com sucesso, sem perda de dados
- Planeamento semanal e lista de compras usados ativamente por ambos (Vítor e Mariana)
- Modo Cozinha usado durante a confeção real, substituindo o telemóvel/tablet a abrir o site antigo

## 10. Roadmap

| Fase | Conteúdo |
|---|---|
| v1.0 | Backend + BD + API própria; gestão de receitas (CRUD, importação por URL, categorias/tags); Home, Detalhe, Modo Cozinha (mobile); Home, Detalhe (desktop); migração de dados do Tandoor |
| v1.1 | Planeamento de refeições + Lista de Compras (design no Figma + implementação) |
| v1.2 | Multi-utilizador (Workspace partilhado Vítor + Mariana), comentários/avaliações |
| v2 | Cálculo automático de nutrição, Modo Cozinha desktop, fotos reais em vez de placeholders, Authentik SSO se não entrar já na v1.0 |

## 11. Riscos e questões em aberto
- **Esforço de desenvolvimento:** ao não reaproveitar backend existente, o esforço é significativamente maior do que a abordagem da v1 — mitigar reutilizando bibliotecas open-source maduras (scraper de receitas, parsing de ingredientes) em vez de construir tudo à mão
- **Parsing de receitas por URL:** é a funcionalidade tecnicamente mais complexa; validar cedo com uma biblioteca existente antes de investir tempo em UI à sua volta
- **Migração de dados:** garantir que o export do Tandoor cobre tudo o que interessa preservar (fotos, notas, histórico) antes de desligar o serviço
- **Prioridade relativa:** confirmar se compensa entregar v1.0 sem planeamento/lista de compras (reduzindo valor imediato face ao Mealie) ou se vale a pena adiantar essas duas funcionalidades para a v1.0 mesmo aumentando o esforço inicial

---

*Documento vivo — atualizar à medida que a arquitetura for validada e os ecrãs de Planeamento/Lista de Compras forem desenhados no Figma.*
