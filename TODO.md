# TODO — tacho_app

Ponto de situação a 2026-08-07. Ver `PRD-app-receitas-v3.2.md`, `PRODUCT.md` e
`DESIGN.md` para o contexto completo de cada item.

> **Mudança importante desde a última revisão:** o Tandoor não tem receitas
> guardadas — **não há migração a fazer**. O script
> `backend/scripts/migrate_from_tandoor.py`, que tinha ficado obsoleto, foi
> removido em 2026-08-07. Vários itens abaixo perderam a urgência que vinha de
> "corrigir antes da migração".
>
> **2026-08-07 — v1.0 concluída.** Os 5 critérios de aceitação da Secção 11.1
> do PRD estão todos cumpridos, incluindo o deploy: o Tacho substituiu o
> Tandoor na CT 202 do homelab (`https://receitas.alveslab.dev`). Ver a
> secção "v1.0 — fechar a fase" abaixo para o detalhe de cada critério.

---

## Já implementado

**Backend** (`backend/`, FastAPI + PostgreSQL + Redis/Celery):
- Modelos: `Workspace`, `Recipe`, `Ingredient`, `Step`, `Category`, `Tag`
  (+ tabelas de associação), com Workspace único semeado pela migração inicial
  da BD (Alembic).
- CRUD completo de receitas/categorias/tags, com filtro por categoria/tag e
  pesquisa de título (`ILIKE`, não full-text — ver v1.1).
- Importação de receitas por URL (`recipe-scrapers`, via Celery, com polling de
  estado) — testada com sites reais PT.
- `/health`, CORS configurado, tudo testado ponta a ponta via HTTP.

**Frontend** (`frontend/`, React + TS + Vite + Tailwind):
- Mundo visual definido e documentado em `DESIGN.md`.
- Home — grid de receitas, pesquisa, filtros por categoria/tag.
- Detalhe da receita — ingredientes, passos, hero stats (tempo/porções),
  categorias/tags, botão Editar.
- Modo Cozinha — passo a passo em ecrã inteiro, barra de progresso, wake lock,
  Anterior/Seguinte.
- Adicionar receita — por link (importação) ou à mão (formulário completo:
  ingredientes/passos dinâmicos, categorias/tags com criação inline).
- Editar receita + apagar (com confirmação).
- Menu de utilizador no header (mostra o agregado, sem fingir login).

## Por testar (sem verificação visual)

- [x] Editor manual de receitas (`AddRecipe.tsx` aba "À mão", `EditRecipe.tsx`,
      `RecipeForm.tsx`) — testado no browser (Playwright): criar receita com
      ingredientes/passos/categoria/tag inline, editar e apagar (confirmação
      via `window.confirm`), tudo sem erros de consola.
- [x] Menu de utilizador (`UserMenu.tsx`) — testado no browser: abre, mostra
      "Vítor & Mariana" e a nota sobre contas individuais na v1.2, sem erros.

---

## v1.0 — fechar a fase

Critérios de aceitação completos no PRD, Secção 11.1. A v1.0 **só se considera
concluída** quando todos estes estiverem verificados.

- [x] Testar no browser o editor manual e o menu de utilizador (ver acima).
- [x] **Armazenamento de imagens** — `Recipe.image_path` (migração Alembic
      aditiva), fotos guardadas em disco em `backend/images/` (fora do git),
      servidas em `/images/{ficheiro}` via `StaticFiles`.
- [x] **Upload de foto pela UI** — `POST /recipes/{id}/image` (valida
      JPEG/PNG/WEBP, máx. 8MB, substitui e apaga o ficheiro antigo; o
      ficheiro é também apagado ao apagar a receita). No formulário de
      criar/editar, com captura pela câmara no telemóvel (`capture`); foto
      visível no card da Home e no hero do Detalhe. Testado no browser
      (criar com foto, ver no card e no Detalhe, reabrir para editar com a
      pré-visualização carregada, apagar e confirmar remoção do ficheiro).
- [x] **Cabeçalhos de secção nos ingredientes** (`Ingredient.is_header: bool`) —
      migração Alembic aditiva, suportado no editor manual (linha de secção
      distinta, com botão "Adicionar cabeçalho de secção") e no Detalhe
      (título em negrito antes do grupo de ingredientes). Testado no browser.
- [x] **Informação nutricional** — entrada manual por porção
      (`calories_kcal`, `protein_g`, `carbs_g`, `fat_g`, migração Alembic
      aditiva). Calorias no hero do Detalhe, macros numa secção própria;
      `accent-orange` **não** foi usado (DESIGN.md linha 84, "The One Role
      Rule" — laranja fica exclusivo de tempo/Modo Cozinha, também para
      dados nutricionais). Cálculo automático fica para a v2, com Open Food
      Facts como base (ver v2 abaixo) — não LLM. Testado no browser.
- [x] **Deploy definitivo no homelab** — ver decisão #4, autorizada
      explicitamente em 2026-08-07: substituir o Tandoor, reutilizando o
      mesmo container (CT 202, `192.168.1.202`), sem novo VMID. Tandoor
      confirmado sem receitas guardadas antes de substituir (0 linhas em
      `cookbook_recipe`) — sem migração de dados. Backend passou a servir o
      frontend compilado diretamente (`Dockerfile` multi-stage na raiz do
      repo + `docker-compose.prod.yml`), sem container nginx dedicado, para
      poupar RAM no host. Acessível em `https://receitas.alveslab.dev`,
      protegido por Authentik forward-auth (o Tacho não tem login próprio —
      v1.2 — por isso mantém-se o mesmo nível de proteção que o Tandoor já
      tinha, em vez de expor sem autenticação). Backup diário automático
      (BD + fotos) configurado e **restauro testado com sucesso**. Dashboard
      Homepage do homelab atualizado (Tandoor → Tacho). Detalhe completo em
      `homelab/inventory.md`, secção "CT 202 — tacho".

---

## v1.1

- [ ] **Planeamento de refeições + Lista de compras** — nada construído.
      Desenhar primeiro no Figma (ainda não existem estes ecrãs).
      Referência de schema: `Food.supermarket_category` do Tandoor é um bom
      padrão para o agrupamento por corredor.
- [ ] **Atualizar o Figma com o novo estilo + criar os ecrãs em falta** —
      trabalho em curso no ficheiro `Receitas App — Design Revamp`
      (`cOvlbDp3d0osvTcPT6TFSR`), **bloqueado pela quota mensal do MCP do
      Figma** (plano Starter, seat View, 6 chamadas/mês — ver
      `file://figma/docs/rate-limits-access.md` do servidor MCP). Plano
      completo em `/root/.claude/plans/atualiza-o-figma-com-keen-quiche.md`.
      **Já feito** (verificado por screenshot): 3 páginas (`Design System`,
      `v1.0 — Ecrãs atuais`, `v1.1 — Planeamento & Compras`); fundação
      completa (9 variáveis de cor, 5 estilos de texto, 4 estilos de
      efeito/sombra, todos batendo certo com `DESIGN.md`/`index.css`); 20
      ícones importados via SVG a partir de `icons.tsx`; componentes `Chip`
      (categoria/tag/filtro ativo/inativo), `Button` (primary/cook-mode/
      ghost), `RecipeCard` (card horizontal fiel ao real, não o vertical do
      mockup antigo), `HeroStat`. **Por fazer, nesta ordem:** (1) Header
      desktop/mobile + BottomNav (2 itens v1.0, 4 itens v1.1-alvo) — script
      já escrito, falhou a meio por limite de quota, nada ficou partido; (2)
      reconstruir os 5 frames existentes (Home, Detalhe, Modo Cozinha,
      mobile+desktop) fiéis ao código, substituindo o mockup antigo
      (sidebar desktop errada, emoji em vez de ícones, cores erradas); (3)
      criar Adicionar receita e Editar receita no Figma (já existem na app,
      nunca desenhados); (4) criar Planeamento de refeições (grelha semanal)
      e Lista de Compras (gerar da semana + itens manuais) em `v1.1`; (5)
      verificação final por screenshot contra a checklist do plano.
- [ ] **Mais destinos no bottom nav** — hoje só "Receitas"/"Adicionar" contra os
      4–5 que o design descreve; desbloqueia quando os ecrãs acima existirem.
- [x] **Escalar porções no Detalhe** — sem mudanças no backend; stepper +/−
      junto ao hero de porções recalcula `quantity` em runtime (padrão
      Mealie). Só afeta ingredientes com `quantity` estruturado — receitas
      importadas por URL não escalam porque a linha scraped ainda fica
      inteira em `Ingredient.name` (ver "Parsing de ingredientes" abaixo).
      Testado no browser (Playwright): "Arroz Doce" 150g→200g ao subir de
      6 para 8 porções, sem erros de consola.
- [x] **Pesquisa full-text** — `ILIKE` substituído por `tsvector`/`tsquery`
      Postgres (config `portuguese`), índice GIN (`ix_recipes_title_tsv`,
      registado em `models.py::Recipe.__table_args__` para o autogenerate
      não voltar a assinalá-lo como removido — já aconteceu duas vezes).
      Query construída como prefixo por palavra (`"bacal fri"` →
      `"bacal:* & fri:*"`) para funcionar enquanto se escreve, não só em
      palavras completas; input do utilizador passa por `\w+` antes de ir
      para o Postgres (nunca sintaxe de tsquery crua). Testado pela API
      (prefixo, multi-palavra, sem resultados, caracteres especiais) e no
      browser (Playwright).
- [ ] **Parsing de ingredientes da importação** — a linha scraped fica inteira
      em `Ingredient.name`, sem separar quantidade/unidade. Desbloqueia o custo
      por porção e a pesquisa por ingredientes (v2).
- [x] **Filtrar lixo nos passos importados** — causa raiz encontrada e
      reproduzida (`mundodereceitasbimby.com.pt`, "Cheesecake de Bolacha -
      gelado sanduíche"): uma `HowToSection` do JSON-LD com
      `itemListElement` como dict solto (em vez de lista) faz o
      `recipe-scrapers` iterar as chaves desse dict como se fossem passos —
      devolve `"@type"`, `"position"`, `"name"`, `"text"` soltos.
      `app/tasks.py::_extract_steps` filtra essas correspondências exatas
      (nunca por comprimento, para não arriscar apagar um passo real e
      curto). Testado com scraping real: 4 entradas de lixo removidas, os 5
      passos legítimos preservados.
- [x] **Trazer a foto da importação por URL** — `backend/app/tasks.py` usa
      `scraper.image()` e descarrega a foto via `images.save_recipe_image_from_url`
      (mesma validação de tipo/tamanho do upload manual: JPEG/PNG/WEBP, máx.
      8MB). Best-effort — qualquer falha (sem imagem, formato não suportado,
      erro de rede) devolve `None` sem chumbar a importação da receita.
      Testado com scraping real (pingodoce.pt) ponta a ponta, incluindo
      verificação visual no browser (Playwright): foto no card da Home e no
      hero do Detalhe, sem erros de consola.
- [ ] **Importação inteligente via Gemini** — (a) fallback de extração quando o
      `recipe-scrapers` falha ou devolve resultado incompleto; (b) **importação
      por foto** (Vision): fotografar página de livro/receita manuscrita, com
      1–3 fotos, resultado sempre pré-preenchido no formulário para revisão —
      nunca gravação direta. Chave em `GEMINI_API_KEY`, funcionalidade opcional
      (sem chave, a app funciona na mesma).
      ⚠️ Validar cedo com fotos reais (livros PT, letra manuscrita) — risco de
      o LLM "corrigir" quantidades silenciosamente.
- [x] **Timers por passo** no Modo Cozinha — `Step.duration_minutes` opcional
      (migração `ab0f3fc87c29`, aditiva), campo de minutos no editor manual
      (`RecipeForm.tsx`, ao lado de cada passo). Quando o passo atual tem
      duração, `CookMode.tsx` mostra "Iniciar temporizador" com o
      `ClockIcon` em laranja (o papel de tempo já reservado pelo
      `DESIGN.md`); a contrair mostra `mm:ss`, e ao chegar a zero passa a
      pílula laranja cheia "Tempo!" (`animate-pulse`) com opção de repor;
      vibração best-effort (`navigator.vibrate`). Estado reinicia por passo
      via `key={step.id}`. Testado no browser (Playwright), incluindo a
      contagem completa até "Tempo!" (não só a meio), sem erros de consola.
- [x] **Tamanho de letra ajustável** no Modo Cozinha (toggle A/A⁺, canto
      superior direito). Persistido em `localStorage` — uma vez ligado, não
      volta ao tamanho normal a cada receita nova. Testado no browser
      (Playwright), sem erros de consola.
- [x] **Notas pós-confeção** — ao concluir o Modo Cozinha, nota rápida opcional
      ("menos sal, +10 min de forno"), guardada com data e visível no Detalhe.
      `models.py::CookNote` (tabela `cook_notes`, FK `recipe_id` cascade,
      `text`, `created_at`), migração `4d0d5fd85a2d`, relação
      `Recipe.cook_notes` (ordenada por `created_at.desc()` — histórico,
      mais recente primeiro; conceito diferente de `Recipe.notes`, que é um
      campo único editável no formulário). `schemas.CookNoteOut`/`CookNoteIn`
      e `RecipeOut.cook_notes` (não `RecipeSummary`); `crud.add_cook_note`
      (padrão de `mark_recipe_made`); `POST /recipes/{id}/notes`. Frontend:
      `CookMode.tsx::handleFinish` pede `window.prompt` opcional depois de
      `markRecipeMade` (mesmo padrão best-effort, nunca impede sair do Modo
      Cozinha); secção "Notas" nova em `RecipeDetail.tsx`, só visível quando
      há notas. Testado no browser (Playwright): receita "Bacalhau à Brás",
      Modo Cozinha até ao fim, nota "Menos sal da próxima vez, ficou
      salgado." aceite no prompt, aparece no Detalhe com data, sem erros de
      consola.
- [x] **"Última vez feita"** — `Recipe.last_made_at` (migração Alembic
      aditiva), marcado via `POST /recipes/{id}/mark-made` ao carregar em
      "Concluir" no Modo Cozinha (best-effort: falha em silêncio, nunca
      impede sair, útil offline na cozinha). Visível no Detalhe. Alimenta a
      métrica M3 do PRD. Testado no browser (Playwright): concluir o Modo
      Cozinha faz aparecer a data no Detalhe, sem erros de consola.
- [x] **Duplicar receita** — `POST /recipes/{id}/duplicate`, botão no
      Detalhe junto a "Editar"; a cópia leva título com sufixo "(cópia)",
      ingredientes/passos/categorias/tags, e a própria foto (ficheiro
      copiado para um nome novo — apagar uma das duas nunca apaga a foto da
      outra, testado). Não copia `last_made_at`. Navega direto para o editor
      da cópia, para renomear logo (ex. "Bolo de cenoura" → "... sem
      lactose", o caso de uso do PRD). Testado no browser (Playwright).
- [x] **Tempos separados** prep / cozedura / total — `prep_minutes` e
      `cook_minutes` já existiam separados no backend e no formulário; só
      faltava mostrar no Detalhe (o hero continua a mostrar só o total, por
      `DESIGN.md` — "Hierarchy": um único hero number por métrica; a
      repartição fica como legenda pequena por baixo, só quando os dois
      tempos são conhecidos). Testado no browser (Playwright).
- [x] **Favoritos** — `Recipe.is_favorite` (bool, Workspace inteiro, não por
      utilizador — decisão já tomada aqui mesmo antes de haver contas).
      `POST /recipes/{id}/favorite` (toggle), `GET /recipes?favorite=true`.
      Coração no `RecipeCard` (Home) e no Detalhe; cor `accent-leaf` — **não**
      `accent-orange`, que o `DESIGN.md` reserva exclusivamente a
      tempo/Modo Cozinha ("The One Role Rule"). Chip "Favoritos" na Home,
      combina com categoria/tag (AND) e com a pesquisa. Não implementado
      como destino do bottom nav (esse item continua bloqueado — "Mais
      destinos no bottom nav" abaixo). Testado no browser (Playwright):
      favoritar no card, filtrar, desfavoritar no Detalhe.
- [x] **Dark mode** — variante escura dos tokens neutros do `DESIGN.md`
      (nova secção "Dark Mode" nesse ficheiro tem o detalhe completo),
      `prefers-color-scheme` com override manual persistido em
      `localStorage` (seletor Sistema/Claro/Escuro no menu de utilizador,
      `theme.ts`). Cores de marca como fundo (forest/leaf/orange, gradiente
      do hero) não mudam; só `bg-sage`, o novo `surface` (fundo de card,
      distinto de `card-white` que fica sempre branco) e `text-primary`/
      `text-secondary` invertem. Verde-floresta como texto ganhou uma
      variante clara nova (`forest-text`, `#5FA97C`) porque a original falha
      o contraste WCAG sobre superfície escura (~2.1:1, medido); leaf não
      precisou (já passa, ~5.3:1). Modo Cozinha fica pixel-idêntico nos dois
      temas (tokens fixados localmente, protege o texto escuro obrigatório
      sobre os CTAs laranja). Testado no browser (Playwright): claro,
      escuro por preferência do sistema, e toggle manual nos dois sentidos
      (incluindo forçar claro com o sistema em escuro) — Home, Detalhe,
      Adicionar receita (manual) e Modo Cozinha, sem erros de consola.
- [x] **PWA instalável** — `manifest.webmanifest` (nome, cores, ícone a partir
      do `favicon.svg` existente) e `sw.js` básico registado em `main.tsx`
      (best-effort, sem suporte a app funciona igual). O service worker só
      intercepta `GET /assets/*` (bundles JS/CSS do Vite, com hash no nome —
      seguro cachear cache-first); tudo o resto passa direto à rede, incluindo
      a API, porque em produção o backend serve o frontend no mesmo domínio
      (`VITE_API_URL=""`) sem prefixo `/api` a distinguir das rotas. Testado
      no browser (Playwright): manifest e `sw.js` servidos com 200, service
      worker fica `active`, sem erros de consola.
- [x] **Export schema.org Recipe (JSON-LD)** — `GET /recipes/{id}/export`
      (`app/schema_org.py`), `application/ld+json`. Cabeçalhos de secção não
      têm equivalente em `recipeIngredient` (schema.org espera lista plana)
      e ficam de fora; o resto mapeia 1:1 (nome, descrição, imagem absoluta,
      porções, tempos em ISO 8601, ingredientes, passos como `HowToStep`,
      categorias/tags, nutrição — todos testados individualmente pela API,
      incluindo nutrição, que nenhuma receita semeada tinha). Imagem usa
      `Settings.public_base_url` (nova variável `PUBLIC_BASE_URL`, só para
      isto) em vez de `request.base_url` — sem isso, atrás do proxy da CT
      202 (sem `--proxy-headers` no `Dockerfile`) a URL exportada ficaria
      com esquema/host internos em vez de `https://receitas.alveslab.dev`;
      **falta definir `PUBLIC_BASE_URL` no `.env` de produção no próximo
      deploy**, ou a imagem exportada continua errada lá. Validado com
      *round-trip* real: o próprio `recipe-scrapers` (`scrape_html`, modo
      genérico) consegue reimportar o JSON-LD exportado e devolve os
      mesmos dados.

---

## v1.2

- [ ] **Multi-utilizador real + autenticação** — nada construído além do
      Workspace único semeado. Ver decisões #1 e #2.
- [ ] **Favoritos por utilizador** — evolução do item da v1.1, padrão
      `favorited_by` do Mealie.
- [ ] **Avaliação por estrelas** — padrão do Mealie (`rating`), não do Tandoor.
- [ ] **Comentários** por receita.

---

## v2

- [ ] **Cálculo automático de nutrição a partir dos ingredientes** — decisão
      tomada: cruzar os ingredientes parseados (v1.1) com uma base de dados
      nutricional real, **Open Food Facts**, não um LLM (o Gemini não tem
      uma base de dados nutricional; pedir-lhe calorias/macros seria
      alucinação em dados de saúde, um risco pior do que o já assinalado
      para a importação por foto — ver Riscos no PRD). O Gemini fica
      reservado ao que já estava previsto: extração de receitas por URL/foto.
- [ ] **Custo por receita/porção** — preço estimado por ingrediente → custo do
      prato e por porção. Depende do parsing estruturado (v1.1). Nenhum dos dois
      (Tandoor/Mealie) faz isto bem.
- [ ] **Despensa/inventário básico** — só "tenho/não tenho" por ingrediente,
      sem quantidades nem validades (âmbito contido de propósito, para não virar
      um Grocy). Cruza com a pesquisa por ingredientes e com a lista de compras.
- [ ] **Pesquisa por ingredientes disponíveis** — "o que consigo fazer com
      frango e cogumelos?".
- [ ] **Cookbooks / coleções** — ver decisão #3 (podem ser antecipados).
- [ ] Modo Cozinha desktop.
- [ ] Modo Cozinha offline (cache da receita ativa via service worker).
- [ ] Galeria de fotos por receita (várias fotos, uma marcada como capa).
- [ ] Vista de impressão / PDF por receita.
- [ ] Fracções em unidades ("½ chávena" em vez de "0.5 chávena").
- [ ] Authentik SSO.

---

## Coisas que precisas de decidir tu

1. **`fastapi-users` + modelo "Workspace" — bate mesmo certo com o Securo?**
   Assumido por analogia de stack (FastAPI+Postgres+Redis+Celery, confirmado no
   `inventory.md`), mas nunca confirmado contra o código real.
   → **verificar no GitHub do `securo-finance`** antes de construir a auth da v1.2.

2. **Como associar a segunda pessoa ao Workspace, sem SMTP no homelab.**
   O plano assumia convite por email; não há infraestrutura de email montada.
   Alternativa mais simples: o dono cria a segunda conta diretamente.
   → **verificar como o Tandoor resolve isto** e decidir entre os dois fluxos.

3. **Cookbooks: em que fase entram, e em que modelo?** Lista manual (Tandoor) ou
   coleção por filtro inteligente (Mealie, mais trabalho mas mais útil a prazo)?
   Hoje estão provisoriamente na v2.

4. **Quando/como implantar no homelab a sério.** Ainda corre só no CT 111, fora
   do `docker-compose.yml`. Falta decidir VMID/IP novo seguindo a convenção do
   `homelab/CLAUDE.md` — ação de infraestrutura partilhada, não tomada sem
   autorização explícita.
   ⚠️ Enquanto não houver autenticação (v1.2), a app **só pode estar acessível
   dentro da tailnet** — nunca exposta à LAN de convidados nem à internet.

5. **O conteúdo do menu de utilizador está bem assim?** Por não haver contas
   reais, mostra só "Vítor & Mariana" com nota de que contas individuais chegam
   na v1.2 — sem fingir um "Sair" que não funciona. Confirma se preferes outra
   coisa (ou nada, até haver auth a sério).

---

## Ideias — não priorizadas

Sem fase atribuída. Só passam ao roadmap com decisão explícita.

- Histórico de alterações a uma receita (ganha valor com duas contas, v1.2+).
- Conversão automática de unidades (chávenas ↔ gramas) — precisa de tabela de
  densidades por alimento; uma chávena de farinha e uma de açúcar não pesam o
  mesmo.