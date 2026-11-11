import { describe, expect, it } from 'vitest'

import { nextMenuIndex } from './menu'

describe('menu keyboard navigation', () => {
  it('moves with the arrow keys and wraps at both ends', () => {
    expect(nextMenuIndex(0, 3, 'ArrowDown')).toBe(1)
    expect(nextMenuIndex(2, 3, 'ArrowDown')).toBe(0)
    expect(nextMenuIndex(1, 3, 'ArrowUp')).toBe(0)
    expect(nextMenuIndex(0, 3, 'ArrowUp')).toBe(2)
  })

  it('starts from the first or last item when nothing is focused', () => {
    expect(nextMenuIndex(-1, 3, 'ArrowDown')).toBe(0)
    expect(nextMenuIndex(-1, 3, 'ArrowUp')).toBe(2)
  })

  it('jumps with Home and End', () => {
    expect(nextMenuIndex(1, 3, 'Home')).toBe(0)
    expect(nextMenuIndex(1, 3, 'End')).toBe(2)
  })

  it('ignores other keys and empty menus', () => {
    expect(nextMenuIndex(0, 3, 'a')).toBeNull()
    expect(nextMenuIndex(-1, 0, 'ArrowDown')).toBeNull()
  })
})
