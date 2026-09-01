import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listCategories, listRecipes, listTags, toggleFavorite } from '../api/recipes'
import { listPantryItems } from '../api/pantry'
import { listMealPlan, listShoppingList } from '../api/planning'
import type { Category, MealPlanEntry, PantryItem, RecipeSummary, ShoppingListItem, Tag } from '../api/types'
import { useAuth } from '../auth/useAuth'
import { PageShell } from '../components/PageShell'
import { RecipeCard } from '../components/RecipeCard'
import { UserMenu } from '../components/UserMenu'
import { CartIcon, HeartIcon, SlidersIcon } from '../components/icons'
import { BottomSheet, Chip, EmptyState, ErrorState, SearchInput, Skeleton } from '../components/ui'
import { addDays, toDateKey } from '../lib/date'

export function Home() {
  const { user } = useAuth()
  const [recipes, setRecipes] = useState<RecipeSummary[] | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [tags, setTags] = useState<Tag[]>([])
  const [q, setQ] = useState('')
  const [categoryId, setCategoryId] = useState<string | null>(null)
  const [tagIds, setTagIds] = useState<string[]>([])
  const [ingredient, setIngredient] = useState('')
  const [ratingMin, setRatingMin] = useState<number | null>(null)
  const [maxTotalMinutes, setMaxTotalMinutes] = useState<number | null>(null)
  const [favoriteOnly, setFavoriteOnly] = useState(false)
  const [makeableOnly, setMakeableOnly] = useState(false)
  const [pantrySuggestions, setPantrySuggestions] = useState(false)
  const [safeForAll, setSafeForAll] = useState(false)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const [error, setError] = useState(false)
  const [upcomingMeals, setUpcomingMeals] = useState<MealPlanEntry[]>([])
  const [pantryItems, setPantryItems] = useState<PantryItem[]>([])
  const [shoppingItems, setShoppingItems] = useState<ShoppingListItem[]>([])

  useEffect(() => {
    listCategories().then(setCategories).catch(() => {})
    listTags().then(setTags).catch(() => {})
    const today = new Date()
    listMealPlan(toDateKey(today), toDateKey(addDays(today, 6))).then(setUpcomingMeals).catch(() => {})
    listPantryItems().then(setPantryItems).catch(() => {})
    listShoppingList().then(setShoppingItems).catch(() => {})
  }, [])

  useEffect(() => {
    const handle = setTimeout(() => {
      setError(false)
      listRecipes({ q: q || undefined, categoryId: categoryId ?? undefined, tagIds: tagIds.length ? tagIds : undefined, ingredient: ingredient || undefined, ratingMin: ratingMin ?? undefined, maxTotalMinutes: maxTotalMinutes ?? undefined, favorite: favoriteOnly || undefined, makeable: makeableOnly || undefined, pantrySuggestions: pantrySuggestions || undefined, safeForAll: safeForAll || undefined })
        .then(setRecipes).catch(() => setError(true))
    }, 250)
    return () => clearTimeout(handle)
  }, [q, categoryId, tagIds, ingredient, ratingMin, maxTotalMinutes, favoriteOnly, makeableOnly, pantrySuggestions, safeForAll])

  async function handleToggleFavorite(id: string) {
    const updated = await toggleFavorite(id)
    setRecipes((previous) => {
      if (!previous) return previous
      if (favoriteOnly && !updated.is_favorite) return previous.filter((recipe) => recipe.id !== id)
      return previous.map((recipe) => recipe.id === id ? { ...recipe, is_favorite: updated.is_favorite } : recipe)
    })
  }

  function selectCategory(id: string) {
    setCategoryId(categoryId === id ? null : id)
  }

  function selectTag(id: string) {
    setTagIds((current) => current.includes(id) ? current.filter((tagId) => tagId !== id) : [...current, id])
  }

  function clearFilters() {
    setCategoryId(null); setTagIds([]); setIngredient(''); setRatingMin(null); setMaxTotalMinutes(null); setFavoriteOnly(false); setMakeableOnly(false); setPantrySuggestions(false); setSafeForAll(false)
  }

  const firstName = user?.name?.trim().split(/\s+/)[0] ?? user?.email.split('@')[0] ?? ''
  const hasFilter = Boolean(categoryId || tagIds.length || ingredient || ratingMin || maxTotalMinutes || favoriteOnly || makeableOnly || pantrySuggestions || safeForAll)
  const allFilters = <>
    <Chip active={favoriteOnly} onClick={() => setFavoriteOnly((value) => !value)}><HeartIcon className="size-4" fill={favoriteOnly ? 'currentColor' : 'none'} /> Favoritos</Chip>
    <Chip active={makeableOnly} onClick={() => setMakeableOnly((value) => !value)}><CartIcon className="size-4" /> Dá para fazer</Chip>
    <Chip active={pantrySuggestions} onClick={() => setPantrySuggestions((value) => !value)}><CartIcon className="size-4" /> Mais próximas</Chip>
    <Chip active={safeForAll} onClick={() => setSafeForAll((value) => !value)}>Adequadas a todos</Chip>
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
      <div><h1 className="text-2xl font-bold tracking-tight text-text-primary">Olá, {firstName} <span aria-hidden>👋</span></h1><p className="mt-1 text-sm text-text-secondary">O que vais cozinhar hoje?</p></div>
      <UserMenu variant="mobile" />
    </header>

    <section className="mb-6 grid gap-3 sm:grid-cols-3" aria-label="Resumo semanal">
      <Link to="/planeamento" className="rounded-2xl border border-border bg-surface p-4 transition hover:border-primary-forest"><p className="text-xs font-bold uppercase tracking-wide text-text-secondary">Próximas refeições</p><p className="mt-2 text-2xl font-bold text-text-primary">{upcomingMeals.length}</p><p className="mt-1 line-clamp-1 text-sm text-text-secondary">{upcomingMeals[0]?.recipe.title ?? 'Completar o planeamento →'}</p></Link>
      <Link to="/despensa" className="rounded-2xl border border-border bg-surface p-4 transition hover:border-primary-forest"><p className="text-xs font-bold uppercase tracking-wide text-text-secondary">Validade próxima</p><p className={`mt-2 text-2xl font-bold ${expiringItems.length ? 'text-accent-orange' : 'text-text-primary'}`}>{expiringItems.length}</p><p className="mt-1 line-clamp-1 text-sm text-text-secondary">{expiringItems[0]?.name ?? 'Nenhum produto nos próximos 7 dias'}</p></Link>
      <Link to="/lista-compras" className="rounded-2xl border border-border bg-surface p-4 transition hover:border-primary-forest"><p className="text-xs font-bold uppercase tracking-wide text-text-secondary">Por comprar</p><p className="mt-2 text-2xl font-bold text-text-primary">{pendingShopping.length}</p><p className="mt-1 text-sm text-text-secondary">artigos pendentes</p></Link>
    </section>

    <div className="flex min-w-0 items-center gap-2 sm:gap-3">
      <SearchInput value={q} onChange={(event) => setQ(event.target.value)} placeholder="Procurar receitas…" className="min-w-0 flex-1" />
      <button type="button" onClick={() => setFiltersOpen(true)} aria-label="Abrir filtros" className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-primary-forest text-white lg:hidden"><SlidersIcon className="size-5" /></button>
    </div>

    <section className="mt-6 hidden sm:block">
      <div className="mb-3 flex items-center justify-between"><h2 className="text-sm font-bold text-text-primary sm:text-base">Filtros rápidos</h2>{hasFilter && <button onClick={clearFilters} className="text-xs font-semibold text-forest-text">Limpar</button>}</div>
      <div className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0 lg:flex-wrap">
        <Chip active={favoriteOnly} onClick={() => setFavoriteOnly((value) => !value)}><HeartIcon className="size-4" fill={favoriteOnly ? 'currentColor' : 'none'} /> Favoritos</Chip>
        <Chip active={makeableOnly} onClick={() => setMakeableOnly((value) => !value)}><CartIcon className="size-4" /> Dá para fazer</Chip>
        <Chip active={pantrySuggestions} onClick={() => setPantrySuggestions((value) => !value)}><CartIcon className="size-4" /> Mais próximas</Chip>
        <Chip active={safeForAll} onClick={() => setSafeForAll((value) => !value)}>Adequadas a todos</Chip>
        {categories.slice(0, 3).map((category) => <Chip key={category.id} kind="category" accentColor={category.color} icon={category.icon} active={categoryId === category.id} onClick={() => selectCategory(category.id)}>{category.name}</Chip>)}
        <Chip onClick={() => setFiltersOpen(true)} className="lg:hidden"><SlidersIcon className="size-4" /> Mais</Chip>
        <span className="hidden contents lg:contents">{categories.slice(3).map((category) => <Chip key={category.id} kind="category" accentColor={category.color} icon={category.icon} active={categoryId === category.id} onClick={() => selectCategory(category.id)}>{category.name}</Chip>)}{tags.map((tag) => <Chip key={tag.id} kind="tag" active={tagIds.includes(tag.id)} onClick={() => selectTag(tag.id)}>#{tag.name}</Chip>)}</span>
      </div>
      <div className="mt-3 hidden grid-cols-3 gap-3 lg:grid">
        <label className="text-xs font-semibold text-text-secondary">Ingrediente<input value={ingredient} onChange={(event) => setIngredient(event.target.value)} placeholder="ex.: tomate" className="mt-1 min-h-10 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-primary-forest" /></label>
        <label className="text-xs font-semibold text-text-secondary">Classificação mínima<select value={ratingMin ?? ''} onChange={(event) => setRatingMin(event.target.value ? Number(event.target.value) : null)} className="mt-1 min-h-10 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary"><option value="">Qualquer</option>{[1, 2, 3, 4, 5].map((rating) => <option key={rating} value={rating}>{rating}+ estrelas</option>)}</select></label>
        <label className="text-xs font-semibold text-text-secondary">Tempo máximo<select value={maxTotalMinutes ?? ''} onChange={(event) => setMaxTotalMinutes(event.target.value ? Number(event.target.value) : null)} className="mt-1 min-h-10 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary"><option value="">Qualquer</option><option value="15">15 minutos</option><option value="30">30 minutos</option><option value="60">1 hora</option><option value="120">2 horas</option></select></label>
      </div>
    </section>

    <section className="mt-8">
      <div className="mb-4 flex items-end justify-between gap-3"><div><h2 className="text-xl font-bold tracking-tight text-text-primary lg:text-2xl">Receitas</h2>{recipes && <p className="mt-0.5 text-sm text-text-secondary">{recipes.length} {recipes.length === 1 ? 'receita' : 'receitas'}</p>}</div><Link to="/colecoes" className="text-sm font-semibold text-forest-text">Ver coleções <span aria-hidden>›</span></Link></div>
      {error && <ErrorState>Não foi possível ligar ao backend. Confirma se está a correr em {import.meta.env.VITE_API_URL}.</ErrorState>}
      {!error && recipes === null && <RecipeGridSkeleton />}
      {!error && recipes !== null && recipes.length === 0 && <EmptyState title={favoriteOnly ? 'Ainda não marcaste receitas favoritas.' : makeableOnly ? 'Nenhuma receita corresponde à despensa.' : 'Ainda não há receitas por aqui.'} description="Ajusta os filtros ou adiciona uma nova receita ao teu livro." action={<Link to="/adicionar" className="font-semibold text-forest-text">Adicionar receita</Link>} />}
      {recipes && recipes.length > 0 && <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">{recipes.map((recipe) => <RecipeCard key={recipe.id} recipe={recipe} onToggleFavorite={handleToggleFavorite} />)}</div>}
    </section>
    <BottomSheet open={filtersOpen} title="Filtrar receitas" onClose={() => setFiltersOpen(false)}><div className="flex flex-wrap gap-2">{allFilters}</div><div className="mt-5 space-y-3"><label className="block text-xs font-semibold text-text-secondary">Ingrediente<input value={ingredient} onChange={(event) => setIngredient(event.target.value)} placeholder="ex.: tomate" className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary outline-none focus:border-primary-forest" /></label><label className="block text-xs font-semibold text-text-secondary">Classificação mínima<select value={ratingMin ?? ''} onChange={(event) => setRatingMin(event.target.value ? Number(event.target.value) : null)} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary"><option value="">Qualquer</option>{[1, 2, 3, 4, 5].map((rating) => <option key={rating} value={rating}>{rating}+ estrelas</option>)}</select></label><label className="block text-xs font-semibold text-text-secondary">Tempo máximo<select value={maxTotalMinutes ?? ''} onChange={(event) => setMaxTotalMinutes(event.target.value ? Number(event.target.value) : null)} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary"><option value="">Qualquer</option><option value="15">15 minutos</option><option value="30">30 minutos</option><option value="60">1 hora</option><option value="120">2 horas</option></select></label>{hasFilter && <button onClick={clearFilters} className="min-h-11 w-full rounded-xl border border-border text-sm font-semibold text-forest-text">Limpar todos os filtros</button>}</div></BottomSheet>
  </PageShell>
}

function RecipeGridSkeleton() {
  return <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 2xl:grid-cols-4">{Array.from({ length: 6 }, (_, index) => <div key={index} className="overflow-hidden rounded-2xl border border-border bg-surface"><Skeleton className="aspect-[4/3] rounded-none" /><div className="space-y-3 p-4"><Skeleton className="h-5 w-3/4" /><Skeleton className="h-4 w-1/2" /></div></div>)}</div>
}
