# Tacho 2.2.0

Esta versão acrescenta preços e leitura de talões na despensa, exportação e
importação de receitas, proteção do login e um polimento geral da interface,
sobretudo no telemóvel.

## Principais novidades

- Despensa com histórico de preços e gráficos de despesa; os preços podem ser
  lidos da fotografia de um talão (requer `GEMINI_API_KEY`) e são revistos
  antes de guardar.
- Datas localizadas e validade relativa na despensa ("Expira em 3 dias"),
  linhas mais compactas e formulário de adição acima da lista.
- Lista de compras que mostra as receitas de origem de cada item, permite
  limpar os itens já comprados e deixa de duplicar ingredientes com nomes
  equivalentes.
- Exportação das receitas do espaço de trabalho num JSON versionado e
  importação desses ficheiros sem duplicados inesperados.
- Ordenação da lista de receitas, com filtros e ordenação guardados no URL.
- Modo cozinha com navegação mãos-livres, leitura em voz alta e vários
  temporizadores em simultâneo.
- Perfis alimentares associados a membros do agregado.
- Definição de idioma da interface.
- Página inicial, detalhe e formulário de receita, planeamento semanal e
  coleções revistos para ecrãs pequenos; as coleções mostram uma colagem das
  capas das receitas.

## Segurança

- Tentativas falhadas de login e de configuração inicial são limitadas por IP
  e por email (`LOGIN_RATE_LIMIT_WINDOW_SECONDS`, `LOGIN_MAX_FAILURES_PER_IP`,
  `LOGIN_MAX_FAILURES_PER_EMAIL`). Atrás de um reverse proxy, define
  `FORWARDED_ALLOW_IPS` para que o IP real do cliente seja usado.
- A importação por URL passa por um cliente que rejeita endereços locais e
  privados, tem limites de tempo e deixa de expor erros internos do worker.
- Os uploads de imagens são validados e as imagens demasiado grandes são
  rejeitadas.
- Novo comando de operador para repor a password ou reativar contas locais.

## Desempenho

- As fotografias passam a ter variantes WebP (miniatura e média), servidas com
  `srcset` e cache de longa duração. As variantes das fotografias antigas são
  criadas na primeira visualização; `docs/upgrading.md` explica como gerá-las
  todas de uma vez.

## Atualização

Cria e verifica um backup da base de dados e das imagens antes de atualizar.
Depois define `TACHO_VERSION=2.2.0` e executa:

```bash
docker compose pull
docker compose up -d --wait
docker compose exec web alembic current
```

As migrações são aplicadas automaticamente pelo serviço `migrate`. Esta versão
acrescenta apenas tabelas novas (preços da despensa e origens dos itens da
lista de compras); os dados existentes não são alterados. Consulta também
`docs/upgrading.md` para instruções de rollback.
