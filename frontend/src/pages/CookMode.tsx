import { useEffect, useRef, useState, type CSSProperties } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { addCookNote, getRecipe, markRecipeMade, recipeImageUrl } from '../api/recipes'
import type { Recipe } from '../api/types'
import { ChevronLeftIcon, ClockIcon } from '../components/icons'

const LARGE_TEXT_KEY = 'tacho:cook-mode-large-text'

// O Modo Cozinha mantém contraste elevado e fundo escuro em qualquer tema,
// mas usa os mesmos tokens semânticos da aplicação (em vez de cores isoladas).
const COOK_MODE_TOKENS = {
  '--color-bg-sage': '#101513',
  '--color-surface': '#171c19',
  '--color-text-primary': '#f4f7f5',
  '--color-text-secondary': '#a2aaa5',
  '--color-forest-text': '#62d66d',
  '--color-border': '#2a302c',
  '--color-muted': '#202622',
  '--color-primary-soft': '#193320',
} as CSSProperties

type CookingTimer = { id: string; label: string; duration: number; remaining: number; running: boolean }

export function CookMode() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [recipe, setRecipe] = useState<Recipe | null>(null)
  const [stepIndex, setStepIndex] = useState(0)
  // Persistido — o telemóvel fica pousado longe na bancada; uma vez ligado,
  // não faz sentido voltar ao tamanho normal a cada receita nova.
  const [largeText, setLargeText] = useState(() => localStorage.getItem(LARGE_TEXT_KEY) === '1')
  const [timers, setTimers] = useState<CookingTimer[]>([])
  const wakeLockRef = useRef<WakeLockSentinel | null>(null)

  useEffect(() => {
    const interval = window.setInterval(() => {
      setTimers((current) => current.map((timer) => {
        if (!timer.running || timer.remaining <= 0) return timer
        const remaining = timer.remaining - 1
        if (remaining === 0) navigator.vibrate?.([200, 100, 200])
        return { ...timer, remaining, running: remaining > 0 }
      }))
    }, 1000)
    return () => window.clearInterval(interval)
  }, [])

  function startTimer(id: string, duration: number, label: string) {
    setTimers((current) => current.some((timer) => timer.id === id)
      ? current.map((timer) => timer.id === id ? { ...timer, running: true } : timer)
      : [...current, { id, label, duration, remaining: duration, running: true }])
  }

  function toggleTimer(id: string) {
    setTimers((current) => current.map((timer) => timer.id === id ? { ...timer, running: !timer.running && timer.remaining > 0 } : timer))
  }

  function resetTimer(id: string) {
    setTimers((current) => current.filter((timer) => timer.id !== id))
  }

  function addCustomTimer() {
    const value = window.prompt('Duração do temporizador em minutos:')
    const minutes = value ? Number(value.replace(',', '.')) : 0
    if (!Number.isFinite(minutes) || minutes <= 0 || minutes > 24 * 60) return
    const label = window.prompt('Nome do temporizador (opcional):')?.trim() || 'Temporizador adicional'
    startTimer(`custom-${Date.now()}`, Math.round(minutes * 60), label)
  }

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
      <div className="flex min-h-svh items-center justify-center bg-bg-sage text-text-primary" style={COOK_MODE_TOKENS}>
        <p className="text-sm">A carregar…</p>
      </div>
    )
  }

  const steps = recipe.steps
  const step = steps[stepIndex]
  const isLast = stepIndex === steps.length - 1

  return (
    <div className="flex min-h-svh flex-col bg-bg-sage text-text-primary" style={COOK_MODE_TOKENS}>
      <header className="mx-auto flex w-full max-w-4xl items-center justify-between px-4 py-4">
        <Link
          to={`/receitas/${recipe.id}`}
          className="flex size-10 items-center justify-center rounded-xl border border-border bg-surface/70 text-text-primary transition hover:bg-muted"
          aria-label="Sair do Modo Cozinha"
        >
          <ChevronLeftIcon className="size-5" />
        </Link>
        <span className="text-sm font-medium text-text-secondary">
          Passo {stepIndex + 1} de {steps.length}
        </span>
        <button
          type="button"
          onClick={() => setLargeText((v) => !v)}
          aria-pressed={largeText}
          aria-label={largeText ? 'Diminuir tamanho de letra' : 'Aumentar tamanho de letra'}
          className={`flex size-10 items-center justify-center rounded-full text-sm font-bold ${
            largeText ? 'bg-primary-forest text-white' : 'border border-border bg-surface/70 text-text-primary'
          }`}
        >
          A{largeText ? '+' : ''}
        </button>
      </header>

      <div className="mx-auto flex w-full max-w-4xl gap-1.5 px-4">
        {steps.map((s, i) => (
          <div
            key={s.id}
            className={`h-1.5 flex-1 rounded-full ${i <= stepIndex ? 'bg-primary-forest' : 'bg-border'}`}
          />
        ))}
      </div>

      <main className="relative flex flex-1 items-center justify-center overflow-hidden px-6 py-10 sm:px-16">
        <span
          aria-hidden
          className="pointer-events-none absolute font-bold text-text-primary/5 leading-none select-none"
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
            {step.duration_minutes != null && <StepTimer minutes={step.duration_minutes} timer={timers.find((timer) => timer.id === `step-${step.id}`)} onStart={() => startTimer(`step-${step.id}`, step.duration_minutes! * 60, `Passo ${stepIndex + 1}`)} onToggle={() => toggleTimer(`step-${step.id}`)} onReset={() => resetTimer(`step-${step.id}`)} />}
          </div>
        ) : (
          <p className="relative text-lg text-text-secondary">Esta receita ainda não tem passos registados.</p>
        )}
      </main>

      <footer className="mx-auto flex w-full max-w-4xl gap-3 p-4 sm:p-6">
        <button
          type="button"
          disabled={stepIndex === 0}
          onClick={() => setStepIndex((i) => Math.max(0, i - 1))}
          className="flex-1 rounded-xl border border-border bg-surface/70 py-4 font-semibold text-text-primary transition hover:bg-muted disabled:opacity-30"
        >
          Anterior
        </button>
        {isLast ? (
          <button
            type="button"
            onClick={handleFinish}
            className="flex flex-1 items-center justify-center rounded-xl bg-primary-forest py-4 font-semibold text-white transition hover:brightness-95"
          >
            Concluir
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setStepIndex((i) => Math.min(steps.length - 1, i + 1))}
            className="flex-1 rounded-xl bg-primary-forest py-4 font-semibold text-white transition hover:brightness-95"
          >
            Seguinte
          </button>
        )}
      </footer>
      {timers.length > 0 && <TimerDock timers={timers} onToggle={toggleTimer} onReset={resetTimer} />}
      <button type="button" onClick={addCustomTimer} className="fixed bottom-24 right-4 z-10 rounded-xl border border-border bg-surface px-3 py-2 text-xs font-semibold text-text-primary shadow-lg transition hover:bg-muted sm:bottom-28 sm:right-6">+ Temporizador</button>
    </div>
  )
}

// `key={step.id}` no chamador garante que o estado reinicia a cada passo —
// mais simples do que sincronizar manualmente via useEffect.
function StepTimer({ minutes, timer, onStart, onToggle, onReset }: { minutes: number; timer?: CookingTimer; onStart: () => void; onToggle: () => void; onReset: () => void }) {
  if (!timer) {
    return (
      <button
        type="button"
        onClick={onStart}
        className="flex items-center gap-2 rounded-xl border border-border bg-surface px-4 py-3 text-sm font-semibold text-text-primary transition hover:bg-muted"
      >
        <ClockIcon className="size-4 text-accent-orange" />
        Iniciar temporizador · {minutes} min
      </button>
    )
  }

  const done = timer.remaining === 0
  const mm = Math.floor(timer.remaining / 60)
  const ss = timer.remaining % 60

  return (
    <div
      className={`flex items-center gap-3 rounded-full px-4 py-2 ${
        done ? 'animate-pulse bg-accent-orange text-text-primary' : 'border border-border bg-surface text-text-primary'
      }`}
    >
      <ClockIcon className={`size-4 ${done ? 'text-text-primary' : 'text-accent-orange'}`} />
      <span className="font-semibold tabular-nums">{done ? 'Tempo!' : `${mm}:${ss.toString().padStart(2, '0')}`}</span>
      {!done && <button type="button" onClick={onToggle} className="text-xs underline">{timer.running ? 'Pausar' : 'Continuar'}</button>}
      <button type="button" onClick={onReset} className="text-xs underline">{done ? 'Repor' : 'Remover'}</button>
    </div>
  )
}

function TimerDock({ timers, onToggle, onReset }: { timers: CookingTimer[]; onToggle: (id: string) => void; onReset: (id: string) => void }) {
  return <aside className="fixed inset-x-4 bottom-[7.5rem] z-20 mx-auto flex max-w-4xl gap-2 overflow-x-auto pb-1" aria-label="Temporizadores ativos">{timers.map((timer) => { const done = timer.remaining === 0; const mm = Math.floor(timer.remaining / 60); const ss = timer.remaining % 60; return <div key={timer.id} className={`flex min-w-44 items-center gap-2 rounded-xl border px-3 py-2 text-xs shadow-lg backdrop-blur ${done ? 'border-accent-orange bg-accent-orange text-text-primary' : 'border-border bg-surface/95 text-text-primary'}`}><span className="min-w-0 flex-1 truncate font-semibold">{timer.label}</span><span className="font-bold tabular-nums">{done ? 'Tempo!' : `${mm}:${ss.toString().padStart(2, '0')}`}</span>{!done && <button type="button" onClick={() => onToggle(timer.id)} aria-label={timer.running ? `Pausar ${timer.label}` : `Continuar ${timer.label}`} className="underline">{timer.running ? 'Pausa' : 'Play'}</button>}<button type="button" onClick={() => onReset(timer.id)} aria-label={`Remover ${timer.label}`} className="underline">×</button></div> })}</aside>
}
