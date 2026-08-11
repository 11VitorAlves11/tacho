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
      **2026-08-10, continuação via Figwright** (plano
      `/root/.claude/plans/continua-o-design-da-toasty-bunny.md`): três
      frentes novas, construídas em paralelo por três agentes e verificadas
      por screenshot no fim (9 variáveis/5 estilos de texto/4 de efeito
      confirmados intactos). **Desktop de Adicionar/Editar receita**
      (`Desktop - Adicionar receita`/`Desktop - Editar receita`, novos na
      página `v1.0`) — só as duas diferenças responsivas reais do código
      (`PageShell.tsx`: padding; `RecipeForm.tsx:447`: grelha de nutrição
      2→4 colunas), confirmado por grep que não há mais nenhuma classe
      `md:`/`lg:` em `AddRecipe.tsx`/`EditRecipe.tsx`/`RecipeForm.tsx`.
      **Ecrãs de v1.2 — Setup, Login, Gestão de membros** (página `v1.0`,
      prefixo `v1.2 —`): descoberta feita antes de desenhar — o backend de
      autenticação **já está em desenvolvimento, sem commit**
      (`backend/app/auth.py`, `backend/app/routers/auth.py`, migração
      `65564d5e86e1`, `models.py`/`schemas.py`/`main.py` modificados),
      contrato real (`GET/POST /setup`, `GET/POST /workspace/members`,
      `SetupRequest`/`MemberInvite` = só email+password, `MemberOut` =
      id/email/joined_at, sem nome) usado como base do desenho em vez de
      especulação. Construído também, pela primeira vez, o estado aberto do
      dropdown do `UserMenu` (`component/UserMenu-Dropdown-Aberto`, página
      `Design System`) com os dois blocos novos "Gestão de membros" e
      "Sair" — na altura em que foi desenhado, o `UserMenu.tsx` real só
      tinha "Agregado" + seletor de tema, sem estes dois. Corrigido depois
      da construção: o `BottomNav` do ecrã "Gestão de membros" tinha
      "Receitas" marcado como activo por engano (era só o clone base) —
      passou a ambos os itens inactivos, já que não há destino de nav
      próprio para esta página. **Atualização, ainda 2026-08-10:** o
      backend de autenticação usado como contrato (não commitado quando
      este desenho começou) **foi committado entretanto, em paralelo, por
      outra sessão** (commits `0810e03`/`48a5981`, "autenticação
      multi-utilizador real (v1.2)") — ver esse item na secção v1.2 acima.
      A implementação real diverge do desenho Figma num ponto: "Gestão de
      membros" ficou **dentro do próprio dropdown do `UserMenu`** (lista +
      formulário "Adicionar pessoa" inline), não como página própria com
      `Header`+`BottomNav`. Os ecrãs `v1.2 — Setup`/`v1.2 — Login` batem
      certo com `pages/Setup.tsx`/`pages/Login.tsx` reais; o ecrã
      `v1.2 — Gestão de membros` como página autónoma fica então como
      conceito alternativo, não como documentação do que existe — por
      reconciliar com o Figma numa próxima passagem, não urgente.
      **Ecrãs de v2 — Cookbooks/coleções** (página `v1.0`, prefixo
      `v2 — Cookbooks —`): a frente mais especulativa, sem modelo
      `Cookbook` em lado nenhum do backend na altura do desenho — decisão
      de produto (lista manual, estilo Tandoor, em vez de coleção por
      filtro inteligente estilo Mealie) foi recomendação aplicada no
      desenho e **entretanto confirmada** (item #3 da secção "Coisas que
      precisas de decidir tu" abaixo, resolvido a 2026-08-10 — modelo a
      implementar: `Cookbook` + tabela de associação `Cookbook`↔`Recipe`
      many-to-many, sem filtro automático). Entrada a partir da Home por
      um link de texto "Coleções →"
      por baixo dos chips de filtro (mobile e desktop), não por um novo
      destino do `BottomNav` — regra do `DESIGN.md` de não adicionar nav
      antes do ecrã existir a sério no código, mesmo padrão já seguido para
      "Favoritos". Dois ecrãs novos, mobile+desktop: "Coleções" (lista,
      cards com nome + contagem de receitas) e "Detalhe da coleção"
      (reutiliza o `RecipeGrid` tal e qual). Deliberadamente **não**
      tocado: o `ActionsGroup` (favorito/duplicar/editar) do Detalhe da
      Receita, já fechado e sem largura livre para um 4.º item — a
      afordância "adicionar a esta coleção" fica só documentada por nota de
      texto como trabalho pendente, para não arriscar partir um ecrã já
      verificado.
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
- [x] **Parsing de ingredientes da importação** — `app/tasks.py::
      _parse_ingredient_line`, aplicado só às linhas vindas do
      `recipe-scrapers` (a entrada manual já guarda quantidade/unidade/nome
      em campos separados desde sempre). Reconhece um número no início
      (inteiro, decimal com vírgula ou ponto, fração `1/2`, fração unicode
      `½¼¾⅓⅔⅛`) seguido de uma unidade PT conhecida (massa/volume — g, kg,
      ml, l, colher(es) de sopa/chá/café incl. abreviatura `c.`, chávena,
      copo — e contagem — dente, fatia, folha, pitada, lata, pacote,
      embalagem, unidade/`unid.`), com "de "/"d'" a seguir removido do
      nome. **Mesma disciplina do `_extract_steps`** (nunca uma heurística
      que arrisque destruir dado real): quando não há confiança total, a
      linha inteira fica intacta em `Ingredient.name` com `quantity`/`unit`
      a `null` — cobre intervalos ("2-3 dentes", "2 a 3 folhas", nunca
      escolhe um lado), frações mistas ("1 ½", não suportado), e linhas sem
      quantidade no início ("Sal q.b.", "Azeite (opcional)"). Caso real
      descoberto só ao testar contra `pingodoce.pt`: o site escreve "1 q.b.
      salsa fresca" — o "1" não é quantidade nenhuma, é só o formato deles
      para "a gosto"; reconhecido e tratado como não-parseável em vez de
      guardar `quantity=1` enganador. Dois bugs de regex apanhados só ao
      testar (não óbvios por inspeção): `colheres?` como escrito
      correspondia a "colhere"/"colheres" (faltava agrupar o "es" opcional,
      `colher(?:es)?`) e a fronteira `\b` no fim de unidades abreviadas
      como "unid."/"c." nunca batia certo (`\b` não conta como fronteira
      entre dois caracteres não-palavra — o "." e o espaço a seguir — por
      isso trocado por `(?!\w)`). Testado com casos sintéticos (frações,
      intervalos, `q.b.`, "3 ovos" sem unidade) e com scraping real de
      `pingodoce.pt` ponta a ponta (task chamada diretamente, sem mock,
      contra a BD local — registo de teste apagado no fim), 10 ingredientes
      todos corretos incluindo os dois casos "q.b." acima. **Desbloqueia**:
      escalar porções também para receitas importadas por URL (hoje só
      funciona para as manuais), custo por porção e pesquisa por
      ingredientes disponíveis (ambos ainda por implementar).
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
      inacessível). **Deploy em produção feito em 2026-08-10** (release
      `v1.2.0`, ver entrada própria mais abaixo) — `AUTH_SECRET` gerado
      (`openssl rand -hex 32`), `AUTH_COOKIE_SECURE=true` e
      `PUBLIC_BASE_URL=https://receitas.alveslab.dev` definidos no `.env`
      do CT 202. **Falta que ficou registada só ao verificar em
      produção, não prevista antes**: as três migrações Alembic desde a
      última tag publicada (`1c5b13ed2ab2` planeamento,
      `65564d5e86e1` auth, `b1d85af98dd0` nome) nunca tinham sido
      aplicadas à BD de produção — não há passo de migração automática
      no `Dockerfile` (só `CMD uvicorn`), fica sempre manual
      (`docker-compose exec web alembic upgrade head`) depois de cada
      deploy que traga migração nova. **Primeira vez que a auth corre em
      produção**: `needs_setup` ficou `true` depois do deploy — a
      primeira conta real (Vítor) precisa de ser criada em
      `https://receitas.alveslab.dev/setup`, ainda por fazer.
- [x] **Secção de perfil no `UserMenu`** — resolve a decisão #5 (comparação
      com o menu de utilizador do Mealie/Tandoor: perfil com nome/email/
      password próprios, sem trazer o que não se aplica ao Tacho — idioma
      fixo PT, sem admin/spaces/roles/tokens). Três acrescentos: **alterar
      password** (`PATCH /users/me`, endpoint do `fastapi-users` que já
      existia sem UI própria), **alterar email** (mesmo endpoint, `safe=True`
      do `BaseUserManager.update` deixa mudar email/password mas não
      `is_superuser`/`is_verified`/`is_active` por esta via — confirmado no
      código-fonte da lib, não assumido), e **nome próprio** — `User` não
      tinha nenhum campo de nome (só os herdados do mixin do
      `fastapi-users`), coluna `name` nova (opcional, migração aditiva
      `b1d85af98dd0`), `UserRead`/`UserUpdate`/`MemberOut` estendidos.
      Iniciais do avatar (`initials()`) passam a usar o nome quando existe
      (duas iniciais, primeira+última palavra) em vez das duas primeiras
      letras do email. Frontend: `InlineEditField`, um componente pequeno
      partilhado pelas 3 formas (nome/email/password são o mesmo padrão —
      link que abre um campo, guarda, mostra confirmação — só muda o tipo
      de input e a chamada à API); `AuthContext.refresh()` chamado depois
      de guardar nome/email para o header atualizar sem recarregar a
      página (password não precisa, não afeta o que é mostrado). **Remover
      pessoa do agregado** também implementado (não estava na decisão #5,
      mas era a assimetria óbvia de só dar para adicionar) —
      `DELETE /workspace/members/{user_id}` apaga a conta por completo via
      `user_manager.delete` (não só a linha de `workspace_members`, que tem
      `ondelete=CASCADE` e desaparece sozinha), para o email ficar livre
      outra vez em vez de reservado para sempre; nunca permite
      auto-remoção (400), 404 se o membro não pertencer à workspace atual.
      Testado pela API com duas contas de teste descartáveis criadas via
      `UserManager` diretamente (token JWT assinado à mão com
      `get_jwt_strategy()`, sem depender das passwords das contas
      `vitor`/`mariana` já existentes, que este teste não tocou): nome/
      email/password mudam e o novo login funciona, email duplicado dá 400
      (`UPDATE_USER_EMAIL_ALREADY_EXISTS`), auto-remoção dá 400, remover
      outro membro dá 204 e desaparece da lista, repetir dá 404 — contas de
      teste apagadas no fim, confirmado por `GET /workspace/members` que só
      sobram `vitor@example.com`/`mariana@example.com`. **Testado também no
      browser** (Playwright, instalado ad-hoc num diretório à parte — não
      ficou como dependência do projeto): sessão injetada via cookie
      `tacho_session` assinado à mão (mesma técnica dos testes pela API,
      para não tocar nas passwords reais de `vitor`/`mariana`), duas contas
      descartáveis (`pw-primary-*`/`pw-secondary-*`). Fluxo completo sem
      erros de consola: alterar nome (painel e iniciais do avatar atualizam
      para "PT" sem reload, `AuthContext.refresh()` a funcionar), alterar
      email, alterar password, agregado a mostrar `vitor`/`mariana` +
      conta secundária, sem botão de remover na própria linha, remover a
      conta secundária (desaparece da lista sem reload), toggle de tema.
      Contas de teste apagadas no fim, confirmado por consulta direta à
      tabela `users` que só sobram as duas reais.
- [x] **Login silencioso via forward-auth do Authentik** — decisão do
      utilizador, 2026-08-10: **não** um botão OIDC como o do Securo
      (comparação feita com o código real do Securo, `oidc_auth.py`, fluxo
      Authorization Code + PKCE completo com Redis para o state) — em
      produção o CT 202 já está atrás do Authentik forward-auth ao nível do
      NPM (`homelab/inventory.md:57`), um botão OIDC faria um segundo
      round-trip a pedir a mesma coisa outra vez. Em vez disso: se o
      pedido já chega autenticado (header de email do forward-auth), o
      Tacho inicia sessão sozinho, sem mostrar o login. Muito mais simples
      que o Securo — sem Redis, sem PKCE/JWKS/nonce, sem auto-registo nem
      criação de workspace (o Tacho não faz nenhuma dessas coisas para
      login normal também). `POST /auth/forward-login`
      (`routers/auth.py`): só confia no header de email
      (`Settings.forward_auth_email_header`, omissão `X-authentik-email`)
      se vier acompanhado de um segredo partilhado
      (`Settings.forward_auth_secret`) — sem isto, qualquer pedido que
      contornasse o NPM (outro container na mesma LAN, por exemplo)
      conseguia forjar o header e entrar como qualquer pessoa; **só o NPM
      pode injetar o segredo, nunca o Authentik em si** (ver checklist
      abaixo). Nunca cria conta nem workspace — só inicia sessão para
      quem já é membro do agregado (`WorkspaceMember` na
      `DEFAULT_WORKSPACE_ID`), mesmo padrão fechado das decisões #1/#2;
      devolve 404 tanto para email desconhecido como para email sem
      membership, para não revelar qual dos dois é o caso. Desligado por
      omissão (`Settings.trust_forward_auth = False`) — inerte em dev e em
      produção até se configurar o NPM. Frontend: `tryForwardLogin()`
      (`api/auth.ts`), chamado por `AuthContext.refresh()` só quando
      `GET /users/me` falha — best-effort, silencioso, sem UI nova
      nenhuma (nem botão nem ecrã — é invisível quando funciona).
      **Testado no browser** (Playwright, backend arrancado com
      `TRUST_FORWARD_AUTH=true`/`FORWARD_AUTH_SECRET` de teste, headers
      simulados via `extraHTTPHeaders` do Playwright — não foi possível
      testar contra o Authentik real, ver nota abaixo): headers válidos →
      entra direto na app sem ver o login; sem headers → login normal;
      email sem conta Tacho → login normal; segredo errado → login normal
      (não entra como a conta real, confirma que forjar só o header do
      email não chega). Sem erros de JavaScript em nenhum cenário (só o
      aviso normal do Chrome para os pedidos 401/404 esperados do próprio
      padrão de "verificar sessão em silêncio", já presente antes disto no
      `GET /users/me` do carregamento normal do `/login`). **Não testado
      contra o Authentik/NPM reais** — isso precisa de configuração do
      lado da infraestrutura partilhada, fora do que este trabalho pode
      fazer sozinho (mesma fronteira da decisão #4). **Checklist para
      produção** (por fazer no NPM + Authentik, não no código):
      1. No Authentik, confirmar que o Provider/Outpost que protege
         `receitas.alveslab.dev` tem a opção de enviar os headers
         `X-authentik-*` ativada (nem todos os outposts do Authentik
         mandam isto por omissão).
      2. No Nginx Proxy Manager (CT 207), na config avançada do host
         `receitas.alveslab.dev`, adicionar
         `proxy_set_header X-Tacho-Forward-Secret "<valor secreto>";`
         — só o NPM injeta isto, por isso um pedido direto ao CT 202 que
         contorne o NPM nunca o consegue forjar.
      3. No `.env` do CT 202, definir `TRUST_FORWARD_AUTH=true` e
         `FORWARD_AUTH_SECRET=<o mesmo valor do passo 2>` (os outros três
         — `AUTH_SECRET`, `AUTH_COOKIE_SECURE`, `PUBLIC_BASE_URL` — já
         ficaram definidos no deploy da `v1.2.0`, ver abaixo).
      4. Confirmar que o NPM não filtra o header `X-authentik-email` a
         caminho do CT 202 (comportamento por omissão, mas vale confirmar).
      5. Testar com as duas contas reais (`vitor`/`mariana`) — o email da
         conta Authentik de cada um tem de bater certo com o email da
         conta Tacho correspondente, senão cai no login normal (por
         omissão, sem revelar qual dos dois falhou).
      **Release e deploy — 2026-08-10.** Tag `v1.2.0` publicada
      (`ghcr.io/11vitoralves11/tacho_app-{web,celery-worker}:v1.2.0`,
      workflow `build-and-push.yml`), `docker-compose.prod.yml` do
      repositório e do CT 202 atualizados, containers `web`/
      `celery-worker` recriados e confirmados a correr essa imagem
      (`docker inspect` vs `docker image inspect`, IDs a bater certo).
      Migrações pendentes aplicadas em produção (ver nota na entrada
      "Multi-utilizador real" acima — não havia passo automático).
      `AUTH_SECRET`/`AUTH_COOKIE_SECURE`/`PUBLIC_BASE_URL` definidos no
      `.env` do CT 202 (estavam em falta desde o deploy anterior —
      produção esteve a usar o `AUTH_SECRET` de omissão, público no
      código, entre o deploy da auth e esta correção; sem sinal de
      exploração, mas é uma janela real a registar). `needs_setup` ficou
      `true` — primeira vez que a auth corre em produção, falta criar a
      conta real do Vítor em `/setup`. Passos 1/2/4/5 da checklist acima
      continuam por fazer (dependem do Authentik/NPM, fora do alcance
      deste trabalho).
- [x] **Fix: `RecipeForm.tsx` a desformatar-se em mobile e a desalinhar o
      `BottomNav`** — reportado pelo utilizador em 2026-08-11. Causa raiz
      única para os dois sintomas: `fieldClass` (linha 179) incluía `w-full`
      e os campos estreitos de Ingredientes/Preparação combinavam
      `${fieldClass} w-16`/`w-24` esperando que a classe mais específica
      ganhasse — mas ambas têm a mesma especificidade CSS (uma classe), e o
      Tailwind v4 gera `.w-full` **depois** de `.w-16`/`.w-24` no mesmo
      `@layer utilities`, por isso `w-full` ganhava sempre o cascade
      (confirmado inspecionando o CSS gerado por um build real, não por
      suposição). Os campos de quantidade/unidade/duração renderizavam a
      100% de largura dentro de linhas `flex`, espremendo os restantes
      campos — visualmente "desformatado". O mesmo overflow horizontal daí
      resultante (confirmado por medição: `document.documentElement
      .scrollWidth` 445px vs `clientWidth` 375px em `/adicionar` mobile,
      antes do fix) explica também o `BottomNav` "não direito": overflow
      horizontal na página quebra o posicionamento de elementos `fixed` no
      viewport visual em browsers móveis reais — o `BottomNav.tsx` em si
      não tinha bug próprio (confirmado por screenshot a 320px/375px, 4
      itens bem alinhados, sem quebra de texto). **Fix**: tirado `w-full`
      da base de `fieldClass`; declarado explicitamente em cada campo que
      precisa dele; campos estreitos (`qtd`, `unidade`, `min` do passo)
      ganharam `shrink-0`; os campos flexíveis ao lado (nome do
      ingrediente, texto do passo) passaram a `min-w-0 flex-1` em vez de
      dependerem do `w-full` implícito. Testado no browser (Playwright,
      sessão via forward-auth de teste): `scrollWidth` volta a 375px = 375px
      (sem overflow), screenshots de `/adicionar` (mobile, tab "À mão"),
      Home, Planeamento e Lista de Compras confirmam layout correto em
      320px/375px/1280px, `tsc -b` e `oxlint` sem erros novos.
- [x] **Favoritos por utilizador** — evolução do favorito único do agregado
      (v1.1) para `favorited_by` por utilizador, padrão Mealie. Tabela de
      associação `recipe_favorites` (`recipe_id`, `user_id`, chave primária
      composta, sem `relationship()` ORM para `User` — `crud.py` consulta-a
      diretamente), migração `514ada9a40d4`; dado antigo migrado para
      "favoritado por todos os membros atuais da workspace" em vez de
      perdido (mais fiel ao comportamento anterior, que era do agregado
      inteiro). **`Recipe.is_favorite` deixou de ser coluna** — passou a
      atributo Python marcado em runtime por `crud._annotate_favorites`
      para o utilizador do pedido (`GET /users/me`), antes de sair para o
      schema; **API e frontend ficaram inalterados** (mesmo nome de campo,
      mesmo endpoint `POST /recipes/{id}/favorite` a fazer toggle), só o
      significado mudou de "favorito do agregado" para "favorito deste
      utilizador" — zero alterações no frontend. Todas as funções de
      `crud.py` que devolvem receitas à API (list/get/update/mark-made/
      add-note/set-image/meal-plan) passaram a exigir `user_id` para
      anotar; `duplicate_recipe`/`create_recipe` marcam `is_favorite=False`
      diretamente (registo novo nunca está favoritado, não herda da
      original). Testado ponta a ponta via curl com as duas contas reais
      (`vitor`/`mariana`, sessão por forward-auth de teste): favoritar com
      uma conta não afeta a outra (confirmado nos dois sentidos), listar
      `?favorite=true` filtra por utilizador, `GET /meal-plan` (que aninha
      `RecipeSummary`) também leva `is_favorite` correto — dados de teste
      desfeitos no fim (nenhum favorito nem entrada de plano ficou na BD).
- [x] **Avaliação por estrelas** — padrão do Mealie (`rating`), não do
      Tandoor (que não tem esta funcionalidade). `Recipe.rating: int | None`
      (1-5), coluna aditiva com `CHECK` na BD (`rating IS NULL OR rating
      BETWEEN 1 AND 5`, defesa em profundidade — a validação principal é
      `schemas.RecipeRatingIn` com `Field(ge=1, le=5)`), migração
      `1124746a9f09`. **Do agregado, não por utilizador** — ao contrário de
      `is_favorite` (evolução recente para per-user), este fica simples
      como a maioria dos campos da receita (notas, calorias): qualquer
      membro vê e muda a mesma avaliação. `PATCH /recipes/{id}/rating`
      (`{"rating": 1..5}` ou `{"rating": null}` para limpar). Não copiado em
      `duplicate_recipe` (mesma lógica de `last_made_at` — é avaliação de
      uso, não conteúdo da receita). Frontend: `StarIcon` novo em
      `icons.tsx` (mesmo estilo dos restantes, traço 24×24); widget de 5
      estrelas em `RecipeDetail.tsx`, entre a descrição e o hero — clicar
      numa estrela já preenchida desfavorita-a (toggle), reaproveita
      `accent-leaf` (não `accent-orange`, reservado a tempo/Modo Cozinha).
      Testado via curl (definir, limpar, 0 e 6 rejeitados com 422) e no
      browser (Playwright): clicar na 4ª estrela preenche 4 de 5 sem
      reload, sem erros de consola — dado de teste limpo no fim.
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

3. ~~Cookbooks: em que fase entram, e em que modelo?~~ **Resolvido, 2026-08-10:**
   lista manual, estilo Tandoor (não coleção por filtro inteligente estilo
   Mealie) — confirma a recomendação já aplicada no desenho Figma (ver
   "v1.1" acima, "Ecrãs de v2 — Cookbooks/coleções"). Fica ainda na v2 (fase
   por confirmar se avança já ou continua em backlog); modelo a implementar:
   `Cookbook` (nome) + tabela de associação `Cookbook`↔`Recipe` (many-to-many,
   uma receita pode estar em várias coleções), sem filtro automático.

4. **Quando/como implantar no homelab a sério.** Ainda corre só no CT 111, fora
   do `docker-compose.yml`. Falta decidir VMID/IP novo seguindo a convenção do
   `homelab/CLAUDE.md` — ação de infraestrutura partilhada, não tomada sem
   autorização explícita.
   ⚠️ Enquanto não houver autenticação (v1.2), a app **só pode estar acessível
   dentro da tailnet** — nunca exposta à LAN de convidados nem à internet.

5. ~~O conteúdo do menu de utilizador está bem assim?~~ **Resolvido,
   2026-08-10**, por comparação com Mealie/Tandoor (ver "v1.2" acima,
   "Secção de perfil no `UserMenu`"): ficou com sessão (nome/email/
   password editáveis), agregado (listar/adicionar/remover), tema, sair —
   sem trazer o que é próprio de apps multi-tenant e não se aplica aqui
   (idioma, admin, spaces, tokens de API).

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