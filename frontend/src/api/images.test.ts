import { describe, expect, it } from 'vitest'

import { api } from './client'
import { publicRecipeImageUrl } from './public'
import { recipeHeroSrcSet, recipeImageUrl, recipeThumbSrcSet } from './recipes'

const base = api.defaults.baseURL
const path = 'receitas/r1/foto.jpg'

describe('recipe image URLs', () => {
  it('serves the original when no size is requested', () => {
    expect(recipeImageUrl(path)).toBe(`${base}/media/${path}`)
  })

  it('requests a backend variant by size', () => {
    expect(recipeImageUrl(path, 'thumb')).toBe(`${base}/media/${path}?size=thumb`)
    expect(publicRecipeImageUrl('tok', 'medium')).toBe(`${base}/public/recipes/tok/image?size=medium`)
  })

  it('offers thumb and medium for grid images', () => {
    expect(recipeThumbSrcSet(path)).toBe(`${base}/media/${path}?size=thumb 480w, ${base}/media/${path}?size=medium 1200w`)
  })

  it('offers medium and the original for hero images', () => {
    expect(recipeHeroSrcSet('m.webp', 'o.jpg')).toBe('m.webp 1200w, o.jpg 2400w')
  })
})
