import { useEffect, useState, type FormEvent } from 'react'
import { deleteDietaryProfile, listDietaryProfiles, saveDietaryProfile } from '../api/profiles'
import { listWorkspaceMembers } from '../api/auth'
import type { DietaryProfile, WorkspaceMember } from '../api/types'
import { PageShell } from '../components/PageShell'
import { PlusIcon, XIcon } from '../components/icons'

const emptyForm = { name: '', user_id: '', allergies: '', intolerances: '', preferences: '' }
const splitTerms = (value: string) => value.split(',').map((term) => term.trim()).filter(Boolean)

export function DietaryProfiles() {
  const [profiles, setProfiles] = useState<DietaryProfile[]>([])
  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState<string | undefined>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [members, setMembers] = useState<WorkspaceMember[]>([])

  useEffect(() => { listDietaryProfiles().then(setProfiles).catch(() => setError('Não foi possível carregar os perfis.')); listWorkspaceMembers().then(setMembers).catch(() => {}) }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const saved = await saveDietaryProfile({ name: form.name, user_id: form.user_id || null, allergies: splitTerms(form.allergies), intolerances: splitTerms(form.intolerances), preferences: splitTerms(form.preferences) }, editingId)
      setProfiles((current) => [...current.filter((profile) => profile.id !== saved.id), saved].sort((a, b) => a.name.localeCompare(b.name, 'pt-PT')))
      setForm(emptyForm)
      setEditingId(undefined)
    } catch { setError('Não foi possível guardar o perfil.') } finally { setBusy(false) }
  }

  function edit(profile: DietaryProfile) {
    setEditingId(profile.id)
    setForm({ name: profile.name, user_id: profile.user_id ?? '', allergies: profile.allergies.join(', '), intolerances: profile.intolerances.join(', '), preferences: profile.preferences.join(', ') })
  }

  async function remove(profile: DietaryProfile) {
    if (!window.confirm(`Apagar o perfil de ${profile.name}?`)) return
    await deleteDietaryProfile(profile.id)
    setProfiles((current) => current.filter((item) => item.id !== profile.id))
  }

  return <PageShell><div><h1 className="text-2xl font-bold text-text-primary sm:text-3xl">Perfis alimentares</h1><p className="mt-1 text-sm text-text-secondary">Regista riscos e preferências de cada pessoa do agregado.</p></div>
    {error && <p role="alert" className="mt-4 rounded-xl bg-danger/5 p-3 text-sm text-danger">{error}</p>}
    <div className="mt-6 grid gap-5 lg:grid-cols-[1fr_380px]">
      <div className="space-y-3">{profiles.map((profile) => <article key={profile.id} className="rounded-2xl border border-border bg-surface p-4"><div className="flex items-start justify-between gap-3"><div><h2 className="font-bold text-text-primary">{profile.name}</h2><p className="mt-1 text-xs text-text-secondary">Os riscos são sempre mostrados; nunca são ocultados silenciosamente.</p></div><div className="flex gap-1"><button type="button" onClick={() => edit(profile)} className="rounded-lg px-2 py-1 text-xs font-semibold text-forest-text hover:bg-primary-soft">Editar</button><button type="button" onClick={() => remove(profile)} aria-label={`Apagar perfil de ${profile.name}`} className="flex size-8 items-center justify-center rounded-lg text-text-secondary hover:bg-muted"><XIcon className="size-4" /></button></div></div><ProfileTerms label="Alergias" terms={profile.allergies} danger /><ProfileTerms label="Intolerâncias" terms={profile.intolerances} danger /><ProfileTerms label="Preferências" terms={profile.preferences} /></article>)}{profiles.length === 0 && <div className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-text-secondary">Ainda não existem perfis alimentares.</div>}</div>
      <form onSubmit={submit} className="h-fit rounded-2xl border border-border bg-surface p-5"><h2 className="font-bold text-text-primary">{editingId ? 'Editar perfil' : 'Novo perfil'}</h2><label className="mt-4 block text-sm font-semibold text-text-primary">Nome<input required value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 font-normal" /></label><label className="mt-4 block text-sm font-semibold text-text-primary">Membro do agregado<select value={form.user_id} onChange={(event) => setForm({ ...form, user_id: event.target.value })} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 text-sm font-normal"><option value="">Sem associação</option>{members.map((member) => <option key={member.id} value={member.id}>{member.name ?? member.email}</option>)}</select></label><TermInput label="Alergias" value={form.allergies} onChange={(value) => setForm({ ...form, allergies: value })} placeholder="ex.: amendoim, marisco" /><TermInput label="Intolerâncias" value={form.intolerances} onChange={(value) => setForm({ ...form, intolerances: value })} placeholder="ex.: lactose, glúten" /><TermInput label="Preferências" value={form.preferences} onChange={(value) => setForm({ ...form, preferences: value })} placeholder="ex.: vegetariano, sem carne" /><p className="mt-2 text-xs text-text-secondary">Separa vários termos por vírgulas.</p><div className="mt-5 flex gap-2"><button disabled={busy} className="flex min-h-11 flex-1 items-center justify-center gap-2 rounded-xl bg-primary-forest px-4 text-sm font-semibold text-white disabled:opacity-50"><PlusIcon className="size-4" />{busy ? 'A guardar…' : 'Guardar perfil'}</button>{editingId && <button type="button" onClick={() => { setEditingId(undefined); setForm(emptyForm) }} className="rounded-xl border border-border px-3 text-sm font-semibold">Cancelar</button>}</div></form>
    </div></PageShell>
}

function TermInput({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder: string }) { return <label className="mt-4 block text-sm font-semibold text-text-primary">{label}<input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} className="mt-1 min-h-11 w-full rounded-xl border border-border bg-surface px-3 font-normal" /></label> }
function ProfileTerms({ label, terms, danger = false }: { label: string; terms: string[]; danger?: boolean }) { if (!terms.length) return null; return <div className="mt-3"><p className="text-xs font-bold uppercase tracking-wide text-text-secondary">{label}</p><div className="mt-1 flex flex-wrap gap-1.5">{terms.map((term) => <span key={term} className={`rounded-full px-2.5 py-1 text-xs font-semibold ${danger ? 'bg-danger/10 text-danger' : 'bg-primary-soft text-forest-text'}`}>{term}</span>)}</div></div> }
