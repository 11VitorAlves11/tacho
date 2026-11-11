import { t, getLanguage } from '../i18n'
import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  bulkCreatePantryItems,
  createPantryItem,
  deletePantryItem,
  getPriceHistory,
  importPantryFromReceipt,
  listPantryItems,
  readReceipt,
  setPantryItemHasIt,
  updatePantryItem,
} from '../api/pantry'
import type { PantryItem, PantryPriceHistory, ReceiptConfirmResult, ReceiptExtraction } from '../api/types'
import { PageShell } from '../components/PageShell'
import { CameraIcon, EuroIcon, PencilIcon, PlusIcon, TrashIcon } from '../components/icons'
import { Modal } from '../components/ui'
import { PantryPricePanel } from '../components/PantryPrices'
import { MonthlySpendChart } from '../components/PriceCharts'
import { ReceiptReview } from '../components/ReceiptReview'
import { expiryStatus, type ExpiryTone } from '../lib/date'
import { fillMonths, lastPriceLabel } from '../lib/prices'

const SPEND_MONTHS = 12

export function Pantry() {
  const [today] = useState(() => new Date())
  const [items, setItems] = useState<PantryItem[] | null>(null)
  const [error, setError] = useState(false)
  const [newName, setNewName] = useState('')
  const [newQuantity, setNewQuantity] = useState('')
  const [newUnit, setNewUnit] = useState('')
  const [newExpiry, setNewExpiry] = useState('')
  const [creating, setCreating] = useState(false)
  const [editingItem, setEditingItem] = useState<PantryItem | null>(null)
  const [pricingItem, setPricingItem] = useState<PantryItem | null>(null)
  const [history, setHistory] = useState<PantryPriceHistory | null>(null)
  const pricedReceiptInputRef = useRef<HTMLInputElement>(null)
  const [readingPrices, setReadingPrices] = useState(false)
  const [receiptDraft, setReceiptDraft] = useState<ReceiptExtraction | null>(null)
  const [receiptSummary, setReceiptSummary] = useState('')

  const receiptInputRef = useRef<HTMLInputElement>(null)
  const [scanning, setScanning] = useState(false)
  const [scanError, setScanError] = useState('')
  // null enquanto não há rascunho nenhum; um Set (mesmo vazio) assim que a
  // fatura foi lida — controla se o cartão de confirmação aparece.
  const [draftNames, setDraftNames] = useState<string[] | null>(null)
  const [checkedNames, setCheckedNames] = useState<Set<string>>(new Set())
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    listPantryItems().then(setItems).catch(() => setError(true))
    getPriceHistory(SPEND_MONTHS).then(setHistory).catch(() => setHistory(null))
  }, [])

  // Depois de registar/apagar preços: a última compra de cada linha e os
  // gastos mensais vêm do backend, por isso recarrega-se em vez de fundir à mão.
  async function refreshPrices() {
    const [nextItems, nextHistory] = await Promise.all([listPantryItems(), getPriceHistory(SPEND_MONTHS)])
    setItems(nextItems)
    setHistory(nextHistory)
  }

  async function handleReceiptFileChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setScanning(true)
    setScanError('')
    setDraftNames(null)
    try {
      const { items: names } = await importPantryFromReceipt(file)
      setDraftNames(names)
      setCheckedNames(new Set(names))
    } catch (err) {
      setScanError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          t('Não foi possível ler esta fatura.'),
      )
    } finally {
      setScanning(false)
    }
  }

  async function handlePricedReceiptChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setReadingPrices(true)
    setScanError('')
    setReceiptSummary('')
    try {
      setReceiptDraft(await readReceipt(file))
    } catch (err) {
      setScanError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          t('Não foi possível ler esta fatura.'),
      )
    } finally {
      setReadingPrices(false)
    }
  }

  async function handleReceiptConfirmed(result: ReceiptConfirmResult) {
    setReceiptDraft(null)
    setReceiptSummary(t('{items} produto(s) atualizados na despensa e {prices} preço(s) registados.', { items: result.items.length, prices: result.price_entries_created }))
    await refreshPrices()
  }

  function toggleDraftName(name: string) {
    setCheckedNames((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  async function handleConfirmDraft() {
    if (checkedNames.size === 0 || confirming) return
    setConfirming(true)
    try {
      // bulk_upsert_pantry_items devolve tanto os itens novos como os que já
      // existiam (agora com has_it=true) — mais simples e correto recarregar
      // a lista toda (já ordenada pelo backend) do que tentar fundir à mão.
      await bulkCreatePantryItems([...checkedNames])
      setItems(await listPantryItems())
      setDraftNames(null)
      setCheckedNames(new Set())
    } finally {
      setConfirming(false)
    }
  }

  function handleDismissDraft() {
    setDraftNames(null)
    setCheckedNames(new Set())
    setScanError('')
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    const name = newName.trim()
    if (!name || creating) return
    setCreating(true)
    try {
      const item = await createPantryItem({ name, quantity: newQuantity ? Number(newQuantity) : null, unit: newUnit.trim() || null, expires_on: newExpiry || null })
      setItems((prev) => [...(prev ?? []), item])
      setNewName('')
      setNewQuantity('')
      setNewUnit('')
      setNewExpiry('')
    } finally {
      setCreating(false)
    }
  }

  async function handleToggle(item: PantryItem) {
    const updated = await setPantryItemHasIt(item.id, !item.has_it)
    setItems((prev) => prev?.map((i) => (i.id === item.id ? updated : i)) ?? prev)
  }

  async function handleDelete(id: string) {
    await deletePantryItem(id)
    setItems((prev) => prev?.filter((i) => i.id !== id) ?? prev)
  }

  function handleEdited(updated: PantryItem) {
    setItems((current) => current?.map((item) => item.id === updated.id ? updated : item) ?? current)
    setEditingItem(null)
  }

  return (
    <PageShell>
      <Link to="/lista-compras" className="text-sm font-medium text-forest-text">
        {t('← Lista de Compras')}
      </Link>
      <h1 className="mt-1 text-2xl font-bold text-text-primary sm:text-3xl">{t('Despensa')}</h1>
      <p className="mt-1 text-sm text-text-secondary">
        {t('Marca o que tens em casa — usado no filtro "Dá para fazer" das receitas.')}
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => receiptInputRef.current?.click()}
          disabled={scanning}
          className="flex items-center gap-1.5 rounded-full bg-surface px-4 py-2 text-sm font-medium text-forest-text shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)] transition-opacity disabled:opacity-60"
        >
          <CameraIcon className="size-4" />
          {scanning ? t('A ler a fatura…') : t('Ler fatura do supermercado')}
        </button>
        <input
          ref={receiptInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleReceiptFileChange}
          className="hidden"
        />
        <button type="button" onClick={() => pricedReceiptInputRef.current?.click()} disabled={readingPrices} className="flex items-center gap-1.5 rounded-full bg-surface px-4 py-2 text-sm font-medium text-forest-text shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)] transition-opacity disabled:opacity-60"><CameraIcon className="size-4" />{readingPrices ? t('A ler a fatura…') : t('Ler fatura com preços')}</button>
        <input ref={pricedReceiptInputRef} type="file" accept="image/jpeg,image/png,image/webp" onChange={handlePricedReceiptChange} className="hidden" aria-label={t('Ler fatura com preços')} />
      </div>
      {scanError && <p role="alert" className="mt-2 text-sm text-accent-orange">{scanError}</p>}
      {receiptSummary && <p role="status" className="mt-2 text-sm font-medium text-forest-text">{receiptSummary}</p>}

      {draftNames && (
        <div className="mt-4 rounded-2xl bg-surface p-4 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
          {draftNames.length === 0 ? (
            <p className="text-sm text-text-secondary">
              {t('Não foi possível reconhecer artigos nesta fatura. Tenta outra foto, com boa luz e a fatura inteira enquadrada.')}
            </p>
          ) : (
            <>
              <p className="text-sm font-medium text-text-primary">
                {t('Reconhecidos')} {draftNames.length} {t('artigo(s) — confirma antes de adicionar à despensa.')}
              </p>
              <ul className="mt-3 flex flex-wrap gap-2">
                {draftNames.map((name) => (
                  <li key={name}>
                    <label
                      className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm transition-colors ${
                        checkedNames.has(name)
                          ? 'bg-accent-leaf/15 text-forest-text'
                          : 'bg-bg-sage text-text-secondary line-through'
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={checkedNames.has(name)}
                        onChange={() => toggleDraftName(name)}
                        className="size-4 accent-accent-leaf"
                      />
                      {name}
                    </label>
                  </li>
                ))}
              </ul>
              <div className="mt-4 flex gap-2">
                <button
                  type="button"
                  onClick={handleConfirmDraft}
                  disabled={checkedNames.size === 0 || confirming}
                  className="flex-1 rounded-full bg-primary-forest py-2.5 text-sm font-semibold text-card-white transition-opacity disabled:opacity-60"
                >
                  {confirming ? t('A adicionar…') : t('Adicionar {count} à despensa', { count: checkedNames.size })}
                </button>
                <button
                  type="button"
                  onClick={handleDismissDraft}
                  className="rounded-full bg-bg-sage px-4 py-2.5 text-sm font-medium text-text-secondary"
                >
                  {t('Cancelar')}
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {error && <p className="mt-4 text-sm text-text-secondary">{t('Não foi possível ligar ao backend.')}</p>}

      {items && items.length === 0 && (
        <div className="mt-4 rounded-2xl bg-surface p-8 text-center">
          <p className="font-medium text-text-primary">{t('A despensa está vazia.')}</p>
          <p className="mt-1 text-sm text-text-secondary">{t('Adiciona os ingredientes que costumas ter em casa.')}</p>
        </div>
      )}

      {items && items.length > 0 && (
        <ul className="mt-4 space-y-2">
          {items.map((item) => (
            <li key={item.id} className="flex items-center gap-2 rounded-xl bg-surface p-3 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
              <label className="flex min-w-0 flex-1 items-start gap-3">
                <input type="checkbox" checked={item.has_it} onChange={() => handleToggle(item)} className="mt-0.5 size-5 shrink-0 accent-accent-leaf" />
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-x-2 gap-y-1"><span className={`max-w-full truncate text-sm font-medium ${item.has_it ? 'text-text-primary' : 'text-text-secondary line-through'}`}>{item.name}</span><PantryItemBadges item={item} today={today} /></span>
                  <PantryItemMeta item={item} />
                </span>
              </label>
              <div className="flex shrink-0 items-center">
                <button type="button" onClick={() => setPricingItem(item)} aria-label={t('Preços de {name}', { name: item.name })} className={ROW_ACTION_CLASS}><EuroIcon className="size-4" /><span className="hidden sm:inline">{t('Preços')}</span></button>
                <button type="button" onClick={() => setEditingItem(item)} aria-label={t('Editar {name}', { name: item.name })} className={ROW_ACTION_CLASS}><PencilIcon className="size-4" /><span className="hidden sm:inline">{t('Editar')}</span></button>
                <button type="button" onClick={() => handleDelete(item.id)} aria-label={t('Remover {name} da despensa', { name: item.name })} className={`${ROW_ACTION_CLASS} text-text-secondary`}><TrashIcon className="size-4" /><span className="hidden sm:inline">{t('Remover')}</span></button>
              </div>
            </li>
          ))}
        </ul>
      )}

      {items && items.length > 0 && history && (
        <section aria-labelledby="monthly-spend-title" className="mt-6 rounded-2xl border border-border bg-surface p-4">
          <h2 id="monthly-spend-title" className="text-sm font-semibold text-text-primary">{t('Gastos por mês')}</h2>
          <MonthlySpendChart totals={fillMonths(history.monthly_totals, SPEND_MONTHS, today)} />
        </section>
      )}

      <form onSubmit={handleCreate} className="mt-6 grid gap-2 rounded-2xl border border-border bg-surface p-4 sm:grid-cols-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder={t('Adicionar ingrediente…')}
          className="min-h-11 min-w-0 rounded-xl border border-border bg-muted px-3 py-2 text-sm outline-none focus:border-accent-leaf"
        />
        <div className="grid grid-cols-2 gap-2"><input type="number" min="0" step="0.01" value={newQuantity} onChange={(event) => setNewQuantity(event.target.value)} placeholder={t('Quantidade')} className="min-h-11 min-w-0 rounded-xl border border-border bg-muted px-3 text-sm outline-none" /><input value={newUnit} onChange={(event) => setNewUnit(event.target.value)} placeholder={t('Unidade')} className="min-h-11 min-w-0 rounded-xl border border-border bg-muted px-3 text-sm outline-none" /></div>
        <input type="date" value={newExpiry} onChange={(event) => setNewExpiry(event.target.value)} aria-label={t('Data de validade')} className="min-h-11 rounded-xl border border-border bg-muted px-3 text-sm text-text-primary outline-none" />
        <button
          type="submit"
          disabled={!newName.trim() || creating}
          className="flex min-h-11 shrink-0 items-center justify-center gap-1 rounded-xl bg-primary-forest px-4 py-2 text-sm font-medium text-card-white disabled:opacity-50"
        >
          <PlusIcon className="size-4" />
          {t('Adicionar')}
        </button>
      </form>
      <Modal open={editingItem !== null} title={t('Editar produto')} onClose={() => setEditingItem(null)}>{editingItem && <PantryEditor item={editingItem} onSaved={handleEdited} />}</Modal>
      <Modal open={receiptDraft !== null} title={t('Rever fatura')} onClose={() => setReceiptDraft(null)}>{receiptDraft && <ReceiptReview draft={receiptDraft} onCancel={() => setReceiptDraft(null)} onConfirmed={handleReceiptConfirmed} />}</Modal>
      <Modal open={pricingItem !== null} title={pricingItem ? t('Preços: {name}', { name: pricingItem.name }) : ''} onClose={() => setPricingItem(null)}>{pricingItem && <PantryPricePanel item={pricingItem} onChanged={refreshPrices} />}</Modal>
    </PageShell>
  )
}

const ROW_ACTION_CLASS = 'flex min-h-9 min-w-9 items-center justify-center gap-1.5 rounded-lg px-2 text-xs font-semibold text-forest-text hover:bg-primary-soft'
const BADGE_CLASS = 'rounded-full px-2 py-0.5 text-[11px] font-semibold leading-4'
const EXPIRY_BADGE_CLASS: Record<ExpiryTone, string> = {
  expired: 'bg-danger/12 text-danger-text',
  soon: 'bg-accent-orange/12 text-warning-text',
  later: 'bg-muted font-medium text-text-secondary',
}

function PantryItemBadges({ item, today }: { item: PantryItem; today: Date }) {
  const lowStock = item.quantity !== null && item.minimum_quantity !== null && item.quantity <= item.minimum_quantity
  const expiry = item.expires_on ? expiryStatus(item.expires_on, today) : null
  return <>{lowStock && <span className={`${BADGE_CLASS} bg-accent-orange/12 text-warning-text`}>{t('Stock baixo')}</span>}{expiry && <span className={`${BADGE_CLASS} ${EXPIRY_BADGE_CLASS[expiry.tone]}`}>{expiry.label}</span>}</>
}

function PantryItemMeta({ item }: { item: PantryItem }) {
  const parts = [item.quantity !== null ? `${item.quantity.toLocaleString(getLanguage())}${item.unit ? ` ${item.unit}` : ''}` : null, item.last_price ? lastPriceLabel(item.last_price) : null].filter(Boolean)
  return parts.length > 0 ? <span className="mt-0.5 block text-xs text-text-secondary">{parts.join(' · ')}</span> : null
}

function PantryEditor({ item, onSaved }: { item: PantryItem; onSaved: (item: PantryItem) => void }) {
  const [name, setName] = useState(item.name)
  const [quantity, setQuantity] = useState(item.quantity?.toString() ?? '')
  const [unit, setUnit] = useState(item.unit ?? '')
  const [expiry, setExpiry] = useState(item.expires_on ?? '')
  const [minimum, setMinimum] = useState(item.minimum_quantity?.toString() ?? '')
  const [saving, setSaving] = useState(false)

  async function save(event: FormEvent) {
    event.preventDefault()
    if (!name.trim()) return
    setSaving(true)
    try {
      onSaved(await updatePantryItem(item.id, { name: name.trim(), quantity: quantity ? Number(quantity) : null, unit: unit.trim() || null, expires_on: expiry || null, minimum_quantity: minimum ? Number(minimum) : null }))
    } finally {
      setSaving(false)
    }
  }

  return <form onSubmit={save} className="space-y-3"><label className="block text-xs font-semibold text-text-secondary">{t('Produto')}<input value={name} onChange={(event) => setName(event.target.value)} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm text-text-primary" /></label><div className="grid grid-cols-2 gap-2"><label className="text-xs font-semibold text-text-secondary">{t('Quantidade')}<input type="number" min="0" step="0.01" value={quantity} onChange={(event) => setQuantity(event.target.value)} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm" /></label><label className="text-xs font-semibold text-text-secondary">{t('Unidade')}<input value={unit} onChange={(event) => setUnit(event.target.value)} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm" /></label></div><label className="block text-xs font-semibold text-text-secondary">{t('Validade')}<input type="date" value={expiry} onChange={(event) => setExpiry(event.target.value)} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm" /></label><label className="block text-xs font-semibold text-text-secondary">{t('Stock mínimo')}<input type="number" min="0" step="0.01" value={minimum} onChange={(event) => setMinimum(event.target.value)} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm" /></label><button disabled={saving} className="min-h-11 w-full rounded-xl bg-primary-forest px-4 text-sm font-semibold text-white disabled:opacity-60">{saving ? t('A guardar…') : t('Guardar alterações')}</button></form>
}
