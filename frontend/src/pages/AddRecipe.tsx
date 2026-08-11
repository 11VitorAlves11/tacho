import { useEffect, useRef, useState, type ChangeEvent, type FormEvent, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { createRecipe, getImportStatus, importRecipeFromPhotos, startImport, uploadRecipeImage } from '../api/recipes'
import type { RecipeExtraction, RecipeInput } from '../api/types'
import { PageShell } from '../components/PageShell'
import { RecipeForm } from '../components/RecipeForm'
import { CameraIcon, LinkIcon } from '../components/icons'

type Phase = 'idle' | 'pending' | 'failed'
type Tab = 'link' | 'manual' | 'photo'

export function AddRecipe() {
  const [tab, setTab] = useState<Tab>('link')
  const [url, setUrl] = useState('')
  const [phase, setPhase] = useState<Phase>('idle')
  const [errorMessage, setErrorMessage] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const navigate = useNavigate()

  const [photoFiles, setPhotoFiles] = useState<File[]>([])
  const [photoDraft, setPhotoDraft] = useState<RecipeExtraction | null>(null)
  const [photoRecognizing, setPhotoRecognizing] = useState(false)
  const [photoError, setPhotoError] = useState('')

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

  function handlePhotoFilesChange(e: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(e.target.files ?? []).slice(0, 3)
    setPhotoFiles(files)
    setPhotoError('')
  }

  async function handleRecognizePhotos() {
    if (photoFiles.length === 0 || photoRecognizing) return
    setPhotoRecognizing(true)
    setPhotoError('')
    try {
      const draft = await importRecipeFromPhotos(photoFiles)
      setPhotoDraft(draft)
    } catch (err) {
      setPhotoError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Não foi possível reconhecer uma receita nestas fotos.',
      )
    } finally {
      setPhotoRecognizing(false)
    }
  }

  return (
    <PageShell>
      <h1 className="text-2xl font-bold text-text-primary">Adicionar receita</h1>

      <div className="mt-4 inline-flex rounded-full bg-surface p-1 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
        <TabButton active={tab === 'link'} onClick={() => setTab('link')}>
          Por link
        </TabButton>
        <TabButton active={tab === 'manual'} onClick={() => setTab('manual')}>
          À mão
        </TabButton>
        <TabButton active={tab === 'photo'} onClick={() => setTab('photo')}>
          Por foto
        </TabButton>
      </div>

      {tab === 'link' ? (
        <>
          <p className="mt-4 text-text-secondary">
            Cola o link de uma receita e o Tacho tenta trazer os ingredientes e os passos sozinho.
          </p>

          <form
            onSubmit={handleImport}
            className="mt-6 rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]"
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
      ) : tab === 'manual' ? (
        <div className="mt-6">
          <RecipeForm onSubmit={handleManualSubmit} submitLabel="Guardar receita" />
        </div>
      ) : photoDraft ? (
        <div className="mt-6">
          <p className="mb-4 rounded-xl bg-bg-sage p-3 text-xs text-text-secondary">
            Reconhecido a partir da foto — confirma tudo antes de guardar, sobretudo quantidades (pode ter
            interpretado mal a letra ou a imagem).
          </p>
          <RecipeForm initial={photoDraft} onSubmit={handleManualSubmit} submitLabel="Guardar receita" />
        </div>
      ) : (
        <>
          <p className="mt-4 text-text-secondary">
            Tira 1 a 3 fotos de uma página de livro ou receita manuscrita — o Tacho tenta reconhecer os
            ingredientes e os passos.
          </p>

          <div className="mt-6 rounded-2xl bg-surface p-5 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
            <label className="flex cursor-pointer flex-col items-center gap-1.5 rounded-xl bg-bg-sage py-8 text-text-secondary">
              <CameraIcon className="size-6" />
              <span className="text-sm font-medium">
                {photoFiles.length > 0 ? `${photoFiles.length} foto(s) escolhida(s)` : 'Escolher fotos (máx. 3)'}
              </span>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                capture="environment"
                multiple
                onChange={handlePhotoFilesChange}
                className="hidden"
              />
            </label>

            <button
              type="button"
              onClick={handleRecognizePhotos}
              disabled={photoFiles.length === 0 || photoRecognizing}
              className="mt-4 w-full rounded-full bg-primary-forest py-3.5 font-semibold text-card-white transition-opacity disabled:opacity-60"
            >
              {photoRecognizing ? 'A reconhecer…' : 'Reconhecer receita'}
            </button>

            {photoError && <p className="mt-3 text-sm text-accent-orange">{photoError}</p>}
          </div>

          <p className="mt-4 text-xs text-text-secondary">
            Nunca guarda nada sozinho — o resultado abre sempre no formulário para reveres e confirmares.
          </p>
        </>
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
