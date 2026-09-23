import { beforeEach, describe, expect, it, vi } from 'vitest'

const storage = new Map<string, string>()
const events = new Map<string, (event: { key: string | null }) => void>()

beforeEach(() => {
  vi.resetModules()
  storage.clear()
  events.clear()
  vi.stubGlobal('localStorage', {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
  })
  vi.stubGlobal('document', { documentElement: { lang: '' } })
  vi.stubGlobal('window', { addEventListener: (name: string, callback: (event: { key: string | null }) => void) => events.set(name, callback) })
})

describe('language preference', () => {
  it('defaults to Portuguese and rejects unsupported stored languages', async () => {
    storage.set('tacho:language', 'invalid')
    const { getLanguage, t } = await import('./index')
    expect(getLanguage()).toBe('pt-PT')
    expect(document.documentElement.lang).toBe('pt-PT')
    expect(t('Receitas')).toBe('Receitas')
  })

  it('persists English, updates accessibility language and restores it on reload', async () => {
    const { setLanguage, t } = await import('./index')
    setLanguage('en')
    expect(t('Receitas')).toBe('Recipes')
    expect(document.documentElement.lang).toBe('en')
    expect(storage.get('tacho:language')).toBe('en')
    expect(t('Remover {name}', { name: 'Arroz $&' })).toBe('Remove Arroz $&')
    expect(t('User-authored recipe')).toBe('User-authored recipe')
    vi.resetModules()
    expect((await import('./index')).getLanguage()).toBe('en')
  })

  it('follows preference changes and storage clearing in another tab', async () => {
    const { getLanguage, setLanguage } = await import('./index')
    setLanguage('en')
    storage.clear()
    events.get('storage')?.({ key: null })
    expect(getLanguage()).toBe('pt-PT')
    expect(document.documentElement.lang).toBe('pt-PT')
  })

  it('allows switching for the session when storage is blocked', async () => {
    vi.stubGlobal('localStorage', { getItem: () => { throw Error('blocked') }, setItem: () => { throw Error('blocked') } })
    const { setLanguage, t } = await import('./index')
    setLanguage('en')
    expect(t('Idioma')).toBe('Language')
  })

  it('localises planner dates without moving the day or changing the Monday week start', async () => {
    const { setLanguage } = await import('./index')
    const { formatDayShort, weekdayLabel, startOfWeek, toDateKey } = await import('../lib/date')
    const date = new Date(2026, 8, 23)
    expect(weekdayLabel(0)).toBe('Segunda')
    setLanguage('en')
    expect(weekdayLabel(0)).toBe('Monday')
    expect(formatDayShort(date)).toContain('Sep')
    expect(toDateKey(startOfWeek(date))).toBe('2026-09-21')
  })
})
