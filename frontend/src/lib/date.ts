import { t, getLanguage } from '../i18n'
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
  return t(WEEKDAY_LABELS[index])
}

export function formatDayShort(d: Date): string {
  return d.toLocaleDateString(getLanguage(), { day: 'numeric', month: 'short' })
}

export function formatWeekRange(start: Date): string {
  const end = addDays(start, 6)
  const sameMonth = start.getMonth() === end.getMonth()
  const startLabel = start.toLocaleDateString(getLanguage(), { day: 'numeric', month: sameMonth ? undefined : 'short' })
  const endLabel = end.toLocaleDateString(getLanguage(), { day: 'numeric', month: 'short' })
  return `${startLabel} – ${endLabel}`
}

/** "YYYY-MM-DD" (da API) como data local — `new Date(key)` seria meia-noite UTC. */
export function parseDateKey(key: string): Date {
  const [year, month, day] = key.split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function formatDateKey(key: string, language: string = getLanguage()): string {
  return parseDateKey(key).toLocaleDateString(language, { day: '2-digit', month: '2-digit', year: 'numeric' })
}

/** Dias de calendário de `from` até `to` (negativo no passado), imune à mudança de hora. */
export function daysBetween(from: Date, to: Date): number {
  return Math.round((Date.UTC(to.getFullYear(), to.getMonth(), to.getDate()) - Date.UTC(from.getFullYear(), from.getMonth(), from.getDate())) / 86_400_000)
}

export type ExpiryTone = 'expired' | 'soon' | 'later'
const EXPIRY_SOON_DAYS = 7

/** Validade relativa a `today`: "Expira em 3 dias", "Expirou há 2 dias" ou a data, quando ainda falta muito. */
export function expiryStatus(key: string, today: Date): { tone: ExpiryTone; label: string } {
  const days = daysBetween(today, parseDateKey(key))
  if (days < -1) return { tone: 'expired', label: t('Expirou há {count} dias', { count: -days }) }
  if (days === -1) return { tone: 'expired', label: t('Expirou ontem') }
  if (days === 0) return { tone: 'expired', label: t('Expira hoje') }
  if (days === 1) return { tone: 'soon', label: t('Expira amanhã') }
  if (days <= EXPIRY_SOON_DAYS) return { tone: 'soon', label: t('Expira em {count} dias', { count: days }) }
  return { tone: 'later', label: t('Validade: {date}', { date: formatDateKey(key) }) }
}
