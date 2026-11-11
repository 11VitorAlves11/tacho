import { t, getLanguage } from '../i18n'
import { useLayoutEffect, useRef, useState } from 'react'
import type { MonthlySpend, PriceHistoryPoint } from '../api/types'
import { buildBarChart, buildLineChart, formatMoney, monthLabel, seriesValues, type ChartBox } from '../lib/prices'

// Gráficos em SVG inline (sem biblioteca), desenhados em píxeis CSS: a largura
// vem do contentor e a altura é fixa, para o texto e os traços manterem o mesmo
// tamanho do telemóvel ao monitor. Cores só por tokens do tema.
const LINE_MARGINS = { height: 180, top: 12, right: 14, bottom: 28, left: 56 }
const BAR_MARGINS = { height: 220, top: 10, right: 6, bottom: 26, left: 56 }
const MAX_BAR_WIDTH = 40
const FALLBACK_WIDTH = 320

/** Largura atual do elemento (com fallback antes da primeira medição). */
function useElementWidth<T extends Element>() {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(FALLBACK_WIDTH)
  useLayoutEffect(() => {
    const element = ref.current
    if (!element) return
    const update = () => setWidth(Math.round(element.getBoundingClientRect().width) || FALLBACK_WIDTH)
    update()
    if (typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(update)
    observer.observe(element)
    return () => observer.disconnect()
  }, [])
  return [ref, width] as const
}

function formatDate(dateKey: string) {
  return new Date(`${dateKey}T00:00:00`).toLocaleDateString(getLanguage(), { day: 'numeric', month: 'short' })
}

export function PriceLineChart({ points }: { points: PriceHistoryPoint[] }) {
  if (points.length === 0) return <p className="rounded-xl bg-muted p-4 text-center text-sm text-text-secondary">{t('Ainda não há preços registados.')}</p>
  return <PriceLineFigure points={points} />
}

function PriceLineFigure({ points }: { points: PriceHistoryPoint[] }) {
  const [ref, width] = useElementWidth<HTMLElement>()
  const box: ChartBox = { ...LINE_MARGINS, width }
  const { mode, unit, values } = seriesValues(points)
  const chart = buildLineChart(points.map((point, index) => ({ date: point.purchased_on, value: values[index] })), box)
  const valueLabel = (value: number) => mode === 'unit' && unit ? `${formatMoney(value)}/${unit}` : formatMoney(value)
  const title = mode === 'unit' && unit ? t('Preço por {unit}', { unit }) : t('Preço pago')
  const first = chart.coords[0]
  const last = chart.coords[chart.coords.length - 1]
  const lowest = Math.min(...values)
  const highest = Math.max(...values)
  const summary = t('{title}: {count} compra(s) entre {from} e {to}; de {min} a {max}, último {last}.', { title, count: points.length, from: formatDate(first.date), to: formatDate(last.date), min: valueLabel(lowest), max: valueLabel(highest), last: valueLabel(last.value) })
  return (
    <figure ref={ref}>
      <figcaption className="text-xs font-semibold text-text-secondary">{title}</figcaption>
      <svg viewBox={`0 0 ${box.width} ${box.height}`} width={box.width} height={box.height} role="img" aria-label={summary} className="mt-1 block overflow-visible">
        {chart.ticks.map((tick) => <g key={tick.value}><line x1={box.left} x2={box.width - box.right} y1={tick.y} y2={tick.y} className="stroke-border" strokeWidth={1} /><text x={box.left - 8} y={tick.y} dy="0.32em" textAnchor="end" className="fill-text-secondary text-[11px]">{formatMoney(tick.value)}</text></g>)}
        <text x={first.x} y={box.height - 8} textAnchor={chart.coords.length > 1 ? 'start' : 'middle'} className="fill-text-secondary text-[11px]">{formatDate(first.date)}</text>
        {chart.coords.length > 1 && <text x={last.x} y={box.height - 8} textAnchor="end" className="fill-text-secondary text-[11px]">{formatDate(last.date)}</text>}
        <path d={chart.path} fill="none" className="stroke-forest-text" strokeWidth={2} strokeLinejoin="round" strokeLinecap="round" />
        {chart.coords.map((coord, index) => <g key={`${coord.date}-${index}`}><circle cx={coord.x} cy={coord.y} r={4} className="fill-forest-text stroke-surface" strokeWidth={2} /><circle cx={coord.x} cy={coord.y} r={12} fill="transparent"><title>{`${formatDate(coord.date)}: ${valueLabel(coord.value)}`}</title></circle></g>)}
      </svg>
      <table className="sr-only"><caption>{title}</caption><thead><tr><th scope="col">{t('Data')}</th><th scope="col">{t('Preço')}</th></tr></thead><tbody>{chart.coords.map((coord, index) => <tr key={`${coord.date}-${index}`}><td>{formatDate(coord.date)}</td><td>{valueLabel(coord.value)}</td></tr>)}</tbody></table>
    </figure>
  )
}

export function MonthlySpendChart({ totals }: { totals: MonthlySpend[] }) {
  const sum = totals.reduce((acc, entry) => acc + entry.total, 0)
  if (sum === 0) return <p className="mt-2 text-sm text-text-secondary">{t('Ainda não há preços registados. Regista um preço num produto ou lê uma fatura com preços.')}</p>
  return <MonthlySpendFigure totals={totals} sum={sum} />
}

function MonthlySpendFigure({ totals, sum }: { totals: MonthlySpend[]; sum: number }) {
  const [ref, width] = useElementWidth<HTMLElement>()
  const box: ChartBox = { ...BAR_MARGINS, width }
  const chart = buildBarChart(totals, box, MAX_BAR_WIDTH)
  const current = totals[totals.length - 1]
  const summary = t('Gastos por mês nos últimos {count} meses: total {total}; este mês {current}.', { count: totals.length, total: formatMoney(sum), current: formatMoney(current.total) })
  return (
    <figure ref={ref} className="mt-2">
      <svg viewBox={`0 0 ${box.width} ${box.height}`} width={box.width} height={box.height} role="img" aria-label={summary} className="block overflow-visible">
        {chart.ticks.map((tick) => <g key={tick.value}><line x1={box.left} x2={box.width - box.right} y1={tick.y} y2={tick.y} className="stroke-border" strokeWidth={1} /><text x={box.left - 8} y={tick.y} dy="0.32em" textAnchor="end" className="fill-text-secondary text-[11px]">{formatMoney(tick.value)}</text></g>)}
        {chart.bars.map((bar, index) => <g key={bar.month}>{bar.height > 0 && <rect x={bar.x} y={bar.y} width={bar.width} height={bar.height} rx={Math.min(4, bar.height / 2)} className={index === chart.bars.length - 1 ? 'fill-forest-text' : 'fill-primary-forest'} />}<rect x={bar.x - 2} y={box.top} width={bar.width + 4} height={box.height - box.top - box.bottom} fill="transparent"><title>{`${monthLabel(bar.month)}: ${formatMoney(bar.total)}`}</title></rect><text x={bar.x + bar.width / 2} y={box.height - 8} textAnchor="middle" className="fill-text-secondary text-[11px]">{monthLabel(bar.month)}</text></g>)}
      </svg>
      <table className="sr-only"><caption>{t('Gastos por mês')}</caption><thead><tr><th scope="col">{t('Mês')}</th><th scope="col">{t('Total')}</th></tr></thead><tbody>{totals.map((entry) => <tr key={entry.month}><td>{`${monthLabel(entry.month)} ${entry.month.slice(0, 4)}`}</td><td>{formatMoney(entry.total)}</td></tr>)}</tbody></table>
    </figure>
  )
}
