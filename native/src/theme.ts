/** Цвета и размеры — те же, что у сайта plonk.rs (styles.css), чтобы приложение выглядело как одна семья. */
import { Appearance, Platform } from 'react-native'
import * as SecureStore from 'expo-secure-store'

/**
 * Тема: «светлая» / «тёмная» / «как в системе» — как на сайте. Выбор читается синхронно при запуске (стили
 * собираются один раз), смена в профиле перезапускает приложение, чтобы всё перекрасилось сразу.
 * Тёмная — мягкая, графитово-зелёная, не чёрная.
 */
export function themePref(): 'light' | 'dark' | 'system' {
  try {
    const v = Platform.OS === 'web' ? globalThis.localStorage?.getItem('plonk_theme') : SecureStore.getItem('plonk_theme')
    return v === 'dark' || v === 'system' ? v : 'light'
  } catch { return 'light' }
}
const pref = themePref()
export const isDark = pref === 'dark' || (pref === 'system' && Appearance.getColorScheme() === 'dark')

const light = {
  // PLONK 2.0 — «тёплая бумага», почти чёрные чернила, зелёный бренда ярче; лайм — метка «новое»
  bg: '#F5F4F0',
  surface: '#FFFFFF',
  sunken: '#ECEBE6',
  ink: '#0F1512',
  inkSoft: '#434B46',
  muted: '#7C847E',
  border: 'rgba(15,21,18,0.07)',
  primary: '#0FA36A',
  primaryDeep: '#075C3C',
  primarySoft: '#DDF4E8',
  accent: '#FF5B2E',
  accentSoft: '#FFE9E1',
  gold: '#D9A857',
  goldDark: '#8A6A1F',
  warmBg: '#FBF3E3',
  photo: '#E7E6E0',
  lime: '#D9F45C',
  inverse: '#CDEFE0', // фон «тёмных» кнопок; в тёмной теме — светлый
  onInverse: '#085041',
  tile: '#ECEBE6', // плитки разделов с картинками
  onTile: '#0F1512',
  danger: '#B42318',
  dangerBg: '#FDECEA',
}
type Palette = { [K in keyof typeof light]: string }
const dark: Palette = {
  bg: '#1E2421',
  surface: '#272E2A',
  sunken: '#323A35',
  ink: '#EEF2EF',
  inkSoft: '#C4CCC6',
  muted: '#939D96',
  border: 'rgba(255,255,255,0.08)',
  primary: '#1FBF7C',
  primaryDeep: '#9FE1CB',
  primarySoft: '#24453A',
  accent: '#FF6A3D',
  accentSoft: '#4A3127',
  gold: '#D9A857',
  goldDark: '#E9C46A',
  warmBg: '#3A3222',
  photo: '#323A35',
  lime: '#D9F45C',
  inverse: '#2E5A4B',
  onInverse: '#DFF5EA',
  tile: '#2D3530',
  onTile: '#EEF2EF',
  danger: '#FF8A80',
  dangerBg: '#4A2A2A',
}
export const colors: Palette = isDark ? dark : light

export const radius = { card: 20, chip: 999, sheet: 28, field: 16 } as const
export const space = { page: 16, gap: 12 } as const

/**
 * Шрифты — как у сайта: Plus Jakarta Sans для текста (начертание по жирности), IBM Plex Mono — для цены
 * в объявлении. Кириллицы в Plus Jakarta Sans нет — телефон сам подставит системный, как Safari на сайте.
 */
export const font = {
  400: 'Onest_400Regular', 500: 'Onest_500Medium', 600: 'Onest_600SemiBold',
  700: 'Onest_700Bold', 800: 'Onest_800ExtraBold',
} as const
export const mono = 'Onest_800ExtraBold' // цены — тем же шрифтом (Onest), цифры одинаковой ширины


// пастельные подложки (плитки, значки) — в тёмной теме своими тёмными оттенками, а не светлыми пятнами
const DARK_TINT: Record<string, string> = {
  '#E9F5EC': '#1F3328', '#E3ECFA': '#24324A', '#E2F1E6': '#213A2C', '#FAE5EE': '#3E2632', '#FFE8DD': '#43301F',
  '#FFE3D6': '#43301F', '#FFF1C9': '#3D3520', '#EDE7FA': '#2F2A44', '#ECEBE6': '#2F3833',
}
export function tint(hex: string): string { return isDark ? (DARK_TINT[hex.toUpperCase()] ?? DARK_TINT[hex] ?? hex) : hex }
