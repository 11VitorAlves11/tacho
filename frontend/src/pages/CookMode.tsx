import { useEffect, useRef, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getRecipe } from '../api/recipes'
import type { Recipe } from '../api/types'
import { ChevronLeftIcon } from '../components/icons'

export function CookMode() {
  const { id } = useParams<{ id: string }>()
  const [recipe, setRecipe] = useState<Recipe | null>(null)
  const [stepIndex, setStepIndex] = useState(0)
  const wakeLockRef = useRef<WakeLockSentinel | null>(null)

  useEffect(() => {
    if (!id) return
    getRecipe(id).then(setRecipe)
  }, [id])

  // "sem bloqueio automático do ecrã" (PRD 4.5) — pede um wake lock
  // enquanto o Modo Cozinha está aberto; falha em silêncio em navegadores
  // sem suporte (ex. Safari iOS mais antigo).
  useEffect(() => {
    let cancelled = false
    async function requestLock() {
      try {
        if ('wakeLock' in navigator) {
          const lock = await navigator.wakeLock.request('screen')
          if (cancelled) {
            lock.release()
          } else {
            wakeLockRef.current = lock
          }
        }
      } catch {
        // sem suporte ou permissão — segue sem bloquear o fluxo
      }
    }
    requestLock()
    return () => {
      cancelled = true
      wakeLockRef.current?.release()
    }
  }, [])

  if (!recipe) {
    return (
      <div className="flex min-h-svh items-center justify-center bg-primary-forest text-card-white">
        <p className="text-sm">A carregar…</p>
      </div>
    )
  }

  const steps = recipe.steps
  const step = steps[stepIndex]
  const isLast = stepIndex === steps.length - 1

  return (
    <div className="flex min-h-svh flex-col bg-primary-forest text-card-white">
      <header className="flex items-center justify-between px-4 py-4">
        <Link
          to={`/receitas/${recipe.id}`}
          className="flex size-10 items-center justify-center rounded-full bg-card-white/10"
          aria-label="Sair do Modo Cozinha"
        >
          <ChevronLeftIcon className="size-5" />
        </Link>
        <span className="text-sm font-medium text-card-white/80">
          Passo {stepIndex + 1} de {steps.length}
        </span>
        <span className="size-10" />
      </header>

      <div className="flex gap-1.5 px-4">
        {steps.map((s, i) => (
          <div
            key={s.id}
            className={`h-1.5 flex-1 rounded-full ${i <= stepIndex ? 'bg-accent-orange' : 'bg-card-white/20'}`}
          />
        ))}
      </div>

      <main className="relative flex flex-1 items-center justify-center overflow-hidden px-6 py-10 sm:px-16">
        <span
          aria-hidden
          className="pointer-events-none absolute font-bold text-card-white/5 leading-none select-none"
          style={{ fontSize: 'min(60vw, 60vh)' }}
        >
          {stepIndex + 1}
        </span>
        {step ? (
          <p className="relative max-w-2xl text-center text-3xl font-semibold leading-snug sm:text-5xl">
            {step.instruction}
          </p>
        ) : (
          <p className="relative text-lg text-card-white/80">Esta receita ainda não tem passos registados.</p>
        )}
      </main>

      <footer className="flex gap-3 p-4 sm:p-6">
        <button
          type="button"
          disabled={stepIndex === 0}
          onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
          className="flex-1 rounded-full bg-card-white/10 py-4 font-medium disabled:opacity-30"
        >
          Anterior
        </button>
        {isLast ? (
          <Link
            to={`/receitas/${recipe.id}`}
            className="flex flex-1 items-center justify-center rounded-full bg-accent-orange py-4 font-semibold text-text-primary"
          >
            Concluir
          </Link>
        ) : (
          <button
            type="button"
            onClick={() => setStepIndex((i) => Math.min(steps.length - 1, i + 1))}
            className="flex-1 rounded-full bg-accent-orange py-4 font-semibold text-text-primary"
          >
            Seguinte
          </button>
        )}
      </footer>
    </div>
  )
}
