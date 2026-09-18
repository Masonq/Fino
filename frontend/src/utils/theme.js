// Тема оформления: светлая, тёмная или как в системе.
//
// Значение хранится в localStorage и применяется атрибутом data-theme на
// <html> — тем же, что ставит маленький скрипт в index.html до первой
// отрисовки. Здесь только переключение уже на живой странице.
export const THEMES = ['auto', 'light', 'dark']
const KEY = 'plonk_theme'

export function storedTheme() {
  try { return localStorage.getItem(KEY) || 'auto' } catch { return 'auto' }
}

export function isDark(theme) {
  if (theme === 'dark') return true
  if (theme === 'light') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

export function applyTheme(theme) {
  const dark = isDark(theme)
  const root = document.documentElement
  root.setAttribute('data-theme', dark ? 'dark' : 'light')
  // Цвет полей по бокам на широком экране и цвет полосы состояния —
  // они живут вне переменных темы: первый на <html>, второй в мете,
  // которую читает система.
  root.style.setProperty('--page-edge', dark ? '#0E1011' : '#E7E7E2')
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', dark ? '#15181A' : '#FAFAF9')
  try { localStorage.setItem(KEY, theme) } catch { /* приватный режим */ }
}

// Пока выбрано «как в системе», следим за системной настройкой: человек
// переключил тему на телефоне — сайт меняется сразу, без перезагрузки.
export function watchSystemTheme() {
  const mq = window.matchMedia('(prefers-color-scheme: dark)')
  const onChange = () => { if (storedTheme() === 'auto') applyTheme('auto') }
  mq.addEventListener('change', onChange)
  return () => mq.removeEventListener('change', onChange)
}
