/** Índice do item a focar num menu após uma tecla de navegação; `null` quando a tecla não navega. */
export function nextMenuIndex(current: number, count: number, key: string): number | null {
  if (count === 0) return null
  if (key === 'ArrowDown') return current < 0 ? 0 : (current + 1) % count
  if (key === 'ArrowUp') return current < 0 ? count - 1 : (current - 1 + count) % count
  if (key === 'Home') return 0
  if (key === 'End') return count - 1
  return null
}
