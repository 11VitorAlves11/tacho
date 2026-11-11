import { describe, expect, it } from 'vitest'

import { visibleSources } from './shoppingList'

const source = (title: string) => ({ id: title, title })

describe('shopping list sources', () => {
  it('shows every source up to the limit', () => {
    expect(visibleSources([source('Bolo'), source('Sopa')])).toEqual({ shown: [source('Bolo'), source('Sopa')], hidden: 0 })
    expect(visibleSources([])).toEqual({ shown: [], hidden: 0 })
  })

  it('truncates the rest into a hidden count', () => {
    expect(visibleSources([source('A'), source('B'), source('C'), source('D')])).toEqual({ shown: [source('A'), source('B')], hidden: 2 })
  })
})
