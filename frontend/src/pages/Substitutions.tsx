import { useEffect, useState, type FormEvent } from 'react'
import { deleteSubstitution, listSubstitutions, saveSubstitution } from '../api/substitutions'
import type { IngredientSubstitution } from '../api/types'
import { PageShell } from '../components/PageShell'
import { XIcon } from '../components/icons'

const emptyForm = { ingredient_name: '', substitute_name: '', quantity_ratio: '', note: '', is_verified: false }

export function Substitutions() {
  const [items, setItems] = useState<IngredientSubstitution[]>([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<string>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { listSubstitutions().then(setItems).catch(() => setError('Não foi possível carregar as substituições.')) }, [])

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const saved = await saveSubstitution({ ingredient_name: form.ingredient_name.trim(), substitute_name: form.substitute_name.trim(), quantity_ratio: form.quantity_ratio ? Number(form.quantity_ratio) : null, note: form.note.trim() || null, is_verified: form.is_verified }, editingId)
      setItems((current) => [...current.filter((item) => item.id !== saved.id), saved].sort((a, b) => a.ingredient_name.localeCompare(b.ingredient_name, 'pt-PT')))
      setForm(emptyForm); setEditingId(undefined)
    } catch { setError('Não foi possível guardar a substituição.') } finally { setBusy(false) }
  }

  function edit(item: IngredientSubstitution) { setEditingId(item.id); setForm({ ingredient_name: item.ingredient_name, substitute_name: item.substitute_name, quantity_ratio: item.quantity_ratio?.toString() ?? '', note: item.note ?? '', is_verified: item.is_verified }) }
  async function remove(id: string) { await deleteSubstitution(id); setItems((current) => current.filter((item) => item.id !== id)) }

  return <PageShell><h1 className="text-2xl font-bold text-text-primary sm:text-3xl">Substituições de ingredientes</h1><p className="mt-1 text-sm text-text-secondary">Alternativas conhecidas aparecem automaticamente quando faltar um ingrediente.</p>{error && <p role="alert" className="mt-4 text-sm text-danger">{error}</p>}<div className="mt-6 grid gap-5 lg:grid-cols-[1fr_380px]"><div className="space-y-3">{items.map((item) => <article key={item.id} className="rounded-2xl border border-border bg-surface p-4"><div className="flex items-start justify-between gap-3"><div><p className="font-bold text-text-primary">{item.ingredient_name} <span className="text-text-secondary">→</span> {item.substitute_name}</p><p className={`mt-1 text-xs font-semibold ${item.is_verified ? 'text-forest-text' : 'text-accent-orange'}`}>{item.is_verified ? 'Alternativa verificada' : 'Sugestão por verificar'}</p></div><div className="flex"><button type="button" onClick={() => edit(item)} className="rounded-lg px-2 text-xs font-semibold text-forest-text">Editar</button><button type="button" onClick={() => remove(item.id)} aria-label="Apagar substituição" className="flex size-8 items-center justify-center text-text-secondary"><XIcon className="size-4" /></button></div></div>{item.quantity_ratio && <p className="mt-2 text-sm text-text-secondary">Usar {item.quantity_ratio}× a quantidade original.</p>}{item.note && <p className="mt-1 text-sm text-text-secondary">{item.note}</p>}</article>)}</div><form onSubmit={submit} className="h-fit rounded-2xl border border-border bg-surface p-5"><h2 className="font-bold text-text-primary">{editingId ? 'Editar alternativa' : 'Nova alternativa'}</h2><Field label="Ingrediente original" value={form.ingredient_name} onChange={(value) => setForm({ ...form, ingredient_name: value })} required /><Field label="Substituto" value={form.substitute_name} onChange={(value) => setForm({ ...form, substitute_name: value })} required /><Field label="Rácio de quantidade" value={form.quantity_ratio} onChange={(value) => setForm({ ...form, quantity_ratio: value })} type="number" placeholder="ex.: 0.5" /><Field label="Notas de utilização" value={form.note} onChange={(value) => setForm({ ...form, note: value })} /><label className="mt-4 flex items-center gap-2 text-sm font-semibold text-text-primary"><input type="checkbox" checked={form.is_verified} onChange={(event) => setForm({ ...form, is_verified: event.target.checked })} className="size-4 accent-primary-forest" />Alternativa verificada</label><div className="mt-5 flex gap-2"><button disabled={busy} className="min-h-11 flex-1 rounded-xl bg-primary-forest px-4 text-sm font-semibold text-white disabled:opacity-50">{busy ? 'A guardar…' : 'Guardar'}</button>{editingId && <button type="button" onClick={() => { setEditingId(undefined); setForm(emptyForm) }} className="rounded-xl border border-border px-3 text-sm font-semibold">Cancelar</button>}</div></form></div></PageShell>
}

function Field({ label, value, onChange, required = false, type = 'text', placeholder }: { label: string; value: string; onChange: (value: string) => void; required?: boolean; type?: string; placeholder?: string }) { return <label className="mt-4 block text-sm font-semibold text-text-primary">{label}<input type={type} step={type === 'number' ? '0.001' : undefined} min={type === 'number' ? '0.001' : undefined} required={required} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 font-normal" /></label> }
