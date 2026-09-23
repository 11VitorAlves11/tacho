import { t } from '../i18n'
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { deleteRecipe, getRecipe, updateRecipe, uploadRecipeImage } from '../api/recipes'
import type { Recipe, RecipeInput } from '../api/types'
import { PageShell } from '../components/PageShell'
import { RecipeForm } from '../components/RecipeForm'
import { TrashIcon } from '../components/icons'
import { ConfirmDialog } from '../components/ui'

export function EditRecipe() {
  const { id } = useParams<{ id: string }>()
  const [recipe, setRecipe] = useState<Recipe | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    if (!id) return
    getRecipe(id).then(setRecipe)
  }, [id])

  async function handleSubmit(payload: RecipeInput, imageFile: File | null) {
    if (!id) return
    await updateRecipe(id, payload)
    if (imageFile) await uploadRecipeImage(id, imageFile)
    navigate(`/receitas/${id}`)
  }

  async function handleDelete() {
    if (!id) return
    await deleteRecipe(id)
    navigate('/')
  }

  if (!recipe) {
    return (
      <PageShell>
        <p className="text-sm text-text-secondary">{t('A carregar…')}</p>
      </PageShell>
    )
  }

  return (
    <PageShell>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-text-primary">{t('Editar receita')}</h1>
        <button
          type="button"
          onClick={() => setConfirmDelete(true)}
          className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium text-accent-orange hover:bg-accent-orange/10"
        >
          <TrashIcon className="size-4" />
          {t('Apagar')}
        </button>
      </div>

      <div className="mt-6">
        <RecipeForm initial={recipe} onSubmit={handleSubmit} submitLabel={t('Guardar alterações')} />
      </div>
      <ConfirmDialog open={confirmDelete} title={t('Apagar receita?')} description={t('Esta ação é permanente e não pode ser desfeita.')} confirmLabel={t('Apagar receita')} onCancel={() => setConfirmDelete(false)} onConfirm={handleDelete} />
    </PageShell>
  )
}
