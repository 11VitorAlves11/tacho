import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { getRecipe, markRecipeMade } from '../api/recipes'
import type { Recipe } from '../api/types'
import { ChevronLeftIcon } from '../components/icons'

const LARGE_TEXT_KEY = 'tacho:cook-mode-large-text'

export function CookMode() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [recipe, setRecipe] = useState<Recipe | null>(null)
  const [stepIndex, setStepIndex] = useState(0)
  // Persistido — o telemóvel fica pousado longe na bancada; uma vez ligado,
  // não faz sentido voltar ao tamanho normal a cada receita nova.
  const [largeText, setLargeText] = useState(() => localStorage.getItem(LARGE_TEXT_KEY) === '1')
  const wakeLockRef = useRef<WakeLockSentinel | null>(null)

  useEffect(() => {
    localStorage.setItem(LARGE_TEXT_KEY, largeText ? '1' : '0')
  }, [largeText])

  // Best-effort — marcar "feita" nunca deve impedir sair do Modo Cozinha,
  // mesmo que a chamada falhe (offline na cozinha é o caso mais comum).
  async function handleFinish() {
    if (id) {
      try {
        await markRecipeMade(id)
      } catch {
        // segue na mesma para o Detalhe
      }
    }
    navigate(`/receitas/${id}`)
  }

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
        <button
          type="button"
          onClick={() => setLargeText((v) => !v)}
          aria-pressed={largeText}
          aria-label={largeText ? 'Diminuir tamanho de letra' : 'Aumentar tamanho de letra'}
          className={`flex size-10 items-center justify-center rounded-full text-sm font-bold ${
            largeText ? 'bg-accent-orange text-text-primary' : 'bg-card-white/10 text-card-white'
          }`}
        >
          A{largeText ? '+' : ''}
        </button>
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
          <p
            className={`relative max-w-2xl text-center font-semibold leading-snug ${
              largeText ? 'text-4xl sm:text-6xl' : 'text-3xl sm:text-5xl'
            }`}
          >
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
          <button
            type="button"
            onClick={handleFinish}
            className="flex flex-1 items-center justify-center rounded-full bg-accent-orange py-4 font-semibold text-text-primary"
          >
            Concluir
          </button>
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
