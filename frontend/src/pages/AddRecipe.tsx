import { useEffect, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { createRecipe, getImportStatus, startImport, uploadRecipeImage } from '../api/recipes'
import type { RecipeInput } from '../api/types'
import { PageShell } from '../components/PageShell'
import { RecipeForm } from '../components/RecipeForm'
import { LinkIcon } from '../components/icons'

type Phase = 'idle' | 'pending' | 'failed'
type Tab = 'link' | 'manual'

export function AddRecipe() {
  const [tab, setTab] = useState<Tab>('link')
  const [url, setUrl] = useState('')
  const [phase, setPhase] = useState<Phase>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const navigate = useNavigate()

  useEffect(() => () => {
    if (pollRef.current) clearInterval(pollRef.current)
  }, [])

  async function handleImport(e: FormEvent) {
    e.preventDefault()
    setPhase('pending')
    setErrorMessage('')
    try {
      const { task_id } = await startImport(url)
      pollRef.current = setInterval(async () => {
        try {
          const status = await getImportStatus(task_id)
          if (status.status === 'done' && status.recipe_id) {
            if (pollRef.current) clearInterval(pollRef.current)
            navigate(`/receitas/${status.recipe_id}`)
          }
        } catch (err) {
          if (pollRef.current) clearInterval(pollRef.current)
          setPhase('failed')
          setErrorMessage(
            (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
              'Não foi possível importar esta receita.',
          )
        }
      }, 1500)
    } catch {
      setPhase('failed')
      setErrorMessage('Não foi possível pedir a importação — confirma o backend.')
    }
  }

  async function handleManualSubmit(payload: RecipeInput, imageFile: File | null) {
    const recipe = await createRecipe(payload)
    if (imageFile) await uploadRecipeImage(recipe.id, imageFile)
    navigate(`/receitas/${recipe.id}`)
  }

  return (
    <PageShell>
      <h1 className="text-2xl font-bold text-text-primary">Adicionar receita</h1>

      <div className="mt-4 inline-flex rounded-full bg-card-white p-1 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
        <TabButton active={tab === 'link'} onClick={() => setTab('link')}>
          Por link
        </TabButton>
        <TabButton active={tab === 'manual'} onClick={() => setTab('manual')}>
          À mão
        </TabButton>
      </div>

      {tab === 'link' ? (
        <>
          <p className="mt-4 text-text-secondary">
            Cola o link de uma receita e o Tacho tenta trazer os ingredientes e os passos sozinho.
          </p>

          <form
            onSubmit={handleImport}
            className="mt-6 rounded-2xl bg-card-white p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]"
          >
            <label className="flex items-center gap-2 rounded-full border border-black/10 bg-bg-sage px-4 py-3 ring-2 ring-transparent transition-shadow focus-within:border-accent-leaf focus-within:ring-accent-leaf/30">
              <LinkIcon className="size-4 shrink-0 text-text-secondary" />
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                type="url"
                required
                placeholder="https://exemplo.pt/receita-de..."
                className="w-full bg-transparent text-sm outline-none placeholder:text-text-secondary"
              />
            </label>

            <button
              type="submit"
              disabled={phase === 'pending'}
              className="mt-4 w-full rounded-full bg-primary-forest py-3.5 font-semibold text-card-white transition-opacity disabled:opacity-60"
            >
              {phase === 'pending' ? 'A importar…' : 'Importar receita'}
            </button>

            {phase === 'failed' && <p className="mt-3 text-sm text-accent-orange">{errorMessage}</p>}
          </form>

          <p className="mt-4 text-xs text-text-secondary">
            Nem todos os sites trazem tudo direito — confirma sempre os ingredientes e os passos
            depois de importar.
          </p>
        </>
      ) : (
        <div className="mt-6">
          <RecipeForm onSubmit={handleManualSubmit} submitLabel="Guardar receita" />
        </div>
      )}
    </PageShell>
  )
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
        active ? 'bg-primary-forest text-card-white' : 'text-text-secondary hover:text-text-primary'
      }`}
    >
      {children}
    </button>
  )
}
