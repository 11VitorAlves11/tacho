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
      `v1.2 — Gestão de membros` como página autónoma ficou marcado como
      "ideia descartada" (nota de texto no próprio frame, feita numa sessão
      de Figma entretanto), a apontar para `component/UserMenu-Dropdown-Aberto`
      como fonte de verdade — reconciliação concluída.
      **Reconciliação do `UserMenu-Dropdown-Aberto`, 2026-08-11:** esse
      componente (página `Componentes`, ficheiro Figma
      `Receitas App - Design Revamp`) tinha ficado desatualizado por ter sido
      construído antes da secção de perfil chegar ao código — só tinha os
      blocos Agregado + Tema. Reconciliado com o `UserMenu.tsx` real: bloco
      "Sessão" passou a mostrar nome+email (quando há nome) e os 3 links
      "Alterar nome"/"Alterar email"/"Alterar password" (estado fechado do
      `InlineEditField`; o estado aberto — formulário de um campo com
      Guardar/Cancelar — fica só anotado por nota de texto, mesmo padrão de
      input em pill já usado no resto do ficheiro); lista "Agregado" passou a
      mostrar o botão de remover (ícone X) em todas as linhas exceto a da
      própria pessoa, replicando `m.id !== user.id` do código. Aproveitado
      para corrigir também o avatar do estado fechado do `UserMenu`, que
      ainda mostrava `"VM"` fixo (iniciais do agregado, herança do UserMenu
      pré-login) em 17 instâncias espalhadas pelo ficheiro — agora mostra as
      iniciais de uma pessoa autenticada (`"VA"`, mesma identidade de exemplo
      do dropdown). Verificado por screenshot (componente isolado e em
      contexto num frame de ecrã real) e `get_variable_defs`/`get_styles` no
      fim (9 variáveis de cor, 5 estilos de texto, 4 de efeito — intactos).
      **Nota à parte, sem relação com o trabalho acima:** o ficheiro Figma
      tinha 3 páginas nos planos anteriores a esta sessão (`Design System`,
      `v1.0 — Ecrãs atuais`, `v1.1 — Planeamento & Compras`) e passou a ter só
      2 (`Componentes`, `Design da Aplicação (Mobile & Desktop)`, mesmos IDs
      `30:2`/`0:1`) — confirmado que foi só uma reorganização/fusão de
      páginas por alguém, sem perda de conteúdo (todos os frames de
      Planeamento, Lista de Compras, Setup, Login e Cookbooks continuam lá).
      Registar aqui para planos futuros não voltarem a assumir "3 páginas".
      **Fix: alinhamento Porções/Preparação/Confeção em mobile, 2026-08-11**
      — reportado pelo utilizador ("caixa de texto das porções está acima
      das outras"). Causa: `Grid3-PorcoesPrepCook` (frame `Mobile - Editar
      receita`) tem 3 colunas independentes (label + input, auto-layout
      vertical), cada uma a fazer HUG à sua própria altura; a coluna
      "Porções" (etiqueta de uma linha, 17px) ficava mais baixa que
      "Preparação (min)"/"Confeção (min)" (etiquetas que quebram para 2
      linhas a 98px de largura, 34px), e como a linha-mãe alinha ao topo
      (`counterAxisAlignItems: MIN`), a caixa de input de "Porções" ficava
      17px acima das outras duas. **Fix final** (pedido do utilizador):
      etiqueta passou de "Porções" para "Porções (und)" — a condizer com
      "Preparação (min)"/"Confeção (min)", que já mostravam a unidade, sem
      ponto (convenção já usada em todo o ficheiro, ex. "25 min"/"35 min"
      no `RecipeCard`, decisão do utilizador: unidades como símbolo, não
      abreviatura truncada). Com o ponto ("und."), o texto quebrava para 2
      linhas nos 98px de mobile e alinhava naturalmente com as outras duas
      colunas; sem ponto ("und"), cabe numa só linha — o `minHeight: 34`
      deixado por segurança na etiqueta `55:654` acabou por ser necessário
      mesmo, e mantém a caixa alinhada com as outras duas apesar de o texto
      já não quebrar. Aplicado em mobile (`55:654`) e desktop
      (`61:1274`, cabe numa linha aos 261px de coluna, sem quebra — mesmo
      comportamento das outras duas colunas no desktop, sem regressão).
      Verificado por screenshot (grelha isolada mobile+desktop e o ecrã
      `Mobile - Editar receita` completo); grelha de Informação nutricional
      (2×2, mais abaixo no mesmo formulário) confirmada sem o mesmo
      problema. **Nota:** a mesma classe de bug (`w-full`/cascade a
      espremer campos) já tinha sido corrigida no código real em
      2026-08-11 (ver entrada "Fix: `RecipeForm.tsx`..." na secção v1.2),
      mas naquela correção não tocou nesta linha Porções/Preparação/
      Confeção — vale a pena a outra sessão confirmar se a app real tem o
      mesmo desalinhamento e, já agora, se faz sentido replicar lá também
      o "(und)" na label de Porções por consistência com o Figma.
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
- [ ] **Importação inteligente via Gemini** — **implementado, mas
      deliberadamente deixado por marcar `[x]`: sem `GEMINI_API_KEY`
      disponível nesta sessão, a chamada real à API do Gemini nunca foi
      exercitada.** Ao contrário de todos os outros itens deste ficheiro,
      não há "testado no browser"/"testado via curl" a validar o que a IA
      realmente devolve — só a integração à volta dela.
      - `app/gemini.py` novo (`google-genai==2.17.0`, `Settings
        .gemini_api_key` opcional — `is_available()` false sem chave, a
        app funciona na mesma, como já estava decidido). Output
        estruturado via `response_schema=schemas.RecipeExtraction`
        (Pydantic), não parsing de texto solto.
      - **(a) fallback de extração** — `app/tasks.py::
        import_recipe_from_url`: só dispara quando o `recipe-scrapers` não
        trouxe **nem** ingredientes **nem** passos (nunca para "melhorar"
        um resultado que já veio preenchido). Confirmado que o caminho
        normal (com scraper a funcionar) fica bit-a-bit igual ao de antes
        — testado de novo contra `pingodoce.pt` real (10 ingredientes,
        como sempre) precisamente para provar que o refactor não mudou
        nada no caminho que não usa Gemini.
      - **(b) importação por foto** — `POST /recipes/import/photo`
        (síncrono, não Celery — ação pontual do utilizador, 1-3 fotos,
        devolve um rascunho para revisão, não uma receita já criada).
        `RecipeForm.tsx` ganhou um tipo `RecipeFormInitial` mais fraco do
        que `Recipe` (só os campos que um rascunho pode ter — sem id,
        sem is_favorite, etc.) para poder pré-preencher a partir de um
        `RecipeExtraction` sem inventar dados; `Recipe` continua a
        satisfazer esse tipo, o modo de edição normal não muda nada.
        `AddRecipe.tsx` ganhou uma 3ª aba "Por foto".
      - **O que foi mesmo testado**: o caminho sem chave (`422`
        "não está configurada", testado via curl e no browser); validação
        de limite de fotos (1-3, testado via curl); o parsing/pré-
        preenchimento do formulário a partir de uma resposta simulada
        (`page.route` do Playwright a devolver um `RecipeExtraction`
        fabricado — confirma que o adaptador `RecipeFormInitial`
        funciona, não que o Gemini vai devolver isto).
      - **O que NÃO foi testado, por falta de chave**: se o Gemini
        realmente extrai bem uma receita PT real (URL com scraper falhado,
        ou foto de livro/letra manuscrita), a qualidade do fallback, e o
        ⚠️ já assinalado no PRD sobre o LLM poder "corrigir" quantidades
        silenciosamente. **Antes de confiar nisto em produção**: definir
        `GEMINI_API_KEY` e validar com casos reais.
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
- [x] **Comentários** por receita — com autor (diferente do `CookNote`, nota
      pós-confeção sem autor, e de `Recipe.notes`, campo único). Modelo
      `Comment` novo (`recipe_id`, `user_id`, `text`, `created_at`),
      migração `49f829cb42e3` (autogenerate propôs também remover o CHECK
      `ck_recipes_rating_range` — falso positivo, mesmo padrão do índice
      GIN documentado em `models.py::Recipe`, removido à mão e deixada nota
      lá para a próxima vez). `author_name`/`author_email` em
      `schemas.CommentOut` não são colunas — properties em `models.Comment`
      que delegam para `comment.user` (mesmo padrão do `Recipe.is_favorite`
      calculado em runtime). Ordem cronológica (mais antigo primeiro, como
      uma conversa — ao contrário do `CookNote`, que é histórico ordenado
      do mais recente). `POST /recipes/{id}/comments`,
      `DELETE /recipes/{id}/comments/{comment_id}` — qualquer membro pode
      apagar qualquer comentário, mesmo modelo de confiança total já usado
      no resto da app (remover pessoa do agregado, editar/apagar receitas
      de outrem). Frontend: secção "Comentários" no Detalhe, entre
      Preparação e a fonte — lista com autor+data+botão apagar, mais um
      formulário simples (input + "Enviar") sempre visível. Testado via
      curl com as duas contas reais (comentar com uma, apagar com a outra,
      ordem cronológica confirmada) e no browser (Playwright): escrever e
      enviar um comentário aparece de imediato sem reload, sem erros de
      consola — dados de teste apagados no fim.

---

## v2

- [x] **Cálculo automático de nutrição a partir dos ingredientes** — Open
      Food Facts, não LLM (decisão já tomada — o Gemini não tem base de
      dados nutricional, pedir-lhe calorias/macros seria alucinação em
      dados de saúde). `app/nutrition.py::estimate_nutrition`: só
      ingredientes com unidade de massa/volume reconhecida (g/kg/ml/l/dl,
      convertidos para gramas-equivalente — `ml`≈`g` assume densidade de
      água, aproximação grosseira mas aceitável para uma estimativa)
      entram na conta; unidades de contagem (dente, unidade, pitada…)
      ficam de fora, sem conversão fiável. Pesquisa de texto na OFF por
      ingrediente, só o primeiro produto com dados nutricionais é usado;
      sem resultado ou sem correspondência, esse ingrediente é ignorado —
      nunca trava o resto. Soma-se a receita toda e só no fim divide-se
      pelas porções (`Recipe.calories_kcal`/etc. são "por porção", não
      pela receita — divisão em falta seria um bug silencioso). **Nunca
      grava sozinho**: `POST /nutrition/estimate` (recebe ingredientes +
      porções do próprio formulário, não precisa da receita já guardada)
      devolve a estimativa com `matched_count`/`skipped_count` para
      transparência; o utilizador tem de clicar "Aplicar" em
      `RecipeForm.tsx` para os 4 campos serem substituídos — mesmo
      princípio do import Gemini, nunca grava direto. **Não totalmente
      verificado**: a pesquisa da Open Food Facts esteve consistentemente
      em baixo (503 "Page temporarily unavailable") durante todo o
      desenvolvimento e teste desta funcionalidade — confirmado que é do
      lado deles (o site e o lookup por código de barras funcionavam
      normalmente, só a pesquisa por texto, nova e antiga API, estava
      afetada). Testado o que deu: agregação e arredondamento corretos
      contra uma resposta real capturada num momento em que a pesquisa
      respondeu (`farinha`+`açúcar`, matched_count confirmado 1-2 em
      várias tentativas); tratamento de erro testado exaustivamente
      (rede em baixo, sem resultados, unidade não reconhecida, cabeçalho
      de secção ignorado, lista vazia, 401 sem sessão) — nunca crasha,
      sempre devolve uma resposta válida. UI testada no browser
      (Playwright) no caminho de falha total (mensagem "não foi possível
      estimar agora" em vez de erro cru). **Por fazer**: validar contra
      pesquisas reais bem-sucedidas quando a OFF recuperar.
- [x] **Custo por receita/porção** — decisão: sem fonte de preços por
      ingrediente disponível nem decidida (nem OFF nem nenhuma API de
      supermercado PT tem isso, e não está nos planos ir buscar uma só
      para isto), por isso **entrada manual** em vez de automática — um
      único campo `Recipe.estimated_cost` (custo da receita **toda**, não
      por porção; migração `90e07c148e15`), mesmo padrão que a nutrição
      usava antes do cálculo automático existir. Custo por porção
      calculado em runtime no frontend (`estimated_cost / servings`,
      arredondado a 2 casas), mostrado como `HeroStat` novo no Detalhe
      (ícone `EuroIcon` novo, ao lado de tempo/porções/calorias, tom
      `forest` como calorias — laranja continua exclusivo de tempo/Modo
      Cozinha). Campo novo em `RecipeForm.tsx`, entre "Fonte" e "Notas".
      Copiado em `duplicate_recipe` (é atributo da receita, como as
      calorias — ao contrário do `rating`, que é avaliação de uso e não é
      copiado). **Efeito colateral desta tarefa**: o CHECK do rating
      (`ck_recipes_rating_range`) finalmente declarado em
      `Recipe.__table_args__` — resolve de vez o falso positivo do
      autogenerate que obrigava a apagar `op.drop_constraint` à mão em
      todas as migrações desde a v1.2 (confirmado com uma migração de
      verificação vazia, descartada). Testado via curl (definir custo,
      confirmar `estimated_cost/servings` correto) e no browser
      (Playwright): campo no editor, "€/porção" no Detalhe — dado de teste
      reposto a `null` no fim (a receita seed não tinha custo definido).
- [x] **Despensa/inventário básico + pesquisa por ingredientes disponíveis**
      — implementados juntos (a pesquisa não tem utilidade sem a despensa).
      `PantryItem` (nome, `has_it`, `UniqueConstraint` por workspace/nome),
      migração `a1ded7dbab02` — só "tenho/não tenho", sem quantidades nem
      validades, âmbito contido de propósito (não virar um Grocy).
      "Dá para fazer": `crud.list_recipes(..., makeable_only=True)` —
      decisão de correspondência (substring normalizada, sem acentos/case:
      `unicodedata.normalize` + `casefold`-like `.lower()`) — uma receita
      "dá para fazer" quando **todos** os ingredientes não-cabeçalho têm o
      nome de despensa como substring do nome do ingrediente (ex. despensa
      "farinha" casa com ingrediente "farinha de trigo"); receita sem
      ingredientes nunca é "makeable" (protege contra receitas vazias
      aparecerem por vacuidade lógica). Filtro em Python, não SQL — a lista
      de despensa é tipicamente pequena, não compensa um JOIN/subquery.
      `GET /recipes?makeable=true`, novo router `app/routers/pantry.py`
      (`GET/POST /pantry`, `PATCH/DELETE /pantry/{id}`). Frontend: página
      `Pantry.tsx` (`/despensa`, checklist simples, acessível a partir de
      um link "Despensa →" na Lista de Compras — mesmo padrão do link
      "Coleções →" da Home, sem novo destino do `BottomNav`); chip "Dá
      para fazer" novo na Home, ao lado de "Favoritos", com estado vazio
      dedicado e link de volta para a despensa. Testado via curl (despensa
      vazia → 0 receitas; adicionar "Arroz" com `has_it=true` → "Arroz
      Doce" aparece; desmarcar → desaparece) e no browser (Playwright,
      fluxo completo Lista→Despensa→adicionar→Home→filtro→Despensa→
      desmarcar→Home→filtro→apagar), despensa confirmada vazia no fim via
      API.
- [x] **Cookbooks / coleções** — modelo exatamente como decidido (decisão #3
      acima): `Cookbook` (nome) + tabela de associação `cookbook_recipes`
      many-to-many com `Recipe` (uma receita pode estar em várias coleções,
      sem filtro automático — lista manual estilo Tandoor), migração
      `8f63280c8233` (o autogenerate voltou a propor remover o CHECK do
      rating por engano — terceira vez, ver nota em `models.py::
      Recipe.rating`). Sem endpoint de renomear — mesmo âmbito de
      `Category`/`Tag`, que também só têm criar/listar/apagar. Entrada a
      partir da Home por link de texto "Coleções →" por baixo dos chips de
      filtro (`Home.tsx`), **não** um novo destino do `BottomNav` — regra
      do `DESIGN.md` já seguida para Favoritos/Lista/Plano, mesmo padrão
      documentado no desenho Figma. Rotas novas `/colecoes` (lista, cards
      nome+contagem, criar/apagar) e `/colecoes/:id` (detalhe, reutiliza
      `RecipeCard` tal como o Figma previa — grid igual ao da Home, com
      `<select>` "+ Adicionar receita" para juntar uma receita existente,
      mesmo padrão do `<select>` de atribuição no `MealPlan.tsx`, e um
      link "Remover da coleção" por baixo de cada card, sem tocar no
      `RecipeCard` partilhado). **Deliberadamente não tocado** (mesma nota
      já deixada no desenho Figma): a afordância "adicionar a esta coleção"
      a partir do `ActionsGroup` do Detalhe da Receita — fica só acessível
      a partir da própria coleção. Apagar uma coleção não apaga as
      receitas (só a associação, `ondelete=CASCADE` na tabela de junção).
      Testado via curl (criar, listar com contagem, adicionar, obter,
      remover, apagar, e confirmar que a receita sobrevive à coleção ser
      apagada) e no browser (Playwright, fluxo completo: Home → "Coleções
      →" → criar → entrar → adicionar receita via select → remover →
      voltar → apagar coleção → estado vazio), sem erros de consola —
      nada de teste ficou na BD no fim.
- [x] **Modo Cozinha desktop** — `CookMode.tsx`: cabeçalho, barra de
      progresso e botões Anterior/Seguinte passaram a `mx-auto max-w-4xl`,
      mesma coluna centrada usada em todo o resto da app (`PageShell.tsx`,
      896px) — em 1280px de largura os botões deixavam de esticar de ponta
      a ponta do ecrã. O fundo cheio (verde-floresta, "modo escuro" fixo do
      Modo Cozinha) e o número gigante de fundo continuam full-bleed, só o
      conteúdo interativo ficou contido. **Pixel-idêntico em mobile**
      (confirmado por screenshot a 375px antes/depois — `max-w-4xl` nunca
      ativa abaixo de 896px). Testado no browser (Playwright) a 1280px e a
      375px.
- [x] **Modo Cozinha offline** (cache da receita ativa via service worker,
      não pré-cache de tudo) — `public/sw.js` ganhou um segundo papel além
      do cache-first de `/assets/*` já existente: uma cache
      `tacho-active-recipe-v1` separada, alimentada por `postMessage`
      (`CookMode.tsx` manda `{type: 'CACHE_ACTIVE_RECIPE', urls}` assim
      que a receita carrega — dados + foto). O `fetch` handler do SW faz
      network-first com fallback a essa cache **só** para pedidos que já lá
      estavam guardados explicitamente — outras receitas nunca cacheadas
      continuam a falhar normalmente offline (confirmado por teste,
      `TypeError: Failed to fetch`), isto não virou um cache de API
      genérico. Abrir uma receita nova no Modo Cozinha limpa a anterior da
      cache primeiro — nunca acumula, só a "ativa" de cada vez. **Testado
      contra o build de produção real** (`npm run build` + `vite preview`,
      não o servidor de dev — o dev do Vite serve módulos individuais não
      cacheados, só faz sentido testar isto num build real): confirmado
      que a receita ativa responde offline com os dados certos, que uma
      receita nunca aberta falha offline como esperado, e que trocar de
      receita substitui a cache. **Nota de âmbito**: isto sobrevive à rede
      cair enquanto a SPA já está montada e a correr (o caso real —
      "estou a meio de cozinhar e a rede caiu"); não sobrevive a um reload
      completo da página já offline, porque isso pré-cachearia o shell da
      app inteiro, que foi decisão explícita não fazer.
- [x] **Galeria de fotos por receita** (várias fotos, uma marcada como
      capa) — `RecipeImage` novo (`recipe_id`, `filename`, `position`,
      `is_cover`), migração `eb74e97da107` (primeira migração desde a
      v1.2 sem o falso positivo do CHECK do rating — confirmado com uma
      migração de verificação vazia, descartada). **Deliberadamente
      separada de `Recipe.image_path`**, que continua exatamente como
      estava (foto principal, upload único via `RecipeForm.tsx`, usada em
      todo o lado — card, hero do Detalhe); a galeria é só fotos extra,
      geridas diretamente no Detalhe (mesmo padrão de comentários/notas —
      sem passar pelo modo de edição). `POST/DELETE /recipes/{id}/images`
      (reaproveita `save_recipe_image`/`delete_recipe_image` já
      existentes), `POST /recipes/{id}/images/{image_id}/cover`. Primeira
      foto adicionada vira capa automaticamente; apagar a foto que é capa
      passa o papel para a seguinte por posição (nunca fica a galeria sem
      capa enquanto tiver pelo menos uma foto). Secção "Galeria" nova no
      Detalhe, entre Notas e Comentários — grid 3/4 colunas, badge "Capa",
      botões estrela (tornar capa)/× (apagar) sempre visíveis (não só
      hover — a app é mobile-first, hover não existe em touch). Testado
      via curl (1ª foto vira capa, 2ª não, mudar capa, apagar a capa herda
      para a que sobra, ficheiro realmente apagado do disco) e no browser
      (Playwright, upload real de ficheiro via `filechooser`): disco
      confirmado a voltar exatamente ao estado original (2 ficheiros) nos
      dois testes.
- [x] **Cartões maiores no menu inicial** (pedido à parte, mesma tarefa) —
      `RecipeCard.tsx` redesenhado de layout horizontal (thumbnail 56px)
      para vertical com imagem grande no topo (`aspect-[4/3]`, largura
      total do cartão), título e metadados por baixo — mais próximo do
      mockup Figma original, que a implementação real tinha simplificado
      para horizontal por velocidade (não por decisão de design). Mesmo
      componente partilhado por `Home.tsx` e `CookbookDetail.tsx`, ambos
      ficam maiores. Verificado por screenshot em mobile e desktop,
      incluindo um cartão com foto real (sem distorção, `object-cover`).
- [x] **Vista de impressão / PDF por receita** — decisão: `window.print()`
      com folha de estilo `@media print` dedicada (via o variant `print:`
      do Tailwind), sem gerar PDF no servidor nem nova dependência de
      geração de PDF. Botão "Imprimir" novo (`PrinterIcon`, ícone novo) ao
      lado de Favorito/Duplicar/Editar no Detalhe. `print:hidden` em tudo
      o que não interessa no papel — cabeçalho, `BottomNav`, os próprios
      botões de ação, steppers +/− de porções (o número fica, só os
      botões desaparecem), "Iniciar Modo Cozinha", secções inteiras de
      Galeria e Comentários (incluindo formulário e botões de apagar).
      Fundo forçado a claro na impressão mesmo com o sistema em modo
      escuro (`index.css`, mesma especificidade dos seletores do dark
      mode, para garantir que ganha) — poupa tinteiro e evita texto claro
      sobre fundo escuro no papel. **Pedido extra do utilizador: QR code
      partilhável** — biblioteca `qrcode` nova (cliente, sem chamada de
      rede; gerado localmente, funciona offline uma vez a app em cache),
      aponta para o URL da própria página (`window.location.href`),
      gerado assim que a receita carrega (antes de clicar "Imprimir", para
      não haver atraso nem flash) e só visível na folha de impressão
      (`hidden print:flex`). Testado no browser (Playwright,
      `emulateMedia({ media: 'print' })`): cabeçalho/nav/botões/
      galeria/comentários corretamente ausentes, QR code presente com o
      URL por baixo, fundo confirmado branco tanto em modo claro como em
      modo escuro do sistema.
- [x] **Fracções em unidades** ("½ chávena" em vez de "0.5 chávena") —
      `RecipeDetail.tsx::formatQuantity`, só formatação de apresentação,
      sem mudanças no backend nem no valor guardado (`Ingredient.quantity`
      continua `0.5`). Reconhece ⅛/¼/⅓/⅜/½/⅝/⅔/¾/⅞ com tolerância 0.02 —
      cobre o arredondamento a 2 casas do parser de importação (1/3 vira
      0.33, não 0.333…) e o erro de vírgula flutuante ao escalar porções.
      Funciona também com parte inteira ("1 ½ colher de sopa"); quando não
      reconhece a fração cai no formato decimal de sempre. Testado com
      script Node isolado (13 casos, incluindo escalar 0.5→1 ao dobrar
      porções, que deve mostrar "1", não "1 ½") e no browser (Playwright,
      receita de teste com farinha ½, açúcar ¼, manteiga 1 ½, sal 2 —
      confirmado visualmente antes e depois de escalar 4→8 porções, receita
      de teste apagada no fim).

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