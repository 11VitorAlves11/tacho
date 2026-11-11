import { t, getLanguage } from '../i18n'
import { useEffect, useState, type FormEvent } from 'react'
import { createPriceEntry, deletePriceEntry, listPriceEntries } from '../api/pantry'
import type { PantryItem, PantryPriceEntry } from '../api/types'
import { formatDateKey, toDateKey } from '../lib/date'
import { lastPriceLabel } from '../lib/prices'
import { XIcon } from './icons'
import { PriceLineChart } from './PriceCharts'

const inputClass = 'mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary'

export function PantryPricePanel({ item, onChanged }: { item: PantryItem; onChanged: () => void }) {
  const [entries, setEntries] = useState<PantryPriceEntry[] | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [price, setPrice] = useState('')
  const [quantity, setQuantity] = useState(item.quantity?.toString() ?? '')
  const [unit, setUnit] = useState(item.unit ?? '')
  const [store, setStore] = useState(item.last_price?.store ?? '')
  const [purchasedOn, setPurchasedOn] = useState(() => toDateKey(new Date()))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    listPriceEntries(item.id).then(setEntries).catch(() => setLoadError(true))
  }, [item.id])

  async function save(event: FormEvent) {
    event.preventDefault()
    if (price === '' || saving) return
    setSaving(true)
    setError('')
    try {
      const entry = await createPriceEntry(item.id, { price: Number(price), quantity: quantity ? Number(quantity) : null, unit: unit.trim() || null, store: store.trim() || null, purchased_on: purchasedOn || null })
      setEntries((current) => [entry, ...(current ?? [])].sort((a, b) => b.purchased_on.localeCompare(a.purchased_on) || b.created_at.localeCompare(a.created_at)))
      setPrice('')
      onChanged()
    } catch (err) {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? t('Não foi possível guardar o preço.'))
    } finally {
      setSaving(false)
    }
  }

  async function remove(entry: PantryPriceEntry) {
    await deletePriceEntry(item.id, entry.id)
    setEntries((current) => current?.filter((candidate) => candidate.id !== entry.id) ?? current)
    onChanged()
  }

  const chartPoints = [...(entries ?? [])].reverse()
  return (
    <div className="max-h-[70svh] space-y-4 overflow-y-auto">
      {loadError && <p className="text-sm text-text-secondary">{t('Não foi possível ligar ao backend.')}</p>}
      {entries && <PriceLineChart points={chartPoints} />}
      <form onSubmit={save} className="grid grid-cols-2 gap-2 rounded-2xl border border-border p-3">
        <p className="col-span-2 text-sm font-semibold text-text-primary">{t('Registar preço')}</p>
        <label className="text-xs font-semibold text-text-secondary">{t('Preço pago (€)')}<input required type="number" inputMode="decimal" min="0" step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} className={inputClass} /></label>
        <label className="text-xs font-semibold text-text-secondary">{t('Data')}<input type="date" max={toDateKey(new Date())} value={purchasedOn} onChange={(event) => setPurchasedOn(event.target.value)} className={inputClass} /></label>
        <label className="text-xs font-semibold text-text-secondary">{t('Quantidade')}<input type="number" inputMode="decimal" min="0" step="0.01" value={quantity} onChange={(event) => setQuantity(event.target.value)} className={inputClass} /></label>
        <label className="text-xs font-semibold text-text-secondary">{t('Unidade')}<input value={unit} onChange={(event) => setUnit(event.target.value)} className={inputClass} /></label>
        <label className="col-span-2 text-xs font-semibold text-text-secondary">{t('Loja')}<input value={store} onChange={(event) => setStore(event.target.value)} placeholder={t('Opcional')} className={inputClass} /></label>
        {error && <p role="alert" className="col-span-2 text-sm text-accent-orange">{error}</p>}
        <button disabled={price === '' || saving} className="col-span-2 min-h-11 rounded-xl bg-primary-forest px-4 text-sm font-semibold text-white disabled:opacity-60">{saving ? t('A guardar…') : t('Guardar preço')}</button>
      </form>
      {entries && entries.length > 0 && (
        <ul className="divide-y divide-border">
          {entries.map((entry) => (
            <li key={entry.id} className="flex items-center gap-2 py-2 text-sm">
              <span className="min-w-0 flex-1"><span className="block font-medium text-text-primary">{lastPriceLabel(entry)}</span><span className="block truncate text-xs text-text-secondary">{formatDateKey(entry.purchased_on)}{entry.quantity !== null && ` · ${entry.quantity.toLocaleString(getLanguage())}${entry.unit ? ` ${entry.unit}` : ''}`}{entry.store && ` · ${entry.store}`}{entry.source === 'receipt' && ` · ${t('fatura')}`}</span></span>
              <button type="button" onClick={() => remove(entry)} aria-label={t('Apagar preço de {date}', { date: formatDateKey(entry.purchased_on) })} className="shrink-0 rounded-full p-1.5 text-text-secondary hover:bg-muted"><XIcon className="size-4" /></button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
