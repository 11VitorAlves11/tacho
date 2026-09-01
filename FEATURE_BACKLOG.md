# Backlog de funcionalidades

Este documento reúne propostas para a evolução do Tacho. As prioridades são
iniciais e podem ser revistas conforme o feedback dos utilizadores e as
dependências técnicas.

## Concluído nesta sessão

### Upgrade visual e navegação

- Atualizada a direção visual para uma interface branca e verde, com suporte
  a dark mode, foco visível e comportamento responsivo.
- Criado o layout desktop com header, sidebar e navegação dedicada.
- Redesenhada a navegação mobile com cápsula flutuante e botão central para
  adicionar receitas.
- Melhorados o header pessoal mobile, o menu do utilizador e os cartões de
  receitas.
- Atualizados login/registo, incluindo nome de utilizador, confirmação de
  password e mostrar/ocultar password.
- Corrigida a utilização do branding Tacho no favicon, manifest/PWA, header e
  sidebar, mantendo o símbolo isolado para os ícones da PWA.
- Renomeado o destino de planeamento para **Planeamento de Refeições**.
- Diferenciadas visualmente categorias e tags em filtros, cards, detalhe,
  partilha pública e formulário: categorias usam badges verdes estruturados;
  tags usam etiquetas laranja arredondadas com contorno tracejado e `#`.
- Extraídos `CategoryBadge` e `TagBadge` para componentes reutilizáveis,
  incluindo estados ativos acessíveis nos filtros.

### Dados de demonstração

- Criadas 10 receitas de teste com imagens fotográficas geradas para os cards.
- Adicionados ingredientes, passos, doses, tempos, categorias e tags para
  permitir testar os principais fluxos da aplicação.
- Criado o script idempotente
  `backend/scripts/seed_test_recipes.py`, que pode ser executado novamente sem
  duplicar os dados.
- Guardadas as imagens em `backend/test-data/recipe-images/`.

### Limpeza de assets

- Removida a pasta antiga e não referenciada `frontend/public/new icon/`.
- Mantidos apenas os assets canónicos necessários ao branding, favicon e PWA.

## Prioridade alta

### 1. Distinguir visualmente categorias e tags

Melhorar a identificação e leitura das categorias e tags em toda a aplicação.

- Permitir associar uma cor e um ícone a cada categoria.
- Apresentar categorias com ícone e cor nos cartões e detalhes das receitas.
- Apresentar tags com cores suaves, evitando excesso de ruído visual.
- Garantir contraste e acessibilidade em modo claro e escuro.
- Disponibilizar uma opção visual neutra quando não existir cor ou ícone.
- Manter a distinção conceptual: categorias representam grupos principais e
  tags representam características flexíveis.

### 2. Calendário semanal no planeamento

Substituir a apresentação em lista por um calendário semanal mais visual.

- Apresentar os dias da semana em colunas.
- Separar pequeno-almoço, almoço, lanche e jantar.
- Permitir navegar entre semanas e regressar rapidamente à semana atual.
- Adicionar, remover ou trocar receitas diretamente no calendário.
- Permitir arrastar refeições entre dias e períodos.
- Permitir repetir uma refeição noutro dia.
- Adaptar a grelha a dispositivos móveis.
- Gerar a lista de compras a partir da semana planeada.

### 3. Pesquisa e filtros avançados

Facilitar a descoberta de receitas dentro de bibliotecas maiores.

- Filtrar por categoria e por várias tags.
- Filtrar por ingredientes, favoritos e classificação.
- Filtrar por tempo de preparação e confeção.
- Combinar vários filtros simultaneamente.
- Permitir limpar todos os filtros rapidamente.
- Preservar os filtros ao abrir uma receita e regressar à pesquisa.

### 4. Lista de compras consolidada

Tornar a lista gerada pelo plano semanal mais útil no momento das compras.

- Agrupar ingredientes repetidos.
- Somar quantidades com unidades compatíveis.
- Manter separadas as quantidades que não possam ser convertidas com segurança.
- Excluir ou assinalar produtos já disponíveis na despensa.
- Permitir adicionar artigos manuais.
- Permitir marcar, desmarcar e remover artigos.
- Indicar quais receitas originaram cada artigo.

### 5. Receitas possíveis com a despensa atual

Ajudar a decidir o que cozinhar com os ingredientes disponíveis.

- Apresentar receitas que podem ser confecionadas com a despensa atual.
- Indicar os ingredientes que estão em falta.
- Ordenar pelo número ou importância dos ingredientes em falta.
- Permitir ignorar ingredientes básicos configuráveis.
- Criar uma lista de compras apenas com o que falta.

## Prioridade média

### 6. Autenticação standard por OIDC

- Permitir ligar o Tacho a um fornecedor OpenID Connect compatível com o standard.
- Configurar issuer/discovery URL, client ID, client secret, scopes e redirect URI por variáveis de ambiente.
- Validar `state`, `nonce`, assinatura, issuer e audience em todos os fluxos de autenticação.
- Suportar Authorization Code Flow com PKCE.
- Associar identidades OIDC a utilizadores existentes de forma explícita e segura, evitando tomadas de conta por coincidência de email.
- Permitir provisionamento opcional de novos utilizadores e associação controlada ao workspace.
- Manter o login local disponível ou permitir desativá-lo por configuração.
- Mostrar erros claros quando a conta estiver inativa, não autorizada ou sem acesso ao workspace.
- Documentar exemplos para fornecedores comuns, sem criar dependências específicas de um único fornecedor.
- Adicionar testes de login, callback, logout, renovação/expiração de sessão e cenários de segurança.

### 7. Inventário detalhado da despensa

- Registar quantidade e unidade de cada produto.
- Guardar data de validade opcional.
- Definir um nível mínimo de stock.
- Assinalar produtos a terminar ou próximos da validade.
- Permitir atualizar quantidades rapidamente.

### 8. Duplicação e variantes de receitas

- Duplicar uma receita sem alterar a original.
- Indicar opcionalmente a receita de origem.
- Usar a duplicação para criar adaptações pessoais ou alimentares.
- Copiar ingredientes, passos, imagens e metadados selecionados.

### 9. Histórico de confeções

- Registar quando uma receita foi preparada.
- Mostrar a última data de confeção.
- Consultar o histórico por receita e por período.
- Usar o histórico para evitar sugestões demasiado repetitivas.

### 10. Notas após cozinhar

- Adicionar notas associadas a uma confeção específica.
- Guardar observações sobre quantidades, tempos e resultado.
- Consultar notas anteriores durante o modo de cozinha.
- Permitir transformar uma nota numa alteração permanente da receita.

### 11. Planeamento recorrente e modelos

- Repetir refeições semanalmente ou em intervalos definidos.
- Copiar o plano da semana anterior.
- Guardar uma semana como modelo reutilizável.
- Aplicar um modelo sem eliminar refeições já planeadas sem confirmação.

### 12. Sugestão de plano semanal

- Sugerir receitas com base em favoritos e classificações.
- Considerar variedade e histórico recente.
- Considerar tempo disponível e produtos próximos da validade.
- Respeitar preferências e restrições alimentares.
- Apresentar a sugestão para revisão antes de alterar o plano.

### 13. Perfis e restrições alimentares

- Registar alergias, intolerâncias e preferências por membro do agregado.
- Assinalar receitas incompatíveis ou potencialmente incompatíveis.
- Filtrar receitas adequadas a todos ou a membros selecionados.
- Nunca ocultar silenciosamente um risco alimentar.

### 14. Substituições de ingredientes

- Registar alternativas para ingredientes comuns.
- Sugerir substitutos quando um ingrediente não existir na despensa.
- Apresentar ajustes de quantidade quando forem conhecidos.
- Distinguir sugestões verificadas de sugestões geradas automaticamente.

## Melhorias futuras

### 15. Dashboard semanal

- Mostrar as próximas refeições.
- Destacar produtos próximos da validade.
- Resumir os artigos pendentes na lista de compras.
- Apresentar sugestões rápidas de receitas.

### 16. Modo de cozinha avançado

- Manter o ecrã ligado durante a confeção.
- Suportar vários temporizadores em simultâneo.
- Melhorar a navegação sem toque e a acessibilidade.
- Avaliar comandos de voz como funcionalidade opcional.

### 17. Importação e exportação portável

- Exportar uma receita individual num formato documentado.
- Exportar todos os dados de um workspace.
- Importar dados exportados sem criar duplicados inesperados.
- Distinguir exportação funcional de backup integral da instalação.

### 18. Visibilidade das receitas

- Permitir receitas pessoais ou partilhadas com o workspace.
- Manter links públicos temporários com expiração e revogação.
- Apresentar claramente quem pode consultar cada receita.

## Sequência sugerida

1. Categorias e tags visuais.
2. Calendário semanal responsivo.
3. Pesquisa e filtros avançados.
4. Lista de compras consolidada e integrada com a despensa.
5. Inventário detalhado da despensa.
6. Receitas possíveis com os ingredientes disponíveis.
7. Histórico, notas e variantes de receitas.
8. Planeamento recorrente e sugestões automáticas.

Esta sequência reforça o fluxo principal do produto: descobrir receitas,
planear refeições, verificar a despensa, fazer compras e cozinhar.

## Critérios gerais

Todas as funcionalidades devem:

- Respeitar o isolamento de dados por workspace.
- Funcionar em computador e dispositivos móveis.
- Ser acessíveis em modo claro e escuro.
- Incluir estados de carregamento, vazio e erro.
- Evitar alterações destrutivas sem confirmação.
- Incluir testes adequados ao comportamento implementado.
- Incluir migrações Alembic quando alterarem o modelo de dados.
- Atualizar a documentação relevante.
