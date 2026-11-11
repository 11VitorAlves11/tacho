import { describe, expect, it } from 'vitest'

import { DEFAULT_RECIPE_FILTERS, clearRecipeFilters, hasActiveFilter, parseRecipeFilters, serializeRecipeFilters, type RecipeFilters } from './recipeFilters'

const CATEGORY = '0b6c8a4e-1f2d-4c3b-9a8e-7d6f5e4c3b2a'
const TAG_A = '11111111-2222-4333-8444-555555555555'
const TAG_B = '66666666-7777-4888-9999-aaaaaaaaaaaa'

describe('recipe filters in the URL', () => {
  it('keeps the URL empty when nothing is set', () => {
    expect(serializeRecipeFilters(DEFAULT_RECIPE_FILTERS).toString()).toBe('')
    expect(parseRecipeFilters(new URLSearchParams())).toEqual(DEFAULT_RECIPE_FILTERS)
  })

  it('round-trips every filter, the search text and the sort', () => {
    const filters: RecipeFilters = {
      q: 'bacalhau à brás', categoryId: CATEGORY, tagIds: [TAG_A, TAG_B], ingredient: 'ovo', ratingMin: 4, maxTotalMinutes: 30,
      favorite: true, makeable: true, pantrySuggestions: true, safeForAll: true, profileIds: [TAG_B], sort: 'least_recently_made',
    }
    const params = serializeRecipeFilters(filters)
    expect(params.get('sort')).toBe('least_recently_made')
    expect(params.get('favorite')).toBe('1')
    expect(parseRecipeFilters(new URLSearchParams(params.toString()))).toEqual(filters)
  })

  it('drops invalid numbers, enums and ids instead of sending them to the API', () => {
    const params = new URLSearchParams({ rating: '9', time: '45', sort: 'bogus', category: 'not-a-uuid', tags: `${TAG_A},x,${TAG_A}`, favorite: 'true' })
    expect(parseRecipeFilters(params)).toEqual({ ...DEFAULT_RECIPE_FILTERS, tagIds: [TAG_A] })
  })

  it('rejects fractional and empty numeric values', () => {
    expect(parseRecipeFilters(new URLSearchParams('rating=2.5&time=')).ratingMin).toBeNull()
    expect(parseRecipeFilters(new URLSearchParams('time=')).maxTotalMinutes).toBeNull()
  })

  it('does not write the default sort', () => {
    expect(serializeRecipeFilters({ ...DEFAULT_RECIPE_FILTERS, sort: 'title' }).has('sort')).toBe(false)
  })

  it('clears filters and sort but keeps the search text', () => {
    const filters = { ...DEFAULT_RECIPE_FILTERS, q: 'sopa', favorite: true, sort: 'rating' as const }
    expect(hasActiveFilter(filters)).toBe(true)
    const cleared = clearRecipeFilters(filters)
    expect(cleared).toEqual({ ...DEFAULT_RECIPE_FILTERS, q: 'sopa' })
    expect(hasActiveFilter(cleared)).toBe(false)
    expect(serializeRecipeFilters(cleared).toString()).toBe('q=sopa')
  })
})
