// Formatação de datas em fuso horário local, nunca UTC — Portugal está em
// UTC+1 (ou +0 no inverno), e `toISOString()` desloca a meia-noite local
// para o dia anterior, o que faria o planeamento cair sempre no dia errado.

export function toDateKey(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

export function startOfWeek(d: Date): Date {
  // getDay() é 0 para domingo — a semana começa à segunda-feira.
  const diff = (d.getDay() + 6) % 7
  const monday = new Date(d.getFullYear(), d.getMonth(), d.getDate() - diff)
  return monday
}

export function addDays(d: Date, n: number): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n)
}

const WEEKDAY_LABELS = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

export function weekdayLabel(index: number): string {
  return WEEKDAY_LABELS[index]
}

export function formatDayShort(d: Date): string {
  return d.toLocaleDateString('pt-PT', { day: 'numeric', month: 'short' })
}

export function formatWeekRange(start: Date): string {
  const end = addDays(start, 6)
  const sameMonth = start.getMonth() === end.getMonth()
  const startLabel = start.toLocaleDateString('pt-PT', { day: 'numeric', month: sameMonth ? undefined : 'short' })
  const endLabel = end.toLocaleDateString('pt-PT', { day: 'numeric', month: 'short' })
  return `${startLabel} – ${endLabel}`
}
