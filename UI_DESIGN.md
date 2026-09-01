# UI e design atual do Tacho

Este documento descreve a interface existente do Tacho, a linguagem visual,
os padrões de interação e o comportamento responsivo. O objetivo é servir de
referência para que novas funcionalidades mantenham coerência com o produto.

## Identidade visual

O Tacho usa uma estética limpa, leve e contemporânea, associada a um livro de
receitas digital. A identidade é construída com branco, verde vivo,
superfícies arredondadas, fotografias de comida e ícones simples.

A interface evita um aspeto excessivamente técnico: os elementos têm bastante
espaço, sombras suaves e linguagem direta. O ícone do tacho é usado como
símbolo principal da marca e como fallback quando uma receita não tem imagem.

## Sistema visual

### Tipografia

A fonte principal é **Inter**, carregada localmente nos pesos `400`, `500`,
`600` e `700`. A hierarquia atual usa:

- peso 700 para títulos de página e títulos principais;
- peso 600 para títulos de cartões e secções;
- peso 500 para botões, navegação, chips e metadados importantes;
- peso 400 para texto corrente e informação secundária.

Os títulos principais usam normalmente `text-2xl` em dispositivos pequenos e
`text-3xl` a partir do breakpoint `sm`.

### Cores

Os tokens visuais estão definidos em `frontend/src/index.css`:

| Token | Tema claro | Utilização |
|---|---:|---|
| `bg-sage` | `#fafafa` | Fundo geral da aplicação |
| `bg-sage-deep-start` | `#43bf50` | Alias de compatibilidade da marca |
| `bg-sage-deep-end` | `#35a943` | Alias de compatibilidade da marca |
| `surface` | `#ffffff` | Cartões, menus e superfícies elevadas |
| `primary-forest` | `#43bf50` | Ações principais e estados ativos |
| `accent-leaf` | `#43bf50` | Favoritos, foco, sucesso e tags |
| `accent-orange` | `#e27732` | Tempo e alertas |
| `text-primary` | `#171a18` | Texto principal |
| `text-secondary` | `#69706c` | Texto auxiliar e elementos inativos |

O verde sólido é o principal elemento de identidade. Os gradientes deixaram de
ser usados nas áreas principais da interface.

### Tema escuro

Existem três opções: tema claro, escuro ou igual ao sistema operativo. A
preferência é guardada em `localStorage` com a chave `tacho:theme`.

No tema escuro mudam os fundos, superfícies e cores de texto. As cores de marca
mantêm-se, exceto o verde usado como texto, que recebe uma variante mais clara
para assegurar contraste. O tema do sistema é aplicado através de
`prefers-color-scheme`.

### Formas e profundidade

- Cartões principais usam cantos `rounded-2xl`.
- Áreas de destaque podem usar `rounded-3xl`.
- Botões, filtros, avatares e navegação usam formas circulares ou
  `rounded-full`.
- Campos de formulário usam normalmente `rounded-lg` ou `rounded-xl`.
- As sombras são suaves e esverdeadas, com maior elevação em menus flutuantes,
  autenticação e navegação móvel.
- Imagens de receitas usam proporções consistentes, geralmente `4:3` nos
  cartões e `16:9` no detalhe.

### Ícones

Os ícones são componentes SVG próprios, centralizados em
`frontend/src/components/icons.tsx`. São usados em conjunto com texto sempre
que existe espaço. Em ecrãs pequenos, algumas ações secundárias mostram apenas
o ícone e mantêm um `aria-label` descritivo.

## Estrutura das páginas

As páginas autenticadas usam `PageShell`, que fornece:

- cabeçalho global;
- conteúdo central com largura máxima `max-w-4xl`;
- margens horizontais responsivas;
- espaço inferior adicional no telemóvel para a navegação fixa;
- navegação inferior móvel.

Esta largura relativamente contida favorece leitura, formulários e utilização
em tablets, sem deixar os conteúdos excessivamente dispersos em monitores
largos.

## Navegação

### Desktop e tablet

O cabeçalho usa o verde sólido da marca e contém:

- logótipo e nome “Tacho” à esquerda;
- controlo do tema;
- menu do utilizador à direita.

A navegação principal vive numa sidebar clara e sticky, com acesso a receitas,
planeamento, lista de compras, coleções e despensa.

### Telemóvel

Em ecrãs pequenos, os destinos principais passam para uma barra fixa na parte
inferior:

- Receitas;
- Lista;
- Plano;
- Adicionar.

A barra é uma cápsula flutuante com fundo semitransparente, blur e sombra. O
destino ativo recebe fundo verde-floresta e texto branco. O cabeçalho móvel
mantém apenas a marca e o menu do utilizador.

### Menu do utilizador

O utilizador é representado por iniciais dentro de um avatar circular. O menu
abre como painel flutuante e agrupa:

- dados da sessão;
- edição inline de nome, email e password;
- gestão dos membros do agregado;
- seleção de tema;
- fim de sessão.

Os formulários de edição são revelados apenas quando necessários, reduzindo a
densidade inicial do menu.

## Página inicial e descoberta de receitas

A página inicial começa com uma saudação pessoal no telemóvel e uma área limpa
de pesquisa que contém:

- pesquisa textual com debounce;
- filtros rápidos para favoritos e receitas que podem ser feitas;
- chips de categorias e tags;
- ligação para as coleções.

As receitas são apresentadas numa coluna no telemóvel e em duas colunas a
partir de `sm`. Cada cartão inclui:

- fotografia ou ícone do Tacho como fallback;
- botão de favorito sobre a imagem;
- título;
- tempo total e número de porções;
- categorias e tags em chips.

Atualmente, categorias e tags distinguem-se apenas pela cor: verde-floresta
para categorias e verde-folha para tags. Ainda não possuem cores nem ícones
configuráveis individualmente.

O cartão aumenta ligeiramente a sombra e a imagem recebe zoom no hover. A ação
de favorito é independente da ligação que abre a receita.

## Detalhe da receita

O detalhe privilegia a fotografia e a leitura sequencial. Apresenta:

- imagem de capa em formato panorâmico;
- título, descrição e classificação por estrelas;
- ações de favorito, duplicação, impressão, partilha e edição;
- metadados como tempo, doses, custo e informação nutricional;
- ajuste de doses e quantidades;
- ingredientes e passos;
- acesso ao modo de cozinha;
- galeria, comentários e histórico relacionado.

Em ecrãs pequenos, o texto das ações secundárias é ocultado e os ícones
permanecem visíveis. A impressão possui estilos próprios: usa sempre cores
claras, remove a navegação e evita cortar ingredientes ou passos entre páginas.

## Formulários

Os formulários usam superfícies brancas ou adaptáveis ao tema, campos
arredondados e anel verde no foco. Os principais padrões são:

- labels visíveis e texto auxiliar em cor secundária;
- botões primários verdes com texto branco;
- botões secundários neutros;
- ações destrutivas assinaladas com laranja;
- estado desativado com opacidade reduzida;
- mensagens de erro ou sucesso junto da ação relevante;
- textos como “A guardar…” durante operações assíncronas.

## Planeamento atual

O planeamento já funciona por semanas, com navegação para a semana anterior e
seguinte. Contudo, a apresentação visual atual é uma **lista vertical de sete
cartões**, um por dia, e não uma grelha de calendário.

Cada dia contém duas áreas:

- almoço;
- jantar.

Uma receita é adicionada através de um `select` e pode ser removida no próprio
bloco. No desktop, almoço e jantar aparecem lado a lado; no telemóvel aparecem
empilhados. Uma futura vista de calendário deverá preservar a leitura móvel e
a simplicidade deste fluxo.

## Autenticação

Login e configuração inicial usam um layout isolado e centrado, sem a
navegação principal. A composição inclui:

- ícone da marca num quadrado arredondado com gradiente;
- título e subtítulo centralizados;
- formulário num cartão elevado com largura máxima pequena.

Este desenho mantém a entrada na aplicação simples e focada numa única tarefa.

## Estados e feedback

As páginas implementam estados básicos de:

- carregamento através de texto “A carregar…”;
- conteúdo vazio com explicação e, quando aplicável, ligação para a próxima
  ação;
- falha de ligação dentro de um cartão neutro;
- botões desativados e texto progressivo durante operações;
- confirmação antes de algumas ações destrutivas.

Ainda não existe um componente global unificado para notificações, skeletons,
diálogos ou mensagens de erro. Alguns fluxos usam `window.confirm` e
`window.alert`, enquanto outros apresentam feedback inline.

## Responsividade

A interface segue uma abordagem mobile-first e usa principalmente o breakpoint
`sm`:

- navegação inferior no telemóvel e navegação no cabeçalho em ecrãs maiores;
- uma coluna de receitas no telemóvel e duas em ecrãs maiores;
- textos de ações ocultados quando o espaço é reduzido;
- espaçamento e padding aumentados em ecrãs maiores;
- conteúdo limitado a `max-w-4xl`.

Não existe uma experiência desktop de alta densidade; o design mantém a mesma
estrutura geral e aumenta apenas o espaço e o número de colunas.

## Acessibilidade existente

- Contraste adaptado ao tema escuro.
- Estados de foco visíveis nos campos.
- `aria-label` em botões representados apenas por ícones.
- `aria-pressed` em favoritos, filtros e classificações.
- `aria-expanded` e `aria-haspopup` no menu do utilizador.
- Labels de navegação e agrupamentos semânticos.
- Respeito pela preferência de tema do sistema.

Ao criar novos componentes, não se deve depender apenas da cor para comunicar
um estado. Ícone, texto ou forma devem complementar qualquer distinção por cor.

## Princípios para novas funcionalidades

Uma nova área do Tacho deve:

- reutilizar os tokens definidos em `frontend/src/index.css`;
- manter o verde como cor primária e o laranja como acento pontual;
- usar Inter e a hierarquia tipográfica existente;
- privilegiar cartões, cápsulas e cantos arredondados;
- funcionar primeiro no telemóvel e adaptar-se a partir de `sm`;
- usar ícones existentes ou adicionar novos ícones com o mesmo traço visual;
- incluir estados de carregamento, vazio, erro, sucesso e desativado;
- funcionar nos temas claro e escuro;
- manter foco, labels e contraste acessíveis;
- evitar criar estilos isolados quando já existe um padrão equivalente.

## Ficheiros de referência

- `frontend/src/index.css`: tokens e regras globais do sistema visual.
- `frontend/src/theme.ts`: persistência e aplicação do tema.
- `frontend/src/components/PageShell.tsx`: estrutura das páginas.
- `frontend/src/components/Header.tsx`: cabeçalho e navegação desktop.
- `frontend/src/components/BottomNav.tsx`: navegação móvel.
- `frontend/src/components/RecipeCard.tsx`: cartão de receita.
- `frontend/src/components/icons.tsx`: biblioteca de ícones.
- `frontend/src/auth/AuthLayout.tsx`: layout de autenticação.
- `frontend/src/pages/Home.tsx`: pesquisa, filtros e grelha de receitas.
- `frontend/src/pages/RecipeDetail.tsx`: composição detalhada de conteúdo.
- `frontend/src/pages/MealPlan.tsx`: planeamento semanal atual.
