import { useState } from 'react'

export type Theme = 'light' | 'dark'
const KEY = 'sb-theme'

/** The theme on the page now. index.html sets it before the first paint, from the saved choice or the device setting. */
export const currentTheme = (): Theme => (document.documentElement.dataset.theme === 'dark' ? 'dark' : 'light')

export function setTheme(theme: Theme) {
  document.documentElement.dataset.theme = theme
  try { localStorage.setItem(KEY, theme) } catch { /* private mode: the choice lasts for this visit only */ }
}

const Sun = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </svg>
)
const Moon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
  </svg>
)

/** Switches between the light and dark theme and remembers the choice on this browser. */
export function ThemeToggle() {
  const [theme, setLocal] = useState<Theme>(currentTheme)
  const next: Theme = theme === 'dark' ? 'light' : 'dark'
  return (
    <button type="button" className="theme-toggle" aria-label={`Switch to the ${next} theme`} title={`Switch to the ${next} theme`}
      onClick={() => { setTheme(next); setLocal(next) }}>
      {theme === 'dark' ? <Sun /> : <Moon />}
    </button>
  )
}
