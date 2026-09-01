import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { addCookNote, getRecipe, markRecipeMade, recipeImageUrl } from '../api/recipes'
import type { Recipe } from '../api/types'
import { ChevronLeftIcon, ClockIcon } from '../components/icons'

const LARGE_TEXT_KEY = 'tacho:cook-mode-large-text'

// O Modo Cozinha já é, por design, o "modo escuro" da app (o
// único lugar onde a marca vira fundo cheio) — fica sempre igual,
// independentemente do tema claro/escuro do resto da app. Fixa aqui os
// tokens adaptáveis aos valores de tema claro, para nunca herdar as
// variantes escuras do :root.
const FIXED_LIGHT_TOKENS = {
  '--color-text-primary': '#171a18',
  '--color-text-secondary': '#69706c',
  '--color-bg-sage': '#fafafa',
  '--color-surface': '#ffffff',
  '--color-forest-text': '#258c34',
} as CSSProperties

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
      const note = window.prompt('Alguma nota para a próxima vez? (opcional)')
      if (note && note.trim()) {
        try {
          await addCookNote(id, note.trim())
        } catch {
          // uma nota falhada nunca deve impedir sair do Modo Cozinha
        }
      }
    }
    navigate(`/receitas/${id}`)
  }

  useEffect(() => {
    if (!id) return
    getRecipe(id).then(setRecipe)
  }, [id])

  // Diz ao service worker para guardar esta receita (dados + foto) para
  // continuar visível se a rede cair a meio de cozinhar — best-effort,
  // nunca bloqueia o Modo Cozinha se falhar ou se não houver SW ativo.
  useEffect(() => {
    if (!recipe || !('serviceWorker' in navigator)) return
    const apiBase = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
    const urls = [`${apiBase}/recipes/${recipe.id}`]
    if (recipe.image_path) urls.push(recipeImageUrl(recipe.image_path))
    navigator.serviceWorker.ready
      .then((registration) => registration.active?.postMessage({ type: 'CACHE_ACTIVE_RECIPE', urls }))
      .catch(() => {})
  }, [recipe])

  // "sem bloqueio automático do ecrã" — pede um wake lock
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
      <div className="flex min-h-svh items-center justify-center bg-[#101513] text-card-white" style={FIXED_LIGHT_TOKENS}>
        <p className="text-sm">A carregar…</p>
      </div>
    )
  }

  const steps = recipe.steps
  const step = steps[stepIndex]
  const isLast = stepIndex === steps.length - 1

  return (
    <div className="flex min-h-svh flex-col bg-[#101513] text-card-white" style={FIXED_LIGHT_TOKENS}>
      <header className="mx-auto flex w-full max-w-4xl items-center justify-between px-4 py-4">
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
            largeText ? 'bg-primary-forest text-white' : 'bg-card-white/10 text-card-white'
          }`}
        >
          A{largeText ? '+' : ''}
        </button>
      </header>

      <div className="mx-auto flex w-full max-w-4xl gap-1.5 px-4">
        {steps.map((s, i) => (
          <div
            key={s.id}
            className={`h-1.5 flex-1 rounded-full ${i <= stepIndex ? 'bg-primary-forest' : 'bg-card-white/20'}`}
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
          <div className="relative flex flex-col items-center gap-4">
            <p
              className={`max-w-2xl text-center font-semibold leading-snug ${
                largeText ? 'text-4xl sm:text-6xl' : 'text-3xl sm:text-5xl'
              }`}
            >
              {step.instruction}
            </p>
            {step.duration_minutes != null && <StepTimer key={step.id} minutes={step.duration_minutes} />}
          </div>
        ) : (
          <p className="relative text-lg text-card-white/80">Esta receita ainda não tem passos registados.</p>
        )}
      </main>

      <footer className="mx-auto flex w-full max-w-4xl gap-3 p-4 sm:p-6">
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
            className="flex flex-1 items-center justify-center rounded-full bg-primary-forest py-4 font-semibold text-white"
          >
            Concluir
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setStepIndex((i) => Math.min(steps.length - 1, i + 1))}
            className="flex-1 rounded-full bg-primary-forest py-4 font-semibold text-white"
          >
            Seguinte
          </button>
        )}
      </footer>
    </div>
  )
}

// `key={step.id}` no chamador garante que o estado reinicia a cada passo —
// mais simples do que sincronizar manualmente via useEffect.
function StepTimer({ minutes }: { minutes: number }) {
  const [remaining, setRemaining] = useState<number | null>(null)
  const [running, setRunning] = useState(false)

  useEffect(() => {
    if (!running || remaining === null) return
    const timeout = setTimeout(() => {
      setRemaining((current) => {
        if (current === null) return null
        if (current <= 1) {
          setRunning(false)
          navigator.vibrate?.(200)
          return 0
        }
        return current - 1
      })
    }, 1000)
    return () => clearTimeout(timeout)
  }, [running, remaining])

  if (remaining === null) {
    return (
      <button
        type="button"
        onClick={() => {
          setRemaining(minutes * 60)
          setRunning(true)
        }}
        className="flex items-center gap-2 rounded-full bg-card-white/10 px-4 py-2 text-sm font-medium text-card-white"
      >
        <ClockIcon className="size-4 text-accent-orange" />
        Iniciar temporizador · {minutes} min
      </button>
    )
  }

  const done = remaining === 0
  const mm = Math.floor(remaining / 60)
  const ss = remaining % 60

  return (
    <div
      className={`flex items-center gap-3 rounded-full px-4 py-2 ${
        done ? 'animate-pulse bg-accent-orange text-text-primary' : 'bg-card-white/10 text-card-white'
      }`}
    >
      <ClockIcon className={`size-4 ${done ? 'text-text-primary' : 'text-accent-orange'}`} />
      <span className="font-semibold tabular-nums">{done ? 'Tempo!' : `${mm}:${ss.toString().padStart(2, '0')}`}</span>
      <button
        type="button"
        onClick={() => {
          setRemaining(null)
          setRunning(false)
        }}
        className="text-xs underline"
      >
        {done ? 'Repor' : 'Parar'}
      </button>
    </div>
  )
}
