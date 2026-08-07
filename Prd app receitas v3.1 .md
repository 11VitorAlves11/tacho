# PRD — Tacho (App de Receitas de raiz)

**Autor:** Vítor Alves
**Data:** Agosto 2026
**Estado:** v3.2 — substitui a v3.1 (migração do Tandoor removida: não existem receitas lá para migrar)
**Ficheiro de design:** [Figma — Receitas App Design Revamp](https://www.figma.com/design/cOvlbDp3d0osvTcPT6TFSR)
**Código:** `tacho_app` (backend + frontend), a correr no CT 111, ainda fora do `docker-compose.yml` principal do homelab

> **Papel deste documento:** fonte de verdade de âmbito e decisões de produto. O dia-a-dia (tarefas, gaps técnicos) vive no `TODO.md` do repositório; os tokens e componentes visuais vivem no `DESIGN.md`. Este PRD sincroniza-se com ambos periodicamente, mas não os substitui.

---

## 1. Contexto e problema

O homelab tem atualmente o Tandoor instalado (gestão de receitas, nutrição, shopping list) e foi considerado também o Mealie (meal planning mais simples e elegante). Manter/integrar dois serviços diferentes, cada um com o seu design, API e stack (Tandoor: Django + Postgres + Nginx; Mealie: FastAPI + Vue), implica complexidade operacional desnecessária para um único agregado familiar. O Tandoor não tem receitas guardadas neste momento, pelo que **não há migração de dados a fazer** — o Tacho arranca com a base de dados vazia e o Tandoor pode ser desligado assim que o Tacho estiver implantado.

A decisão foi consolidar as funcionalidades de ambos numa **única aplicação própria**, com um único stack, uma única base de dados, e o design definido no Figma.

## 2. Objetivo

Construir o **Tacho**, uma web app de receitas self-hosted, de raiz, que substitua completamente o Tandoor e o Mealie, cobrindo:
- Gestão de receitas (com importação automática por URL)
- Planeamento de refeições (meal planner semanal)
- Lista de compras (gerada automaticamente a partir do plano)
- Modo Cozinha dedicado
- Suporte multi-utilizador para o agregado (Vítor + Mariana)

## 3. Utilizador-alvo

Utilizador doméstico (Vítor e Mariana), self-hosted no Proxmox, com acesso remoto via Tailscale. Não é um produto multi-tenant/SaaS.

## 4. Estado de implementação (2026-08-07)

Resumo — o detalhe por funcionalidade está na Secção 5, com símbolo de estado em cada item (✅ feito · 🔶 parcial ou por testar · ⬜ por fazer).

- **Backend** (FastAPI + PostgreSQL + Redis/Celery): modelos, CRUD de receitas/categorias/tags, importação por URL via Celery, `/health` e CORS — tudo testado ponta a ponta via HTTP. Existe também um script de migração do Tandoor (`migrate_from_tandoor.py`), entretanto tornado desnecessário — ver Secção 5.8.
- **Frontend** (React + TS + Vite + Tailwind): Home, Detalhe, Modo Cozinha, Adicionar (link/manual), Editar/Apagar, menu de utilizador. O editor manual e o menu de utilizador passaram build e linter, mas **ainda não foram testados visualmente no browser**.

## 5. Âmbito — funcionalidades v1

Lista consolidada a partir das funcionalidades centrais do Tandoor e do Mealie, com estado atual.

### 5.1 Gestão de receitas
- ✅ CRUD completo (criar, editar, apagar receitas)
- ⬜ **Duplicar receita** — estava no âmbito original e caiu silenciosamente na v3; repor. Útil para variações ("Bolo de cenoura" → "Bolo de cenoura sem lactose") e barato de implementar *(v1.1)*
- ⬜ **Tempos separados: preparação / cozedura / total** — hoje só existe "tempo"; Tandoor e Mealie distinguem os três, e faz diferença para escolher "o que dá para fazer hoje à noite" *(v1.1)*
- ✅ Editor de passos e ingredientes
- 🔶 **Escalar porções** — decisão de implementação tomada: sem alterações ao backend, seguindo o padrão do Mealie (recalcular `quantity` em runtime a partir de `servings` desejado vs. original, só no frontend). Por implementar.
- ⬜ **Cabeçalhos de secção nos ingredientes** (ex. "Para o recheio:") — padrão real de Tandoor e Mealie (`Ingredient.is_header`); mantém-se como funcionalidade de produto (receitas com estrutura em secções), agora sem urgência ligada a migração
- ⬜ **Armazenamento de imagens** — o modelo `Recipe` não tem campo de imagem; pré-requisito do upload pela UI e das fotos vindas da importação por URL
- ⬜ **Upload de fotos pela UI** — adicionar/substituir foto de uma receita diretamente no formulário (criar e editar), e captura pela câmara no telemóvel (input nativo com `capture` — útil para fotografar o prato acabado de fazer). Depende do item anterior; inclui também mostrar a foto no card da Home e no hero do Detalhe, substituindo os placeholders
- ⬜ **Galeria de fotos por receita** — evolução do item anterior: várias fotos por receita (o prato em diferentes ocasiões), com uma marcada como capa *(v2; a v1 fica-se por uma foto)*
- ✅ **Importação automática por URL** (`recipe-scrapers`, via Celery, testada com sites reais PT)
- ⬜ **Fallback de importação por URL via Gemini API** — quando o `recipe-scrapers` não suporta o site ou devolve resultado incompleto, enviar o HTML/texto da página ao Gemini para extrair a receita estruturada (título, ingredientes, passos, tempos, porções). Corre no mesmo worker Celery; o resultado entra sempre em modo de revisão antes de gravar
- ⬜ **Importação por foto (Gemini Vision)** — nova forma de adicionar receita: fotografar uma página de livro de receitas, uma receita manuscrita ou um ecrã, e o Gemini extrai a receita estruturada. Entrada pela mesma UI de "Adicionar receita" (terceira aba, junto a "Por link" e "À mão"), com upload/captura de 1–3 fotos; resultado abre pré-preenchido no formulário manual para revisão antes de gravar — nunca gravação directa sem confirmação
- 🔶 **Parsing de ingredientes da importação** — a linha scraped fica inteira em `Ingredient.name`, sem separar quantidade/unidade/nome. Deixado deliberadamente por resolver para não somar um segundo risco técnico não validado na mesma fatia de trabalho
- ⬜ **Filtro de lixo nos passos importados** — alguns sites (ex. `mundodereceitasbimby.com.pt`) devolvem entradas tipo `"@type"`/`"position"` misturadas com passos reais
- ⬜ Informação nutricional por receita (entrada manual) — sem campos no modelo nem UI; é também o motivo de o `accent-orange` do design system ainda não aparecer em lado nenhum
- ⬜ Notas privadas por receita
- ⬜ **Fracções em unidades** (ex. "½ chávena" em vez de "0.5 chávena") — padrão do Mealie (`Unit.fraction`)
- ⬜ **"Última vez feita"** — marcar `last_made = now()` ao concluir o Modo Cozinha; alimenta diretamente a métrica M3 (Secção 10)
- ⬜ **Custo por receita/porção** — preço estimado por ingrediente (introduzido manualmente, com atualização ocasional) → custo total do prato e por porção, visível no Detalhe ao lado das calorias. Nenhum dos dois (Tandoor/Mealie) faz isto bem, e alinha com o perfil de otimização de finanças do agregado (Securo). Depende do parsing de ingredientes estruturado (quantidade/unidade separadas) *(v2)*

### 5.2 Organização e pesquisa
- ✅ Categorias e tags
- ⬜ **Cookbooks / coleções** — fase por decidir (Decisão #3): lista manual (Tandoor) ou coleção "inteligente" por filtro de tags/categoria (Mealie — mais trabalho, mais útil a prazo)
- ⬜ **Favoritos** — a sidebar do design tem "Favoritos" desde o primeiro desenho, mas nunca foi especificado. Definição: coração rápido na receita; enquanto não houver contas (pré-v1.2), o favorito é do Workspace; com contas, passa a ser por utilizador (padrão `favorited_by` do Mealie, alinhado com a avaliação por estrelas da Secção 5.7) *(v1.1)*
- ⬜ **Pesquisa por ingredientes disponíveis** — "o que consigo fazer com frango e cogumelos?": devolve receitas ordenadas por quantos dos ingredientes indicados usam. Depende do parsing de ingredientes estruturado (5.1) e casa com a pesquisa full-text *(v2)*
- 🔶 **Pesquisa** — hoje `ILIKE` sobre o título, com filtros por categoria/tag a funcionar. A versão full-text (Postgres `tsvector`, o mesmo caminho do Tandoor) fica agendada para a **v1.1** — o `ILIKE` é aceitável enquanto a biblioteca de receitas for pequena, mas degrada com o crescimento; *(resolve a contradição da v3, que pedia full-text como requisito v1 mas o agendava para v2)*

### 5.3 Planeamento de refeições
- ⬜ Nada construído. Calendário semanal/mensal, slots (pequeno-almoço/almoço/jantar/lanche), drag & drop, regras de plano, sugestão aleatória
- Referência de modelo: o campo `Food.supermarket_category` do Tandoor é um bom padrão para o agrupamento por corredor pedido na Secção 5.4 — usar como inspiração de schema, sem inventar uma estrutura nova

### 5.4 Lista de compras
- ⬜ Nada construído. Geração automática a partir do plano, agrupamento por secção/corredor de supermercado, itens manuais, marcar como comprado/desfazer, consolidação de ingredientes repetidos entre receitas
- ⬜ **Despensa/inventário básico** — marcar o que existe em casa; cruza com a pesquisa por ingredientes ("o que consigo fazer com o que tenho", Secção 5.2) e com a lista de compras (não sugerir o que já existe). **Âmbito deliberadamente contido:** é território mais do Grocy do que do Tandoor/Mealie — na v2 fica-se por uma lista simples de "tenho/não tenho" por ingrediente, sem quantidades, validades nem códigos de barras, para não virar um segundo projeto *(v2)*

### 5.5 Modo Cozinha
- ✅ Ecrã full-screen, passo a passo, com wake lock (impede o ecrã de bloquear durante a confeção)
- ✅ Navegação Anterior/Seguinte
- ⬜ Timers por passo — agendado para a **v1.1** *(na v3 este item não pertencia a fase nenhuma)*
- ⬜ **Tamanho de letra ajustável** — toggle A/A⁺ no Modo Cozinha; o telemóvel fica pousado longe na bancada e a legibilidade a 1 metro faz mais diferença do que parece *(v1.1)*
- ⬜ **Notas pós-confeção / diário de cozinha** — ao concluir o Modo Cozinha, além do `last_made`, pedir opcionalmente uma nota rápida ("da próxima vez, menos sal, +10 min de forno"), guardada com data no histórico da receita e visível no Detalhe. É conhecimento que hoje se perde; complementa a métrica M3 *(v1.1)*
- ⬜ **PWA instalável** — manifest + service worker básico, para "instalar" a app no ecrã inicial do telemóvel e abrir em ecrã inteiro, sem chrome do browser *(v1.1)*
- ⬜ **Modo Cozinha offline** — uma receita aberta continua a funcionar (passos, timers) se o Wi-Fi da cozinha falhar; cache da receita ativa via service worker *(v2)*

### 5.6 Multi-utilizador
- ⬜ Nada construído além do Workspace único semeado na migração inicial da BD (Alembic) — sem contas reais, sem `fastapi-users` ligado, sem convite/associação (Decisões #1 e #2)
- ✅ **Menu de utilizador no header** — placeholder honesto: mostra "Vítor & Mariana" fixo, com nota de que contas individuais chegam na v1.2, sem fingir um "Sair" que não funciona (Decisão #5)
- **Modelo-alvo (v1.2):** cada pessoa com conta própria; ambas associadas ao mesmo Workspace; sem separação entre "receitas do Vítor" e "receitas da Mariana". O mecanismo de associação (convite por email vs. criação direta da segunda conta) é a Decisão #2

### 5.7 Social leve
- ⬜ Comentários
- ⬜ **Avaliação por estrelas** — padrão especificamente do Mealie (`rating` + `favorited_by`); o Tandoor só tem comentários

### 5.8 Dados e integrações
- ⬜ Exportação/backup dos dados próprios do Tacho (critério: qualquer pessoa consegue extrair tudo num formato aberto sem acesso à BD). **Formato: schema.org Recipe (JSON-LD)** — o mesmo standard que os sites de receitas usam e que o `recipe-scrapers` lê; garante que qualquer app futura importa as receitas do Tacho sem script de migração dedicado — a lição do Tandoor aplicada ao próprio Tacho *(v1.1)*
- ⬜ **Vista de impressão / PDF por receita** — layout limpo (sem navegação, uma coluna, ingredientes + passos) para imprimir ou gerar PDF e partilhar uma receita com família sem lhes dar acesso à app *(v2)*
- ✅ API REST própria (testada ponta a ponta via HTTP)
- 🗑 Script de migração do Tandoor (`backend/scripts/migrate_from_tandoor.py`) — construído numa fase em que se assumia haver dados a migrar; **tornado desnecessário** porque o Tandoor não tem receitas guardadas. Pode ser removido do repositório ou arquivado; não recebe mais trabalho

## 6. Fora de âmbito (v1)
- Leitura de códigos de barras
- Sincronização com Nextcloud/Dropbox
- Arquitetura de plugins de terceiros
- Suporte multi-idioma (apenas PT-PT / EN)
- Apps móveis nativas (só web responsiva mobile+desktop)
- Cálculo automático de nutrição a partir dos ingredientes (fica para v2)

## 7. Design

### 7.1 Racional
Paleta sage/verde-floresta, inspirada em apps de nutrição/saúde. O **`DESIGN.md` do repositório é a fonte de verdade viva** para tokens e componentes; este PRD mantém apenas o resumo abaixo para contexto e não deve divergir dele.

### 7.2 Mini design system (resumo)

| Token | Uso | Hex |
|---|---|---|
| `bg-sage` | Fundo principal da app | `#EAF0E7` |
| `bg-sage-deep` | Headers/heroes com gradiente | `#1F3D2B` → `#2D6A4F` |
| `card-white` | Fundo dos cards | `#FFFFFF` |
| `primary-forest` | CTA principal, elementos ativos | `#2D5F3F` |
| `accent-leaf` | Acento secundário, ícones, progress bars | `#4CAF50` |
| `accent-orange` | Dados nutricionais — ainda sem uso real (ver 5.1) | `#F2994A` |
| `text-primary` | Texto principal | `#1C2B1F` |
| `text-secondary` | Metadata, legendas | `#5C6B5E` |

### 7.3 Dark mode *(v1.1)*
O design system atual só define o tema claro. Fica em aberto na v1.0, mas a v1.1 adiciona uma **variante escura** dos tokens (a cozinha à noite e a consulta na cama a planear o jantar pedem-no): mesmo mapa de tokens (`bg-sage`, `card-white`, etc.) com valores alternativos, alternância automática por preferência do sistema (`prefers-color-scheme`) com override manual. Os tokens já existem como variáveis — o trabalho é definir a paleta escura no `DESIGN.md` e garantir contraste equivalente.

### 7.4 Estado dos ecrãs
Desenhados no Figma, já na paleta verde: Home, Detalhe, Modo Cozinha (mobile + desktop, exceto Modo Cozinha desktop). Implementados no frontend com o mesmo mundo visual. Por desenhar **e** implementar: Planeamento, Lista de Compras. O ecrã "Adicionar receita" (link/manual) foi implementado sem passar pelo Figma — desenhá-lo a posteriori para manter o Figma como espelho fiel do produto.

## 8. Arquitetura técnica

```
┌────────────────────┐     REST/JSON    ┌─────────────────────┐
│  Frontend            │ ───────────────▶ │  Backend               │
│  React + TS + Vite     │ ◀─────────────── │  FastAPI               │
└────────────────────┘                  └─────────┬───────────┘
                                                      │
                              ┌───────────────────────┼───────────────────────┐
                              │                        │                        │
                    ┌─────────▼───────────┐  ┌─────────▼───────────┐ ┌─────────▼───────────┐
                    │  PostgreSQL           │  │  Redis                 │ │  Celery worker         │
                    │  (dados por Workspace) │  │  (fila de tarefas)     │ │  (importação por URL) │
                    └──────────────────────┘  └──────────────────────┘ └──────────────────────┘
```
*(Tudo em Docker; hoje no CT 111 de desenvolvimento, deploy definitivo pendente — Decisão #4.)*

- **Backend:** Python + FastAPI, SQLAlchemy + Alembic — implementado
- **Autenticação (v1.2):** `fastapi-users`, assumido "mesmo padrão do Securo" — **equivalência nunca confirmada contra o código real do Securo**, só por analogia de stack. Verificar antes de construir (Decisão #1)
- **Multi-tenancy:** modelo de Workspace com scope por pedido (`X-Workspace-Id`) — schema existe, só com um Workspace semeado
- **Fila de tarefas:** Redis + Celery — implementado, em uso na importação por URL
- **Base de dados:** PostgreSQL — implementado
- **Scraper:** `recipe-scrapers` dentro do worker Celery — implementado
- **Gemini API (importação inteligente):** chamada a partir do worker Celery para (a) fallback de extração quando o `recipe-scrapers` falha e (b) importação por foto (Vision). Chave de API guardada como secret no `.env` do backend, nunca exposta ao frontend. Usar o free tier enquanto o volume for doméstico; se um dia houver custos, são desprezáveis a esta escala. **Funcionalidade opcional por configuração:** sem chave configurada, a app funciona normalmente e estas duas formas de importação ficam simplesmente indisponíveis na UI
- **Frontend:** React + TypeScript + Vite + Tailwind CSS — implementado
- **Deploy:** pendente (Decisão #4) — ver requisito de segurança na Secção 9
- **Acesso remoto:** via Tailscale, como o resto do stack — só depois do deploy definitivo

## 9. Requisitos não-funcionais

- **Segurança do deploy sem autenticação:** enquanto não existir autenticação real (v1.2), a app **só pode estar acessível dentro da tailnet** (Tailscale) — nunca exposta à LAN de convidados nem à internet. Este requisito resolve explicitamente o desalinhamento do roadmap (deploy na v1.0, auth só na v1.2): é aceitável implantar sem login **apenas** porque a superfície de acesso fica limitada à tailnet do agregado. Revisitar se alguma vez se quiser partilhar acesso fora dela.
- Stack completo (frontend + backend + worker + PostgreSQL + Redis) deve correr confortavelmente no Mini PC N200/12GB, junto aos restantes CTs
- Tempo de resposta da API < 200ms em rede local para operações comuns
- Interface responsiva única para mobile e desktop
- Dados sempre exportáveis, sem dependência de serviço externo **para o funcionamento base** — inclui as fotos carregadas, guardadas em disco local (volume Docker), não em serviço externo, e cobertas pelo mesmo esquema de backups da BD. Exceção deliberada: a importação inteligente (fallback de URL e importação por foto) usa a Gemini API, um serviço externo — é opcional, desativável, e a sua indisponibilidade nunca afeta as receitas já guardadas nem as restantes funcionalidades. Nota de privacidade: nesses dois fluxos, o conteúdo da página/foto é enviado à Google — aceitável para receitas, mas fica registado como decisão consciente
- Backups: a BD e o volume de fotos do Tacho entram no esquema de backups existente do homelab a partir do momento em que a app começa a guardar receitas reais — **agendados e automáticos** (num homelab, o que não é automático não acontece), com um teste de restauro feito pelo menos uma vez antes de declarar a v1.0 concluída

## 10. Métricas de sucesso

Reformuladas para serem verificáveis, com o momento de avaliação explícito:

| # | Métrica | Como se verifica | Quando |
|---|---|---|---|
| M1 | Tandoor e Mealie desligados | CTs parados e removidos do arranque automático, sem falta sentida | Assim que a v1.0 estiver implantada e em uso |
| M2 | Adoção do planeamento/lista | ≥ 3 semanas com plano preenchido e lista gerada, no primeiro mês após a v1.1 | 1 mês após v1.1 |
| M3 | Adoção do Modo Cozinha | ≥ 5 receitas com `last_made` preenchido no primeiro mês (requer o item "Última vez feita", 5.1) | 1 mês após v1.0 em uso |
| M4 | Biblioteca a crescer | ≥ 20 receitas criadas/importadas no primeiro mês (a BD parte do zero — sem migração, a adoção mede-se pelo que se adiciona) | 1 mês após v1.0 em uso |

## 11. Roadmap

| Fase | Conteúdo | Estado |
|---|---|---|
| v1.0 (núcleo) | CRUD de receitas; importação por URL; Home, Detalhe, Modo Cozinha, Adicionar/Editar | 🔶 Construído; ver critérios de aceitação abaixo |
| v1.0 (deploy) | Container definitivo no homelab, acessível só via tailnet; desligar Tandoor/Mealie | ⬜ Decisão #4 |
| v1.1 | Planeamento de refeições + Lista de Compras (Figma + implementação); pesquisa full-text (`tsvector`); timers no Modo Cozinha; parsing de ingredientes e filtro de lixo na importação; **importação inteligente via Gemini (fallback de URL + importação por foto)**; duplicar receita; tempos prep/cozedura separados; favoritos; notas pós-confeção; PWA instalável; tamanho de letra ajustável no Modo Cozinha; dark mode; export schema.org JSON-LD | ⬜ |
| v1.2 | Multi-utilizador real (contas, `fastapi-users`, associação ao Workspace), avaliação por estrelas, comentários, favoritos por utilizador | ⬜ Decisões #1, #2 e #5 condicionam o desenho |
| v2 | Cálculo automático de nutrição, Modo Cozinha desktop e offline, fracções em unidades, Cookbooks (se não entrarem antes — Decisão #3), pesquisa por ingredientes disponíveis, galeria de fotos por receita, vista de impressão/PDF, custo por receita/porção, despensa/inventário básico, Authentik SSO | ⬜ |

### 11.1 Critérios de aceitação da v1.0 ("definição de pronto")

A v1.0 só se considera concluída quando **todos** estes pontos estiverem verificados:

1. Editor manual e menu de utilizador testados visualmente no browser (hoje só passaram build/linter)
2. Cabeçalhos de secção nos ingredientes suportados no modelo e no editor
3. Campo de imagem no modelo `Recipe`, com **upload/substituição de foto funcional na UI** (formulário de criar/editar) e a foto visível no card da Home e no hero do Detalhe
4. Deploy definitivo feito, acessível apenas via tailnet (Secção 9), com Tandoor/Mealie desligados e **backup automático configurado + um restauro testado com sucesso**
5. Informação nutricional com entrada manual disponível na UI *(mantém-se da definição original de v1.0; se for adiada para v1.1, registar como decisão explícita, não por omissão)*

## 12. Decisões pendentes

Itens que só o Vítor pode resolver — bloqueiam trabalho a jusante.

1. **`fastapi-users` + Workspace — bate mesmo certo com o Securo?** Assumido por analogia de stack, nunca confirmado contra o código real. Verificar no GitHub do `securo-finance` antes de construir a autenticação da v1.2.
2. **Associação da segunda pessoa ao Workspace, sem SMTP no homelab.** O plano original assumia convite por email; não há infraestrutura de email montada. Alternativa: o dono cria a segunda conta diretamente. Verificar primeiro como o Tandoor resolve a associação de utilizadores a um espaço sem depender de email, e decidir entre os dois fluxos.
3. **Cookbooks: em que fase entram, e em que modelo?** Lista manual (Tandoor) ou coleção por filtro inteligente (Mealie)? Hoje estão provisoriamente na v2 do roadmap — confirmar ou antecipar.
4. **Deploy definitivo.** Decidir VMID/IP novo segundo a convenção do `homelab/CLAUDE.md`; ação de infraestrutura partilhada, não tomada sem autorização explícita. Inclui desligar o Tandoor (e Mealie, se instalado) depois de o Tacho estar no ar. - sim troca o tandoor por esta app, mas esta app deve ser feito o deploy pelo docker

5. **Menu de utilizador.** Confirmar se o placeholder atual ("Vítor & Mariana" fixo, sem "Sair") é o comportamento desejado até à v1.2, ou se deve ficar mais escondido até haver autenticação real. - pode ficar assim para já

## 13. Riscos

- **Divergência PRD ↔ código** — a implementação avança mais depressa que o documento; mitigação: `TODO.md`/`DESIGN.md` como fonte do dia-a-dia, este PRD sincronizado a cada marco (fim de fase ou decisão tomada), não a cada sessão
- **Importação por URL "meio pronta"** — parsing de ingredientes e filtro de lixo ficaram deliberadamente por resolver; até estarem feitos (v1.1), a importação deve ser tratada como funcional mas com revisão manual obrigatória do resultado
- **Qualidade da importação via Gemini** — extração por LLM pode inventar ou "corrigir" quantidades e passos de forma silenciosa (sobretudo em fotos manuscritas ou de má qualidade); mitigação já no desenho: o resultado abre sempre pré-preenchido no formulário para revisão humana, nunca é gravado diretamente. Validar cedo com fotos reais (livros PT, letra manuscrita) antes de considerar a funcionalidade pronta
- **App sem autenticação em produção** — coberto pelo requisito de tailnet-only (Secção 9); o risco reativa-se se o âmbito de acesso mudar antes da v1.2

## 14. Ideias — não priorizadas

Fora do âmbito comprometido. Não têm fase atribuída e não entram em nenhum critério de aceitação — ficam registadas para não se perderem, e só passam ao roadmap se e quando houver uma decisão explícita nesse sentido.

- **Histórico de alterações a uma receita** — quem mudou o quê e quando; ganha valor quando houver duas contas a editar (v1.2), não antes
- **Conversão automática de unidades** — chávenas ↔ gramas, ml ↔ dl, etc.; depende do parsing de ingredientes estruturado e de uma tabela de densidades por alimento (a conversão volume↔peso não é universal: uma chávena de farinha e uma de açúcar não pesam o mesmo)

---

*Documento vivo — próxima sincronização quando as Decisões #1–#5 estiverem resolvidas ou a v1.0 for declarada concluída (critérios 11.1).*