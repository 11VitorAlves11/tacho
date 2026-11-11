import { t } from '../i18n'
import { useState, type FormEvent } from 'react'
import { confirmReceipt } from '../api/pantry'
import type { ReceiptConfirmResult, ReceiptExtraction } from '../api/types'
import { toDateKey } from '../lib/date'
import { formatMoney } from '../lib/prices'
import { XIcon } from './icons'

interface DraftLine {
  key: number
  name: string
  quantity: string
  unit: string
  price: string
}

const fieldClass = 'min-h-10 w-full min-w-0 rounded-lg border border-border bg-surface px-2 text-sm text-text-primary'
const toNumber = (value: string) => (value.trim() === '' ? null : Number(value))

/** Rascunho lido pelo Gemini: nada é gravado até o utilizador confirmar as linhas revistas. */
export function ReceiptReview({ draft, onCancel, onConfirmed }: { draft: ReceiptExtraction; onCancel: () => void; onConfirmed: (result: ReceiptConfirmResult) => void }) {
  const [store, setStore] = useState(draft.store ?? '')
  const [purchasedOn, setPurchasedOn] = useState(draft.purchased_on ?? toDateKey(new Date()))
  const [lines, setLines] = useState<DraftLine[]>(() => draft.items.map((line, key) => ({ key, name: line.name, quantity: line.quantity?.toString() ?? '', unit: line.unit ?? '', price: line.price?.toString() ?? '' })))
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  function updateLine(key: number, patch: Partial<DraftLine>) {
    setLines((current) => current.map((line) => (line.key === key ? { ...line, ...patch } : line)))
  }

  const validLines = lines.filter((line) => line.name.trim())
  const total = validLines.reduce((sum, line) => sum + (toNumber(line.price) ?? 0), 0)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (validLines.length === 0 || saving) return
    setSaving(true)
    setError('')
    try {
      onConfirmed(await confirmReceipt({ store: store.trim() || null, purchased_on: purchasedOn || null, items: validLines.map((line) => ({ name: line.name.trim(), quantity: toNumber(line.quantity), unit: line.unit.trim() || null, price: toNumber(line.price) })) }))
    } catch (err) {
      setError((err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? t('Não foi possível guardar a fatura.'))
    } finally {
      setSaving(false)
    }
  }

  if (draft.items.length === 0) {
    return <div className="space-y-4"><p className="text-sm text-text-secondary">{t('Não foi possível reconhecer artigos nesta fatura. Tenta outra foto, com boa luz e a fatura inteira enquadrada.')}</p><button type="button" onClick={onCancel} className="min-h-11 w-full rounded-xl bg-bg-sage px-4 text-sm font-medium text-text-secondary">{t('Fechar')}</button></div>
  }

  return (
    <form onSubmit={submit} className="max-h-[70svh] space-y-3 overflow-y-auto">
      <p className="text-sm text-text-secondary">{t('Revê as linhas antes de guardar — corrige nomes, quantidades e preços ou remove o que não interessa.')}</p>
      <div className="grid grid-cols-2 gap-2">
        <label className="text-xs font-semibold text-text-secondary">{t('Loja')}<input value={store} onChange={(event) => setStore(event.target.value)} placeholder={t('Opcional')} className={`mt-1 ${fieldClass}`} /></label>
        <label className="text-xs font-semibold text-text-secondary">{t('Data')}<input type="date" max={toDateKey(new Date())} value={purchasedOn} onChange={(event) => setPurchasedOn(event.target.value)} className={`mt-1 ${fieldClass}`} /></label>
      </div>
      <ul className="space-y-2">
        {lines.map((line, index) => (
          <li key={line.key} className="rounded-xl border border-border p-2">
            <div className="flex items-center gap-2"><input value={line.name} onChange={(event) => updateLine(line.key, { name: event.target.value })} aria-label={t('Produto da linha {n}', { n: index + 1 })} className={fieldClass} /><button type="button" onClick={() => setLines((current) => current.filter((candidate) => candidate.key !== line.key))} aria-label={t('Remover {name}', { name: line.name || t('linha {n}', { n: index + 1 }) })} className="shrink-0 rounded-full p-1.5 text-text-secondary hover:bg-muted"><XIcon className="size-4" /></button></div>
            <div className="mt-2 grid grid-cols-3 gap-2">
              <label className="text-[11px] font-semibold text-text-secondary">{t('Quantidade')}<input type="number" inputMode="decimal" min="0" step="0.01" value={line.quantity} onChange={(event) => updateLine(line.key, { quantity: event.target.value })} className={`mt-0.5 ${fieldClass}`} /></label>
              <label className="text-[11px] font-semibold text-text-secondary">{t('Unidade')}<input value={line.unit} onChange={(event) => updateLine(line.key, { unit: event.target.value })} className={`mt-0.5 ${fieldClass}`} /></label>
              <label className="text-[11px] font-semibold text-text-secondary">{t('Preço (€)')}<input type="number" inputMode="decimal" min="0" step="0.01" value={line.price} onChange={(event) => updateLine(line.key, { price: event.target.value })} className={`mt-0.5 ${fieldClass}`} /></label>
            </div>
          </li>
        ))}
      </ul>
      <p className="text-sm font-medium text-text-primary">{t('Total: {total}', { total: formatMoney(total) })}</p>
      {error && <p role="alert" className="text-sm text-accent-orange">{error}</p>}
      <div className="flex gap-2">
        <button disabled={validLines.length === 0 || saving} className="min-h-11 flex-1 rounded-xl bg-primary-forest px-4 text-sm font-semibold text-white disabled:opacity-60">{saving ? t('A guardar…') : t('Guardar {count} artigo(s)', { count: validLines.length })}</button>
        <button type="button" onClick={onCancel} className="min-h-11 rounded-xl bg-bg-sage px-4 text-sm font-medium text-text-secondary">{t('Cancelar')}</button>
      </div>
    </form>
  )
}
