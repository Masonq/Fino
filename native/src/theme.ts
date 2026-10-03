/** Цвета и размеры — те же, что у сайта plonk.rs (styles.css), чтобы приложение выглядело как одна семья. */
export const colors = {
  bg: '#FAFAF9',
  surface: '#FFFFFF',
  sunken: '#F2F2EF',
  ink: '#1C2620',
  inkSoft: '#4B554E',
  muted: '#8D958E',
  border: 'rgba(20,30,25,0.08)',
  primary: '#0E9F6E',
  primaryDeep: '#0B5C42',
  primarySoft: '#E4F6EE',
  accent: '#FF6A3D',
  accentSoft: '#FFEDE6',
  gold: '#D9A857',
  goldDark: '#8A6A1F',
  warmBg: '#FBF3E3',
  photo: '#E9EEE9',
} as const

export const radius = { card: 14, chip: 999, sheet: 22, field: 14 } as const
export const space = { page: 12, gap: 10 } as const

/**
 * Шрифты — как у сайта: Plus Jakarta Sans для текста (начертание по жирности), IBM Plex Mono — для цены
 * в объявлении. Кириллицы в Plus Jakarta Sans нет — телефон сам подставит системный, как Safari на сайте.
 */
export const font = {
  400: 'PlusJakartaSans_400Regular', 500: 'PlusJakartaSans_500Medium', 600: 'PlusJakartaSans_600SemiBold',
  700: 'PlusJakartaSans_700Bold', 800: 'PlusJakartaSans_800ExtraBold',
} as const
export const mono = 'IBMPlexMono_700Bold'

