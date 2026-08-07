---
name: Tacho
description: App de receitas do agregado, em sage e verde-floresta, para substituir o Tandoor e o Mealie.
colors:
  bg-sage: "#EAF0E7"
  bg-sage-deep-start: "#1F3D2B"
  bg-sage-deep-end: "#2D6A4F"
  card-white: "#FFFFFF"
  primary-forest: "#2D5F3F"
  accent-leaf: "#4CAF50"
  accent-orange: "#F2994A"
  text-primary: "#1C2B1F"
  text-secondary: "#5C6B5E"
typography:
  hero-number:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.5rem–1.875rem (2.25rem–3rem no Modo Cozinha)"
    fontWeight: 700
    lineHeight: 1
  section-title:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "1.125rem–1.25rem"
    fontWeight: 600
    lineHeight: 1.3
  body:
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif"
    fontSize: "0.75rem–0.875rem"
    fontWeight: 400
    lineHeight: 1.5
rounded:
  control: "9999px"
  card: "16px"
  hero: "24px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary-forest}"
    textColor: "{colors.card-white}"
    rounded: "{rounded.control}"
    padding: "14px 20px"
  button-cook-mode:
    backgroundColor: "{colors.accent-orange}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.control}"
    padding: "16px"
  card-recipe:
    backgroundColor: "{colors.card-white}"
    rounded: "{rounded.card}"
    padding: "16px"
---

# Design System: Tacho

## Overview

**Creative North Star: "O Tacho ao Lume"**

Tacho existe para substituir duas ferramentas de terceiros — Tandoor e Mealie — por uma só, com a identidade do próprio agregado. A linguagem visual vem diretamente da Secção 6 do PRD: fundo sage muito claro, cards brancos bem destacados, e verde-floresta como cor de marca em vez de mais uma tag de categoria. Isto comunica "saudável, fresco, caseiro" sem cair na estética quente de creme/terracota que uma app de "comida artesanal" assumiria por omissão — a referência é antes o mundo das apps de nutrição e bem-estar, mas aplicado a uma coisa muito concreta e doméstica: a receita que o agregado cozinha mesmo.

O sistema é deliberadamente contido: um único acento de marca (verde-floresta), um acento secundário para estado/organização (verde-folha), e o laranja reservado a um único papel — tempo e o "modo ativo" do Modo Cozinha, nunca decoração geral. Fora do Modo Cozinha (imersivo, em verde-floresta cheio), todos os ecrãs partilham o mesmo fundo sage claro e cards brancos: a app não muda de humor consoante o ecrã.

**Key Characteristics:**
- Fundo sage claro constante; branco reservado a cards e superfícies de conteúdo.
- Verde-floresta como cor de marca/CTA, não como um acento entre vários.
- Laranja com um papel único e não-negociável: tempo e o "modo ativo" do Modo Cozinha.
- Números grandes e a bold para métricas (tempo, porções, passo atual) — nunca para decoração.
- Ícones de traço próprios (stroke 1.75, 24×24), nunca glifos ou emoji.

## Colors

Paleta de dois verdes e um único acento quente, sobre um fundo neutro muito claro.

### Primary
- **Floresta Funda** (`#2D5F3F`): cor de marca. Usada em CTAs primários ("Iniciar Modo Cozinha", "Importar receita"), no item ativo da navegação, no fundo cheio do Modo Cozinha, e nos chips de categoria.

### Secondary
- **Verde-Folha** (`#4CAF50`): acento de estado e organização — chips de tag, ícone/anel de foco dos campos de pesquisa e URL. Nunca usado em CTAs (essa é função exclusiva do verde-floresta).

### Tertiary
- **Laranja Tacho** (`#F2994A`): reservado a tempo e ao "modo ativo". Usado no ícone de relógio (nunca no texto do tempo — ver a Regra do Ícone Colorido, em Componentes), na barra de progresso e no CTA "Seguinte" do Modo Cozinha. **The One Role Rule.** O laranja tem um único papel em todo o sistema — tempo e Modo Cozinha — e não aparece em mais lado nenhum, incluindo dados nutricionais (ainda por implementar; ver `PRODUCT.md`).

### Neutral
- **Sage Claro** (`#EAF0E7`): fundo base de toda a app fora do Modo Cozinha.
- **Floresta Profunda** (gradiente `#1F3D2B → #2D6A4F`): fundo do cabeçalho/hero, dá profundidade sem sair da paleta.
- **Branco Cartão** (`#FFFFFF`): fundo de todos os cards e superfícies de conteúdo — sempre destacado do sage.
- **Verde-Quase-Preto** (`#1C2B1F`): texto principal.
- **Verde Acinzentado** (`#5C6B5E`): texto secundário, metadata, legendas.

### Named Rules
**The One Voice Rule.** Verde-floresta é a única cor de ação/CTA em todo o sistema. Verde-folha organiza (tags, foco), nunca convida a agir.

## Typography

**Corpo e display:** Inter (400/500/600/700), self-hosted via `@fontsource` — pinada pelo PRD (Secção 6.2: "mantém-se"), não é o fallback de sistema.

**Character:** uma voz só, sem serifa nem mono — a mesma família carrega tanto o número grande de "20 min" como a legenda "porções". A hierarquia vem inteiramente de peso e tamanho, nunca de mudança de família.

### Hierarchy
- **Hero number** (bold 700, 1.5–1.875rem; 2.25–3rem no Modo Cozinha, leading 1): tempo total, porções, número do passo atual. Sempre acompanhado de uma legenda pequena por baixo.
- **Título de página** (bold 700, 1.5–1.875rem): título da receita, título da secção hero da Home.
- **Título de secção** (semibold 600, 1.125–1.25rem): "Ingredientes", "Preparação".
- **Corpo** (regular 400, 0.875rem): descrição da receita, texto dos passos, nomes de ingredientes.
- **Label** (regular/medium, 0.75rem): legendas dos hero numbers, metadata dos cards, texto de ajuda.

### Named Rules
**The No-Decoration Rule.** Tamanho grande e peso bold estão reservados a números que respondem a uma pergunta real do utilizador (quanto tempo? quantas porções? em que passo vou?). Nunca usados para ênfase decorativa de texto comum.

## Layout

Página de largura de conteúdo `max-w-4xl` centrada, com respiro lateral `px-4` (mobile) a `px-6` (`sm:` e acima). Grid de receitas: uma coluna em mobile, duas em `sm:` e acima (`grid-cols-2`). Densidade baixa: um card por receita, sem agrupamento denso — a lista é curta por natureza (receitas de família, não um catálogo).

**Mobile vs. desktop:** a app não troca de composição entre tamanhos, só de disposição — o mesmo cabeçalho, hero e grid, apenas mais coluna em ecrãs largos. A navegação é que muda de verdade: pill flutuante fixa ao fundo em mobile (`sm:hidden`), substituída por um link no cabeçalho em desktop (`hidden sm:flex`). O CTA "Iniciar Modo Cozinha" segue a mesma lógica — visível como botão de largura total no Detalhe em mobile, ausente em desktop (Modo Cozinha desktop é v2, PRD Secção 10).

## Elevation & Depth

Sistema de sombras suaves com offset e blur reais — nunca halos de offset zero. Cada sombra é tingida com a cor do texto principal (`rgba(28,43,31,…)`) ou, no CTA primário, com o verde-floresta (`rgba(45,95,63,…)`) — nunca preto neutro.

### Shadow Vocabulary
- **Card em repouso** (`0 2px 10px -2px rgba(28,43,31,0.12)`): cards de receita, formulário de Adicionar, hero stats do Detalhe.
- **Card em hover** (`0 8px 24px -4px rgba(28,43,31,0.22)`): `RecipeCard` ao passar o rato — eleva sem mudar de cor.
- **CTA primário** (`0 8px 20px -6px rgba(45,95,63,0.6)`): "Iniciar Modo Cozinha" — sombra tingida a verde-floresta, não neutra, para o botão parecer "pairar" sobre a página.
- **Navegação flutuante** (`0 10px 30px -8px rgba(28,43,31,0.35)`): a pill do bottom nav — a sombra é a única fonte de elevação (ver a Regra do Cartão Fantasma).

### Named Rules
**The Ghost Card Rule.** Elevação declara-se uma vez só — borda OU sombra, nunca as duas na mesma superfície. (Corrigido durante a revisão de finalização: o bottom nav tinha as duas.)

## Shapes

Dois raios, dois papéis. `16px` (`rounded-2xl`) para todos os cards de conteúdo — receita, formulário, hero stats. `24px` (`rounded-3xl`) só para o bloco hero da Home, proporcional à sua escala maior. Pills (`rounded-full`) exclusivamente para controlos pequenos e navegação: barra de pesquisa, barra de URL, chips de filtro/tag, bottom nav, botões CTA. Nunca um raio pill num container de conteúdo.

## Components

### Buttons
- **Shape:** pill (`rounded-full`, 9999px) — nunca cantos quadrados ou levemente arredondados.
- **Primary** (`button-primary`): fundo verde-floresta, texto branco, `padding: 14px 20px`, peso semibold.
- **Cook Mode** (`button-cook-mode`): fundo laranja, texto verde-quase-preto (não branco — o laranja não tem contraste suficiente para texto branco nem para ser usado como cor de texto sobre branco; ver a Regra do Ícone Colorido), `padding: 16px`, usado só dentro do Modo Cozinha ("Seguinte", "Concluir").
- **Ghost** (chip de filtro inativo): fundo `card-white/15` sobre o hero, texto branco; ativo troca para fundo branco sólido com texto verde-floresta.

### Chips (tags e categorias)
- **Categoria:** fundo `primary-forest/10`, texto verde-floresta.
- **Tag:** fundo `accent-leaf/10`, texto verde-folha.
- **State:** sem variante de seleção — são só rótulos informativos nos cards; a seleção ativa vive nos chips de filtro do hero (fundo branco quando ativo, `card-white/15` quando inativo).

### Cards / Containers
- **Corner Style:** 16px.
- **Background:** sempre branco, sempre sobre fundo sage — nunca branco sobre branco.
- **Shadow Strategy:** ver Elevation & Depth — repouso e hover, nunca borda.
- **Internal Padding:** 16px (cards de receita), 20px (hero stats, formulário).

### Inputs / Fields
- **Style:** pill, fundo branco (Home) ou sage (Adicionar), sem borda visível em repouso na Home; borda sutil (`black/10`) no campo de URL.
- **Focus:** anel `focus-within:ring-accent-leaf` no `<label>` que envolve o input — corrigido na revisão de finalização, onde `outline-none` no input não tinha nenhum substituto temático.

### Navigation
- **Mobile:** pill flutuante fixa ao fundo (`fixed inset-x-4 bottom-4`), fundo branco 95% opaco com `backdrop-blur`, item ativo em fundo verde-floresta cheio. Dois destinos reais na v1.0 (Receitas, Adicionar) — a Secção 6.2 do PRD descreve "4–5 ícones", ainda por atingir enquanto Planeamento e Lista de Compras (v1.1/v1.2) não tiverem ecrãs próprios.
- **Desktop:** barra fina no topo, gradiente floresta profunda, logótipo + link "Adicionar receita".

### Modo Cozinha (componente de assinatura)
Ecrã full-bleed em verde-floresta cheio (não sage) — o único lugar do sistema onde a cor de marca vira fundo, não acento. Um numeral gigante do passo atual, quase invisível (`text-card-white/5`), fica atrás do texto da instrução como marca d'água de escala — resolve o problema de um passo curto de texto flutuar sozinho num ecrã grande. Barra de progresso segmentada (um segmento por passo, laranja para os concluídos/atual) substitui qualquer paginação numérica. CTA "Seguinte"/"Concluir" sempre em laranja — o único sítio da app onde o laranja é fundo de botão, não só ícone.

## Do's and Don'ts

### Do:
- **Do** usar verde-floresta como a única cor de CTA/ação em toda a app.
- **Do** reservar o laranja a tempo e ao Modo Cozinha — nunca como decoração geral nem em texto sobre fundo branco (contraste ~2.2:1, insuficiente; usar só em ícones ou como fundo com texto escuro por cima).
- **Do** manter cards sempre brancos sobre o fundo sage, nunca brancos sobre brancos nem sage sobre sage.
- **Do** declarar elevação uma vez só por superfície — borda ou sombra, nunca as duas.

### Don't:
- **Don't** usar laranja como cor de texto corrido sobre fundo branco ou card branco — falha o contraste mínimo (4.5:1 texto normal, 3:1 texto grande).
- **Don't** introduzir uma segunda família tipográfica; Inter cobre display, corpo e labels.
- **Don't** adicionar mais destinos ao bottom nav antes de existir o ecrã real por trás deles (Planeamento, Lista de Compras) — um link morto é pior do que um nav com só 2 itens.
- **Don't** copiar o padrão de card do Tandoor/Mealie (ícone + foto grande) sem primeiro resolver o gap de imagens do modelo `Recipe` (ver `PRODUCT.md`) — o ícone de marca no lugar da foto é uma decisão deliberada, não um placeholder a substituir por uma foto assim que houver uma.
