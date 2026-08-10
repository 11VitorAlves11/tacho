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

- [x] **Planeamento de refeições + Lista de compras** — implementado a partir
      dos ecrãs desenhados no Figma (ver entrada abaixo). Backend:
      `MealPlanEntry` (dia + `almoco`/`jantar`, `UniqueConstraint` por
      workspace/dia/refeição, upsert substitui o que lá estivesse) e
      `ShoppingListItem` (`name`, `quantity` texto livre já composto, ex.
      "500 g", `is_checked`), migração `1c5b13ed2ab2`. `routers/planning.py`:
      `GET/PUT/DELETE /meal-plan{,/…}`, `GET/POST /shopping-list`,
      `PATCH/DELETE /shopping-list/{id}`, `POST /shopping-list/generate`
      (registado antes de `/shopping-list/{item_id}` — mesmo cuidado de
      ordem de rotas do `/recipes/import`). **A geração agrega dados que já
      existem hoje** (`Ingredient.quantity`/`unit` já são colunas
      estruturadas para receitas manuais, não é preciso esperar pelo
      parsing de ingredientes da importação, que só afeta receitas trazidas
      por URL) — corrige uma nota antiga do mockup Figma que dizia o
      contrário. Um item por ingrediente da semana (sem somar quantidades
      entre receitas, isso precisava de conversão de unidades, fora de
      âmbito); gerar duas vezes não duplica itens por comprar, mas volta a
      criar um item já marcado como comprado (para poder gerar de novo
      depois de esvaziar o carrinho). Frontend: `pages/MealPlan.tsx`
      (navegação por semana, 7 cards Segunda–Domingo × Almoço/Jantar,
      `<select>` para atribuir, botão para remover), `pages/ShoppingList.tsx`
      (botão "Gerar da semana", adicionar item à mão, marcar
      comprado/riscado, apagar) — `lib/date.ts` centraliza a formatação de
      data em fuso horário local (nunca `toISOString()`, que desloca a
      meia-noite em Portugal para o dia anterior) e o cálculo da segunda-feira
      da semana. **Simplificações face ao mockup Figma**: sem agrupamento
      por corredor (`Food.supermarket_category` do Tandoor) — o modelo
      `ShoppingListItem` não tem esse campo, fica para quando fizer falta a
      sério; `BottomNav` real tem 4 destinos (Receitas/Lista/Plano/
      Adicionar), sem "Favoritos" (o Figma `v1.1-alvo` mostrava 4 com
      Favoritos em vez de Adicionar — não há ecrã de Favoritos na app real,
      só um filtro na Home, por isso fica de fora até esse ecrã existir,
      regra do `DESIGN.md`); slot preenchido mostra só o título da receita,
      sem a mini-thumb que o mockup tinha (`MealPlanEntryOut.recipe` já traz
      `image_path`, é só questão de desenhar o `<img>` quando quiser ficar
      mais próximo do Figma). Testado pela API via curl (todos os endpoints,
      incluindo 404s e a idempotência da geração) e no browser via
      Playwright instalado nesta sessão (fluxo completo: atribuir/remover
      receita num slot, navegar semana, adicionar/marcar/apagar item, gerar
      lista, sem erros de consola); dados de teste apagados da BD local no
      fim, para não poluir o ambiente de dev.
- [x] **Atualizar o Figma com o novo estilo + criar os ecrãs em falta** —
      trabalho em curso no ficheiro `Receitas App — Design Revamp`
      (`cOvlbDp3d0osvTcPT6TFSR`). O MCP oficial do Figma ficou bloqueado pela
      quota mensal (plano Starter, seat View, 6 chamadas/mês); **2026-08-09
      — retomado via Figwright** (plugin Figma + servidor MCP local, sem
      esse limite — precisa do plugin aberto no browser para funcionar,
      liga/desliga com o browser). Plano atual em
      `/root/.claude/plans/continuar-redesign-figma-via-figwright.md` (substitui
      `/root/.claude/plans/atualiza-o-figma-com-keen-quiche.md`, que ainda
      tem o histórico da fase MCP-oficial). Dark mode **fora de âmbito** no
      Figma por decisão explícita — só documentado em nota de texto na
      página `Design System`, sem frames escuros.
      **Já feito** (verificado por screenshot): 3 páginas (`Design System`,
      `v1.0 — Ecrãs atuais`, `v1.1 — Planeamento & Compras`); fundação
      completa (9 variáveis de cor, 5 estilos de texto, 4 estilos de
      efeito/sombra, todos batendo certo com `DESIGN.md`/`index.css`); 18
      ícones importados via SVG a partir de `icons.tsx` (inclui `UserIcon`,
      não 20 como uma nota anterior dizia); componentes `Chip`
      (categoria/tag/filtro ativo/inativo), `Button` (primary/cook-mode/
      ghost), `RecipeCard` (card horizontal fiel ao real, não o vertical do
      mockup antigo), `HeroStat`. **2026-08-09, via Figwright:** `Header`
      (variantes Mobile e Desktop, gradiente diagonal, logo, botão
      "Adicionar receita" só desktop, avatar `UserMenu` "VM" + chevron) e
      `BottomNav` (variante v1.0 real de 2 itens Receitas/Adicionar +
      variante v1.1-alvo de 4 itens Receitas/Lista/Plano/Favoritos,
      claramente anotada como estado-alvo — ícones de Lista/Plano são
      placeholder, `Copy`/`Clock`, até existir iconografia dedicada); os 5
      frames de `v1.0` deixaram de ter espaço reservado — **Home mobile e
      desktop reconstruídos** fiéis ao `Home.tsx` (hero com copy real,
      pesquisa, chip Favoritos + chips de categoria/tag, grid de
      `RecipeCard` 1 col mobile / 2 col desktop). **2026-08-10, via
      Figwright:** **Detalhe da Receita (mobile + desktop) e Modo Cozinha
      (mobile) reconstruídos**, substituindo por completo o mockup antigo
      nesses 3 frames (receita fictícia "Bowl Poke de Salmão", chip azul,
      emoji `🍣🔥👥⏱←♡`, sidebar desktop de 240px inexistente no código
      real). Receita canónica usada em todo o conteúdo: "Bacalhau à Brás"
      (já usada no card da Home e no teste de nota pós-confeção), com dados
      a exercitar todas as secções condicionais (tempos separados,
      porções+stepper, calorias+macros, categoria+tag, cabeçalho de secção
      nos ingredientes, nota pós-confeção, última vez feita, fonte).
      Confirmado por inventário ao vivo (não por suposição) que nada no
      ficheiro é `COMPONENT`/`INSTANCE` do Figma — os nós `component/X` são
      `FRAME`s normais com essa convenção de nome; reconstrução feita por
      `clone_node` a partir da biblioteca já existente na página
      `Design System` (ícones, chips, botões, `HeroStat`, `Header`,
      `BottomNav`), nunca redesenhada do zero. Decisão tomada e documentada
      em nota de texto na página `Design System`: os tokens `surface` e
      `forest-text` (só existem no código, sem variável Figma própria)
      ficam ligados a `color/card-white` e `color/primary-forest`
      respetivamente — em modo claro têm o mesmo valor, e assim a contagem
      fica nas 9 variáveis/5 estilos de texto/4 de efeito originais,
      confirmada intacta no fim. Desktop sem sidebar: `PageShell.tsx` real
      é uma coluna única centrada `max-w-4xl` (896px), não duas colunas —
      corrigido no Figma, grid Ingredientes/Preparação só a 2 colunas
      dentro dessa coluna. Verificado por screenshot dos 3 frames.
      **Adicionar receita e Editar receita criados** (mobile, novos no
      Figma — não existiam antes): "Editar receita" tem o `RecipeForm.tsx`
      completo pré-preenchido com "Bacalhau à Brás" (5 cards: foto+campos
      principais, ingredientes com cabeçalho de secção e botões
      "Adicionar ingrediente"/"Adicionar cabeçalho de secção", preparação
      com duração por passo, categorias/tags com chips ativos/inativos e
      `InlineAdd` de borda tracejada, nutrição em grid 2 colunas) mais o
      cabeçalho com botão "Apagar" em laranja; "Adicionar receita" mostra
      as tabs "Por link"/"À mão" (Por link ativo por omissão) com o card de
      importação por URL (`LinkIcon`, botão "Importar receita", aviso sobre
      confirmar depois de importar) — a tab "À mão" não foi duplicada,
      fica anotada em nota de texto no próprio frame a apontar para o
      formulário completo do ecrã Editar, para não repetir os 5 cards.
      Desktop destes dois ecrãs não construído (o código só tem duas
      diferenças responsivas nestes ficheiros — padding do `PageShell` e a
      grelha de nutrição 2→4 colunas — por isso o mobile já documenta a
      estrutura toda). **Planeamento de refeições e Lista de Compras
      criados** (mobile, página `v1.1 — Planeamento & Compras`, ainda vazia
      antes destes dois): "Planeamento" tem navegação por semana
      (chevron/label/chevron) e um card por dia (Segunda a Domingo, datas
      3–9 de agosto), cada um com secção Almoço e Jantar — vazio mostra pill
      tracejada "+ Adicionar receita", preenchido mostra mini-card
      horizontal (thumb + título, ex. "Bacalhau à Brás" na Segunda,
      "Frango Assado com Batata" na Quinta); "Lista de Compras" tem o botão
      "Gerar da semana", com os itens mostrados agrupados por corredor
      (`Food.supermarket_category`: Peixe e Marisco, Hortícolas, Laticínios
      e Ovos, Mercearia) com checkbox riscado/opacidade reduzida no estado
      "comprado" (sem ícone de visto — nenhum existe em `icons.tsx`, a
      indicação é só risco+opacidade, como o próprio plano previa) e uma
      linha final "+ Adicionar item". **Nota da implementação real (ver
      v1.1 acima):** a mockup tinha uma anotação a dizer que "Gerar da
      semana" dependia do parsing estruturado de ingredientes — não
      dependia (`Ingredient.quantity`/`unit` já são colunas próprias para
      receitas manuais) e a versão implementada não agrupa por corredor
      (`ShoppingListItem` não tem esse campo); o Figma em si não foi
      corrigido, fica só esta nota a apontar a divergência. Ambos usam o `BottomNav-v1.1-alvo` (4
      itens) com o destino correspondente ativo ("Plano"/"Lista"),
      reaproveitado sem redesenhar, tal como os `Chip`/`Button`/`Header` já
      existentes — nenhum componente novo na fundação, só instâncias novas
      via `clone_node`. **Verificação final feita**: os 9 frames (Home
      mobile+desktop, Detalhe mobile+desktop, Modo Cozinha, Adicionar,
      Editar, Planeamento, Lista) revistos por screenshot contra a
      checklist do plano — sem emoji; laranja só em relógio/progresso/CTAs
      do Modo Cozinha (mais o botão "Apagar" do Editar, exceção já
      documentada e fiel ao código); cards brancos sobre sage; sombra OU
      contorno tracejado, nunca as duas na mesma peça; sem sidebar desktop.
      Design system confirmado intacto no fim (9 variáveis de cor, 5
      estilos de texto, 4 de efeito — os mesmos desde o início). O redesign
      Figma fica assim concluído para o âmbito atual (v1.0 + v1.1); o único
      item da secção "Já feito" desta lista que continua por desenhar é
      "Mais destinos no bottom nav" na app real, que é trabalho de código,
      não de Figma (ver item abaixo).
- [x] **Mais destinos no bottom nav** — `BottomNav.tsx` passou de 2 para 4
      itens (Receitas/Lista/Plano/Adicionar), agora que os ecrãs de
      Planeamento e Lista de Compras existem de facto (ver item acima).
      "Favoritos", que o Figma `v1.1-alvo` também mostrava, fica de fora —
      não há ecrã de Favoritos, só um filtro na Home; volta a ficar em
      aberto se algum dia se justificar um ecrã próprio.
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
      mesmos dados. **Atualização pós-autenticação (v1.2 abaixo):** este
      endpoint passou a exigir sessão (cookie), como todos os outros —
      já não é consumível externamente sem login, ao contrário do que a
      validação original por round-trip fazia parecer (nessa altura ainda
      não havia auth nenhuma). Só `/images/{ficheiro}` continua público,
      sem exigir sessão — `StaticFiles`, protegido só por o nome do
      ficheiro ser um UUID4 imprevisível, decisão deliberada para não
      complicar o servir de imagens.

---

## v1.2

- [x] **Multi-utilizador real + autenticação** — implementado seguindo as
      decisões #1 e #2 (resolvidas contra o código real do Securo, ver
      acima). `fastapi-users[sqlalchemy]` + modelos `User`
      (`SQLAlchemyBaseUserTableUUID`) e `WorkspaceMember` (`workspace_id`,
      `user_id`, sem coluna de papel/role — o Tacho tem sempre duas
      pessoas e uma única workspace, ao contrário do Securo), migração
      `65564d5e86e1`. **Motor assíncrono isolado só para autenticação**
      (`app/auth.py::async_engine`, driver `asyncpg`,
      `Settings.async_database_url` deriva de `database_url` trocando só o
      driver) — `fastapi_users_db_sqlalchemy` não tem variante síncrona
      (decisão #1); todo o resto da app (`crud.py`, todos os routers)
      continua 100% síncrono sobre o `Session` de sempre, mesma BD. Sessão
      por cookie httpOnly + JWT (`CookieTransport`/`JWTStrategy`,
      `Settings.auth_secret`/`auth_cookie_secure` — este último `false` por
      omissão para o dev local em `http://`, produção tem de o pôr `true`
      no `.env` do CT 202). `deps.get_workspace_id()` deixou de devolver a
      constante fixa — passa a resolver a partir de `current_active_user`
      + a linha em `workspace_members`; como todos os endpoints de
      receitas/planeamento/taxonomia já dependiam de
      `Depends(get_workspace_id)`, ficaram todos protegidos
      transitivamente sem tocar em `recipes.py`/`taxonomy.py`/
      `planning.py` (só `GET /recipes/import/{task_id}`, que não usava
      workspace_id, precisou de `Depends(current_active_user)` explícito).
      **Bootstrap sem SMTP** (decisão #2): `POST /setup` cria a primeira
      conta e liga-a ao `Workspace` já semeado (`DEFAULT_WORKSPACE_ID`,
      nunca cria uma workspace nova), só funciona enquanto existirem zero
      utilizadores; `POST /workspace/members` deixa qualquer membro já
      autenticado juntar a segunda pessoa fornecendo email+password
      diretamente — mesmo padrão do `invite_member` do Securo, sem os
      extras (moeda/preferências/workspace pessoal) que só fazem sentido
      lá. Frontend: `AuthContext` (verifica `GET /users/me` +
      `GET /setup/status` no arranque), `App.tsx` só monta as rotas da app
      quando há sessão válida, `pages/Setup.tsx` + `pages/Login.tsx`,
      `UserMenu.tsx` mostra o email real da sessão (já não "VM" fixo),
      lista o agregado e tem "Adicionar pessoa" + "Sair" reais. **Dois
      bugs apanhados e corrigidos só no teste no browser** (não apareciam
      nos testes via curl): (1) depois do `/setup`, o `AuthContext` não
      atualizava `needsSetup`, criando um ciclo de redireção infinito
      entre `/login` e `/setup` — corrigido chamando `refresh()` antes do
      `navigate`; (2) o menu do utilizador (`position: absolute`, sem
      `z-index`) ficava a pintar por baixo dos cards de receita (`position:
      relative`) sempre que o conteúdo do menu crescia — CSS pinta
      elementos posicionados sem `z-index` explícito por ordem do DOM, e o
      `<header>` vem antes do `<main>` — tornava o botão "Sair" clicável
      "no ar" mas fisicamente por baixo de outro elemento; corrigido com
      `z-30` explícito no painel do menu. **Authentik mantém-se em
      produção** (decisão do utilizador) — continua a proteger o acesso à
      CT 202 (defesa em profundidade), o login do Tacho identifica Vítor
      vs Mariana dentro da app, não substitui o forward-auth. Testado via
      curl (setup, login, logout, password errada, adicionar segundo
      membro, todos os routers 401 sem sessão) e no browser via Playwright
      ponta a ponta (setup → login → adicionar pessoa → logout → rota
      protegida bloqueada → login da segunda conta → workspace partilhado
      confirmado visualmente, 2 contas de teste `vitor@example.com`/
      `mariana@example.com` deixadas na BD local — sem elas a app fica
      inacessível). **Falta para produção**: definir `AUTH_SECRET` e
      `AUTH_COOKIE_SECURE=true` no `.env` do CT 202 antes do próximo
      deploy (os valores por omissão são só para dev local).
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

1. ~~`fastapi-users` + modelo "Workspace" — bate mesmo certo com o Securo?~~
   **Resolvido, 2026-08-10, verificado contra o código real** (repositório
   `securo-finance/securo`, fork do utilizador em `11VitorAlves11/securo`):
   sim, bate certo. `backend/pyproject.toml` confirma `fastapi-users
   [sqlalchemy]>=13.0.0` + `sqlalchemy>=2.0.0`; `app/models/workspace.py` tem
   `Workspace`/`WorkspaceMember` (roles `owner`/`editor`/`viewer`,
   `UniqueConstraint(workspace_id, user_id)`); `app/services/
   workspace_service.py::require_membership` é o padrão de permissão. **Mas
   a forma do Securo é maior do que o Tacho precisa** — várias workspaces
   por utilizador, `managed_by_user_id` (gestor externo sem ser membro),
   roles com tabela de ranking, arquivo com guarda de "última workspace".
   O Tacho tem duas pessoas e uma workspace, para sempre (`PRODUCT.md`,
   `UserMenu.tsx` já diz "Vítor & Mariana") — nada disto se aplica; construir
   à imagem do Securo seria sobre-engenharia. **Descoberta nova, decisiva
   para o plano:** `fastapi_users_db_sqlalchemy` (a versão atual, 7.0.0, a
   única compatível com `fastapi-users` 15.x, que é o que o PyPI resolve
   contra o `fastapi` 0.141.1 já pinado aqui) só suporta `AsyncSession` —
   `SQLAlchemyUserDatabase.session: AsyncSession`, todos os métodos `async
   def`, sem variante síncrona (confirmado a extrair o wheel e inspecionar
   o código-fonte, não assumido pela documentação). O `crud.py`/routers
   atuais do Tacho são 100% síncronos (`Session`, `db.scalars(...)`). Adotar
   `fastapi-users` não obriga a reescrever a app toda para async, mas obriga
   a uma segunda ligação assíncrona à mesma BD (motor `asyncpg` ou
   `psycopg[async]`) só para o subsistema de autenticação — um custo real,
   não trivial, que fica por decidir no início da implementação da v1.2.

2. ~~Como associar a segunda pessoa ao Workspace, sem SMTP no homelab.~~
   **Resolvido, 2026-08-10, verificado contra o código real do Securo** (não
   contra o Tandoor, que nunca teve multi-utilizador de facto): a
   alternativa mais simples já prevista aqui — "o dono cria a segunda conta
   diretamente" — é exatamente o que o Securo faz. `POST /api/workspaces/
   {id}/members` (`app/api/workspaces.py::invite_member`) recebe email +
   password fornecidos pelo dono da workspace; se o email não corresponde a
   nenhum utilizador existente, cria a conta ali mesmo
   (`fastapi_users.schemas.BaseUserCreate` + `user_manager.create(...)`),
   sem enviar nenhum email — nada de SMTP, nada de token de convite por
   link. Padrão a copiar para o Tacho, sem os extras (moeda/preferências/
   workspace pessoal automática) que só fazem sentido no domínio do Securo.

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
- **Ligar receitas entre si (sub-receitas/componentes)** — hoje não há forma de
  uma receita apontar para outra; uma "Lasanha" que leva "Molho de Tomate" e
  "Molho Bechamel" como componentes só pode referenciar os nomes em texto
  livre nos ingredientes/passos, sem link real nem reaproveitamento
  automático de ingredientes/tempo. Caso real surgido a importar receitas do
  Notion (2026-08-08). Padrão a inspirar: `Ingredient` do Tandoor pode
  apontar para outra `Recipe` em vez de (ou além de) um `Food`.
- **Repositório GitHub em inglês + nome só "Tacho"** — hoje é
  `11VitorAlves11/tacho_app`, com documentação em PT. Passar todo o conteúdo
  do repositório (README, docs como `DESIGN.md`/`PRODUCT.md`/`PRD-*`, este
  `TODO.md`) para inglês, e renomear o repositório para só `Tacho` (sem o
  sufixo `_app`). Por decidir antes de executar: se inclui também
  comentários no código e strings da UI (a app em si está em pt-PT por
  desenho, `DESIGN.md`/`PRODUCT.md` documentam isso como intencional) ou só
  a documentação/README voltados para quem vê o repositório no GitHub. Um
  rename de repositório no GitHub quebra URLs antigas (redireciona, mas
  ações/webhooks/deploy que apontem para o nome antigo têm de ser
  atualizados) — confirmar antes de executar.