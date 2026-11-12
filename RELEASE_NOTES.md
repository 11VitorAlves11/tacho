# Tacho 2.2.1

Versão de manutenção com atualizações de segurança de dependências. Não há
alterações funcionais nem migrações novas em relação à 2.2.0.

## Alterações

- Atualiza o Mako (usado pelo Alembic nas migrações) para 1.4.3, que corrige
  uma vulnerabilidade conhecida.
- Atualiza as ferramentas de desenvolvimento do frontend (Vite 8.2.4, Vitest
  4.1.12 e source-map-js 1.2.2) para versões corrigidas. Estas ferramentas não
  fazem parte da aplicação servida em produção.

## Atualização

Cria e verifica um backup da base de dados e das imagens antes de atualizar.
Depois define `TACHO_VERSION=2.2.1` e executa:

```bash
docker compose pull
docker compose up -d --wait
docker compose exec web alembic current
```

Quem atualiza diretamente da 2.1.0 deve ler também as notas da 2.2.0 e
`docs/upgrading.md`.
