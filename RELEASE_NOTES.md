# Tacho 2.1.0

Esta versão expande o fluxo completo entre receitas, despensa, planeamento e
compras, e inclui uma renovação visual responsiva.

## Principais novidades

- Calendário semanal com quatro períodos, vista vertical no telemóvel,
  fotografias, drag-and-drop, repetição, cópia de semanas e modelos.
- Sugestões semanais revistas antes de aplicar, considerando favoritos,
  classificação, histórico, despensa, validade e riscos alimentares.
- Pesquisa combinada por categorias, várias tags, ingrediente, classificação,
  tempo, favoritos e disponibilidade na despensa.
- Despensa detalhada com quantidades, unidades, validade e stock mínimo.
- Lista de compras consolidada, com soma de unidades compatíveis e exclusão do
  que já existe na despensa.
- Perfis alimentares, avisos de alergias/intolerâncias e filtro de receitas
  adequadas a todos.
- Catálogo de substituições de ingredientes, incluindo rácios, notas e estado
  de verificação.
- Histórico de confeções, notas por confeção e variantes de receitas.
- Autenticação OpenID Connect standard com Authorization Code + PKCE e
  associação explícita de contas.
- Nova identidade visual, navegação responsiva, imagens de demonstração e
  melhorias de acessibilidade.

## Atualização

Cria e verifica um backup da base de dados e das imagens antes de atualizar.
Depois define `TACHO_VERSION=2.1.0` e executa:

```bash
docker compose pull
docker compose up -d --wait
docker compose exec web alembic current
```

As migrações são aplicadas automaticamente pelo serviço `migrate`. Consulta
também `docs/upgrading.md` para instruções de rollback.
