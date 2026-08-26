import { describe, expect, it } from 'vitest'

import { formatQuantity, scaleQuantity } from './quantity'

describe('recipe quantities', () => {
  it('scales numeric quantities between serving sizes', () => {
    expect(scaleQuantity(2, 2, 4)).toBe(4)
  })

  it('formats common fractions for cooking', () => {
    expect(formatQuantity(0.5)).toBe('½')
  })
})
