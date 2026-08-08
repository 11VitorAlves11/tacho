const KEY = 'tacho:theme'

export type Theme = 'light' | 'dark' | 'system'

export function getStoredTheme(): Theme {
  const v = localStorage.getItem(KEY)
  return v === 'light' || v === 'dark' ? v : 'system'
}

// 'system' remove o atributo — o CSS segue prefers-color-scheme sozinho.
export function applyTheme(theme: Theme) {
  if (theme === 'system') {
    delete document.documentElement.dataset.theme
    localStorage.removeItem(KEY)
  } else {
    document.documentElement.dataset.theme = theme
    localStorage.setItem(KEY, theme)
  }
}
