import { getLanguage, t } from '../i18n'
import type { MonthlySpend, PantryPriceEntry, PriceHistoryPoint } from '../api/types'

// Helpers puros dos gráficos de preços da despensa — sem biblioteca de
// gráficos: as escalas e o path do SVG são calculados aqui e testados à parte.

/** Moeda única (EUR): a API não guarda moeda, ver docs/configuration.md. */
export function formatMoney(value: number, language: string = getLanguage()): string {
  return new Intl.NumberFormat(language, { style: 'currency', currency: 'EUR' }).format(value)
}

/** Preço da última compra (e preço unitário quando há quantidade), para a linha do produto. */
export function lastPriceLabel(entry: PantryPriceEntry, language: string = getLanguage()): string {
  const total = formatMoney(entry.price, language)
  return entry.unit_price !== null ? `${total} · ${formatMoney(entry.unit_price, language)}/${entry.unit ?? t('un')}` : total
}

/** "YYYY-MM" dos `months` meses que terminam no mês de `today`, do mais antigo para o atual. */
export function monthKeys(months: number, today: Date): string[] {
  const keys: string[] = []
  for (let offset = months - 1; offset >= 0; offset--) {
    const date = new Date(today.getFullYear(), today.getMonth() - offset, 1)
    keys.push(`${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`)
  }
  return keys
}

/** A API só devolve meses com compras; o gráfico precisa de todos (os vazios a 0). */
export function fillMonths(totals: MonthlySpend[], months: number, today: Date): MonthlySpend[] {
  const byMonth = new Map(totals.map((entry) => [entry.month, entry.total]))
  return monthKeys(months, today).map((month) => ({ month, total: byMonth.get(month) ?? 0 }))
}

export function monthLabel(month: string, language: string = getLanguage()): string {
  const [year, monthNumber] = month.split('-').map(Number)
  return new Date(year, monthNumber - 1, 1).toLocaleDateString(language, { month: 'short' }).replace('.', '')
}

/** Topo "redondo" do eixo Y (1, 2, 2.5, 5 × 10^n) acima de `value`; nunca 0. */
export function niceCeiling(value: number): number {
  if (!(value > 0)) return 1
  const magnitude = 10 ** Math.floor(Math.log10(value))
  const step = [1, 2, 2.5, 5, 10].find((candidate) => candidate * magnitude >= value) ?? 10
  return step * magnitude
}

/** Divisões do eixo Y que dão valores legíveis para o topo de `niceCeiling` (ex. 200 → 0/50/100/150/200, nunca 66,67). */
export function axisTicks(max: number): number[] {
  const leading = Math.round((max / 10 ** Math.floor(Math.log10(max))) * 10) / 10
  const count = leading === 1 || leading === 2 ? 4 : 5
  return Array.from({ length: count + 1 }, (_, index) => (max / count) * index)
}

/** Usa o preço unitário só quando todos os pontos o têm na mesma unidade — senão compara o total pago. */
export function seriesValues(points: PriceHistoryPoint[]): { mode: 'unit' | 'total'; unit: string | null; values: number[] } {
  const units = new Set(points.map((point) => point.unit))
  if (points.length > 0 && units.size === 1 && points.every((point) => point.unit_price !== null)) {
    return { mode: 'unit', unit: points[0].unit, values: points.map((point) => point.unit_price as number) }
  }
  return { mode: 'total', unit: null, values: points.map((point) => point.price) }
}

export interface ChartBox {
  width: number
  height: number
  top: number
  right: number
  bottom: number
  left: number
}

export interface LineChart {
  coords: { x: number; y: number; date: string; value: number }[]
  path: string
  ticks: { value: number; y: number }[]
  max: number
}

function dayNumber(dateKey: string): number {
  const [year, month, day] = dateKey.split('-').map(Number)
  return Date.UTC(year, month - 1, day) / 86_400_000
}

const round = (value: number) => Math.round(value * 10) / 10

/** Escala temporal no X (por dia) e linear a partir de 0 no Y; um só dia fica centrado. */
export function buildLineChart(points: { date: string; value: number }[], box: ChartBox): LineChart {
  const innerWidth = box.width - box.left - box.right
  const innerHeight = box.height - box.top - box.bottom
  const max = niceCeiling(Math.max(0, ...points.map((point) => point.value)))
  const days = points.map((point) => dayNumber(point.date))
  const first = Math.min(...days)
  const span = Math.max(...days) - first
  const yOf = (value: number) => round(box.top + innerHeight - (value / max) * innerHeight)
  const coords = points.map((point, index) => ({
    x: round(box.left + (span === 0 ? innerWidth / 2 : ((days[index] - first) / span) * innerWidth)),
    y: yOf(point.value),
    date: point.date,
    value: point.value,
  }))
  const path = coords.map((coord, index) => `${index === 0 ? 'M' : 'L'}${coord.x} ${coord.y}`).join(' ')
  const ticks = axisTicks(max).map((value) => ({ value, y: yOf(value) }))
  return { coords, path, ticks, max }
}

export interface BarChart {
  bars: { x: number; y: number; width: number; height: number; month: string; total: number }[]
  ticks: { value: number; y: number }[]
  max: number
}

export function buildBarChart(totals: MonthlySpend[], box: ChartBox): BarChart {
  const innerWidth = box.width - box.left - box.right
  const innerHeight = box.height - box.top - box.bottom
  const max = niceCeiling(Math.max(0, ...totals.map((entry) => entry.total)))
  const slot = totals.length ? innerWidth / totals.length : innerWidth
  const width = round(slot * 0.62)
  const bars = totals.map((entry, index) => {
    const height = round((entry.total / max) * innerHeight)
    return { x: round(box.left + slot * index + (slot - width) / 2), y: round(box.top + innerHeight - height), width, height, month: entry.month, total: entry.total }
  })
  const ticks = axisTicks(max).map((value) => ({ value, y: round(box.top + innerHeight - (value / max) * innerHeight) }))
  return { bars, ticks, max }
}
