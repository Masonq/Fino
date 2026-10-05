import { Appearance } from 'react-native'

import { prefs } from './prefs'

/**
 * Тема приложения: 'auto' — как в системе, 'light' / 'dark' — закреплённая в профиле. Выбор хранится в настройках;
 * при запуске ставится через Appearance.setColorScheme — если тема от этого меняется, приложение перезапускается
 * (стили собираются под тему один раз), и дальше открывается уже в нужной.
 */
export type ThemePref = 'auto' | 'light' | 'dark'
const KEY = 'plonk_theme'

export async function getThemePref(): Promise<ThemePref> {
  const v = await prefs.get(KEY)
  return v === 'light' || v === 'dark' ? v : 'auto'
}

export function applyThemePref(p: ThemePref) {
  Appearance.setColorScheme(p === 'auto' ? 'unspecified' : p)
}

export async function setThemePref(p: ThemePref) {
  await prefs.set(KEY, p)
  applyThemePref(p)
}
