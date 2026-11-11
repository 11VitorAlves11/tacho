import { t } from '../i18n'
import { useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigationType, useSearchParams } from 'react-router-dom'
import { exportWorkspaceRecipes, importWorkspaceRecipes, listCategories, listRecipes, listTags, toggleFavorite } from '../api/recipes'
import { listPantryItems } from '../api/pantry'
import { listMealPlan, listShoppingList } from '../api/planning'
import { listDietaryProfiles } from '../api/profiles'
import type { Category, DietaryProfile, MealPlanEntry, PantryItem, RecipeImportItem, RecipeImportResult, RecipeSort, RecipeSummary, ShoppingListItem, Tag } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { PageShell } from '../components/PageShell'
import { RecipeCard } from '../components/RecipeCard'
import { UserMenu } from '../components/UserMenu'
import { CartIcon, HeartIcon, SlidersIcon } from '../components/icons'
import { BottomSheet, Chip, EmptyState, ErrorState, Modal, SearchInput, Skeleton } from '../components/ui'
import { addDays, toDateKey } from '../lib/date'
import { MAX_IMPORTED_RECIPES, parseRecipeExport, type RecipeExportError } from '../lib/recipeExport'
import { RATING_OPTIONS, RECIPE_SORTS, clearRecipeFilters, hasActiveFilter, parseRecipeFilters, serializeRecipeFilters, type RecipeFilters } from '../lib/recipeFilters'

const SORT_LABELS: Record<RecipeSort, string> = {
  title: 'Título (A–Z)',
  newest: 'Mais recentes',
  updated: 'Atualizadas recentemente',
  rating: 'Melhor classificadas',
  least_recently_made: 'Há mais tempo sem cozinhar',
}

const KPI_TILE = 'min-w-0 rounded-2xl border border-border bg-surface p-3 transition hover:border-primary-forest sm:p-4'
const KPI_LABEL = 'line-clamp-2 min-h-[2lh] text-[10px] font-bold uppercase leading-tight tracking-wide text-text-secondary sm:line-clamp-1 sm:min-h-0 sm:text-xs'
const KPI_VALUE = 'mt-1 text-xl font-bold sm:mt-2 sm:text-2xl'
const KPI_DETAIL = 'mt-0.5 truncate text-xs text-text-secondary sm:mt-1 sm:text-sm'

export function Home() {
  const { user } = useAuth()
  const [recipes, setRecipes] = useState<RecipeSummary[] | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [tags, setTags] = useState<Tag[]>([])
  // Filtros vivem no estado local (inputs controlados não podem depender da
  // navegação, que o router faz em transição) e são espelhados no URL com
  // `replace`, para voltar de uma receita ou partilhar o link repor a vista.
  const [searchParams, setSearchParams] = useSearchParams()
  const location = useLocation()
  const navigationType = useNavigationType()
  const [filters, setFilters] = useState<RecipeFilters>(() => parseRecipeFilters(searchParams))
  const [locationKey, setLocationKey] = useState(location.key)
  const [dietaryProfiles, setDietaryProfiles] = useState<DietaryProfile[]>([])
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [error, setError] = useState(false)
  const [upcomingMeals, setUpcomingMeals] = useState<MealPlanEntry[]>([])
  const [pantryItems, setPantryItems] = useState<PantryItem[]>([])
  const [shoppingItems, setShoppingItems] = useState<ShoppingListItem[]>([])
  const [reloadKey, setReloadKey] = useState(0)
  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<RecipeImportResult | null>(null)
  const [importError, setImportError] = useState<string | null>(null)
  const importInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    listCategories().then(setCategories).catch(() => {})
    listTags().then(setTags).catch(() => {})
    listDietaryProfiles().then(setDietaryProfiles).catch(() => {})
    const today = new Date()
    listMealPlan(toDateKey(today), toDateKey(addDays(today, 6))).then(setUpcomingMeals).catch(() => {})
    listPantryItems().then(setPantryItems).catch(() => {})
    listShoppingList().then(setShoppingItems).catch(() => {})
  }, [])

  // Uma navegação nova para `/` (logótipo, barra inferior) traz o seu próprio
  // URL; as nossas escritas são sempre REPLACE e não devem repor o estado.
  if (location.key !== locationKey) {
    setLocationKey(location.key)
    if (navigationType !== 'REPLACE') setFilters(parseRecipeFilters(searchParams))
  }

  useEffect(() => {
    const next = serializeRecipeFilters(filters)
    if (next.toString() !== searchParams.toString()) setSearchParams(next, { replace: true })
  }, [filters, searchParams, setSearchParams])

  useEffect(() => {
    const { q, categoryId, tagIds, ingredient, ratingMin, maxTotalMinutes, favorite, makeable, pantrySuggestions, safeForAll, profileIds, sort } = filters
    const handle = setTimeout(() => {
      setError(false)
      listRecipes({ q: q || undefined, categoryId: categoryId ?? undefined, tagIds: tagIds.length ? tagIds : undefined, ingredient: ingredient || undefined, ratingMin: ratingMin ?? undefined, maxTotalMinutes: maxTotalMinutes ?? undefined, favorite: favorite || undefined, makeable: makeable || undefined, pantrySuggestions: pantrySuggestions || undefined, safeForAll: safeForAll || profileIds.length > 0 || undefined, profileIds: profileIds.length ? profileIds : undefined, sort })
        .then(setRecipes).catch(() => setError(true))
    }, 250)
    return () => clearTimeout(handle)
  }, [filters, reloadKey])

  function updateFilters(patch: Partial<RecipeFilters>) {
    setFilters((current) => ({ ...current, ...patch }))
  }

  async function handleToggleFavorite(id: string) {
    const updated = await toggleFavorite(id)
    setRecipes((previous) => {
      if (!previous) return previous
      if (filters.favorite && !updated.is_favorite) return previous.filter((recipe) => recipe.id !== id)
      return previous.map((recipe) => recipe.id === id ? { ...recipe, is_favorite: updated.is_favorite } : recipe)
    })
  }

  async function handleExport() {
    const payload = await exportWorkspaceRecipes()
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `tacho-receitas-${toDateKey(new Date())}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  async function handleImportFile(file: File) {
    setImportError(null)
    setImportResult(null)
    const parsed = parseRecipeExport(await file.text())
    if ('error' in parsed) {
      setImportError(importErrorMessage(parsed.error))
      return
    }
    setImporting(true)
    try {
      setImportResult(await importWorkspaceRecipes(parsed.document))
      listCategories().then(setCategories).catch(() => {})
      listTags().then(setTags).catch(() => {})
      setReloadKey((key) => key + 1)
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      setImportError(typeof detail === 'string' ? detail : t('Não foi possível importar o ficheiro. Verifica a ligação e tenta de novo.'))
    } finally {
      setImporting(false)
    }
  }

  function selectCategory(id: string) {
    setFilters((current) => ({ ...current, categoryId: current.categoryId === id ? null : id }))
  }

  function selectTag(id: string) {
    setFilters((current) => ({ ...current, tagIds: current.tagIds.includes(id) ? current.tagIds.filter((tagId) => tagId !== id) : [...current.tagIds, id] }))
  }

  function toggleProfile(id: string) {
    setFilters((current) => ({ ...current, profileIds: current.profileIds.includes(id) ? current.profileIds.filter((profileId) => profileId !== id) : [...current.profileIds, id] }))
  }

  function toggleFlag(key: 'favorite' | 'makeable' | 'pantrySuggestions' | 'safeForAll') {
    setFilters((current) => ({ ...current, [key]: !current[key] }))
  }

  function clearFilters() {
    setFilters(clearRecipeFilters)
  }

  const firstName = user?.name?.trim().split(/\s+/)[0] ?? user?.email.split('@')[0] ?? ''
  const { categoryId, tagIds, ingredient, ratingMin, maxTotalMinutes, favorite: favoriteOnly, makeable: makeableOnly, pantrySuggestions, safeForAll, profileIds: selectedProfileIds, sort } = filters
  const hasFilter = hasActiveFilter(filters)
  const allFilters = <>
    <Chip active={favoriteOnly} onClick={() => toggleFlag('favorite')}><HeartIcon className="size-4" fill={favoriteOnly ? 'currentColor' : 'none'} /> {t('Favoritos')}</Chip>
    <Chip active={makeableOnly} onClick={() => toggleFlag('makeable')}><CartIcon className="size-4" /> {t('Dá para fazer')}</Chip>
    <Chip active={pantrySuggestions} onClick={() => toggleFlag('pantrySuggestions')}><CartIcon className="size-4" /> {t('Mais próximas')}</Chip>
    <Chip active={safeForAll} onClick={() => toggleFlag('safeForAll')}>{t('Adequadas a todos')}</Chip>
    {dietaryProfiles.map((profile) => <Chip key={profile.id} active={selectedProfileIds.includes(profile.id)} onClick={() => toggleProfile(profile.id)}>{t('Seguro:')} {profile.name}</Chip>)}
    {categories.map((category) => <Chip key={category.id} kind="category" accentColor={category.color} icon={category.icon} active={categoryId === category.id} onClick={() => selectCategory(category.id)}>{category.name}</Chip>)}
    {tags.map((tag) => <Chip key={tag.id} kind="tag" active={tagIds.includes(tag.id)} onClick={() => selectTag(tag.id)}>#{tag.name}</Chip>)}
  </>
  const expiringItems = pantryItems.filter((item) => {
    if (!item.has_it || !item.expires_on) return false
    const days = Math.ceil((new Date(`${item.expires_on}T00:00:00`).getTime() - new Date().setHours(0, 0, 0, 0)) / 86400000)
    return days <= 7
  })
  const pendingShopping = shoppingItems.filter((item) => !item.is_checked)

  return <PageShell wide>
    <header className="mb-6 flex items-start justify-between gap-4 lg:hidden">
      <div><h1 className="text-2xl font-bold tracking-tight text-text-primary">{t('Olá,')} {firstName} <span aria-hidden>👋</span></h1><p className="mt-1 text-sm text-text-secondary">{t('O que vais cozinhar hoje?')}</p></div>
      <UserMenu variant="mobile" />
    </header>

    <section className="mb-5 grid grid-cols-3 gap-2 sm:mb-6 sm:gap-3" aria-label={t('Resumo semanal')}>
      <Link to="/planeamento" className={KPI_TILE}><p className={KPI_LABEL}>{t('Próximas refeições')}</p><p className={`${KPI_VALUE} text-text-primary`}>{upcomingMeals.length}</p><p className={KPI_DETAIL}>{upcomingMeals[0]?.recipe.title ?? t('Completar o planeamento →')}</p></Link>
      <Link to="/despensa" className={KPI_TILE}><p className={KPI_LABEL}>{t('Validade próxima')}</p><p className={`${KPI_VALUE} ${expiringItems.length ? 'text-accent-orange' : 'text-text-primary'}`}>{expiringItems.length}</p><p className={KPI_DETAIL}>{expiringItems[0]?.name ?? t('Nenhum produto nos próximos 7 dias')}</p></Link>
      <Link to="/lista-compras" className={KPI_TILE}><p className={KPI_LABEL}>{t('Por comprar')}</p><p className={`${KPI_VALUE} text-text-primary`}>{pendingShopping.length}</p><p className={KPI_DETAIL}>{t('artigos pendentes')}</p></Link>
    </section>

    <div className="flex min-w-0 items-center gap-2 sm:gap-3">
      <SearchInput value={filters.q} onChange={(event) => updateFilters({ q: event.target.value })} placeholder={t('Procurar receitas…')} className="min-w-0 flex-1" />
      <button type="button" onClick={() => setFiltersOpen(true)} aria-label={t('Abrir filtros')} className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary-forest text-white lg:hidden"><SlidersIcon className="size-5" /></button>
    </div>

    <section className="mt-6 hidden sm:block">
      <div className="mb-3 flex items-center justify-between"><h2 className="text-sm font-bold text-text-primary sm:text-base">{t('Filtros rápidos')}</h2>{hasFilter && <button onClick={clearFilters} className="text-xs font-semibold text-forest-text">{t('Limpar')}</button>}</div>
      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0 lg:flex-wrap">
        <Chip active={favoriteOnly} onClick={() => toggleFlag('favorite')}><HeartIcon className="size-4" fill={favoriteOnly ? 'currentColor' : 'none'} /> {t('Favoritos')}</Chip>
        <Chip active={makeableOnly} onClick={() => toggleFlag('makeable')}><CartIcon className="size-4" /> {t('Dá para fazer')}</Chip>
        <Chip active={pantrySuggestions} onClick={() => toggleFlag('pantrySuggestions')}><CartIcon className="size-4" /> {t('Mais próximas')}</Chip>
        <Chip active={safeForAll} onClick={() => toggleFlag('safeForAll')}>{t('Adequadas a todos')}</Chip>
        {dietaryProfiles.map((profile) => <Chip key={profile.id} active={selectedProfileIds.includes(profile.id)} onClick={() => toggleProfile(profile.id)}>{t('Seguro:')} {profile.name}</Chip>)}
        {categories.slice(0, 3).map((category) => <Chip key={category.id} kind="category" accentColor={category.color} icon={category.icon} active={categoryId === category.id} onClick={() => selectCategory(category.id)}>{category.name}</Chip>)}
        <Chip onClick={() => setFiltersOpen(true)} className="lg:hidden"><SlidersIcon className="size-4" /> {t('Mais')}</Chip>
        <span className="hidden contents lg:contents">{categories.slice(3).map((category) => <Chip key={category.id} kind="category" accentColor={category.color} icon={category.icon} active={categoryId === category.id} onClick={() => selectCategory(category.id)}>{category.name}</Chip>)}{tags.map((tag) => <Chip key={tag.id} kind="tag" active={tagIds.includes(tag.id)} onClick={() => selectTag(tag.id)}>#{tag.name}</Chip>)}</span>
      </div>
      <div className="mt-3 hidden grid-cols-4 gap-3 lg:grid">
        <label className="text-xs font-semibold text-text-secondary">{t('Ingrediente')}<input value={ingredient} onChange={(event) => updateFilters({ ingredient: event.target.value })} placeholder={t('ex.: tomate')} className="mt-1 min-h-10 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-primary-forest" /></label>
        <label className="text-xs font-semibold text-text-secondary">{t('Classificação mínima')}<select value={ratingMin ?? ''} onChange={(event) => updateFilters({ ratingMin: event.target.value ? Number(event.target.value) : null })} className="mt-1 min-h-10 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary"><option value="">{t('Qualquer')}</option>{RATING_OPTIONS.map((rating) => <option key={rating} value={rating}>{rating}{t('+ estrelas')}</option>)}</select></label>
        <label className="text-xs font-semibold text-text-secondary">{t('Tempo máximo')}<select value={maxTotalMinutes ?? ''} onChange={(event) => updateFilters({ maxTotalMinutes: event.target.value ? Number(event.target.value) : null })} className="mt-1 min-h-10 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary"><option value="">{t('Qualquer')}</option><option value="15">{t('15 minutos')}</option><option value="30">{t('30 minutos')}</option><option value="60">{t('1 hora')}</option><option value="120">{t('2 horas')}</option></select></label>
        <label className="text-xs font-semibold text-text-secondary">{t('Ordenar por')}<select value={sort} onChange={(event) => updateFilters({ sort: event.target.value as RecipeSort })} className="mt-1 min-h-10 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary">{RECIPE_SORTS.map((value) => <option key={value} value={value}>{t(SORT_LABELS[value])}</option>)}</select></label>
      </div>
    </section>

    <section className="mt-8">
      <div className="mb-4 flex items-end justify-between gap-3"><div><h2 className="text-xl font-bold tracking-tight text-text-primary lg:text-2xl">{t('Receitas')}</h2>{recipes && <p className="mt-0.5 text-sm text-text-secondary">{recipes.length} {recipes.length === 1 ? t('receita') : t('receitas')}</p>}</div><div className="flex items-center gap-3"><button type="button" onClick={() => void handleExport()} className="text-sm font-semibold text-forest-text">{t('Exportar')}</button><button type="button" disabled={importing} onClick={() => importInput.current?.click()} className="text-sm font-semibold text-forest-text disabled:opacity-50">{importing ? t('A importar…') : t('Importar')}</button><input ref={importInput} type="file" accept="application/json,.json" className="hidden" onChange={(event) => { const file = event.target.files?.[0]; event.target.value = ''; if (file) void handleImportFile(file) }} /><Link to="/colecoes" className="text-sm font-semibold text-forest-text">{t('Ver coleções')} <span aria-hidden>›</span></Link></div></div>
      {error && <ErrorState>{t('Não foi possível ligar ao backend. Confirma se está a correr em')} {import.meta.env.VITE_API_URL}.</ErrorState>}
      {!error && recipes === null && <RecipeGridSkeleton />}
      {!error && recipes !== null && recipes.length === 0 && <EmptyState title={favoriteOnly ? t('Ainda não marcaste receitas favoritas.') : makeableOnly ? t('Nenhuma receita corresponde à despensa.') : t('Ainda não há receitas por aqui.')} description={t('Ajusta os filtros ou adiciona uma nova receita ao teu livro.')} action={<Link to="/adicionar" className="font-semibold text-forest-text">{t('Adicionar receita')}</Link>} />}
      {recipes && recipes.length > 0 && <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">{recipes.map((recipe) => <RecipeCard key={recipe.id} recipe={recipe} onToggleFavorite={handleToggleFavorite} />)}</div>}
    </section>
    <Modal open={Boolean(importResult || importError)} title={importError ? t('Importação falhou') : t('Importação concluída')} onClose={() => { setImportResult(null); setImportError(null) }}>{importError ? <p className="text-sm leading-relaxed text-text-secondary">{importError}</p> : importResult && <ImportSummary result={importResult} />}</Modal>
    <BottomSheet open={filtersOpen} title={t('Filtrar receitas')} onClose={() => setFiltersOpen(false)}><div className="flex flex-wrap gap-2">{allFilters}</div><div className="mt-5 space-y-3"><label className="block text-xs font-semibold text-text-secondary">{t('Ingrediente')}<input value={ingredient} onChange={(event) => updateFilters({ ingredient: event.target.value })} placeholder={t('ex.: tomate')} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-primary-forest" /></label><label className="block text-xs font-semibold text-text-secondary">{t('Classificação mínima')}<select value={ratingMin ?? ''} onChange={(event) => updateFilters({ ratingMin: event.target.value ? Number(event.target.value) : null })} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary"><option value="">{t('Qualquer')}</option>{RATING_OPTIONS.map((rating) => <option key={rating} value={rating}>{rating}{t('+ estrelas')}</option>)}</select></label><label className="block text-xs font-semibold text-text-secondary">{t('Tempo máximo')}<select value={maxTotalMinutes ?? ''} onChange={(event) => updateFilters({ maxTotalMinutes: event.target.value ? Number(event.target.value) : null })} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary"><option value="">{t('Qualquer')}</option><option value="15">{t('15 minutos')}</option><option value="30">{t('30 minutos')}</option><option value="60">{t('1 hora')}</option><option value="120">{t('2 horas')}</option></select></label><label className="block text-xs font-semibold text-text-secondary">{t('Ordenar por')}<select value={sort} onChange={(event) => updateFilters({ sort: event.target.value as RecipeSort })} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary">{RECIPE_SORTS.map((value) => <option key={value} value={value}>{t(SORT_LABELS[value])}</option>)}</select></label>{hasFilter && <button onClick={clearFilters} className="min-h-11 w-full rounded-xl border border-border text-sm font-semibold text-forest-text">{t('Limpar todos os filtros')}</button>}</div></BottomSheet>
  </PageShell>
}

function importErrorMessage(error: RecipeExportError) {
  if (error === 'invalid_json') return t('O ficheiro não é JSON válido.')
  if (error === 'unsupported_version') return t('Versão do ficheiro de exportação não suportada.')
  if (error === 'no_recipes') return t('O ficheiro não tem receitas para importar.')
  if (error === 'too_many') return t('Demasiadas receitas num só ficheiro (máx. {max}).', { max: MAX_IMPORTED_RECIPES })
  return t('O ficheiro não é uma exportação de receitas do Tacho.')
}

function importReason(item: RecipeImportItem) {
  if (item.reason === 'duplicate') return t('já existe no livro de receitas')
  if (item.reason === 'duplicate_in_file') return t('repetida no ficheiro')
  return item.detail ? `${t('entrada inválida')} (${item.detail})` : t('entrada inválida')
}

function ImportSummary({ result }: { result: RecipeImportResult }) {
  const skipped = result.items.filter((item) => item.status === 'skipped')
  return <div className="space-y-3 text-sm text-text-secondary">
    <p className="text-text-primary"><strong>{result.imported}</strong> {t('importadas')} · <strong>{result.skipped}</strong> {t('ignoradas')}</p>
    {(result.created_categories.length > 0 || result.created_tags.length > 0) && <p>{t('Criadas:')} {[...result.created_categories, ...result.created_tags.map((name) => `#${name}`)].join(', ')}</p>}
    {result.images_not_imported > 0 && <p>{t('As fotografias não fazem parte da exportação — {count} receitas importadas ficaram sem foto.', { count: result.images_not_imported })}</p>}
    {skipped.length > 0 && <ul className="max-h-60 space-y-1 overflow-y-auto">{skipped.map((item, index) => <li key={index}><span className="font-medium text-text-primary">{item.title}</span> — {importReason(item)}</li>)}</ul>}
  </div>
}

function RecipeGridSkeleton() {
  return <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">{Array.from({ length: 6 }, (_, index) => <div key={index} className="overflow-hidden rounded-2xl border border-border bg-surface"><Skeleton className="aspect-[4/3] rounded-none" /><div className="space-y-3 p-4"><Skeleton className="h-5 w-3/4" /><Skeleton className="h-4 w-1/2" /></div></div>)}</div>
}
