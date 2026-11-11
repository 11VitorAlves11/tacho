import { describe, expect, it } from 'vitest'

import { parseRecipeExport } from './recipeExport'

const valid = { format: 'tacho.recipe-export', version: 1, recipes: [{ title: 'Caldo verde' }] }

describe('recipe export files', () => {
  it('accepts a document produced by the export', () => {
    expect(parseRecipeExport(JSON.stringify(valid))).toEqual({ document: valid })
  })

  it('rejects text that is not JSON', () => {
    expect(parseRecipeExport('not json {')).toEqual({ error: 'invalid_json' })
  })

  it.each([
    ['[]'],
    ['null'],
    ['"tacho.recipe-export"'],
    [JSON.stringify({ ...valid, format: 'other' })],
    [JSON.stringify({ version: 1, recipes: [] })],
  ])('rejects documents of another format: %s', (text) => {
    expect(parseRecipeExport(text)).toEqual({ error: 'wrong_format' })
  })

  it('rejects other versions, including a version given as text', () => {
    expect(parseRecipeExport(JSON.stringify({ ...valid, version: 2 }))).toEqual({ error: 'unsupported_version' })
    expect(parseRecipeExport(JSON.stringify({ ...valid, version: '1' }))).toEqual({ error: 'unsupported_version' })
  })

  it('rejects files without recipes', () => {
    expect(parseRecipeExport(JSON.stringify({ ...valid, recipes: [] }))).toEqual({ error: 'no_recipes' })
    expect(parseRecipeExport(JSON.stringify({ ...valid, recipes: {} }))).toEqual({ error: 'no_recipes' })
  })

  it('rejects files above the per-request limit', () => {
    const recipes = Array.from({ length: 501 }, (_, index) => ({ title: `Receita ${index}` }))
    expect(parseRecipeExport(JSON.stringify({ ...valid, recipes }))).toEqual({ error: 'too_many' })
  })

  it('drops unknown top-level fields', () => {
    expect(parseRecipeExport(JSON.stringify({ ...valid, extra: true }))).toEqual({ document: valid })
  })
})
