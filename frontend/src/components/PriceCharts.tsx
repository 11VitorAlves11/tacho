import { t, getLanguage } from '../i18n'
import type { MonthlySpend, PriceHistoryPoint } from '../api/types'
import { buildBarChart, buildLineChart, formatMoney, monthLabel, seriesValues } from '../lib/prices'

// Gráficos em SVG inline (sem biblioteca): viewBox fixo e largura 100%,
// por isso escalam até à largura do telemóvel. Cores só por tokens do tema.
const LINE_BOX = { width: 320, height: 170, top: 12, right: 14, bottom: 28, left: 52 }
const BAR_BOX = { width: 320, height: 150, top: 10, right: 6, bottom: 24, left: 52 }

function formatDate(dateKey: string) {
  return new Date(`${dateKey}T00:00:00`).toLocaleDateString(getLanguage(), { day: 'numeric', month: 'short' })
}

export function PriceLineChart({ points }: { points: PriceHistoryPoint[] }) {
  if (points.length === 0) return <p className="rounded-xl bg-muted p-4 text-center text-sm text-text-secondary">{t('Ainda não há preços registados.')}</p>
  const { mode, unit, values } = seriesValues(points)
  const chart = buildLineChart(points.map((point, index) => ({ date: point.purchased_on, value: values[index] })), LINE_BOX)
  const valueLabel = (value: number) => mode === 'unit' && unit ? `${formatMoney(value)}/${unit}` : formatMoney(value)
  const title = mode === 'unit' && unit ? t('Preço por {unit}', { unit }) : t('Preço pago')
  const first = chart.coords[0]
  const last = chart.coords[chart.coords.length - 1]
  const lowest = Math.min(...values)
  const highest = Math.max(...values)
  const summary = t('{title}: {count} compra(s) entre {from} e {to}; de {min} a {max}, último {last}.', { title, count: points.length, from: formatDate(first.date), to: formatDate(last.date), min: valueLabel(lowest), max: valueLabel(highest), last: valueLabel(last.value) })
  return (
    <figure>
      <figcaption className="text-xs font-semibold text-text-secondary">{title}</figcaption>
      <svg viewBox={`0 0 ${LINE_BOX.width} ${LINE_BOX.height}`} width="100%" role="img" aria-label={summary} className="mt-1 block overflow-visible">
        {chart.ticks.map((tick) => <g key={tick.value}><line x1={LINE_BOX.left} x2={LINE_BOX.width - LINE_BOX.right} y1={tick.y} y2={tick.y} className="stroke-border" strokeWidth={tick.value === 0 ? 1 : 0.6} /><text x={LINE_BOX.left - 6} y={tick.y} dy="0.32em" textAnchor="end" className="fill-text-secondary text-[9px]">{formatMoney(tick.value)}</text></g>)}
        <text x={first.x} y={LINE_BOX.height - 8} textAnchor={chart.coords.length > 1 ? 'start' : 'middle'} className="fill-text-secondary text-[9px]">{formatDate(first.date)}</text>
        {chart.coords.length > 1 && <text x={last.x} y={LINE_BOX.height - 8} textAnchor="end" className="fill-text-secondary text-[9px]">{formatDate(last.date)}</text>}
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
  const chart = buildBarChart(totals, BAR_BOX)
  const current = totals[totals.length - 1]
  const summary = t('Gastos por mês nos últimos {count} meses: total {total}; este mês {current}.', { count: totals.length, total: formatMoney(sum), current: formatMoney(current.total) })
  return (
    <figure className="mt-2">
      <svg viewBox={`0 0 ${BAR_BOX.width} ${BAR_BOX.height}`} width="100%" role="img" aria-label={summary} className="block overflow-visible">
        {chart.ticks.map((tick) => <g key={tick.value}><line x1={BAR_BOX.left} x2={BAR_BOX.width - BAR_BOX.right} y1={tick.y} y2={tick.y} className="stroke-border" strokeWidth={tick.value === 0 ? 1 : 0.6} /><text x={BAR_BOX.left - 6} y={tick.y} dy="0.32em" textAnchor="end" className="fill-text-secondary text-[9px]">{formatMoney(tick.value)}</text></g>)}
        {chart.bars.map((bar, index) => <g key={bar.month}>{bar.height > 0 && <rect x={bar.x} y={bar.y} width={bar.width} height={bar.height} rx={Math.min(3, bar.height / 2)} className={index === chart.bars.length - 1 ? 'fill-primary-forest' : 'fill-primary-forest/60'} />}<rect x={bar.x - 2} y={BAR_BOX.top} width={bar.width + 4} height={BAR_BOX.height - BAR_BOX.top - BAR_BOX.bottom} fill="transparent"><title>{`${monthLabel(bar.month)}: ${formatMoney(bar.total)}`}</title></rect><text x={bar.x + bar.width / 2} y={BAR_BOX.height - 8} textAnchor="middle" className="fill-text-secondary text-[9px]">{monthLabel(bar.month)}</text></g>)}
      </svg>
      <table className="sr-only"><caption>{t('Gastos por mês')}</caption><thead><tr><th scope="col">{t('Mês')}</th><th scope="col">{t('Total')}</th></tr></thead><tbody>{totals.map((entry) => <tr key={entry.month}><td>{entry.month}</td><td>{formatMoney(entry.total)}</td></tr>)}</tbody></table>
    </figure>
  )
}
