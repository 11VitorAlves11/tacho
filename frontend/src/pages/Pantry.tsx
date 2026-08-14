import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  bulkCreatePantryItems,
  createPantryItem,
  deletePantryItem,
  importPantryFromReceipt,
  listPantryItems,
  setPantryItemHasIt,
} from '../api/pantry'
import type { PantryItem } from '../api/types'
import { PageShell } from '../components/PageShell'
import { CameraIcon, PlusIcon, XIcon } from '../components/icons'

export function Pantry() {
  const [items, setItems] = useState<PantryItem[] | null>(null)
  const [error, setError] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)

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
  }, [])

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
          'Não foi possível ler esta fatura.',
      )
    } finally {
      setScanning(false)
    }
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
      const item = await createPantryItem(name)
      setItems((prev) => [...(prev ?? []), item])
      setNewName('')
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

  return (
    <PageShell>
      <Link to="/lista-compras" className="text-sm font-medium text-forest-text">
        ← Lista de Compras
      </Link>
      <h1 className="mt-1 text-2xl font-bold text-text-primary sm:text-3xl">Despensa</h1>
      <p className="mt-1 text-sm text-text-secondary">
        Marca o que tens em casa — usado no filtro "Dá para fazer" das receitas.
      </p>

      <div className="mt-4">
        <button
          type="button"
          onClick={() => receiptInputRef.current?.click()}
          disabled={scanning}
          className="flex items-center gap-1.5 rounded-full bg-surface px-4 py-2 text-sm font-medium text-forest-text shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)] transition-opacity disabled:opacity-60"
        >
          <CameraIcon className="size-4" />
          {scanning ? 'A ler a fatura…' : 'Ler fatura do supermercado'}
        </button>
        <input
          ref={receiptInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handleReceiptFileChange}
          className="hidden"
        />
        {scanError && <p className="mt-2 text-sm text-accent-orange">{scanError}</p>}
      </div>

      {draftNames && (
        <div className="mt-4 rounded-2xl bg-surface p-4 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]">
          {draftNames.length === 0 ? (
            <p className="text-sm text-text-secondary">
              Não foi possível reconhecer artigos nesta fatura. Tenta outra foto, com boa luz e a fatura inteira
              enquadrada.
            </p>
          ) : (
            <>
              <p className="text-sm font-medium text-text-primary">
                Reconhecidos {draftNames.length} artigo(s) — confirma antes de adicionar à despensa.
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
                  {confirming ? 'A adicionar…' : `Adicionar ${checkedNames.size} à despensa`}
                </button>
                <button
                  type="button"
                  onClick={handleDismissDraft}
                  className="rounded-full bg-bg-sage px-4 py-2.5 text-sm font-medium text-text-secondary"
                >
                  Cancelar
                </button>
              </div>
            </>
          )}
        </div>
      )}

      {error && <p className="mt-4 text-sm text-text-secondary">Não foi possível ligar ao backend.</p>}

      {items && items.length === 0 && (
        <div className="mt-4 rounded-2xl bg-surface p-8 text-center">
          <p className="font-medium text-text-primary">A despensa está vazia.</p>
          <p className="mt-1 text-sm text-text-secondary">Adiciona os ingredientes que costumas ter em casa.</p>
        </div>
      )}

      {items && items.length > 0 && (
        <ul className="mt-4 space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between gap-2 rounded-xl bg-surface p-3 shadow-[0_2px_10px_-2px_rgba(28,43,31,0.12)]"
            >
              <label className="flex min-w-0 flex-1 items-center gap-3">
                <input
                  type="checkbox"
                  checked={item.has_it}
                  onChange={() => handleToggle(item)}
                  className="size-5 shrink-0 accent-accent-leaf"
                />
                <span className={`truncate text-sm ${item.has_it ? 'text-text-primary' : 'text-text-secondary line-through'}`}>
                  {item.name}
                </span>
              </label>
              <button
                type="button"
                onClick={() => handleDelete(item.id)}
                className="shrink-0 rounded-full p-1.5 text-text-secondary hover:bg-bg-sage"
                aria-label={`Remover ${item.name} da despensa`}
              >
                <XIcon className="size-4" />
              </button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={handleCreate} className="mt-6 flex gap-2">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="Adicionar ingrediente…"
          className="min-w-0 flex-1 rounded-xl border border-black/10 bg-bg-sage px-3 py-2 text-sm outline-none ring-2 ring-transparent transition-shadow focus:border-accent-leaf focus:ring-accent-leaf/30"
        />
        <button
          type="submit"
          disabled={!newName.trim() || creating}
          className="flex shrink-0 items-center gap-1 rounded-xl bg-primary-forest px-4 py-2 text-sm font-medium text-card-white disabled:opacity-50"
        >
          <PlusIcon className="size-4" />
          Adicionar
        </button>
      </form>
    </PageShell>
  )
}
