/** Цвета и размеры — те же, что у сайта plonk.rs (styles.css), чтобы приложение выглядело как одна семья. */
import { Appearance } from 'react-native'

/**
 * Тёмная тема — как в системе телефона. Стили собираются один раз при запуске, поэтому при смене темы
 * в системе приложение перезапускается само (_layout.tsx).
 */
export const isDark = Appearance.getColorScheme() === 'dark'

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
  inverse: '#0F1512', // фон «тёмных» кнопок; в тёмной теме — светлый
  onInverse: '#FFFFFF',
  tile: '#ECEBE6', // плитки разделов с картинками
  onTile: '#0F1512',
  danger: '#B42318',
  dangerBg: '#FDECEA',
}
type Palette = { [K in keyof typeof light]: string }
const dark: Palette = {
  bg: '#0D100F',
  surface: '#161A18',
  sunken: '#1F2421',
  ink: '#EEF2EF',
  inkSoft: '#BFC7C1',
  muted: '#87908A',
  border: 'rgba(255,255,255,0.08)',
  primary: '#1FBF7C',
  primaryDeep: '#7BE3B5',
  primarySoft: '#123326',
  accent: '#FF6A3D',
  accentSoft: '#3A1F16',
  gold: '#D9A857',
  goldDark: '#E9C46A',
  warmBg: '#2C2414',
  photo: '#1F2421',
  lime: '#D9F45C',
  inverse: '#EEF2EF',
  onInverse: '#0D100F',
  tile: '#E9E8E3', // картинки разделов нарисованы на светлом — плитки светлые и в тёмной теме
  onTile: '#0F1512',
  danger: '#FF8A80',
  dangerBg: '#3A1A18',
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

