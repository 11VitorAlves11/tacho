# TODO — tacho_app

Ponto de situação a 2026-08-07. Ver `PRD-app-receitas-v3.2.md`, `PRODUCT.md` e
`DESIGN.md` para o contexto completo de cada item.

> **Mudança importante desde a última revisão:** o Tandoor não tem receitas
> guardadas — **não há migração a fazer**. O script
> `backend/scripts/migrate_from_tandoor.py` ficou obsoleto e pode ser removido
> ou arquivado. Vários itens abaixo perderam a urgência que vinha de "corrigir
> antes da migração".

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

## Limpeza

- [ ] Remover/arquivar `backend/scripts/migrate_from_tandoor.py` e os fixtures
      de export sintético que o acompanham.

---

## v1.0 — fechar a fase

Critérios de aceitação completos no PRD, Secção 11.1. A v1.0 **só se considera
concluída** quando todos estes estiverem verificados.

- [x] Testar no browser o editor manual e o menu de utilizador (ver acima).
- [ ] **Armazenamento de imagens** — `Recipe` sem campo de imagem.
      Pré-requisito de tudo o que envolve fotos.
- [ ] **Upload de foto pela UI** — adicionar/substituir foto no formulário de
      criar/editar, com captura pela câmara no telemóvel (`capture`); foto
      visível no card da Home e no hero do Detalhe (hoje há placeholders).
- [ ] **Cabeçalhos de secção nos ingredientes** (`Ingredient.is_header: bool`) —
      padrão de Tandoor e Mealie; mantém-se como funcionalidade de produto,
      agora sem a urgência de migração.
- [ ] **Informação nutricional** — sem campos no modelo nem UI. É também o
      motivo de o `accent-orange` do `DESIGN.md` nunca aparecer.
      *(Se for adiado para v1.1, registar como decisão explícita no PRD, não
      deixar escorregar por omissão.)*
- [ ] **Deploy definitivo no homelab** — ver decisão #4. Inclui backup
      automático configurado **e um restauro testado com sucesso**, e desligar
      o Tandoor (CT 202).

---

## v1.1

- [ ] **Planeamento de refeições + Lista de compras** — nada construído.
      Desenhar primeiro no Figma (ainda não existem estes ecrãs).
      Referência de schema: `Food.supermarket_category` do Tandoor é um bom
      padrão para o agrupamento por corredor.
- [ ] **Mais destinos no bottom nav** — hoje só "Receitas"/"Adicionar" contra os
      4–5 que o design descreve; desbloqueia quando os ecrãs acima existirem.
- [ ] **Escalar porções no Detalhe** — sem mudanças no backend; padrão do
      Mealie (recalcular `quantity` em runtime a partir de `servings` desejado
      / original).
- [ ] **Pesquisa full-text** — hoje `ILIKE` sobre o título. Postgres `tsvector`
      é o caminho óbvio (é o que o Tandoor usa).
- [ ] **Parsing de ingredientes da importação** — a linha scraped fica inteira
      em `Ingredient.name`, sem separar quantidade/unidade. Desbloqueia o custo
      por porção e a pesquisa por ingredientes (v2).
- [ ] **Filtrar lixo nos passos importados** — alguns sites (ex.
      `mundodereceitasbimby.com.pt`) devolvem `"@type"`, `"position"` misturados
      com passos reais; sem filtro nenhum agora.
- [ ] **Importação inteligente via Gemini** — (a) fallback de extração quando o
      `recipe-scrapers` falha ou devolve resultado incompleto; (b) **importação
      por foto** (Vision): fotografar página de livro/receita manuscrita, com
      1–3 fotos, resultado sempre pré-preenchido no formulário para revisão —
      nunca gravação direta. Chave em `GEMINI_API_KEY`, funcionalidade opcional
      (sem chave, a app funciona na mesma).
      ⚠️ Validar cedo com fotos reais (livros PT, letra manuscrita) — risco de
      o LLM "corrigir" quantidades silenciosamente.
- [ ] **Timers por passo** no Modo Cozinha.
- [ ] **Tamanho de letra ajustável** no Modo Cozinha (toggle A/A⁺).
- [ ] **Notas pós-confeção** — ao concluir o Modo Cozinha, nota rápida opcional
      ("menos sal, +10 min de forno"), guardada com data e visível no Detalhe.
- [ ] **"Última vez feita"** — `last_made = now()` ao concluir o Modo Cozinha.
      Barato, e alimenta a métrica M3 do PRD.
- [ ] **Duplicar receita** — estava no âmbito original e caiu; repor.
- [ ] **Tempos separados** prep / cozedura / total (hoje só existe "tempo").
- [ ] **Favoritos** — o design tem "Favoritos" na navegação desde o início mas
      nunca foi especificado. Até haver contas, o favorito é do Workspace.
- [ ] **Dark mode** — variante escura dos tokens do `DESIGN.md`,
      `prefers-color-scheme` com override manual.
- [ ] **PWA instalável** — manifest + service worker básico.
- [ ] **Export schema.org Recipe (JSON-LD)** — o mesmo standard que os sites
      usam e que o `recipe-scrapers` lê; garante que qualquer app futura importa
      as receitas sem script dedicado.

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

- [ ] Cálculo automático de nutrição a partir dos ingredientes.
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