// Тема сайта: 'auto' — как в системе, 'light' / 'dark' — закреплённая в профиле. Хранится в localStorage,
// ставится на <html data-theme> до первой отрисовки (без вспышки светлой темы).
const KEY = 'plonk_theme'
export const getTheme = () => { try { return localStorage.getItem(KEY) || 'auto' } catch { return 'auto' } }
const isDark = (t) => t === 'dark' || (t === 'auto' && window.matchMedia?.('(prefers-color-scheme: dark)').matches)
export function applyTheme(t = getTheme()) {
  const el = document.documentElement
  if (t === 'auto') el.removeAttribute('data-theme'); else el.setAttribute('data-theme', t)
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', isDark(t) ? '#0D100F' : '#F5F4F0')
}
export function setTheme(t) { try { localStorage.setItem(KEY, t) } catch { /* без хранилища — только до перезагрузки */ } applyTheme(t) }
export function watchSystemTheme() {
  window.matchMedia?.('(prefers-color-scheme: dark)').addEventListener?.('change', () => { if (getTheme() === 'auto') applyTheme('auto') })
}
