import { useSyncExternalStore } from 'react'
import en from './en.json'

export type Language = 'pt-PT' | 'en'
export const LANGUAGE_KEY = 'tacho:language'
export const LANGUAGE_OPTIONS = [
  { value: 'pt-PT', label: 'Português (Portugal)' },
  { value: 'en', label: 'English' },
] as const

export function readLanguage(): Language {
  try {
    return localStorage.getItem(LANGUAGE_KEY) === 'en' ? 'en' : 'pt-PT'
  } catch {
    return 'pt-PT'
  }
}

let language = readLanguage()
const listeners = new Set<() => void>()

export function getLanguage(): Language {
  return language
}

export function setLanguage(next: Language) {
  language = next === 'en' ? 'en' : 'pt-PT'
  document.documentElement.lang = language
  try {
    localStorage.setItem(LANGUAGE_KEY, language)
  } catch {
    // The current session still works when browser storage is unavailable.
  }
  listeners.forEach((listener) => listener())
}

function subscribe(listener: () => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

export function useLanguage() {
  return useSyncExternalStore(subscribe, getLanguage, () => 'pt-PT' as Language)
}

/** Source strings are the Portuguese fallback; recipe/user data is never translated. */
export function t(source: string, values: Record<string, string | number> = {}): string {
  const message = language === 'en' ? (en as Record<string, string>)[source] ?? source : source
  return message.replace(/\{(\w+)\}/g, (match, key: string) => String(values[key] ?? match))
}

if (typeof window !== 'undefined') {
  document.documentElement.lang = language
  window.addEventListener('storage', (event) => {
    if (event.key === LANGUAGE_KEY || event.key === null) {
      language = readLanguage()
      document.documentElement.lang = language
      listeners.forEach((listener) => listener())
    }
  })
}
