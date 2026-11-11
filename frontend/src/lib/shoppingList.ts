import type { ShoppingListItemSource } from '../api/types'

// Mostra no máximo `limit` receitas de origem; as restantes ficam num "+N".
export function visibleSources(sources: ShoppingListItemSource[], limit = 2) {
  return { shown: sources.slice(0, limit), hidden: Math.max(sources.length - limit, 0) }
}
