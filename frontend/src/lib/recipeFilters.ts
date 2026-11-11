import type { RecipeSort } from '../api/types'

export const RECIPE_SORTS: readonly RecipeSort[] = ['title', 'newest', 'updated', 'rating', 'least_recently_made']
export const RATING_OPTIONS = [1, 2, 3, 4, 5] as const
export const MAX_TIME_OPTIONS = [15, 30, 60, 120] as const

export interface RecipeFilters {
  q: string
  categoryId: string | null
  tagIds: string[]
  ingredient: string
  ratingMin: number | null
  maxTotalMinutes: number | null
  favorite: boolean
  makeable: boolean
  pantrySuggestions: boolean
  safeForAll: boolean
  profileIds: string[]
  sort: RecipeSort
}

export const DEFAULT_RECIPE_FILTERS: RecipeFilters = {
  q: '', categoryId: null, tagIds: [], ingredient: '', ratingMin: null, maxTotalMinutes: null,
  favorite: false, makeable: false, pantrySuggestions: false, safeForAll: false, profileIds: [], sort: 'title',
}

// Ids vindos do URL vão direto para a API, que responde 422 a um uuid inválido — descartamos já aqui.
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

function parseId(value: string | null): string | null {
  return value && UUID_PATTERN.test(value) ? value : null
}

function parseIdList(value: string | null): string[] {
  return [...new Set((value ?? '').split(',').filter((id) => UUID_PATTERN.test(id)))]
}

function parseOption(value: string | null, options: readonly number[]): number | null {
  const parsed = Number(value)
  return value && options.includes(parsed) ? parsed : null
}

function parseFlag(value: string | null): boolean {
  return value === '1'
}

export function parseRecipeFilters(params: URLSearchParams): RecipeFilters {
  const sort = params.get('sort')
  return {
    q: params.get('q') ?? '',
    categoryId: parseId(params.get('category')),
    tagIds: parseIdList(params.get('tags')),
    ingredient: params.get('ingredient') ?? '',
    ratingMin: parseOption(params.get('rating'), RATING_OPTIONS),
    maxTotalMinutes: parseOption(params.get('time'), MAX_TIME_OPTIONS),
    favorite: parseFlag(params.get('favorite')),
    makeable: parseFlag(params.get('makeable')),
    pantrySuggestions: parseFlag(params.get('pantry')),
    safeForAll: parseFlag(params.get('safe')),
    profileIds: parseIdList(params.get('profiles')),
    sort: RECIPE_SORTS.find((value) => value === sort) ?? DEFAULT_RECIPE_FILTERS.sort,
  }
}

/** Só escreve o que difere do valor por omissão, para a página sem filtros ficar em `/` limpo. */
export function serializeRecipeFilters(filters: RecipeFilters): URLSearchParams {
  const params = new URLSearchParams()
  if (filters.q) params.set('q', filters.q)
  if (filters.categoryId) params.set('category', filters.categoryId)
  if (filters.tagIds.length) params.set('tags', filters.tagIds.join(','))
  if (filters.ingredient) params.set('ingredient', filters.ingredient)
  if (filters.ratingMin !== null) params.set('rating', String(filters.ratingMin))
  if (filters.maxTotalMinutes !== null) params.set('time', String(filters.maxTotalMinutes))
  if (filters.favorite) params.set('favorite', '1')
  if (filters.makeable) params.set('makeable', '1')
  if (filters.pantrySuggestions) params.set('pantry', '1')
  if (filters.safeForAll) params.set('safe', '1')
  if (filters.profileIds.length) params.set('profiles', filters.profileIds.join(','))
  if (filters.sort !== DEFAULT_RECIPE_FILTERS.sort) params.set('sort', filters.sort)
  return params
}

/** Mostra o "Limpar": tudo menos a pesquisa por texto, que tem a sua própria caixa. */
export function hasActiveFilter(filters: RecipeFilters): boolean {
  return Boolean(filters.categoryId || filters.tagIds.length || filters.ingredient || filters.ratingMin || filters.maxTotalMinutes || filters.favorite || filters.makeable || filters.pantrySuggestions || filters.safeForAll || filters.profileIds.length || filters.sort !== DEFAULT_RECIPE_FILTERS.sort)
}

/** Repõe os valores por omissão mas mantém o texto pesquisado, como antes de os filtros irem para o URL. */
export function clearRecipeFilters(filters: RecipeFilters): RecipeFilters {
  return { ...DEFAULT_RECIPE_FILTERS, q: filters.q }
}
